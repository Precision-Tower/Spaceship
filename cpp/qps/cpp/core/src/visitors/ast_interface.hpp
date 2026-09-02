// qps/core/src/visitors/ast_interface.hpp

#ifndef QPS_VISITORS_AST_INTERFACE_HPP
#define QPS_VISITORS_AST_INTERFACE_HPP

// Forward declare all AST node types to avoid circular includes
// These are necessary because the AstVisitor will have visit() methods for each concrete AST node.
namespace qps {
namespace ast {
    class ProgramNode;
    class ItemDeclarationNode;
    class TermDeclarationNode;
    class KeyDeclarationNode;
    class DictionaryDeclarationNode;
    class DictionaryEntryNode;
    class ContainerNode;
    class CausalRelationshipNode;
    class FunctionDeclarationNode;
    class ClassDeclarationNode;
    class StringLiteralNode;
    class NumericLiteralNode;
    class BooleanLiteralNode;
    class NullLiteralNode;
    class PathReferenceNode;
    class SymbolReferenceNode;
    class IdentifierNode;
    class BinaryExpressionNode;
    class FunctionCallNode;
    class CalculationNode;
    class ExecutionBlockNode;
    class ExecutionDefinitionNode;
    class ExecutionCallNode;
    class ExecutionActionNode;
    class LetStatementNode;
    class SetStatementNode;
    class AssertStatementNode;
    class BreakStatementNode;
    class ContinueStatementNode;
    class ElifStatementNode;
    class ElseStatementNode;
    class ForStatementNode;
    class IfStatementNode;
    class LoopStatementNode;
    class PrintStatementNode;
    class ReturnStatementNode;
    class RaiseStatementNode;
    class TryStatementNode;
    class WhileStatementNode;
    class PassStatementNode;
    // Add any other AST node types as they are defined
} // namespace ast

namespace visitors {

// Abstract base class for all AST visitors.
// This interface defines a 'visit' method for each concrete AST node type.
// Any class that wishes to operate on the AST without modifying the AST nodes themselves
// will implement this interface.
class AstVisitor {
public:
    virtual ~AstVisitor() = default;

    // Pure virtual visit methods for each concrete AST node.
    // These methods must be implemented by any concrete visitor.
    virtual void visit(ast::ProgramNode* node) = 0;
    virtual void visit(ast::ItemDeclarationNode* node) = 0;
    virtual void visit(ast::TermDeclarationNode* node) = 0;
    virtual void visit(ast::KeyDeclarationNode* node) = 0;
    virtual void visit(ast::DictionaryDeclarationNode* node) = 0;
    virtual void visit(ast::DictionaryEntryNode* node) = 0;
    virtual void visit(ast::ContainerNode* node) = 0;
    virtual void visit(ast::CausalRelationshipNode* node) = 0;
    virtual void visit(ast::FunctionDeclarationNode* node) = 0;
    virtual void visit(ast::ClassDeclarationNode* node) = 0;
    virtual void visit(ast::StringLiteralNode* node) = 0;
    virtual void visit(ast::NumericLiteralNode* node) = 0;
    virtual void visit(ast::BooleanLiteralNode* node) = 0;
    virtual void visit(ast::NullLiteralNode* node) = 0;
    virtual void visit(ast::PathReferenceNode* node) = 0;
    virtual void visit(ast::SymbolReferenceNode* node) = 0;
    virtual void visit(ast::IdentifierNode* node) = 0;
    virtual void visit(ast::BinaryExpressionNode* node) = 0;
    virtual void visit(ast::FunctionCallNode* node) = 0;
    virtual void visit(ast::CalculationNode* node) = 0;
    virtual void visit(ast::ExecutionBlockNode* node) = 0;
    virtual void visit(ast::ExecutionDefinitionNode* node) = 0;
    virtual void visit(ast::ExecutionCallNode* node) = 0;
    virtual void visit(ast::ExecutionActionNode* node) = 0;
    virtual void visit(ast::LetStatementNode* node) = 0;
    virtual void visit(ast::SetStatementNode* node) = 0;
    virtual void visit(ast::AssertStatementNode* node) = 0;
    virtual void visit(ast::BreakStatementNode* node) = 0;
    virtual void visit(ast::ContinueStatementNode* node) = 0;
    virtual void visit(ast::ElifStatementNode* node) = 0;
    virtual void visit(ast::ElseStatementNode* node) = 0;
    virtual void visit(ast::ForStatementNode* node) = 0;
    virtual void visit(ast::IfStatementNode* node) = 0;
    virtual void visit(ast::LoopStatementNode* node) = 0;
    virtual void visit(ast::PrintStatementNode* node) = 0;
    virtual void visit(ast::ReturnStatementNode* node) = 0;
    virtual void visit(ast::RaiseStatementNode* node) = 0;
    virtual void visit(ast::TryStatementNode* node) = 0;
    virtual void visit(ast::WhileStatementNode* node) = 0;
    virtual void visit(ast::PassStatementNode* node) = 0;
    // Add any other visit methods for new AST nodes here.
};

} // namespace visitors
} // namespace qps

#endif // QPS_VISITORS_AST_INTERFACE_HPP
