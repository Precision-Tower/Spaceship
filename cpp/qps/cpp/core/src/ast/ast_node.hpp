// qps/core/src/ast/ast_node.hpp

#ifndef QPS_AST_NODE_HPP
#define QPS_AST_NODE_HPP

#include <vector>
#include <memory>   // For std::unique_ptr
#include <string>   // For holding names, definitions etc.
#include <variant>  // For holding literal values in ValueNode

// Forward declare all AST node types as they are now defined in modular headers
// This is done to ensure the AstVisitor interface (which needs to see all nodes)
// can be declared without circular dependencies, and for general forward declarations
// for pointers/references between node types.
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
    class CausalDefinitionNode;
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
    class CalculationNode;
    class ExecutionBlockNode;
    class ExecutionDefinitionNode;
    class ExecutionCallNode;
    class FunctionCallNode;
    class ExecutionActionNode;
    class TestDeclarationNode;
    class LetStatementNode;
    class SetStatementNode;
    class AssertStatementNode;
    class FailStatementNode;
    class RaisesStatementNode;
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
} // namespace ast

namespace visitors {
    class AstVisitor; // Forward declare the AstVisitor interface
} // namespace visitors
} // namespace qps


namespace qps {
namespace ast {

// Enum to categorize different types of AST nodes.
// This remains here as it's a global classification of all nodes.
enum class AstNodeType {
    PROGRAM,
    ITEM_DECLARATION,
    TERM_DECLARATION,
    KEY_DECLARATION,
    DICTIONARY_DECLARATION,
    CONTAINER,
    CAUSAL_RELATIONSHIP,
    CAUSAL_DEFINITION,
    FUNCTION_DECLARATION,
    CLASS_DECLARATION,
    DEFINITION_STRING, // Special type for 'def"..."' string literal content
    NUMERIC_LITERAL,
    STRING_LITERAL,
    BOOLEAN_LITERAL,
    NULL_LITERAL,
    PATH_REFERENCE,
    SYMBOL_REFERENCE,
    DICT_INPUT_REFERENCE,
    DICT_OUTPUT_REFERENCE,
    BINARY_EXPRESSION,
    UNARY_EXPRESSION,
    CALCULATION,
    EXECUTION_BLOCK,
    EXECUTION_DEFINITION,
    EXECUTION_CALL,
    EXECUTION_ACTION,
    TEST_DECLARATION,
    FUNCTION_CALL,
    IDENTIFIER,
    // Control flow and other executable statements
    LET_STATEMENT,
    SET_STATEMENT,
    IF_STATEMENT,
    ELSE_STATEMENT,
    ELIF_STATEMENT,
    LOOP_STATEMENT,
    WHILE_STATEMENT,
    FOR_STATEMENT,
    RETURN_STATEMENT,
    PRINT_STATEMENT,
    ASSERT_STATEMENT,
    FAIL_STATEMENT,
    RAISES_STATEMENT,
    TRY_STATEMENT,
    RAISE_STATEMENT,
    BREAK_STATEMENT,
    CONTINUE_STATEMENT,
    PASS_STATEMENT
};

// Base class for all Abstract Syntax Tree nodes.
// Each node represents a construct in the QPS language.
// It uses a virtual destructor to ensure proper cleanup of derived classes.
class AstNode {
public:
    AstNode(AstNodeType type, int line, int column)
        : type_(type), line_(line), column_(column) {}

    virtual ~AstNode() = default;

    AstNodeType getType() const { return type_; }
    int getLine() const { return line_; }
    int getColumn() const { return column_; }

    // Virtual method to accept a visitor.
    // Each concrete AST node will implement this to call the appropriate visit method
    // on the passed visitor.
    virtual void accept(visitors::AstVisitor& visitor) = 0;

protected:
    AstNodeType type_;
    int line_;
    int column_;
};

} // namespace ast
} // namespace qps

// Include modular AST node declarations
// These headers now define the concrete AST node classes.
#include "h/declarations.hpp"
#include "h/expressions.hpp"
#include "h/statements.hpp"

#endif // QPS_AST_NODE_HPP
