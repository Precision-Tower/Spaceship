#pragma once

#include "ast_node.hpp"

#include <string>

namespace qps::ast {

/*
 * Observe a scalar Item value by authored structural path.
 *
 * Structural identity/navigation is owned by structural_selection.
 * This mechanism interprets the textual selector and renders the
 * terminal Item scalar value.
 */
std::string queryScalar(
    const ProgramNode& document,
    const std::string& path);

} // namespace qps::ast
