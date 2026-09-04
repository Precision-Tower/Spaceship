#include "../h/symbol_resolver.hpp"

#include "../h/document_store.hpp"
#include "../h/path_resolver.hpp"

#include "../../ast/ast_node.hpp"
#include "../../ast/structural_selection.hpp"

#include <stdexcept>
#include <utility>

namespace qps {
namespace runtime {

namespace fs = std::filesystem;

SymbolResolver::SymbolResolver(
    PathResolver& paths,
    DocumentStore& documents)
    : paths_(paths),
      documents_(documents) {}

ResolvedSymbol SymbolResolver::resolve(
    const std::string& symbol,
    const fs::path& start_module) const {

    fs::path module = start_module.lexically_normal();

    while (true) {
        const fs::path index_file =
            paths_.indexFile(module);

        auto index_ast =
            documents_.get(index_file);

        const ast::ItemDeclarationNode* match = nullptr;

        for (const auto& statement : index_ast->statements) {
            auto* item =
                dynamic_cast<ast::ItemDeclarationNode*>(
                    statement.get());

            if (!item) {
                continue;
            }

            auto* identifier_target =
                dynamic_cast<ast::IdentifierNode*>(
                    item->target_.get());

            if (!identifier_target ||
                identifier_target->name_ != symbol) {
                continue;
            }

            if (match != nullptr) {
                throw std::runtime_error(
                    "Duplicate surfaced symbol '" +
                    symbol +
                    "' in " +
                    index_file.string());
            }

            match = item;
        }

        if (match != nullptr) {
            auto* path_ref =
                dynamic_cast<ast::PathReferenceNode*>(
                    match->value_node_.get());

            if (!path_ref) {
                throw std::runtime_error(
                    "Surfaced symbol '" +
                    symbol +
                    "' in " +
                    index_file.string() +
                    " must reference a QPS path.");
            }

            const auto& segments =
                path_ref->getPathSegments();

            if (segments.empty()) {
                throw std::runtime_error(
                    "Surfaced symbol '" +
                    symbol +
                    "' has an empty target path.");
            }

            // A surfaced path may point either to:
            //
            //   1. A document inside the current module:
            //
            //        p- U.p/p;
            //
            //      -> U.qps
            //
            //   2. A child QPS module:
            //
            //        p- KE.p/p;
            //
            //      -> KE/_index.qps
            //      -> recursively resolve p from module KE
            //
            // QPS modules are directories containing _index.qps.
            const fs::path child_module =
                (module / segments.front()).lexically_normal();

            if (paths_.isModule(child_module)) {
                // Module delegation currently requires exactly one surfaced
                // symbol after the module name. Deeper traversal happens
                // recursively through each module's own _index.qps.
                //
                // Example:
                //
                //   defs/_index.qps      : p- KE.p/p;
                //   defs/KE/_index.qps   : p- U.p/p;
                //
                // The first resolution delegates to defs/KE. The second
                // resolves U.qps normally.
                if (segments.size() != 2) {
                    throw std::runtime_error(
                        "Module surface path for symbol '" +
                        symbol +
                        "' must contain exactly '<module>.<symbol>'.");
                }

                ResolvedSymbol nested =
                    resolve(segments[1], child_module);

                // Preserve the symbol requested at this surface. The
                // terminal resolution metadata remains that of the nested
                // module/document that actually owns the semantic object.
                nested.symbol = symbol;

                return nested;
            }

            // Document surface rule:
            //
            //   p- U.p/p;
            //
            // First segment = .qps document stem.
            // Remaining segments = semantic path inside document.
            fs::path document_relative = module;

            document_relative /=
                segments.front() + ".qps";

            const fs::path document_file =
                paths_.resolveFile(document_relative);

            ResolvedSymbol result;
            result.symbol = symbol;
            result.surface_module = module;
            result.index_file = index_file;
            result.document_file = document_file;

            result.semantic_path.assign(
                segments.begin() + 1,
                segments.end());

            if (result.semantic_path.empty()) {
                throw std::runtime_error(
                    "Surfaced symbol '" +
                    symbol +
                    "' resolves to a document but no semantic target.");
            }

            // V1 semantic-target proof:
            // resolve the first semantic segment as a top-level Key.
            //
            // Example:
            //   p- uni.p/p;
            //
            // document_file  -> uni.qps
            // semantic_path  -> ["p"]
            // target         -> KeyDeclarationNode("p")
            auto document_ast =
                documents_.get(result.document_file);

            result.document_owner = document_ast;

            const std::string& target_name =
                result.semantic_path.front();

            const ast::KeyDeclarationNode* target = nullptr;

            for (const auto& statement :
                 document_ast->statements) {

                auto* key =
                    dynamic_cast<ast::KeyDeclarationNode*>(
                        statement.get());

                if (!key ||
                    key->identifier_ != target_name) {
                    continue;
                }

                if (target != nullptr) {
                    throw std::runtime_error(
                        "Duplicate semantic Key '" +
                        target_name +
                        "' in " +
                        result.document_file.string());
                }

                target = key;
            }

            if (target == nullptr) {
                throw std::runtime_error(
                    "Semantic Key '" +
                    target_name +
                    "' not found in " +
                    result.document_file.string());
            }

            // Do not retain the AST pointer here: document_ast is locally
            // owned and will be destroyed when resolve() returns.
            // Record verified identity only. AST lifetime comes later.
            result.target_type = "KEY_DECLARATION";
            result.target_identifier =
                target->identifier_;

            result.target_node =
                const_cast<ast::KeyDeclarationNode*>(target);

            return result;
        }

        // Empty module path represents the workspace root.
        if (module.empty()) {
            break;
        }

        module = module.parent_path();
    }

    throw std::runtime_error(
        "Unresolved QPS symbol '" +
        symbol +
        "' from module '" +
        start_module.string() +
        "'.");
}


StructuralHandle SymbolResolver::resolveFrom(
    const StructuralHandle& root,
    const ast::SymbolReferenceNode& reference) const {

    if (reference.getOrigin() !=
        ast::SymbolReferenceOrigin::LOCAL_BINDING) {

        throw std::runtime_error(
            "Local structural rebasing requires LOCAL_BINDING reference origin.");
    }

    const auto& local_segments =
        reference.getSegments();

    if (local_segments.size() < 2) {
        throw std::runtime_error(
            "Local structural reference '" +
            reference.getSymbol() +
            "' must identify a binding and child structure.");
    }

    if (!root.document_owner ||
        root.target_node == nullptr) {

        throw std::runtime_error(
            "Local structural root is incomplete.");
    }

    StructuralHandle result;
    result.document_owner = root.document_owner;

    ast::AstNode* current =
        root.target_node;

    const std::size_t structural_end =
        reference.selectsItemValue()
            ? local_segments.size() - 1
            : local_segments.size();

    // Segment zero is the local runtime binding name.
    // Navigation begins directly at the bound AST node.
    for (std::size_t i = 1;
         i < structural_end;
         ++i) {

        ast::AstNode* match = nullptr;

        try {
            match =
                ast::selectStructuralChild(
                    *current,
                    local_segments[i].name);
        }
        catch (const std::runtime_error& error) {
            throw std::runtime_error(
                std::string(error.what()) +
                " while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        if (!match) {
            throw std::runtime_error(
                "Semantic structure '" +
                local_segments[i].name +
                "' not found while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        current = match;
    }

    if (reference.selectsItemValue()) {
        const std::string& item_name =
            local_segments.back().name;

        ast::ItemDeclarationNode* match = nullptr;

        try {
            match =
                ast::selectStructuralItem(
                    *current,
                    item_name);
        }
        catch (const std::runtime_error& error) {
            throw std::runtime_error(
                std::string(error.what()) +
                " while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        if (!match) {
            throw std::runtime_error(
                "Semantic Item '" +
                item_name +
                "' not found while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        current = match;
    }

    if (auto* resolved_key =
            dynamic_cast<ast::KeyDeclarationNode*>(
                current)) {

        result.target_type =
            "KEY_DECLARATION";
        result.target_identifier =
            resolved_key->identifier_;
    }
    else if (auto* resolved_term =
                 dynamic_cast<ast::TermDeclarationNode*>(
                     current)) {

        result.target_type =
            "TERM_DECLARATION";
        result.target_identifier =
            resolved_term->identifier_;
    }
    else if (auto* resolved_item =
                 dynamic_cast<ast::ItemDeclarationNode*>(
                     current)) {

        auto* identifier =
            dynamic_cast<ast::IdentifierNode*>(
                resolved_item->getTarget());

        if (!identifier) {
            throw std::runtime_error(
                "Resolved semantic Item does not have an identifier target.");
        }

        result.target_type =
            "ITEM_VALUE";
        result.target_identifier =
            identifier->name_;
    }
    else {
        throw std::runtime_error(
            "Structural QPS reference resolved to unsupported AST node.");
    }

    result.target_node = current;

    return result;
}


StructuralHandle SymbolResolver::resolve(
    const ast::SymbolReferenceNode& reference,
    const StructuralReferenceContext& context) const {

    if (context.current_document.empty()) {
        throw std::runtime_error(
            "Structural QPS resolution requires a current document.");
    }

    if (context.current_document.is_absolute()) {
        throw std::runtime_error(
            "Structural QPS current document must be workspace-relative.");
    }

    if (context.current_document.extension() != ".qps") {
        throw std::runtime_error(
            "Structural QPS current document must use .qps extension.");
    }

    const fs::path current_document =
        context.current_document.lexically_normal();

    const fs::path current_module =
        current_document.parent_path();

    const auto& segments =
        reference.getSegments();

    // Resolve document scope from the authored reference origin.
    //
    // CURRENT_FILE:
    //   [>dimensions]
    //
    // CURRENT_FOLDER_FILE:
    //   [>.shape.dimensions]
    //
    // RELATIVE_MODULE:
    //   [>semantic_walk/shape.dimensions]
    //   [>/shape.dimensions]
    //   [>//shape.dimensions]
    fs::path document_relative;
    std::size_t semantic_start = 0;

    if (reference.getOrigin() ==
        ast::SymbolReferenceOrigin::CURRENT_FILE) {

        document_relative =
            current_document;

        semantic_start = 0;
    }
    else {
        fs::path base_module =
            current_module;

        const int parent_depth =
            reference.getParentDepth();

        for (int i = 0; i < parent_depth; ++i) {
            if (base_module.empty()) {
                throw std::runtime_error(
                    "Structural QPS reference '" +
                    reference.getSymbol() +
                    "' escapes the workspace root.");
            }

            base_module =
                base_module.parent_path();
        }

        std::size_t document_index = 0;

        if (reference.getOrigin() ==
            ast::SymbolReferenceOrigin::RELATIVE_MODULE) {

            while (document_index + 1 < segments.size() &&
                   segments[document_index + 1].separator ==
                       ast::SymbolReferenceSeparator::SLASH) {

                base_module /=
                    segments[document_index].name;

                paths_.resolveModule(base_module);

                ++document_index;
            }
        }

        if (document_index >= segments.size()) {
            throw std::runtime_error(
                "Structural QPS reference '" +
                reference.getSymbol() +
                "' does not identify a document.");
        }

        document_relative =
            base_module /
            (segments[document_index].name + ".qps");

        semantic_start =
            document_index + 1;
    }

    fs::path document_file;

    if (reference.getOrigin() ==
        ast::SymbolReferenceOrigin::CURRENT_FILE) {

        // CURRENT_FILE already identifies the authored document.
        // It does not traverse the QPS module web, so its parent
        // directory is not required to be a QPS module.
        document_file =
            (paths_.workspaceRoot() / document_relative)
                .lexically_normal();

        if (!fs::is_regular_file(document_file)) {
            throw std::runtime_error(
                "QPS current document not found: " +
                document_file.string());
        }
    }
    else {
        // Cross-document references traverse the QPS module web.
        document_file =
            paths_.resolveFile(document_relative);
    }

    auto document_ast =
        documents_.get(document_file);

    StructuralHandle result;
    result.document_owner = document_ast;

    if (semantic_start >= segments.size()) {
        throw std::runtime_error(
            "Structural QPS reference '" +
            reference.getSymbol() +
            "' does not identify semantic structure.");
    }

    ast::AstNode* current = nullptr;

    // First semantic segment is resolved from the document surface.
    {
        const std::string& name =
            segments[semantic_start].name;

        try {
            current =
                ast::selectDocumentStructure(
                    *document_ast,
                    name);
        }
        catch (const std::runtime_error& error) {
            throw std::runtime_error(
                std::string(error.what()) +
                " while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        if (!current) {
            throw std::runtime_error(
                "Semantic structure '" +
                name +
                "' not found in " +
                document_file.string());
        }
    }

    // Everything after the Key is semantic descent.
    //
    // Structural references consume all remaining segments as Terms.
    // Item-value references reserve the final segment for explicit
    // Item lookup:
    //
    //   [>shape.shape.dimensions.cylinder]
    //   [>shape.shape.dimensions.cylinder.radius-]
    const std::size_t structural_end =
        reference.selectsItemValue()
            ? segments.size() - 1
            : segments.size();

    for (std::size_t i = semantic_start + 1;
         i < structural_end;
         ++i) {

        ast::AstNode* match = nullptr;

        try {
            match =
                ast::selectStructuralChild(
                    *current,
                    segments[i].name);
        }
        catch (const std::runtime_error& error) {
            throw std::runtime_error(
                std::string(error.what()) +
                " while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        if (!match) {
            throw std::runtime_error(
                "Semantic structure '" +
                segments[i].name +
                "' not found while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        current = match;
    }

    if (reference.selectsItemValue()) {
        const std::string& item_name =
            segments.back().name;

        ast::ItemDeclarationNode* match = nullptr;

        try {
            match =
                ast::selectStructuralItem(
                    *current,
                    item_name);
        }
        catch (const std::runtime_error& error) {
            throw std::runtime_error(
                std::string(error.what()) +
                " while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        if (!match) {
            throw std::runtime_error(
                "Semantic Item '" +
                item_name +
                "' not found while resolving '" +
                reference.getSymbol() +
                "'.");
        }

        current = match;
    }

    if (auto* resolved_key =
            dynamic_cast<ast::KeyDeclarationNode*>(
                current)) {

        result.target_type =
            "KEY_DECLARATION";
        result.target_identifier =
            resolved_key->identifier_;
    }
    else if (auto* resolved_term =
                 dynamic_cast<ast::TermDeclarationNode*>(
                     current)) {

        result.target_type =
            "TERM_DECLARATION";
        result.target_identifier =
            resolved_term->identifier_;
    }
    else if (auto* resolved_item =
                 dynamic_cast<ast::ItemDeclarationNode*>(
                     current)) {

        auto* identifier =
            dynamic_cast<ast::IdentifierNode*>(
                resolved_item->getTarget());

        if (!identifier) {
            throw std::runtime_error(
                "Resolved semantic Item does not have an identifier target.");
        }

        result.target_type =
            "ITEM_VALUE";
        result.target_identifier =
            identifier->name_;
    }
    else {
        throw std::runtime_error(
            "Structural QPS reference resolved to unsupported AST node.");
    }

    result.target_node = current;

    return result;
}


} // namespace runtime
} // namespace qps
