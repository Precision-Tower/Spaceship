// qps/core/src/visitors/open3d.hpp

#ifndef QPS_VISITORS_OPEN3D_HPP
#define QPS_VISITORS_OPEN3D_HPP

#include "../ast_interface.hpp" // Include the abstract AstVisitor interface
#include <iostream>          // For placeholder output
#include <string>
// #include <Open3D/Open3D.h> // Future: Include actual Open3D headers

namespace qps {
namespace visitors {

// The Open3DVisitor is a concrete implementation of AstVisitor.
// Its purpose is to traverse the Abstract Syntax Tree and generate
// Open3D visualization calls or construct Open3D data structures
// based on the parsed physical system definition.
// This is currently a placeholder, actual Open3D integration logic will be implemented here.
class Open3DVisitor : public AstVisitor {
public:
    explicit Open3DVisitor() {}

    ~Open3DVisitor() override = default;

    // --- Implementations of visit methods for each AST node type ---
    // These are currently placeholders that just print the node type.
    // Actual Open3D logic will involve calling Open3D API functions.

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
    // Future: Open3D data structures (e.g., std::shared_ptr<open3d::geometry::PointCloud> cloud;)
    // Future: Methods to build geometries, set camera, etc.
};

} // namespace visitors
} // namespace qps

#endif // QPS_VISITORS_OPEN3D_HPP
