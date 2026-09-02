// qps/core/src/ast/c/expressions.cpp

#include "../h/expressions.hpp" // Expressions specific header
#include "../../visitors/ast_interface.hpp" // For AstVisitor acceptance
#include <algorithm> // For std::remove_if
#include <sstream>   // For stringstream in parsePath
#include <utility>   // For std::move

namespace qps {
namespace ast {

// --- Expressions Node Implementations ---

// StringLiteralNode
StringLiteralNode::StringLiteralNode(const std::string& value, int line, int column)
    : AstNode(AstNodeType::STRING_LITERAL, line, column), value_(value) {}

void StringLiteralNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// NumericLiteralNode
NumericLiteralNode::NumericLiteralNode(double value, int line, int column)
    : AstNode(AstNodeType::NUMERIC_LITERAL, line, column), value_(value) {}

void NumericLiteralNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// BooleanLiteralNode
BooleanLiteralNode::BooleanLiteralNode(bool value, int line, int column)
    : AstNode(AstNodeType::BOOLEAN_LITERAL, line, column), value_(value) {}

void BooleanLiteralNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// NullLiteralNode
NullLiteralNode::NullLiteralNode(int line, int column)
    : AstNode(AstNodeType::NULL_LITERAL, line, column) {}

void NullLiteralNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// PathReferenceNode
PathReferenceNode::PathReferenceNode(const std::string& path, int line, int column)
    : AstNode(AstNodeType::PATH_REFERENCE, line, column), path_segments_(parsePath(path)) {}

const std::vector<std::string>& PathReferenceNode::getPathSegments() const {
    return path_segments_;
}

// Helper to split path string into segments.
std::vector<std::string> PathReferenceNode::parsePath(const std::string& path_str) {
    std::vector<std::string> segments;
    std::string current_segment;
    std::istringstream iss(path_str);
    char c;
    while (iss.get(c)) {
        if (c == '/' || c == '.') {
            if (!current_segment.empty()) {
                segments.push_back(current_segment);
                current_segment = "";
            }
        } else {
            current_segment += c;
        }
    }
    if (!current_segment.empty()) {
        segments.push_back(current_segment);
    }
    return segments;
}

void PathReferenceNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}


// SymbolReferenceNode
SymbolReferenceNode::SymbolReferenceNode(
    const std::string& symbol,
    SymbolReferenceOrigin origin,
    int parent_depth,
    std::vector<SymbolReferenceSegment> segments,
    bool selects_item_value,
    int line,
    int column)
    : AstNode(AstNodeType::SYMBOL_REFERENCE, line, column),
      symbol_(symbol),
      origin_(origin),
      parent_depth_(parent_depth),
      segments_(std::move(segments)),
      selects_item_value_(selects_item_value) {}

const std::string& SymbolReferenceNode::getSymbol() const {
    return symbol_;
}

SymbolReferenceOrigin SymbolReferenceNode::getOrigin() const {
    return origin_;
}

int SymbolReferenceNode::getParentDepth() const {
    return parent_depth_;
}

const std::vector<SymbolReferenceSegment>&
SymbolReferenceNode::getSegments() const {
    return segments_;
}

bool SymbolReferenceNode::selectsItemValue() const {
    return selects_item_value_;
}

void SymbolReferenceNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// IdentifierNode
IdentifierNode::IdentifierNode(const std::string& name, int line, int column)
    : AstNode(AstNodeType::IDENTIFIER, line, column), name_(name) {}

void IdentifierNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// FunctionCallNode
FunctionCallNode::FunctionCallNode(const std::string& name, int line, int column)
    : AstNode(AstNodeType::FUNCTION_CALL, line, column), name_(name) {}

void FunctionCallNode::addArgument(std::unique_ptr<AstNode> argument) {
    arguments_.push_back(std::move(argument));
}

void FunctionCallNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// BinaryExpressionNode
BinaryExpressionNode::BinaryExpressionNode(std::unique_ptr<AstNode> left, Operator op, std::unique_ptr<AstNode> right, int line, int column)
    : AstNode(AstNodeType::BINARY_EXPRESSION, line, column), left_(std::move(left)), op_(op), right_(std::move(right)) {}

AstNode* BinaryExpressionNode::getLeft() const { return left_.get(); }
AstNode* BinaryExpressionNode::getRight() const { return right_.get(); }
BinaryExpressionNode::Operator BinaryExpressionNode::getOperator() const { return op_; }

void BinaryExpressionNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// CalculationNode
CalculationNode::CalculationNode(std::unique_ptr<AstNode> target,
                                 std::unique_ptr<AstNode> expression,
                                 int line, int column)
    : AstNode(AstNodeType::CALCULATION, line, column),
      target_(std::move(target)),
      expression_(std::move(expression)) {}

AstNode* CalculationNode::getTarget() const {
    return target_.get();
}

AstNode* CalculationNode::getExpression() const {
    return expression_.get();
}

bool CalculationNode::hasTarget() const {
    return target_ != nullptr;
}

void CalculationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

} // namespace ast
} // namespace qps
