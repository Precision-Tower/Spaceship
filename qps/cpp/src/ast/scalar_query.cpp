#include "scalar_query.hpp"
#include "structural_selection.hpp"

#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace qps::ast {
namespace {

std::string scalarValue(
    const AstNode& node) {

    if (const auto* value =
            dynamic_cast<const StringLiteralNode*>(&node)) {
        return value->value_;
    }

    if (const auto* value =
            dynamic_cast<const NumericLiteralNode*>(&node)) {
        std::ostringstream out;
        out << value->value_;
        return out.str();
    }

    if (const auto* value =
            dynamic_cast<const BooleanLiteralNode*>(&node)) {
        return value->value_ ? "true" : "false";
    }

    if (dynamic_cast<const NullLiteralNode*>(&node)) {
        return "null";
    }

    throw std::runtime_error(
        "QPS query target is not a scalar value.");
}

} // namespace

std::string queryScalar(
    const ProgramNode& program,
    const std::string& query_path) {

    const AstNode* target =
        selectStructuralPath(
            program,
            query_path);

    if (!target) {
        throw std::runtime_error(
            "QPS query path not found: " +
            query_path);
    }

    const auto* item =
        dynamic_cast<const ItemDeclarationNode*>(
            target);

    if (!item) {
        throw std::runtime_error(
            "QPS query target is structural, not a scalar Item: " +
            query_path);
    }

    if (!item->value_node_) {
        throw std::runtime_error(
            "QPS query target Item has no value: " +
            query_path);
    }

    return scalarValue(*item->value_node_);
}


} // namespace qps::ast
