#pragma once

#include "engineering/quantity.hpp"

#include "ast/ast_node.hpp"

namespace engineering {

// Translate a dimensioned QPS Item value into an Engineering Quantity.
//
// QPS owns the authored structure:
//     diameter- 1/in;
//
// Engineering owns the meaning of "in" and its physical dimension.
//
// Plain numeric Items are not quantities and are rejected by this
// translation boundary.
Quantity makeQuantity(
    const qps::ast::ItemDeclarationNode& item);

} // namespace engineering
