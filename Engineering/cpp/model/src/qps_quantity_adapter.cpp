#include "engineering/qps_quantity_adapter.hpp"

#include <stdexcept>

namespace engineering {

Quantity makeQuantity(
    const qps::ast::ItemDeclarationNode& item) {

    if (!item.unit_hint_.has_value()) {
        throw std::runtime_error(
            "QPS Item does not declare an Engineering unit.");
    }

    const auto* numeric =
        dynamic_cast<const qps::ast::NumericLiteralNode*>(
            item.value_node_.get());

    if (numeric == nullptr) {
        throw std::runtime_error(
            "QPS Engineering quantity requires a numeric Item value.");
    }

    return Quantity::fromUnit(
        numeric->value_,
        *item.unit_hint_);
}

} // namespace engineering
