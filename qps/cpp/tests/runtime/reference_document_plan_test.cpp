#include "runtime/h/symbol_resolver.hpp"
#include "ast/ast_node.hpp"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

namespace ast = qps::ast;
namespace runtime = qps::runtime;

ast::SymbolReferenceNode reference(
    std::string symbol,
    ast::SymbolReferenceOrigin origin,
    int parent_depth,
    std::vector<ast::SymbolReferenceSegment> segments,
    bool selects_item_value = false) {

    return ast::SymbolReferenceNode(
        symbol,
        origin,
        parent_depth,
        std::move(segments),
        selects_item_value,
        1,
        1);
}

void requirePlan(
    const runtime::ReferenceDocumentPlan& plan,
    const std::filesystem::path& expected_document,
    std::size_t expected_semantic_start,
    const std::string& witness) {

    if (plan.document_relative != expected_document) {
        throw std::runtime_error(
            witness +
            " document mismatch: expected '" +
            expected_document.string() +
            "', got '" +
            plan.document_relative.string() +
            "'.");
    }

    if (plan.semantic_start != expected_semantic_start) {
        throw std::runtime_error(
            witness +
            " semantic_start mismatch.");
    }
}

} // namespace

int main() {
    try {
        using ast::SymbolReferenceOrigin;
        using ast::SymbolReferenceSegment;
        using ast::SymbolReferenceSeparator;

        // [>shape.dimensions]
        {
            auto ref = reference(
                "shape.dimensions",
                SymbolReferenceOrigin::CURRENT_FILE,
                0,
                {
                    {"shape", SymbolReferenceSeparator::ROOT},
                    {"dimensions", SymbolReferenceSeparator::DOT}
                });

            requirePlan(
                runtime::planReferenceDocument(
                    ref,
                    {"defs/semantic_walk/shape.qps"}),
                "defs/semantic_walk/shape.qps",
                0,
                "CURRENT_FILE");
        }

        // [>.shape.shape]
        {
            auto ref = reference(
                ".shape.shape",
                SymbolReferenceOrigin::CURRENT_FOLDER_FILE,
                0,
                {
                    {"shape", SymbolReferenceSeparator::ROOT},
                    {"shape", SymbolReferenceSeparator::DOT}
                });

            requirePlan(
                runtime::planReferenceDocument(
                    ref,
                    {"defs/semantic_walk/_index.qps"}),
                "defs/semantic_walk/shape.qps",
                1,
                "CURRENT_FOLDER_FILE");
        }

        // [>semantic_walk/shape.shape.dimensions]
        {
            auto ref = reference(
                "semantic_walk/shape.shape.dimensions",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                0,
                {
                    {"semantic_walk", SymbolReferenceSeparator::ROOT},
                    {"shape", SymbolReferenceSeparator::SLASH},
                    {"shape", SymbolReferenceSeparator::DOT},
                    {"dimensions", SymbolReferenceSeparator::DOT}
                });

            requirePlan(
                runtime::planReferenceDocument(
                    ref,
                    {"defs/_index.qps"}),
                "defs/semantic_walk/shape.qps",
                2,
                "CHILD_MODULE");
        }

        // [>/KE/U.p]
        {
            auto ref = reference(
                "/KE/U.p",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                1,
                {
                    {"KE", SymbolReferenceSeparator::ROOT},
                    {"U", SymbolReferenceSeparator::SLASH},
                    {"p", SymbolReferenceSeparator::DOT}
                });

            requirePlan(
                runtime::planReferenceDocument(
                    ref,
                    {"defs/semantic_walk/shape.qps"}),
                "defs/KE/U.qps",
                2,
                "ONE_PARENT");
        }

        // [>//defs/KE/U.p]
        {
            auto ref = reference(
                "//defs/KE/U.p",
                SymbolReferenceOrigin::RELATIVE_MODULE,
                2,
                {
                    {"defs", SymbolReferenceSeparator::ROOT},
                    {"KE", SymbolReferenceSeparator::SLASH},
                    {"U", SymbolReferenceSeparator::SLASH},
                    {"p", SymbolReferenceSeparator::DOT}
                });

            requirePlan(
                runtime::planReferenceDocument(
                    ref,
                    {"items/MC/_index.qps"}),
                "defs/KE/U.qps",
                3,
                "TWO_PARENT");
        }

        // Parent traversal cannot escape above workspace-relative root.
        {
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

            bool rejected = false;

            try {
                (void)runtime::planReferenceDocument(
                    ref,
                    {"items/MC/_index.qps"});
            }
            catch (const std::runtime_error& error) {
                rejected =
                    std::string(error.what()).find(
                        "escapes the workspace root") !=
                    std::string::npos;
            }

            if (!rejected) {
                throw std::runtime_error(
                    "Workspace escape was not rejected.");
            }
        }

        std::cout
            << "REFERENCE DOCUMENT PLAN: PASS\n";

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
