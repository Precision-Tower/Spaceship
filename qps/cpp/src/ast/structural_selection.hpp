#pragma once

#include "ast_node.hpp"

#include <string>

namespace qps::ast {

AstNode* selectStructuralChild(
    AstNode& parent,
    const std::string& name);

ItemDeclarationNode* selectStructuralItem(
    AstNode& parent,
    const std::string& name);

} // namespace qps::ast
