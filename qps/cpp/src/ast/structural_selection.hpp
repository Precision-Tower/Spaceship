#pragma once

#include "ast_node.hpp"

#include <string>

namespace qps::ast {

AstNode* selectDocumentStructure(
    ProgramNode& document,
    const std::string& name);

AstNode* selectStructuralChild(
    AstNode& parent,
    const std::string& name);

ItemDeclarationNode* selectStructuralItem(
    AstNode& parent,
    const std::string& name);

} // namespace qps::ast
