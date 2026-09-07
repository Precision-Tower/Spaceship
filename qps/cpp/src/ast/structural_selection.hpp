#pragma once

#include "ast_node.hpp"

#include <string>
#include <vector>

namespace qps::ast {

AstNode* selectDocumentStructure(
    ProgramNode& document,
    const std::string& name);

/*
 * Select authored structure by dot-separated structural path.
 *
 * The final segment may identify a Key, Term, or Item.
 * Returns nullptr when the path does not resolve.
 * Path syntax belongs here so consumers do not independently
 * reinterpret authored structural coordinates.
 */
const AstNode* selectStructuralPath(
    const ProgramNode& document,
    const std::string& path);

/*
 * Return the immediate authored structural members of a selected
 * Key or Term in source order.
 *
 * Container nodes are transparent grouping structure: their immediate
 * elements participate at the same authored structural level.
 *
 * This is document-local structural inspection only. It does not
 * resolve references, traverse files, or recurse into child structures.
 */
std::vector<const AstNode*> structuralScope(
    const AstNode& parent);

/*
 * Find every authored structural identity with an exact name inside
 * one already-selected QPS document.
 *
 * This may recursively inspect authored structure within the document.
 * It does not discover files, modules, or filesystem descendants.
 */
std::vector<const AstNode*> scoutStructuralName(
    const ProgramNode& document,
    const std::string& name);


const AstNode* selectDocumentStructure(
    const ProgramNode& document,
    const std::string& name);

AstNode* selectStructuralChild(
    AstNode& parent,
    const std::string& name);

const AstNode* selectStructuralChild(
    const AstNode& parent,
    const std::string& name);

ItemDeclarationNode* selectStructuralItem(
    AstNode& parent,
    const std::string& name);

const ItemDeclarationNode* selectStructuralItem(
    const AstNode& parent,
    const std::string& name);

} // namespace qps::ast
