// qps/core/src/ast/h/declarations.hpp

#ifndef QPS_AST_H_DECLARATIONS_HPP
#define QPS_AST_H_DECLARATIONS_HPP

#include <vector>
#include <memory>
#include <string>

// Forward declarations for types used within these declarations,
// to avoid circular dependencies if they are in other AST logical groups.
// These are essential because a declaration might contain other types of nodes (e.g., expressions).
#include "../ast_node.hpp"
#include <optional>
#include "../../tokens/h/token.hpp"

namespace qps {
namespace ast {
    class AstNode; // Base class
    class ExecutionBlockNode; // Used by Function/Class
    class ElifStatementNode; // Used by If
    class ElseStatementNode; // Used by If
}
namespace visitors {
    class AstVisitor; // Visitor interface
}
}

namespace qps {
namespace ast {

// ItemDeclarationNode: binds a value to a local or semantic target.
//
// Examples:
//   voltage- 30/n;   -> IdentifierNode target
//   [>v]- 30/n;      -> SymbolReferenceNode target
class ItemDeclarationNode : public AstNode {
public:
    ItemDeclarationNode(
        std::unique_ptr<AstNode> target,
        int line,
        int column);

    std::unique_ptr<AstNode> target_;
    std::unique_ptr<AstNode> value_node_;

    // Explicit source-level type annotation, if supplied.
    //
    // Examples:
    //   radius-;       -> none
    //   radius-/n;     -> TYPE_NUMERIC
    //   radius- 10;    -> none (literal may be inferred downstream)
    //   radius- 10/n;  -> TYPE_NUMERIC
    std::optional<tokens::TokenType> type_hint_;

    // Optional authored Engineering unit attached to this Item value.
    //
    // Examples:
    //   diameter- 1/in;
    //   depth- 5/mm;
    //   pressure- 120/psi;
    //
    // Unit semantics are resolved downstream by Engineering.
    std::optional<std::string> unit_hint_;

    AstNode* getTarget() const;

    void accept(visitors::AstVisitor& visitor) override;
};

// TermDeclarationNode: Represents 'term: content;'
class TermDeclarationNode : public AstNode {
public:
    TermDeclarationNode(const std::string& identifier, int line, int column);
    std::string identifier_;
    std::vector<std::unique_ptr<AstNode>> content_; // Can contain other declarations, literals, etc.

    // Execution-only statement qualification.
    //
    // False for ordinary authored Terms and unqualified local
    // structural bindings. True only when this Term was explicitly
    // introduced by '@' inside an execution definition.
    bool geometry_qualified_ = false;

    void accept(visitors::AstVisitor& visitor) override;
};

// KeyDeclarationNode: Represents 'key. content;'
class KeyDeclarationNode : public AstNode {
public:
    KeyDeclarationNode(const std::string& identifier, int line, int column);
    std::string identifier_;
    std::vector<std::unique_ptr<AstNode>> content_; // Can contain other declarations, literals, etc.
    void accept(visitors::AstVisitor& visitor) override;
};

// ContainerNode: Represents a '()' block for grouping
class ContainerNode : public AstNode {
public:
    ContainerNode(int line, int column);
    std::vector<std::unique_ptr<AstNode>> elements; // Elements within the container
    void accept(visitors::AstVisitor& visitor) override;
};

// DictionaryEntryNode: Represents a single entry in a dictionary, e.g., '1: <.potential: earth_potential;'
class DictionaryEntryNode : public AstNode {
public:
    DictionaryEntryNode(int id, int line, int column);
    int id_;
    std::unique_ptr<AstNode> value_node_; // The actual content of the dictionary entry
    void accept(visitors::AstVisitor& visitor) override;
};

// DictionaryDeclarationNode: Represents a '[]' block with multiple entries
class DictionaryDeclarationNode : public AstNode {
public:
    DictionaryDeclarationNode(int line, int column);
    std::vector<std::unique_ptr<DictionaryEntryNode>> entries; // Entries in the dictionary
    void accept(visitors::AstVisitor& visitor) override;
};

// CausalRelationshipNode: Represents an 'EntityA: (InputA = OutputA) = EntityB: (InputB = OutputB);'
class CausalRelationshipNode : public AstNode {
public:
    // Represents one side of the causal relationship (e.g., EntityA: (InputA = OutputA))
    struct CausalSide {
        std::unique_ptr<AstNode> entity;
        std::unique_ptr<AstNode> input;
        std::unique_ptr<AstNode> output;
    };

    CausalRelationshipNode(std::unique_ptr<CausalSide> left, std::unique_ptr<CausalSide> right, int line, int column);
    std::unique_ptr<CausalSide> left_side_;
    std::unique_ptr<CausalSide> right_side_;
    void accept(visitors::AstVisitor& visitor) override;
};

// ClassDeclarationNode: Represents a '-class key. { <member_definitions> };'
class ClassDeclarationNode : public AstNode {
public:
    ClassDeclarationNode(const std::string& name, int line, int column);
    std::string name_;
    std::vector<std::unique_ptr<AstNode>> members; // Can include function definitions, Key., Term:, Item-
    void accept(visitors::AstVisitor& visitor) override;
};

// FunctionDeclarationNode: Represents a '-func key. [> p1, p2]. { <body_statements> };'
class FunctionDeclarationNode : public AstNode {
public:
    FunctionDeclarationNode(const std::string& name, std::unique_ptr<AstNode> params_node,
                            std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::string name_;
    std::unique_ptr<AstNode> params_node_; // e.g., a Dictionary or Container node
    std::unique_ptr<ExecutionBlockNode> body_; // The executable block of the function
    void accept(visitors::AstVisitor& visitor) override;
};


} // namespace ast
} // namespace qps

#endif // QPS_AST_H_DECLARATIONS_HPP
