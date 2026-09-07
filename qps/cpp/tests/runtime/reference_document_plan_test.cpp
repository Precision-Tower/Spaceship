#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/execution_engine.hpp"
#include "runtime/h/symbol_resolver.hpp"
#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <unordered_map>
#include <vector>

namespace {

namespace ast = qps::ast;
namespace runtime = qps::runtime;
namespace fs = std::filesystem;

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string readFile(
    const fs::path& path) {

    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error(
            "Could not open authored reference planner: " +
            path.string());
    }

    return std::string(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

std::unique_ptr<ast::ProgramNode>
parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);

    return parser.parseProgram();
}

ast::SymbolReferenceNode reference(
    std::string symbol,
    ast::SymbolReferenceOrigin origin,
    int parent_depth,
    std::vector<ast::SymbolReferenceSegment> segments,
    bool selects_item_value = false) {

    return ast::SymbolReferenceNode(
        std::move(symbol),
        origin,
        parent_depth,
        std::move(segments),
        selects_item_value,
        1,
        1);
}

std::string originName(
    ast::SymbolReferenceOrigin origin) {

    switch (origin) {
        case ast::SymbolReferenceOrigin::CURRENT_FILE:
            return "CURRENT_FILE";

        case ast::SymbolReferenceOrigin::CURRENT_FOLDER_FILE:
            return "CURRENT_FOLDER_FILE";

        case ast::SymbolReferenceOrigin::RELATIVE_MODULE:
            return "RELATIVE_MODULE";

        case ast::SymbolReferenceOrigin::LOCAL_BINDING:
            return "LOCAL_BINDING";
    }

    throw std::runtime_error(
        "Unsupported structural reference origin.");
}

std::string separatorName(
    ast::SymbolReferenceSeparator separator) {

    switch (separator) {
        case ast::SymbolReferenceSeparator::ROOT:
            return "ROOT";

        case ast::SymbolReferenceSeparator::DOT:
            return "DOT";

        case ast::SymbolReferenceSeparator::SLASH:
            return "SLASH";
    }

    throw std::runtime_error(
        "Unsupported structural reference separator.");
}

runtime::RuntimeValue runtimeSegments(
    const ast::SymbolReferenceNode& reference) {

    std::vector<runtime::RuntimeDictionaryEntry>
        segment_entries;

    int segment_id = 1;

    for (const auto& segment :
         reference.getSegments()) {

        std::vector<runtime::RuntimeDictionaryEntry>
            facts;

        facts.push_back({
            1,
            runtime::RuntimeValue::string(
                segment.name)
        });

        facts.push_back({
            2,
            runtime::RuntimeValue::string(
                separatorName(segment.separator))
        });

        segment_entries.push_back({
            segment_id,
            runtime::RuntimeValue::dictionary(
                std::move(facts))
        });

        ++segment_id;
    }

    return runtime::RuntimeValue::dictionary(
        std::move(segment_entries));
}

const runtime::RuntimeValue&
dictionaryEntry(
    const std::vector<
        runtime::RuntimeDictionaryEntry>& dictionary,
    int id,
    const std::string& context) {

    for (const auto& entry : dictionary) {
        if (entry.id == id) {
            return entry.value;
        }
    }

    throw std::runtime_error(
        context +
        " missing Dictionary entry " +
        std::to_string(id) +
        ".");
}

runtime::ReferenceDocumentPlan
executeAuthoredPlanner(
    const ast::TermDeclarationNode& planner,
    const ast::SymbolReferenceNode& reference,
    const fs::path& current_document) {

    runtime::ExecutionEngine engine;
    engine.registerDefinition(planner);

    std::unordered_map<
        std::string,
        runtime::RuntimeValue
    > overrides;

    overrides.emplace(
        "current_document",
        runtime::RuntimeValue::string(
            current_document.generic_string()));

    overrides.emplace(
        "origin",
        runtime::RuntimeValue::string(
            originName(reference.getOrigin())));

    overrides.emplace(
        "parent_depth",
        runtime::RuntimeValue::numeric(
            reference.getParentDepth()));

    overrides.emplace(
        "segments",
        runtimeSegments(reference));

    const auto instance =
        engine.instantiate(
            "Reference_Document",
            overrides);

    require(
        instance.result.has_value(),
        "Authored planner returned no value.");

    require(
        instance.result->isDictionary(),
        "Authored planner did not return a Dictionary.");

    const auto& dictionary =
        instance.result->asDictionary(
            "authored reference plan");

    const auto& document =
        dictionaryEntry(
            dictionary,
            1,
            "authored reference plan");

    const auto& semantic_start =
        dictionaryEntry(
            dictionary,
            2,
            "authored reference plan");

    require(
        document.isString(),
        "Authored planner document_relative is not a string.");

    require(
        semantic_start.isNumeric(),
        "Authored planner semantic_start is not numeric.");

    runtime::ReferenceDocumentPlan plan;

    plan.document_relative =
        document.asString(
            "authored document_relative");

    plan.semantic_start =
        static_cast<std::size_t>(
            semantic_start.asNumber(
                "authored semantic_start"));

    return plan;
}

void requirePlan(
    const runtime::ReferenceDocumentPlan& actual,
    const runtime::ReferenceDocumentPlan& expected,
    const std::string& witness) {

    if (actual.document_relative !=
        expected.document_relative) {

        throw std::runtime_error(
            witness +
            " document mismatch: expected '" +
            expected.document_relative.string() +
            "', got '" +
            actual.document_relative.string() +
            "'.");
    }

    if (actual.semantic_start !=
        expected.semantic_start) {

        throw std::runtime_error(
            witness +
            " semantic_start mismatch: expected " +
            std::to_string(expected.semantic_start) +
            ", got " +
            std::to_string(actual.semantic_start) +
            ".");
    }
}

void requireAuthoredPlan(
    const ast::TermDeclarationNode& planner,
    const ast::SymbolReferenceNode& reference,
    const fs::path& current_document,
    const fs::path& expected_document,
    std::size_t expected_semantic_start,
    const std::string& witness) {

    const auto authored =
        executeAuthoredPlanner(
            planner,
            reference,
            current_document);

    runtime::ReferenceDocumentPlan expected;
    expected.document_relative = expected_document;
    expected.semantic_start = expected_semantic_start;

    requirePlan(
        authored,
        expected,
        witness);

    std::cout
        << witness
        << ": PASS\n";
}

void requireWorkspaceEscape(
    const ast::TermDeclarationNode& planner) {

    using ast::SymbolReferenceOrigin;
    using ast::SymbolReferenceSeparator;

    auto ref = reference(
        "///defs/KE/U.p",
        SymbolReferenceOrigin::RELATIVE_MODULE,
        3,
        {
            {"defs", SymbolReferenceSeparator::ROOT},
            {"KE", SymbolReferenceSeparator::SLASH},
            {"U", SymbolReferenceSeparator::SLASH},
            {"p", SymbolReferenceSeparator::DOT}
        });

    const fs::path current_document =
        "items/MC/_index.qps";

    std::string authored_error;

    try {
        (void)executeAuthoredPlanner(
            planner,
            ref,
            current_document);
    }
    catch (const std::exception& error) {
        authored_error = error.what();
    }

    const std::string fragment =
        "escapes the workspace root";

    require(
        authored_error.find(fragment) !=
            std::string::npos,
        "Authored planner did not reject workspace escape.");

    std::cout
        << "WORKSPACE_ESCAPE: PASS\n";
}

} // namespace

int main(
    int argc,
    char** argv) {

    try {
        if (argc != 2) {
            throw std::runtime_error(
                "usage: qps_reference_document_plan_test "
                "<reference_document.qps>");
        }

        runtime::DocumentLoader loader;
        runtime::DocumentStore documents(loader);

        auto program =
            parseSource(
                readFile(argv[1]));

        require(
            program->statements.size() == 1,
            "Authored planner must contain exactly one "
            "top-level statement.");

        const auto* planner_term =
            dynamic_cast<
                const ast::TermDeclarationNode*>(
                    program->statements.front().get());

        require(
            planner_term != nullptr,
            "Authored planner top-level statement "
            "must be a Term declaration.");

        require(
            planner_term->identifier_ ==
                "Reference_Document",
            "Authored planner Term must be "
            "'Reference_Document'.");

        std::size_t planner_bodies = 0;

        for (const auto& child : planner_term->content_) {
            if (dynamic_cast<
                    const ast::ExecutionBlockNode*>(
                        child.get())) {

                ++planner_bodies;
            }
        }

        require(
            planner_bodies == 1,
            "Authored Reference_Document Term "
            "must own exactly one execution body.");

        const ast::TermDeclarationNode* planner =
            planner_term;

        using ast::SymbolReferenceOrigin;
        using ast::SymbolReferenceSeparator;

        // [>shape.dimensions]
        requireAuthoredPlan(
            *planner,
            reference(
                "shape.dimensions",
                SymbolReferenceOrigin::CURRENT_FILE,
                0,
                {
                    {
                        "shape",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "dimensions",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "defs/semantic_walk/shape.qps",
            "defs/semantic_walk/shape.qps",
            0,
            "CURRENT_FILE");

        // [>.shape.shape]
        requireAuthoredPlan(
            *planner,
            reference(
                ".shape.shape",
                SymbolReferenceOrigin::CURRENT_FOLDER_FILE,
                0,
                {
                    {
                        "shape",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "shape",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "defs/semantic_walk/_index.qps",
            "defs/semantic_walk/shape.qps",
            1,
            "CURRENT_FOLDER_FILE");

        // [>semantic_walk/shape.shape.dimensions]
        requireAuthoredPlan(
            *planner,
            reference(
                "semantic_walk/shape.shape.dimensions",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                0,
                {
                    {
                        "semantic_walk",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "shape",
                        SymbolReferenceSeparator::SLASH
                    },
                    {
                        "shape",
                        SymbolReferenceSeparator::DOT
                    },
                    {
                        "dimensions",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "defs/_index.qps",
            "defs/semantic_walk/shape.qps",
            2,
            "CHILD_MODULE");

        // [>/KE/U.p]
        requireAuthoredPlan(
            *planner,
            reference(
                "/KE/U.p",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                1,
                {
                    {
                        "KE",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "U",
                        SymbolReferenceSeparator::SLASH
                    },
                    {
                        "p",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "defs/semantic_walk/shape.qps",
            "defs/KE/U.qps",
            2,
            "ONE_PARENT");

        // [>//defs/KE/U.p]
        requireAuthoredPlan(
            *planner,
            reference(
                "//defs/KE/U.p",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                2,
                {
                    {
                        "defs",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "KE",
                        SymbolReferenceSeparator::SLASH
                    },
                    {
                        "U",
                        SymbolReferenceSeparator::SLASH
                    },
                    {
                        "p",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "items/MC/_index.qps",
            "defs/KE/U.qps",
            3,
            "TWO_PARENT");

        // Root current-folder document: [>.shape.shape]
        requireAuthoredPlan(
            *planner,
            reference(
                ".shape.shape",
                SymbolReferenceOrigin::CURRENT_FOLDER_FILE,
                0,
                {
                    {
                        "shape",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "shape",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "_index.qps",
            "shape.qps",
            1,
            "ROOT_CURRENT_FOLDER_FILE");

        // Root relative-module document: [>shape.shape]
        requireAuthoredPlan(
            *planner,
            reference(
                "shape.shape",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                0,
                {
                    {
                        "shape",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "shape",
                        SymbolReferenceSeparator::DOT
                    }
                }),
            "_index.qps",
            "shape.qps",
            1,
            "ROOT_RELATIVE_MODULE");

        requireWorkspaceEscape(*planner);

        // Native path-fact contract retained by the authored bridge.
        {
            auto ref = reference(
                "shape.dimensions",
                SymbolReferenceOrigin::CURRENT_FILE,
                0,
                {
                    {
                        "shape",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "dimensions",
                        SymbolReferenceSeparator::DOT
                    }
                });

            const auto requireFailure =
                [&](const std::filesystem::path& current_document,
                    const std::string& fragment,
                    const std::string& witness) {

                    std::string authored_error;

                    try {
                        (void)runtime::planReferenceDocumentAuthored(
                    documents,
                            ref,
                            {current_document},
                            argv[1]);
                    }
                    catch (const std::exception& error) {
                        authored_error = error.what();
                    }

                    require(
                        authored_error.find(fragment) !=
                            std::string::npos,
                        witness +
                        " authored planner did not reject as expected.");

                    std::cout
                        << witness
                        << ": PASS\n";
                };

            requireFailure(
                {},
                "requires a current document",
                "EMPTY_CURRENT_DOCUMENT");

            requireFailure(
                "/tmp/shape.qps",
                "must be workspace-relative",
                "ABSOLUTE_CURRENT_DOCUMENT");

            requireFailure(
                "defs/shape.txt",
                "must use .qps extension",
                "NON_QPS_CURRENT_DOCUMENT");
        }

        // Both paths must normalize before policy execution.
        {
            auto ref = reference(
                "shape.dimensions",
                SymbolReferenceOrigin::CURRENT_FILE,
                0,
                {
                    {
                        "shape",
                        SymbolReferenceSeparator::ROOT
                    },
                    {
                        "dimensions",
                        SymbolReferenceSeparator::DOT
                    }
                });

            const std::filesystem::path current_document =
                "defs/semantic_walk/../semantic_walk/shape.qps";

            const auto authored =
                runtime::planReferenceDocumentAuthored(
                    documents,
                    ref,
                    {current_document},
                    argv[1]);

            runtime::ReferenceDocumentPlan expected;
            expected.document_relative =
                "defs/semantic_walk/shape.qps";
            expected.semantic_start = 0;

            requirePlan(
                authored,
                expected,
                "NORMALIZED_CURRENT_DOCUMENT");

            std::cout
                << "NORMALIZED_CURRENT_DOCUMENT: PASS\n";
        }

        std::cout
            << "QPS AUTHORED REFERENCE PLANNER: PASS\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "ERROR: "
            << error.what()
            << "\n";

        return 1;
    }
}
