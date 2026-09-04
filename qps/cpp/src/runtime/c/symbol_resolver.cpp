#include "../h/symbol_resolver.hpp"

#include "../h/document_store.hpp"
#include "../h/interpreter.hpp"
#include "../h/path_resolver.hpp"

#include "../../ast/ast_node.hpp"
#include "../../ast/structural_selection.hpp"
#include "../../parser/h/_index.hpp"
#include "../../tokens/h/char_stream.hpp"
#include "../../tokens/h/lexer.hpp"

#include <fstream>
#include <iterator>
#include <optional>
#include <stdexcept>
#include <utility>

namespace qps {
namespace runtime {

namespace fs = std::filesystem;

SymbolResolver::SymbolResolver(
    PathResolver& paths,
    DocumentStore& documents,
    fs::path reference_planner)
    : paths_(paths),
      documents_(documents),
      reference_planner_(
          std::move(reference_planner)) {}

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


ReferenceDocumentPlan planReferenceDocument(
    const ast::SymbolReferenceNode& reference,
    const StructuralReferenceContext& context) {

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

    ReferenceDocumentPlan plan;

    if (reference.getOrigin() ==
        ast::SymbolReferenceOrigin::CURRENT_FILE) {

        plan.document_relative =
            current_document;

        plan.semantic_start = 0;

        return plan;
    }

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

            ++document_index;
        }
    }

    if (document_index >= segments.size()) {
        throw std::runtime_error(
            "Structural QPS reference '" +
            reference.getSymbol() +
            "' does not identify a document.");
    }

    plan.document_relative =
        base_module /
        (segments[document_index].name + ".qps");

    plan.semantic_start =
        document_index + 1;

    return plan;
}



namespace {

std::string referenceOriginName(
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

std::string referenceSeparatorName(
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

RuntimeValue referenceSegmentsValue(
    const ast::SymbolReferenceNode& reference) {

    std::vector<RuntimeDictionaryEntry> entries;

    int id = 1;

    for (const auto& segment :
         reference.getSegments()) {

        std::vector<RuntimeDictionaryEntry> facts;

        facts.push_back({
            1,
            RuntimeValue::string(segment.name)
        });

        facts.push_back({
            2,
            RuntimeValue::string(
                referenceSeparatorName(
                    segment.separator))
        });

        entries.push_back({
            id,
            RuntimeValue::dictionary(
                std::move(facts))
        });

        ++id;
    }

    return RuntimeValue::dictionary(
        std::move(entries));
}

const RuntimeValue& referencePlanEntry(
    const std::vector<RuntimeDictionaryEntry>& dictionary,
    int id) {

    for (const auto& entry : dictionary) {
        if (entry.id == id) {
            return entry.value;
        }
    }

    throw std::runtime_error(
        "Authored reference planner result missing Dictionary entry " +
        std::to_string(id) +
        ".");
}

} // namespace


ReferenceDocumentPlan planReferenceDocumentAuthored(
    const ast::SymbolReferenceNode& reference,
    const StructuralReferenceContext& context,
    const fs::path& planner_file) {

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

    std::ifstream input(planner_file);

    if (!input) {
        throw std::runtime_error(
            "Could not open authored reference planner: " +
            planner_file.string());
    }

    const std::string source{
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>()};

    tokens::CharStream char_stream(source);
    tokens::Lexer lexer(char_stream);
    parser::Parser parser(lexer);

    auto program =
        parser.parseProgram();

    if (program->statements.size() != 1) {
        throw std::runtime_error(
            "Authored reference planner must contain exactly one "
            "top-level statement.");
    }

    const auto* planner =
        dynamic_cast<const ast::ExecutionBlockNode*>(
            program->statements.front().get());

    if (!planner) {
        throw std::runtime_error(
            "Authored reference planner top-level statement "
            "must be an execution block.");
    }

    ExecutionScope scope;

    scope.bind(
        "current_document",
        RuntimeValue::string(
            current_document.generic_string()),
        std::nullopt,
        BindingOrigin::SUPPLIED);

    scope.bind(
        "origin",
        RuntimeValue::string(
            referenceOriginName(
                reference.getOrigin())),
        std::nullopt,
        BindingOrigin::SUPPLIED);

    scope.bind(
        "parent_depth",
        RuntimeValue::numeric(
            reference.getParentDepth()),
        std::nullopt,
        BindingOrigin::SUPPLIED);

    scope.bind(
        "segments",
        referenceSegmentsValue(reference),
        std::nullopt,
        BindingOrigin::SUPPLIED);

    InterpreterOptions options;
    options.allow_return = true;
    options.symbol_resolver = nullptr;

    Interpreter interpreter(
        scope,
        FunctionTable{},
        options);

    const auto result =
        interpreter.executeForResult(*planner);

    if (!result.has_value() ||
        !result->isDictionary()) {

        throw std::runtime_error(
            "Authored reference planner must return a Dictionary.");
    }

    const auto& dictionary =
        result->asDictionary(
            "authored reference plan");

    const auto& document =
        referencePlanEntry(dictionary, 1);

    const auto& semantic_start =
        referencePlanEntry(dictionary, 2);

    if (!document.isString()) {
        throw std::runtime_error(
            "Authored reference planner document_relative "
            "must be a string.");
    }

    if (!semantic_start.isNumeric()) {
        throw std::runtime_error(
            "Authored reference planner semantic_start "
            "must be numeric.");
    }

    ReferenceDocumentPlan plan;

    plan.document_relative =
        document.asString(
            "authored document_relative");

    plan.semantic_start =
        static_cast<std::size_t>(
            semantic_start.asNumber(
                "authored semantic_start"));

    return plan;
}


StructuralHandle SymbolResolver::resolve(
    const ast::SymbolReferenceNode& reference,
    const StructuralReferenceContext& context) const {

    const ReferenceDocumentPlan plan =
        planReferenceDocumentAuthored(
            reference,
            context,
            reference_planner_);

    const fs::path document_relative =
        plan.document_relative;

    const std::size_t semantic_start =
        plan.semantic_start;

    const auto& segments =
        reference.getSegments();

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
