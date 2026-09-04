// qps/core/src/ast/ast_utils.hpp

#ifndef QPS_AST_UTILS_HPP
#define QPS_AST_UTILS_HPP

#include "ast_node.hpp"

#include <memory>
#include <string>

namespace qps {
namespace ast {

std::unique_ptr<ProgramNode> createProgramNode(int line, int column);

std::unique_ptr<ItemDeclarationNode> createItemDeclarationNode(
    std::unique_ptr<AstNode> target,
    int line,
    int column);

std::unique_ptr<StringLiteralNode> createStringLiteralNode(
    const std::string& value, int line, int column);

std::unique_ptr<NumericLiteralNode> createNumericLiteralNode(
    double value, int line, int column);

std::unique_ptr<BooleanLiteralNode> createBooleanLiteralNode(
    bool value, int line, int column);

std::unique_ptr<NullLiteralNode> createNullLiteralNode(
    int line, int column);

std::unique_ptr<PathReferenceNode> createPathReferenceNode(
    const std::string& path, int line, int column);

std::unique_ptr<SymbolReferenceNode> createSymbolReferenceNode(
    const std::string& symbol,
    SymbolReferenceOrigin origin,
    int parent_depth,
    std::vector<SymbolReferenceSegment> segments,
    bool selects_item_value,
    int line,
    int column);

std::unique_ptr<IdentifierNode> createIdentifierNode(
    const std::string& name, int line, int column);

std::unique_ptr<FunctionCallNode> createFunctionCallNode(
    const std::string& name,
    int line,
    int column);

std::unique_ptr<TermDeclarationNode> createTermDeclarationNode(
    const std::string& identifier, int line, int column);

std::unique_ptr<KeyDeclarationNode> createKeyDeclarationNode(
    const std::string& identifier, int line, int column);

std::unique_ptr<ContainerNode> createContainerNode(
    int line, int column);

std::unique_ptr<DictionaryEntryNode> createDictionaryEntryNode(
    int id, int line, int column);

std::unique_ptr<DictionaryDeclarationNode> createDictionaryDeclarationNode(
    int line, int column);

std::unique_ptr<BinaryExpressionNode> createBinaryExpressionNode(
    std::unique_ptr<AstNode> left,
    BinaryExpressionNode::Operator op,
    std::unique_ptr<AstNode> right,
    int line, int column);

std::unique_ptr<CalculationNode> createCalculationNode(
    std::unique_ptr<AstNode> target,
    std::unique_ptr<AstNode> expression,
    int line, int column);

std::unique_ptr<ExecutionBlockNode> createExecutionBlockNode(
    int line, int column);

std::unique_ptr<ExecutionDefinitionNode> createExecutionDefinitionNode(
    const std::string& identifier,
    bool identifier_is_numeric,
    ExecutionDomain domain,
    std::unique_ptr<ExecutionBlockNode> body,
    int line,
    int column);

std::unique_ptr<ExecutionCallNode> createExecutionCallNode(
    const std::string& identifier,
    bool identifier_is_numeric,
    int line,
    int column);

std::unique_ptr<ExecutionActionNode> createExecutionActionNode(
    const std::string& action_name,
    std::unique_ptr<AstNode> source,
    std::unique_ptr<ContainerNode> parameters,
    int line,
    int column);

std::unique_ptr<TestDeclarationNode> createTestDeclarationNode(
    std::unique_ptr<ExecutionBlockNode> body,
    int line,
    int column);

std::unique_ptr<CausalDefinitionNode> createCausalDefinitionNode(
    const std::string& identifier,
    int line,
    int column);

std::unique_ptr<CausalRelationshipNode::CausalSide> createCausalSide(
    std::unique_ptr<AstNode> entity,
    std::unique_ptr<AstNode> input,
    std::unique_ptr<AstNode> output);

std::unique_ptr<CausalRelationshipNode> createCausalRelationshipNode(
    std::unique_ptr<CausalRelationshipNode::CausalSide> left,
    std::unique_ptr<CausalRelationshipNode::CausalSide> right,
    int line, int column);

std::unique_ptr<ClassDeclarationNode> createClassDeclarationNode(
    const std::string& name, int line, int column);

std::unique_ptr<FunctionDeclarationNode> createFunctionDeclarationNode(
    const std::string& name,
    std::unique_ptr<AstNode> params_node,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<LetStatementNode> createLetStatementNode(
    const std::string& identifier,
    std::unique_ptr<AstNode> initial_value,
    int line, int column);

std::unique_ptr<SetStatementNode> createSetStatementNode(
    std::unique_ptr<AstNode> target,
    std::unique_ptr<AstNode> value,
    int line, int column);

std::unique_ptr<AssertStatementNode> createAssertStatementNode(
    std::unique_ptr<AstNode> condition,
    int line, int column);

std::unique_ptr<FailStatementNode> createFailStatementNode(
    std::unique_ptr<AstNode> message,
    int line, int column);

std::unique_ptr<RaisesStatementNode> createRaisesStatementNode(
    const std::string& expected_message,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<BreakStatementNode> createBreakStatementNode(
    int line, int column);

std::unique_ptr<ContinueStatementNode> createContinueStatementNode(
    int line, int column);

std::unique_ptr<ElifStatementNode> createElifStatementNode(
    std::unique_ptr<AstNode> condition,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<ElseStatementNode> createElseStatementNode(
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<ForStatementNode> createForStatementNode(
    std::unique_ptr<AstNode> loop_control,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<IfStatementNode> createIfStatementNode(
    std::unique_ptr<AstNode> condition,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<LoopStatementNode> createLoopStatementNode(
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<PrintStatementNode> createPrintStatementNode(
    std::unique_ptr<AstNode> expression,
    int line, int column);

std::unique_ptr<ReturnStatementNode> createReturnStatementNode(
    std::unique_ptr<AstNode> expression,
    int line, int column);

std::unique_ptr<RaiseStatementNode> createRaiseStatementNode(
    std::unique_ptr<AstNode> message,
    int line, int column);

std::unique_ptr<TryStatementNode> createTryStatementNode(
    std::unique_ptr<ExecutionBlockNode> try_body,
    int line, int column);

std::unique_ptr<WhileStatementNode> createWhileStatementNode(
    std::unique_ptr<AstNode> condition,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column);

std::unique_ptr<PassStatementNode> createPassStatementNode(
    int line, int column);

} // namespace ast
} // namespace qps

#endif // QPS_AST_UTILS_HPP
