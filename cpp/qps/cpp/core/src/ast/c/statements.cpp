// qps/core/src/ast/c/statements.cpp

#include "../h/statements.hpp" // Statements specific header
#include "../h/declarations.hpp"
#include "../../visitors/ast_interface.hpp" // For AstVisitor acceptance
#include <utility> // For std::move

namespace qps {
namespace ast {

// --- Statements Node Implementations ---

// ProgramNode
ProgramNode::ProgramNode(int line, int column)
    : AstNode(AstNodeType::PROGRAM, line, column) {}

void ProgramNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ExecutionBlockNode
ExecutionBlockNode::ExecutionBlockNode(int line, int column)
    : AstNode(AstNodeType::EXECUTION_BLOCK, line, column) {}

void ExecutionBlockNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ExecutionDefinitionNode
ExecutionDefinitionNode::ExecutionDefinitionNode(
    const std::string& identifier,
    bool identifier_is_numeric,
    ExecutionDomain domain,
    std::unique_ptr<ExecutionBlockNode> body,
    int line,
    int column)
    : AstNode(AstNodeType::EXECUTION_DEFINITION, line, column),
      identifier_(identifier),
      identifier_is_numeric_(identifier_is_numeric),
      domain_(domain),
      body_(std::move(body)) {}

void ExecutionDefinitionNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ExecutionCallNode
ExecutionCallNode::ExecutionCallNode(
    const std::string& identifier,
    bool identifier_is_numeric,
    int line,
    int column)
    : AstNode(AstNodeType::EXECUTION_CALL, line, column),
      identifier_(identifier),
      identifier_is_numeric_(identifier_is_numeric) {}

ExecutionCallNode::~ExecutionCallNode() = default;

void ExecutionCallNode::addArgument(
    std::unique_ptr<ItemDeclarationNode> argument) {

    arguments_.push_back(std::move(argument));
}

void ExecutionCallNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ExecutionActionNode
ExecutionActionNode::ExecutionActionNode(
    const std::string& action_name,
    std::unique_ptr<AstNode> source,
    std::unique_ptr<ContainerNode> parameters,
    int line,
    int column)
    : AstNode(AstNodeType::EXECUTION_ACTION, line, column),
      action_name_(action_name),
      source_(std::move(source)),
      parameters_(std::move(parameters)) {}

ExecutionActionNode::~ExecutionActionNode() = default;

AstNode* ExecutionActionNode::getSource() const {
    return source_.get();
}

ContainerNode* ExecutionActionNode::getParameters() const {
    return parameters_.get();
}

void ExecutionActionNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// LetStatementNode
LetStatementNode::LetStatementNode(const std::string& identifier, int line, int column)
    : AstNode(AstNodeType::LET_STATEMENT, line, column), identifier_(identifier), initial_value_(nullptr) {}

void LetStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// SetStatementNode
SetStatementNode::SetStatementNode(std::unique_ptr<AstNode> target, std::unique_ptr<AstNode> value, int line, int column)
    : AstNode(AstNodeType::SET_STATEMENT, line, column), target_(std::move(target)), value_(std::move(value)) {}

void SetStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// AssertStatementNode
AssertStatementNode::AssertStatementNode(std::unique_ptr<AstNode> condition, int line, int column)
    : AstNode(AstNodeType::ASSERT_STATEMENT, line, column), condition_(std::move(condition)) {}

void AssertStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// BreakStatementNode
BreakStatementNode::BreakStatementNode(int line, int column)
    : AstNode(AstNodeType::BREAK_STATEMENT, line, column) {}

void BreakStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ContinueStatementNode
ContinueStatementNode::ContinueStatementNode(int line, int column)
    : AstNode(AstNodeType::CONTINUE_STATEMENT, line, column) {}

void ContinueStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ElifStatementNode
ElifStatementNode::ElifStatementNode(std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::ELIF_STATEMENT, line, column), condition_(std::move(condition)), body_(std::move(body)) {}

void ElifStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ElseStatementNode
ElseStatementNode::ElseStatementNode(std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::ELSE_STATEMENT, line, column), body_(std::move(body)) {}

void ElseStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ForStatementNode
ForStatementNode::ForStatementNode(std::unique_ptr<AstNode> loop_control, std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::FOR_STATEMENT, line, column), loop_control_(std::move(loop_control)), body_(std::move(body)) {}

void ForStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// IfStatementNode
IfStatementNode::IfStatementNode(std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::IF_STATEMENT, line, column), condition_(std::move(condition)), body_(std::move(body)) {}

void IfStatementNode::addElifBlock(std::unique_ptr<ElifStatementNode> elif_node) {
    elif_blocks_.push_back(std::move(elif_node));
}

void IfStatementNode::setElseBlock(std::unique_ptr<ElseStatementNode> else_node) {
    else_block_ = std::move(else_node);
}

void IfStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// LoopStatementNode
LoopStatementNode::LoopStatementNode(std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::LOOP_STATEMENT, line, column), body_(std::move(body)) {}

void LoopStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// PrintStatementNode
PrintStatementNode::PrintStatementNode(std::unique_ptr<AstNode> expression, int line, int column)
    : AstNode(AstNodeType::PRINT_STATEMENT, line, column), expression_(std::move(expression)) {}

void PrintStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ReturnStatementNode
ReturnStatementNode::ReturnStatementNode(std::unique_ptr<AstNode> expression, int line, int column)
    : AstNode(AstNodeType::RETURN_STATEMENT, line, column), expression_(std::move(expression)) {}

void ReturnStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// RaiseStatementNode
RaiseStatementNode::RaiseStatementNode(std::unique_ptr<AstNode> message, int line, int column)
    : AstNode(AstNodeType::RAISE_STATEMENT, line, column), message_(std::move(message)) {}

void RaiseStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// TryStatementNode
TryStatementNode::TryStatementNode(std::unique_ptr<ExecutionBlockNode> try_body, int line, int column)
    : AstNode(AstNodeType::TRY_STATEMENT, line, column), try_body_(std::move(try_body)) {}

void TryStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// WhileStatementNode
WhileStatementNode::WhileStatementNode(std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::WHILE_STATEMENT, line, column), condition_(std::move(condition)), body_(std::move(body)) {}

void WhileStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// PassStatementNode
PassStatementNode::PassStatementNode(int line, int column)
    : AstNode(AstNodeType::PASS_STATEMENT, line, column) {}

void PassStatementNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

} // namespace ast
} // namespace qps
