// qps/core/src/visitors/type_check.hpp

#ifndef QPS_VISITORS_TYPE_CHECK_HPP
#define QPS_VISITORS_TYPE_CHECK_HPP

#include "../ast_interface.hpp" // Include the abstract AstVisitor interface
#include <iostream>          // For placeholder output (will be replaced by actual type checking logic)
#include <string>
#include <vector>
#include <map> // For symbol table (future use)

namespace qps {
namespace visitors {

// The TypeCheckVisitor is a concrete implementation of AstVisitor.
// Its purpose is to traverse the Abstract Syntax Tree and perform semantic analysis,
// primarily ensuring type compatibility and correct usage of identifiers.
// This is currently a placeholder, actual type checking logic will be implemented here.
class TypeCheckVisitor : public AstVisitor {
public:
    // Constructor (can take a reference to a symbol table or error reporter in a real implementation)
    explicit TypeCheckVisitor() {}

    // Destructor (defaulted).
    ~TypeCheckVisitor() override = default;

    // --- Implementations of visit methods for each AST node type ---
    // These are currently placeholders that just print the node type.
    // Actual type checking logic will involve checking child nodes' types,
    // resolving symbols, and reporting errors.

    void visit(ast::ProgramNode* node) override;
    void visit(ast::ItemDeclarationNode* node) override;
    void visit(ast::TermDeclarationNode* node) override;
    void visit(ast::KeyDeclarationNode* node) override;
    void visit(ast::DictionaryDeclarationNode* node) override;
    void visit(ast::DictionaryEntryNode* node) override;
    void visit(ast::ContainerNode* node) override;
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

    // A collection to store type-checking errors/warnings (for future implementation)
    std::vector<std::string> errors_;

private:
    // Future: Symbol table for tracking variable types and scopes
    // std::map<std::string, /* TypeInfo */> symbol_table_;
    // void enterScope();
    // void exitScope();
    // void defineSymbol(const std::string& name, /* TypeInfo */ type);
    // /* TypeInfo */ lookupSymbol(const std::string& name);
    // void reportError(const std::string& message, int line, int column);
};

} // namespace visitors
} // namespace qps

#endif // QPS_VISITORS_TYPE_CHECK_HPP
