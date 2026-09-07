#pragma once

#include "ast_node.hpp"

#include <string>

namespace qps::ast {

/*
 * Observe a scalar Item value by authored structural path.
 *
 * Structural identity/navigation remains owned by
 * structural_selection. This mechanism only interprets the textual
 * selector and converts the terminal Item's scalar value to text.
 */
std::string queryScalar(
    const ProgramNode& document,
    const std::string& path);

} // namespace qps::ast
