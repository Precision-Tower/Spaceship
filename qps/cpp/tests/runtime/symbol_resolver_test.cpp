#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/path_resolver.hpp"
#include "runtime/h/symbol_resolver.hpp"
#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " <workspace-root> <reference-planner>\n";
        return 2;
    }

    try {
        qps::runtime::PathResolver paths(argv[1]);
        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(loader);

        qps::runtime::SymbolResolver symbols(
            paths,
            documents,
            argv[2]);

        const std::filesystem::path witness_document =
            "defs/semantic_walk/shape.qps";

        const std::string witness_key =
            "shape";

        // Structural-reference resolver witnesses.
        //
        // Use the same physical document already proven by the legacy
        // resolver. Build the references through the parser so this test
        // crosses the actual QPS syntax -> AST -> resolver boundary.
        {
            const auto document_stem =
                witness_document.stem().string();

            const auto key_name =
                witness_key;

            const std::string source =
                "{Reference_Witness:"
                "%key_ref: [>." +
                document_stem + "." +
                key_name +
                "]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse structural resolver witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Structural resolver witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Structural resolver witness expression is not a SymbolReferenceNode.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        witness_document
                    });

            if (direct.target_type != "KEY_DECLARATION") {
                throw std::runtime_error(
                    "Direct structural Key reference did not resolve as Key.");
            }

            if (direct.target_identifier != key_name) {
                throw std::runtime_error(
                    "Direct structural Key reference resolved wrong identifier.");
            }

            if (!dynamic_cast<qps::ast::KeyDeclarationNode*>(
                    direct.target_node)) {
                throw std::runtime_error(
                    "Direct structural Key reference did not retain Key AST target.");
            }

            std::cout
                << "DIRECT STRUCTURAL KEY: "
                << direct.target_identifier
                << "\n";
        }

        // Nested structural Term witness.
        //
        // Engineering/qps/defs/semantic_walk/shape.qps:
        //
        //   shape.
        //   dimensions: (
        //       cylinder: (
        //           radius- 5/m;,
        //           depth- 5/ft;\
        //       );
        //   );
        //
        // Containers are grouping syntax and therefore do not appear in:
        //
        //   [>shape.shape.dimensions.cylinder]
        {
            const std::string source =
                "{Reference_Witness:"
                "%term_ref: "
                "[>shape.dimensions.cylinder]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse nested structural Term witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Nested structural Term witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Nested structural Term witness expression is not a SymbolReferenceNode.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/semantic_walk/shape.qps"
                    });

            if (direct.target_type != "TERM_DECLARATION") {
                throw std::runtime_error(
                    "Nested structural reference did not resolve as Term.");
            }

            if (direct.target_identifier != "cylinder") {
                throw std::runtime_error(
                    "Nested structural reference resolved wrong Term.");
            }

            auto* cylinder =
                dynamic_cast<qps::ast::TermDeclarationNode*>(
                    direct.target_node);

            if (!cylinder) {
                throw std::runtime_error(
                    "Nested structural reference did not retain Term AST target.");
            }

            std::cout
                << "DIRECT STRUCTURAL TERM: "
                << direct.target_identifier
                << "\n";
        }

        // Explicit Item-value reference witness.
        //
        // Source:
        //   radius- 5/m;
        //
        // Reference:
        //   [>shape.shape.dimensions.cylinder.radius-]
        //
        // The resolver returns the Item declaration, preserving both
        // the value node and authored Engineering unit metadata.
        {
            const std::string source =
                "{Reference_Witness:"
                "%item_ref: "
                "[>shape.dimensions.cylinder.radius-]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse explicit Item-value witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Item-value witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Item-value witness expression is not a SymbolReferenceNode.");
            }

            if (!reference->selectsItemValue()) {
                throw std::runtime_error(
                    "Item-value witness did not preserve trailing '-' semantics.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/semantic_walk/shape.qps"
                    });

            if (direct.target_type != "ITEM_VALUE") {
                throw std::runtime_error(
                    "Explicit Item reference did not resolve as ITEM_VALUE.");
            }

            if (direct.target_identifier != "radius") {
                throw std::runtime_error(
                    "Explicit Item reference resolved wrong identifier.");
            }

            auto* item =
                dynamic_cast<qps::ast::ItemDeclarationNode*>(
                    direct.target_node);

            if (!item) {
                throw std::runtime_error(
                    "Explicit Item reference did not retain ItemDeclarationNode.");
            }

            auto* numeric =
                dynamic_cast<qps::ast::NumericLiteralNode*>(
                    item->value_node_.get());

            if (!numeric) {
                throw std::runtime_error(
                    "Resolved radius Item does not contain numeric value.");
            }

            if (numeric->value_ != 5.0) {
                throw std::runtime_error(
                    "Resolved radius Item has wrong numeric value.");
            }

            if (!item->unit_hint_ ||
                *item->unit_hint_ != "m") {
                throw std::runtime_error(
                    "Resolved radius Item did not preserve authored unit 'm'.");
            }

            std::cout
                << "DIRECT ITEM VALUE: "
                << direct.target_identifier
                << " = "
                << numeric->value_
                << "/"
                << *item->unit_hint_
                << "\n";
        }

        // Child-module structural reference witness.
        //
        // Start module:
        //   defs
        //
        // Reference:
        //   [>semantic_walk/shape.shape.dimensions.cylinder]
        //
        // Filesystem portion:
        //   semantic_walk/shape.qps
        //
        // Semantic portion:
        //   shape.dimensions.cylinder
        {
            const std::string source =
                "{Reference_Witness:"
                "%child_module_ref: "
                "[>semantic_walk/shape.shape.dimensions.cylinder]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse child-module structural reference witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Child-module structural reference witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Child-module witness expression is not a SymbolReferenceNode.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/_index.qps"
                    });

            if (direct.target_type != "TERM_DECLARATION") {
                throw std::runtime_error(
                    "Child-module structural reference did not resolve as Term.");
            }

            if (direct.target_identifier != "cylinder") {
                throw std::runtime_error(
                    "Child-module structural reference resolved wrong Term.");
            }

            auto* cylinder =
                dynamic_cast<qps::ast::TermDeclarationNode*>(
                    direct.target_node);

            if (!cylinder) {
                throw std::runtime_error(
                    "Child-module structural reference did not retain Term AST target.");
            }

            std::cout
                << "DIRECT CHILD-MODULE TERM: "
                << direct.target_identifier
                << "\n";
        }

        // One-parent module traversal.
        //
        // Current document:
        //   defs/semantic_walk/shape.qps
        //
        // Reference:
        //   [>/KE/U.p]
        //
        // Resolution:
        //   defs/semantic_walk
        //       /
        //   defs
        //       KE/U.qps
        //       p
        {
            const std::string source =
                "{Reference_Witness:"
                "%parent_ref: "
                "[>/KE/U.p]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse one-parent reference witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "One-parent reference witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "One-parent witness expression is not a SymbolReferenceNode.");
            }

            if (reference->getParentDepth() != 1) {
                throw std::runtime_error(
                    "One-parent reference did not preserve parent depth 1.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/semantic_walk/shape.qps"
                    });

            if (direct.target_identifier != "p") {
                throw std::runtime_error(
                    "One-parent reference resolved wrong semantic target.");
            }

            if (!dynamic_cast<qps::ast::KeyDeclarationNode*>(
                    direct.target_node)) {
                throw std::runtime_error(
                    "One-parent reference did not resolve p structure.");
            }

            std::cout
                << "DIRECT ONE-PARENT: "
                << direct.target_identifier
                << "\n";
        }

        // Two-parent module traversal.
        //
        // Current document:
        //   items/MC/_index.qps
        //
        // Reference:
        //   [>//defs/KE/U.p]
        //
        // Resolution:
        //   items/MC
        //       //
        //   workspace root
        //       defs/KE/U.qps
        //       p
        {
            const std::string source =
                "{Reference_Witness:"
                "%two_parent_ref: "
                "[>//defs/KE/U.p]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse two-parent reference witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Two-parent reference witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Two-parent witness expression is not a SymbolReferenceNode.");
            }

            if (reference->getParentDepth() != 2) {
                throw std::runtime_error(
                    "Two-parent reference did not preserve parent depth 2.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "items/MC/_index.qps"
                    });

            if (direct.target_identifier != "p") {
                throw std::runtime_error(
                    "Two-parent reference resolved wrong semantic target.");
            }

            if (!dynamic_cast<qps::ast::KeyDeclarationNode*>(
                    direct.target_node)) {
                throw std::runtime_error(
                    "Two-parent reference did not resolve p structure.");
            }

            std::cout
                << "DIRECT TWO-PARENT: "
                << direct.target_identifier
                << "\n";
        }

        // Parent traversal may not escape the QPS workspace root.
        {
            const std::string source =
                "{Reference_Witness:"
                "%escape_ref: "
                "[>///defs/KE/U.p]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse escape-boundary reference witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Escape-boundary witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Escape-boundary witness expression is not a SymbolReferenceNode.");
            }

            bool rejected = false;

            try {
                (void)symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "items/MC/_index.qps"
                    });
            }
            catch (const std::runtime_error& e) {
                const std::string message = e.what();

                if (message.find("escapes the workspace root") !=
                    std::string::npos) {
                    rejected = true;
                }
            }

            if (!rejected) {
                throw std::runtime_error(
                    "Parent traversal escaped workspace root.");
            }

            std::cout
                << "PARENT ESCAPE REJECTED"
                << "\n";
        }


        // Current-file structural reference witness.
        //
        // Current document:
        //   defs/semantic_walk/shape.qps
        //
        // Reference:
        //   [>shape.dimensions]
        //
        // Resolves the nested dimensions Term in the current document.
        {
            const std::string source =
                "{Reference_Witness:"
                "%current_file_ref: "
                "[>shape.dimensions]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse current-file reference witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Current-file witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Current-file witness expression is not a SymbolReferenceNode.");
            }

            if (reference->getOrigin() !=
                qps::ast::SymbolReferenceOrigin::CURRENT_FILE) {
                throw std::runtime_error(
                    "Current-file witness did not preserve CURRENT_FILE origin.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/semantic_walk/shape.qps"
                    });

            if (direct.target_type != "TERM_DECLARATION" ||
                direct.target_identifier != "dimensions") {
                throw std::runtime_error(
                    "Current-file structural reference resolved incorrectly.");
            }

            std::cout
                << "DIRECT CURRENT-FILE TERM: "
                << direct.target_identifier
                << "\n";
        }

        // Current-folder sibling-file witness.
        //
        // Current document:
        //   defs/semantic_walk/_index.qps
        //
        // Reference:
        //   [>.shape.shape]
        //
        // Resolves:
        //   defs/semantic_walk/shape.qps
        //   Key shape
        {
            const std::string source =
                "{Reference_Witness:"
                "%sibling_ref: "
                "[>.shape.shape]"
                "}";

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto witness_program =
                parser.parseProgram();

            auto* definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    witness_program->statements.front().get());

            if (!definition ||
                definition->body_->statements.empty()) {
                throw std::runtime_error(
                    "Failed to parse current-folder reference witness.");
            }

            auto* calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    definition->body_->statements.front().get());

            if (!calculation) {
                throw std::runtime_error(
                    "Current-folder witness is not a CalculationNode.");
            }

            auto* reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    calculation->getExpression());

            if (!reference) {
                throw std::runtime_error(
                    "Current-folder witness expression is not a SymbolReferenceNode.");
            }

            if (reference->getOrigin() !=
                qps::ast::SymbolReferenceOrigin::CURRENT_FOLDER_FILE) {
                throw std::runtime_error(
                    "Current-folder witness did not preserve CURRENT_FOLDER_FILE origin.");
            }

            const auto direct =
                symbols.resolve(
                    *reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/semantic_walk/_index.qps"
                    });

            if (direct.target_type != "KEY_DECLARATION" ||
                direct.target_identifier != "shape") {
                throw std::runtime_error(
                    "Current-folder structural reference resolved incorrectly.");
            }

            std::cout
                << "DIRECT CURRENT-FOLDER KEY: "
                << direct.target_identifier
                << "\n";
        }

        // Local-binding rebasing witness.
        //
        // First resolve:
        //   [>shape.dimensions]
        //
        // Then rebase local binding:
        //   [v.cylinder]
        //
        // Expected terminal target:
        //   Term cylinder
        {
            const std::string root_source =
                "{Reference_Witness:"
                "%root_ref: "
                "[>shape.dimensions]"
                "}";

            qps::tokens::CharStream root_stream(root_source);
            qps::tokens::Lexer root_lexer(root_stream);
            qps::parser::Parser root_parser(root_lexer);

            auto root_program =
                root_parser.parseProgram();

            auto* root_definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    root_program->statements.front().get());

            auto* root_calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    root_definition->body_->statements.front().get());

            auto* root_reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    root_calculation->getExpression());

            if (!root_reference) {
                throw std::runtime_error(
                    "Local-binding root witness is not a SymbolReferenceNode.");
            }

            const auto root =
                symbols.resolve(
                    *root_reference,
                    qps::runtime::StructuralReferenceContext{
                        "defs/semantic_walk/shape.qps"
                    });

            const std::string local_source =
                "{Reference_Witness:"
                "%local_ref: "
                "[v.cylinder]"
                "}";

            qps::tokens::CharStream local_stream(local_source);
            qps::tokens::Lexer local_lexer(local_stream);
            qps::parser::Parser local_parser(local_lexer);

            auto local_program =
                local_parser.parseProgram();

            auto* local_definition =
                dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
                    local_program->statements.front().get());

            auto* local_calculation =
                dynamic_cast<qps::ast::CalculationNode*>(
                    local_definition->body_->statements.front().get());

            auto* local_reference =
                dynamic_cast<qps::ast::SymbolReferenceNode*>(
                    local_calculation->getExpression());

            if (!local_reference) {
                throw std::runtime_error(
                    "Local-binding witness is not a SymbolReferenceNode.");
            }

            if (local_reference->getOrigin() !=
                qps::ast::SymbolReferenceOrigin::LOCAL_BINDING) {
                throw std::runtime_error(
                    "Local-binding witness did not preserve LOCAL_BINDING origin.");
            }

            // Local rebasing must depend only on the owned AST and
            // selected node, not reconstructed resolver path metadata.
            auto minimal_root = root;
            minimal_root.target_type.clear();
            minimal_root.target_identifier.clear();

            const auto rebound =
                symbols.resolveFrom(
                    minimal_root,
                    *local_reference);

            if (rebound.target_type != "TERM_DECLARATION" ||
                rebound.target_identifier != "cylinder") {
                throw std::runtime_error(
                    "Local-binding structural reference resolved incorrectly.");
            }

            std::cout
                << "DIRECT LOCAL-BINDING TERM: "
                << rebound.target_identifier
                << "\n";
        }

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr
            << "ERROR: "
            << e.what()
            << "\n";
        return 1;
    }
}
