// qps/core/src/visitors/print.hpp

#ifndef QPS_VISITORS_PRINT_HPP
#define QPS_VISITORS_PRINT_HPP

#include "../ast_interface.hpp" // Update: Path changed to reflect new directory structure
#include <iostream>          // For std::cout
#include <string>            // For indentation strings

namespace qps {
namespace visitors {

// The PrintVisitor is a concrete implementation of AstVisitor.
// Its purpose is to traverse the Abstract Syntax Tree and print a human-readable
// representation of its structure and content to standard output.
class PrintVisitor : public AstVisitor {
public:
    // Constructor initializes the indentation level.
    explicit PrintVisitor(int initial_indent = 0) : indent_level_(initial_indent) {}

    // Destructor (defaulted as there's no dynamic memory to manage).
    ~PrintVisitor() override = default;

    // --- Implementations of visit methods for each AST node type ---
    // These methods will be called polymorphically via AstNode::accept().

    void visit(ast::ProgramNode* node) override;
    void visit(ast::ItemDeclarationNode* node) override;
    void visit(ast::TermDeclarationNode* node) override;
    void visit(ast::KeyDeclarationNode* node) override;
    void visit(ast::DictionaryDeclarationNode* node) override;
    void visit(ast::DictionaryEntryNode* node) override;
    void visit(ast::ContainerNode* node) override;
    void visit(ast::CausalDefinitionNode* node) override;
    void visit(ast::CausalRelationshipNode* node) override;
    void visit(ast::FunctionDeclarationNode* node) override;
    void visit(ast::ClassDeclarationNode* node) override;
    void visit(ast::StringLiteralNode* node) override;
    void visit(ast::NumericLiteralNode* node) override;
    void visit(ast::BooleanLiteralNode* node) override;
    void visit(ast::NullLiteralNode* node) override;
    void visit(ast::PathReferenceNode* node) override;
    void visit(ast::SymbolReferenceNode* node) override;
    void visit(ast::IdentifierNode* node) override;
    void visit(ast::BinaryExpressionNode* node) override;
    void visit(ast::FunctionCallNode* node) override;
    void visit(ast::CalculationNode* node) override;
    void visit(ast::ExecutionBlockNode* node) override;
    void visit(ast::ExecutionDefinitionNode* node) override;
    void visit(ast::ExecutionCallNode* node) override;
    void visit(ast::ExecutionActionNode* node) override;
    void visit(ast::TestDeclarationNode* node) override;
    void visit(ast::LetStatementNode* node) override;
    void visit(ast::SetStatementNode* node) override;
    void visit(ast::AssertStatementNode* node) override;
    void visit(ast::FailStatementNode* node) override;
    void visit(ast::RaisesStatementNode* node) override;
    void visit(ast::BreakStatementNode* node) override;
    void visit(ast::ContinueStatementNode* node) override;
    void visit(ast::ElifStatementNode* node) override;
    void visit(ast::ElseStatementNode* node) override;
    void visit(ast::ForStatementNode* node) override;
    void visit(ast::IfStatementNode* node) override;
    void visit(ast::LoopStatementNode* node) override;
    void visit(ast::PrintStatementNode* node) override;
    void visit(ast::ReturnStatementNode* node) override;
    void visit(ast::RaiseStatementNode* node) override;
    void visit(ast::TryStatementNode* node) override;
    void visit(ast::WhileStatementNode* node) override;
    void visit(ast::PassStatementNode* node) override;

private:
    int indent_level_; // Current indentation level for pretty-printing
    std::string getIndent() const; // Helper to get the current indent string
};

} // namespace visitors
} // namespace qps

#endif // QPS_VISITORS_PRINT_HPP
