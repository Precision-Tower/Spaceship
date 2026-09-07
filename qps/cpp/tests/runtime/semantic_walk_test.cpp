#include "../../src/ast/ast_node.hpp"
#include "../../src/ast/structural_selection.hpp"
#include "../../src/parser/h/_index.hpp"
#include "../../src/runtime/h/interpreter.hpp"
#include "../../src/runtime/h/execution_engine.hpp"
#include "../../src/runtime/h/symbol_table.hpp"
#include "../../src/tokens/h/char_stream.hpp"
#include "../../src/tokens/h/lexer.hpp"

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

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string readFile(
    const std::string& path) {

    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error(
            "Could not open authored semantic walker: " +
            path);
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

struct Fixture {
    std::shared_ptr<ast::ProgramNode> owner;
    ast::AstNode* root = nullptr;
};

Fixture fixture(
    bool duplicate_child = false) {

    auto owner =
        std::make_shared<ast::ProgramNode>(
            1,
            1);

    auto root =
        std::make_unique<ast::KeyDeclarationNode>(
            "root",
            1,
            1);

    auto child =
        std::make_unique<ast::TermDeclarationNode>(
            "child",
            1,
            1);

    auto nested =
        std::make_unique<ast::TermDeclarationNode>(
            "nested",
            1,
            1);

    nested->content_.push_back(
        std::make_unique<ast::ItemDeclarationNode>(
            std::make_unique<ast::IdentifierNode>(
                "value",
                1,
                1),
            1,
            1));

    child->content_.push_back(
        std::move(nested));

    root->content_.push_back(
        std::move(child));

    if (duplicate_child) {
        auto transparent =
            std::make_unique<ast::ContainerNode>(
                1,
                1);

        transparent->elements.push_back(
            std::make_unique<ast::TermDeclarationNode>(
                "child",
                1,
                1));

        root->content_.push_back(
            std::move(transparent));
    }

    ast::AstNode* root_node =
        root.get();

    owner->statements.push_back(
        std::move(root));

    return {
        std::move(owner),
        root_node
    };
}

runtime::RuntimeValue segments(
    std::initializer_list<std::string> names) {

    std::vector<runtime::RuntimeDictionaryEntry>
        entries;

    int id = 1;

    for (const auto& name : names) {
        std::vector<runtime::RuntimeDictionaryEntry>
            facts;

        facts.push_back({
            1,
            runtime::RuntimeValue::string(name)
        });

        entries.push_back({
            id,
            runtime::RuntimeValue::dictionary(
                std::move(facts))
        });

        ++id;
    }

    return runtime::RuntimeValue::dictionary(
        std::move(entries));
}

runtime::StructuralHandle nativeWalk(
    const Fixture& f,
    const std::vector<std::string>& names,
    std::size_t structural_start,
    bool selects_item_value) {

    ast::AstNode* current =
        f.root;

    const std::size_t structural_end =
        selects_item_value
            ? names.size() - 1
            : names.size();

    for (std::size_t i = structural_start;
         i < structural_end;
         ++i) {

        ast::AstNode* selected =
            ast::selectStructuralChild(
                *current,
                names[i]);

        if (!selected) {
            throw std::runtime_error(
                "native structural child missing");
        }

        current = selected;
    }

    if (selects_item_value) {
        ast::ItemDeclarationNode* selected =
            ast::selectStructuralItem(
                *current,
                names.back());

        if (!selected) {
            throw std::runtime_error(
                "native structural item missing");
        }

        current = selected;
    }

    runtime::StructuralHandle result;
    result.document_owner = f.owner;
    result.target_node = current;

    return result;
}

runtime::StructuralHandle authoredWalk(
    const ast::TermDeclarationNode& walker,
    const Fixture& f,
    runtime::RuntimeValue segment_value,
    std::size_t structural_start,
    bool selects_item_value) {

    runtime::StructuralHandle start;
    start.document_owner = f.owner;
    start.target_node = f.root;

    runtime::ExecutionEngine engine;
    engine.registerDefinition(walker);

    std::unordered_map<
        std::string,
        runtime::RuntimeValue
    > overrides;

    overrides.emplace(
        "current_structure",
        runtime::RuntimeValue::structure(
            std::move(start)));

    overrides.emplace(
        "segments",
        std::move(segment_value));

    overrides.emplace(
        "structural_start",
        runtime::RuntimeValue::numeric(
            static_cast<double>(
                structural_start)));

    overrides.emplace(
        "selects_item_value",
        runtime::RuntimeValue::numeric(
            selects_item_value ? 1.0 : 0.0));

    const auto instance =
        engine.instantiate(
            "Semantic_Walk",
            overrides);

    require(
        instance.result.has_value(),
        "Authored semantic walker returned no value.");

    require(
        instance.result->isStructure(),
        "Authored semantic walker did not return STRUCTURE.");

    return instance.result->asStructure(
        "authored semantic walk");
}

void requireSameIdentity(
    const runtime::StructuralHandle& authored,
    const runtime::StructuralHandle& native,
    const std::string& witness) {

    require(
        authored.document_owner.get() ==
            native.document_owner.get(),
        witness +
            " document owner mismatch.");

    require(
        authored.target_node ==
            native.target_node,
        witness +
            " target node mismatch.");
std::cout
        << witness
        << ": PASS\n";
}

void parity(
    const ast::TermDeclarationNode& walker,
    const Fixture& f,
    const std::vector<std::string>& names,
    std::size_t structural_start,
    bool selects_item_value,
    const std::string& witness) {

    runtime::RuntimeValue runtime_segments;

    {
        std::vector<runtime::RuntimeDictionaryEntry>
            entries;

        int id = 1;

        for (const auto& name : names) {
            std::vector<runtime::RuntimeDictionaryEntry>
                facts;

            facts.push_back({
                1,
                runtime::RuntimeValue::string(name)
            });

            entries.push_back({
                id++,
                runtime::RuntimeValue::dictionary(
                    std::move(facts))
            });
        }

        runtime_segments =
            runtime::RuntimeValue::dictionary(
                std::move(entries));
    }

    const auto native =
        nativeWalk(
            f,
            names,
            structural_start,
            selects_item_value);

    const auto authored =
        authoredWalk(
            walker,
            f,
            std::move(runtime_segments),
            structural_start,
            selects_item_value);

    requireSameIdentity(
        authored,
        native,
        witness);
}

template <typename NativeCall, typename AuthoredCall>
void requireBothReject(
    NativeCall native_call,
    AuthoredCall authored_call,
    const std::string& witness) {

    bool native_rejected = false;
    bool authored_rejected = false;

    try {
        native_call();
    }
    catch (const std::exception&) {
        native_rejected = true;
    }

    try {
        authored_call();
    }
    catch (const std::exception&) {
        authored_rejected = true;
    }

    require(
        native_rejected,
        witness +
            " native selector did not reject.");

    require(
        authored_rejected,
        witness +
            " authored walker did not reject.");

    std::cout
        << witness
        << ": PASS\n";
}

} // namespace

int main(
    int argc,
    char** argv) {

    try {
        if (argc != 2) {
            throw std::runtime_error(
                "usage: qps_semantic_walk_test "
                "<semantic_walk.qps>");
        }

        auto walker_program =
            parseSource(
                readFile(argv[1]));

        require(
            walker_program->statements.size() == 1,
            "Authored semantic walker must contain "
            "exactly one top-level statement.");

        const auto* walker_term =
            dynamic_cast<
                const ast::TermDeclarationNode*>(
                    walker_program
                        ->statements.front()
                        .get());

        require(
            walker_term != nullptr,
            "Authored semantic walker top-level "
            "statement must be a Term declaration.");

        require(
            walker_term->identifier_ ==
                "Semantic_Walk",
            "Authored semantic walker Term must be "
            "'Semantic_Walk'.");

        std::size_t walker_bodies = 0;

        for (const auto& child : walker_term->content_) {
            if (dynamic_cast<
                    const ast::ExecutionBlockNode*>(
                        child.get())) {

                ++walker_bodies;
            }
        }

        require(
            walker_bodies == 1,
            "Authored Semantic_Walk Term "
            "must own exactly one execution body.");

        const ast::TermDeclarationNode* walker =
            walker_term;

        {
            const auto f = fixture();

            parity(
                *walker,
                f,
                {"child", "nested"},
                0,
                false,
                "CHILD_DESCENT");
        }

        {
            const auto f = fixture();

            parity(
                *walker,
                f,
                {"root"},
                1,
                false,
                "ZERO_ADDITIONAL_DESCENT");
        }

        {
            const auto f = fixture();

            parity(
                *walker,
                f,
                {"child", "nested", "value"},
                0,
                true,
                "ITEM_SELECTION");
        }

        {
            const auto f = fixture();

            const std::vector<std::string> names{
                "missing"
            };

            requireBothReject(
                [&]() {
                    (void)nativeWalk(
                        f,
                        names,
                        0,
                        false);
                },
                [&]() {
                    (void)authoredWalk(
                        *walker,
                        f,
                        segments({"missing"}),
                        0,
                        false);
                },
                "MISSING_CHILD");
        }

        {
            const auto f = fixture();

            const std::vector<std::string> names{
                "child",
                "nested",
                "missing"
            };

            requireBothReject(
                [&]() {
                    (void)nativeWalk(
                        f,
                        names,
                        0,
                        true);
                },
                [&]() {
                    (void)authoredWalk(
                        *walker,
                        f,
                        segments({
                            "child",
                            "nested",
                            "missing"
                        }),
                        0,
                        true);
                },
                "MISSING_ITEM");
        }

        {
            // "nested" exists, but it is a Term. Explicit Item selection
            // must reject it rather than accepting structural identity.
            const auto f = fixture();

            requireBothReject(
                [&]() {
                    (void)nativeWalk(
                        f,
                        {"child", "nested"},
                        0,
                        true);
                },
                [&]() {
                    (void)authoredWalk(
                        *walker,
                        f,
                        segments({
                            "child",
                            "nested"
                        }),
                        0,
                        true);
                },
                "TERM_IS_NOT_ITEM");
        }

        {
            const auto f =
                fixture(true);

            const std::vector<std::string> names{
                "child"
            };

            requireBothReject(
                [&]() {
                    (void)nativeWalk(
                        f,
                        names,
                        0,
                        false);
                },
                [&]() {
                    (void)authoredWalk(
                        *walker,
                        f,
                        segments({"child"}),
                        0,
                        false);
                },
                "DUPLICATE_CHILD");
        }

        std::cout
            << "QPS AUTHORED SEMANTIC WALK: PASS\n";

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
