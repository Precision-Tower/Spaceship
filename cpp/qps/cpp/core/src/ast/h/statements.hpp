// qps/core/src/ast/h/statements.hpp

#ifndef QPS_AST_H_STATEMENTS_HPP
#define QPS_AST_H_STATEMENTS_HPP

#include <vector>
#include <memory>
#include <string>
#include "../ast_node.hpp"

// Forward declarations for types used within these statements.
namespace qps {
namespace ast {
    class AstNode; // Base class
    class ItemDeclarationNode;
    class ContainerNode;
    class ExecutionBlockNode; // Used by many statements for their bodies
    // Also forward declare specific statement nodes if they refer to each other (e.g., If referring to Elif/Else)
    class ElifStatementNode;
    class ElseStatementNode;
}
namespace visitors {
    class AstVisitor; // Visitor interface
}
}

namespace qps {
namespace ast {

// ProgramNode: The root of the AST, representing an entire .qps file.
// It's conceptually a statement list, but is typically the root of the AST.
// Placed here for simplicity as it contains other statements.
class ProgramNode : public AstNode {
public:
    ProgramNode(int line, int column);
    std::vector<std::unique_ptr<AstNode>> statements; // Top-level declarations/statements
    void accept(visitors::AstVisitor& visitor) override;
};

// ExecutionBlockNode: Represents a '{ ... }' executable block (e.g., function body, loop body).
class ExecutionBlockNode : public AstNode {
public:
    ExecutionBlockNode(int line, int column);
    std::vector<std::unique_ptr<AstNode>> statements; // Statements within the block
    void accept(visitors::AstVisitor& visitor) override;
};

enum class ExecutionDomain {
    GENERIC,
    GEOMETRY
};

// ExecutionDefinitionNode: Represents an addressable reusable execution definition: {id: ...}.
class ExecutionDefinitionNode : public AstNode {
public:
    ExecutionDefinitionNode(
        const std::string& identifier,
        bool identifier_is_numeric,
        ExecutionDomain domain,
        std::unique_ptr<ExecutionBlockNode> body,
        int line,
        int column);

    std::string identifier_;
    bool identifier_is_numeric_;
    ExecutionDomain domain_;
    std::unique_ptr<ExecutionBlockNode> body_;

    void accept(visitors::AstVisitor& visitor) override;
};

// ExecutionCallNode: Represents a fresh instance call: {>id: overrides...}.
class ExecutionCallNode : public AstNode {
public:
    ExecutionCallNode(
        const std::string& identifier,
        bool identifier_is_numeric,
        int line,
        int column);
    ~ExecutionCallNode() override;

    std::string identifier_;
    bool identifier_is_numeric_;
    std::vector<std::unique_ptr<ItemDeclarationNode>> arguments_;

    void addArgument(std::unique_ptr<ItemDeclarationNode> argument);
    void accept(visitors::AstVisitor& visitor) override;
};

// ExecutionActionNode: Represents a QPS execution-language action such as
// '-cylinder' or 'body -bore(...)'. The domain selects the dispatcher.
class ExecutionActionNode : public AstNode {
public:
    ExecutionActionNode(
        const std::string& action_name,
        std::unique_ptr<AstNode> source,
        std::unique_ptr<ContainerNode> parameters,
        int line,
        int column);
    ~ExecutionActionNode() override;

    std::string action_name_;

    AstNode* getSource() const;
    ContainerNode* getParameters() const;

    void accept(visitors::AstVisitor& visitor) override;

private:
    std::unique_ptr<AstNode> source_;
    std::unique_ptr<ContainerNode> parameters_;
};

// LetStatementNode: Represents a '-let identifier initial_value/type_;' or '-let identifier_;'
class LetStatementNode : public AstNode {
public:
    LetStatementNode(const std::string& identifier, int line, int column);
    std::string identifier_;
    std::unique_ptr<AstNode> initial_value_; // Optional: can be null if not initialized
    void accept(visitors::AstVisitor& visitor) override;
};

// SetStatementNode: Represents a '-set target_path value/type_;'
class SetStatementNode : public AstNode {
public:
    SetStatementNode(std::unique_ptr<AstNode> target, std::unique_ptr<AstNode> value, int line, int column);
    std::unique_ptr<AstNode> target_; // The path/identifier being assigned to
    std::unique_ptr<AstNode> value_;  // The new value being assigned
    void accept(visitors::AstVisitor& visitor) override;
};

// AssertStatementNode: Represents an '-assert condition_;'
class AssertStatementNode : public AstNode {
public:
    AssertStatementNode(std::unique_ptr<AstNode> condition, int line, int column);
    std::unique_ptr<AstNode> condition_; // The expression that must evaluate to true
    void accept(visitors::AstVisitor& visitor) override;
};

// BreakStatementNode: Represents a '-break_;' statement for loop control.
class BreakStatementNode : public AstNode {
public:
    BreakStatementNode(int line, int column);
    void accept(visitors::AstVisitor& visitor) override;
};

// ContinueStatementNode: Represents a '-continue_;' statement for loop control.
class ContinueStatementNode : public AstNode {
public:
    ContinueStatementNode(int line, int column);
    void accept(visitors::AstVisitor& visitor) override;
};

// ElifStatementNode: Represents an '-elif condition { body }' block.
class ElifStatementNode : public AstNode {
public:
    ElifStatementNode(std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::unique_ptr<AstNode> condition_;
    std::unique_ptr<ExecutionBlockNode> body_;
    void accept(visitors::AstVisitor& visitor) override;
};

// ElseStatementNode: Represents an '-else { body }' block.
class ElseStatementNode : public AstNode {
public:
    ElseStatementNode(std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::unique_ptr<ExecutionBlockNode> body_;
    void accept(visitors::AstVisitor& visitor) override;
};

// ForStatementNode: Represents a '-for (control_expression) { body }_' statement for iteration.
class ForStatementNode : public AstNode {
public:
    ForStatementNode(std::unique_ptr<AstNode> loop_control, std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::unique_ptr<AstNode> loop_control_;
    std::unique_ptr<ExecutionBlockNode> body_;
    void accept(visitors::AstVisitor& visitor) override;
};

// IfStatementNode: Represents an '-if condition { body }' with optional elif and else blocks.
class IfStatementNode : public AstNode {
public:
    IfStatementNode(std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::unique_ptr<AstNode> condition_;
    std::unique_ptr<ExecutionBlockNode> body_;
    std::vector<std::unique_ptr<ElifStatementNode>> elif_blocks_;
    std::unique_ptr<ElseStatementNode> else_block_;
    void addElifBlock(std::unique_ptr<ElifStatementNode> elif_node);
    void setElseBlock(std::unique_ptr<ElseStatementNode> else_node);
    void accept(visitors::AstVisitor& visitor) override;
};

// LoopStatementNode: Represents an '-loop { body }_' statement for unconditional iteration.
class LoopStatementNode : public AstNode {
public:
    LoopStatementNode(std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::unique_ptr<ExecutionBlockNode> body_;
    void accept(visitors::AstVisitor& visitor) override;
};

// PrintStatementNode: Represents a '-print expression_;' statement to output a value.
class PrintStatementNode : public AstNode {
public:
    PrintStatementNode(std::unique_ptr<AstNode> expression, int line, int column);
    std::unique_ptr<AstNode> expression_;
    void accept(visitors::AstVisitor& visitor) override;
};

// ReturnStatementNode: Represents a '-return- expression_;' statement to return a value from a function.
class ReturnStatementNode : public AstNode {
public:
    ReturnStatementNode(std::unique_ptr<AstNode> expression, int line, int column);
    std::unique_ptr<AstNode> expression_;
    void accept(visitors::AstVisitor& visitor) override;
};

// RaiseStatementNode: Represents a '-raise message_;' statement to signal an error or exception.
class RaiseStatementNode : public AstNode {
public:
    RaiseStatementNode(std::unique_ptr<AstNode> message, int line, int column);
    std::unique_ptr<AstNode> message_;
    void accept(visitors::AstVisitor& visitor) override;
};

// TryStatementNode: Represents a '-try { body }' block, with optional catch and finally blocks.
class TryStatementNode : public AstNode {
public:
    TryStatementNode(std::unique_ptr<ExecutionBlockNode> try_body, int line, int column);
    std::unique_ptr<ExecutionBlockNode> try_body_;
    void accept(visitors::AstVisitor& visitor) override;
};

// WhileStatementNode: Represents a '-while condition { body }_' statement for conditional iteration.
class WhileStatementNode : public AstNode {
public:
    WhileStatementNode(std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column);
    std::unique_ptr<AstNode> condition_;
    std::unique_ptr<ExecutionBlockNode> body_;
    void accept(visitors::AstVisitor& visitor) override;
};

// PassStatementNode: Represents a '-pass_;' statement (no-op).
class PassStatementNode : public AstNode {
public:
    PassStatementNode(int line, int column);
    void accept(visitors::AstVisitor& visitor) override;
};

} // namespace ast
} // namespace qps

#endif // QPS_AST_H_STATEMENTS_HPP
