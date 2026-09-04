// qps/core/src/ast/h/expressions.hpp

#ifndef QPS_AST_H_EXPRESSIONS_HPP
#define QPS_AST_H_EXPRESSIONS_HPP

#include <string>
#include <vector>
#include <memory>
#include <variant> // For literal values
#include "../ast_node.hpp"

// Forward declarations for types used within these expressions.
namespace qps {
namespace ast {
    class AstNode; // Base class
}
namespace visitors {
    class AstVisitor; // Visitor interface
}
}

namespace qps {
namespace ast {

// StringLiteralNode: Represents "value"
class StringLiteralNode : public AstNode {
public:
    StringLiteralNode(const std::string& value, int line, int column);
    std::string value_;
    void accept(visitors::AstVisitor& visitor) override;
};

// NumericLiteralNode: Represents a numeric value (e.g., 10, 3.14)
class NumericLiteralNode : public AstNode {
public:
    NumericLiteralNode(double value, int line, int column);
    double value_;
    void accept(visitors::AstVisitor& visitor) override;
};

// BooleanLiteralNode: Represents 'true' or 'false'
class BooleanLiteralNode : public AstNode {
public:
    BooleanLiteralNode(bool value, int line, int column);
    bool value_;
    void accept(visitors::AstVisitor& visitor) override;
};

// NullLiteralNode: Represents 'null'
class NullLiteralNode : public AstNode {
public:
    NullLiteralNode(int line, int column);
    void accept(visitors::AstVisitor& visitor) override;
};

// PathReferenceNode: Represents a reference like 'folder/file.key.item-'
class PathReferenceNode : public AstNode {
public:
    PathReferenceNode(const std::string& path, int line, int column);
    const std::vector<std::string>& getPathSegments() const;

private:
    std::vector<std::string> path_segments_;
    std::vector<std::string> parsePath(const std::string& path_str); // Helper to split path
    void accept(visitors::AstVisitor& visitor) override;
};


enum class SymbolReferenceOrigin {
    // [>name]
    CURRENT_FILE,

    // [>.file.name]
    CURRENT_FOLDER_FILE,

    // [>/file.name], [>//file.name], [>folder/file.name]
    RELATIVE_MODULE,

    // [v.child]
    //
    // Navigation begins from an already-bound local structural root.
    LOCAL_BINDING
};

enum class SymbolReferenceSeparator {
    ROOT,
    SLASH,
    DOT
};

struct SymbolReferenceSegment {
    std::string name;
    SymbolReferenceSeparator separator =
        SymbolReferenceSeparator::ROOT;
};

// SymbolReferenceNode preserves scoped QPS navigation syntax.
//
// Examples:
//   [>key.term]
//   [>folder/file.key.term]
//   [>/file.key.term]
//   [>//file.key.term]
//
// Interpretation of those segments belongs to semantic resolution.
// The AST preserves authored navigation without flattening it.
class SymbolReferenceNode : public AstNode {
public:
    SymbolReferenceNode(
        const std::string& symbol,
        SymbolReferenceOrigin origin,
        int parent_depth,
        std::vector<SymbolReferenceSegment> segments,
        bool selects_item_value,
        int line,
        int column);

    // Authored reference path.
    //
    // Examples:
    //   key.dimensions
    //   key.dimensions.body.radius-
    const std::string& getSymbol() const;

    SymbolReferenceOrigin getOrigin() const;

    int getParentDepth() const;

    const std::vector<SymbolReferenceSegment>&
    getSegments() const;

    // True only when the reference explicitly ends in '-':
    //
    //   [>key.dimensions.body.radius-]
    //
    // Structural references such as [>key.dimensions] remain false.
    bool selectsItemValue() const;

private:
    std::string symbol_;
    SymbolReferenceOrigin origin_ =
        SymbolReferenceOrigin::CURRENT_FILE;
    int parent_depth_ = 0;
    std::vector<SymbolReferenceSegment> segments_;
    bool selects_item_value_ = false;

    void accept(visitors::AstVisitor& visitor) override;
};

// IdentifierNode: Represents a generic identifier (e.g., a variable name, function name segment)
class IdentifierNode : public AstNode {
public:
    IdentifierNode(const std::string& name, int line, int column);
    std::string name_;
    void accept(visitors::AstVisitor& visitor) override;
};

// FunctionCallNode: Represents a primary expression call like name(arg1, arg2)
class FunctionCallNode : public AstNode {
public:
    FunctionCallNode(const std::string& name, int line, int column);

    std::string name_;
    std::vector<std::unique_ptr<AstNode>> arguments_;

    void addArgument(std::unique_ptr<AstNode> argument);

    void accept(visitors::AstVisitor& visitor) override;
};

// BinaryExpressionNode: Represents mathematical operations like A + B, C * D
class BinaryExpressionNode : public AstNode {
public:
    enum class Operator { ADD, SUBTRACT, MULTIPLY, DIVIDE, EQUAL };

    BinaryExpressionNode(std::unique_ptr<AstNode> left, Operator op, std::unique_ptr<AstNode> right, int line, int column);
    AstNode* getLeft() const;
    AstNode* getRight() const;
    Operator getOperator() const;

private:
    std::unique_ptr<AstNode> left_;
    Operator op_;
    std::unique_ptr<AstNode> right_;
    void accept(visitors::AstVisitor& visitor) override;
};

// CalculationNode: Represents one % calculation inside an execution block.
//
// Target semantics:
//   %a: ...      -> local execution binding "a"
//   %1: ...      -> local execution binding "1"
//   %[>a]: ...   -> semantic binding to canonical symbol "a"
//
// The target is syntax, not merely a stored string, so the AST preserves
// whether the result is local or semantically bound.
class CalculationNode : public AstNode {
public:
    CalculationNode(std::unique_ptr<AstNode> target,
                    std::unique_ptr<AstNode> expression,
                    int line, int column);

    AstNode* getTarget() const;
    AstNode* getExpression() const;
    bool hasTarget() const;

private:
    std::unique_ptr<AstNode> target_;
    std::unique_ptr<AstNode> expression_;
    void accept(visitors::AstVisitor& visitor) override;
};

} // namespace ast
} // namespace qps

#endif // QPS_AST_H_EXPRESSIONS_HPP
