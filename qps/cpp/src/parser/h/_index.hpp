// qps/core/src/parser/h/_index.hpp

#ifndef QPS_PARSER_H_INDEX_HPP
#define QPS_PARSER_H_INDEX_HPP

#include <memory>    // For std::unique_ptr
#include <vector>    // For holding sequences of nodes
#include <string>    // For identifiers and error messages
#include <stdexcept> // For parsing errors

#include "../../tokens/h/lexer.hpp" // Includes the Lexer for token input
#include "../../tokens/h/token.hpp" // Includes Token definitions
#include "../../ast/ast_node.hpp" // Includes AST node definitions

// Include all modular parser headers
#include "item.hpp"
#include "term.hpp"
#include "key.hpp"
#include "dictionary.hpp"
#include "container.hpp"
#include "causal.hpp"
#include "math.hpp"
#include "class.hpp"
#include "function.hpp"
#include "reference.hpp"
#include "value.hpp"
#include "library.hpp"
// Include modular statement headers
#include "statements/let.hpp"
#include "statements/set.hpp"
#include "statements/assert.hpp"
#include "statements/fail.hpp"
#include "statements/raises.hpp"
#include "statements/test.hpp"
#include "statements/break.hpp"
#include "statements/continue.hpp"
#include "statements/elif.hpp"
#include "statements/else.hpp"
#include "statements/for.hpp"
#include "statements/if.hpp"
#include "statements/loop.hpp"
#include "statements/print.hpp"
#include "statements/return.hpp"
#include "statements/raise.hpp"
#include "statements/try.hpp"
#include "statements/while.hpp"
#include "statements/pass.hpp"

namespace qps {
namespace parser {

// The Parser class is responsible for syntactic analysis.
// It consumes a stream of tokens from the Lexer and constructs an Abstract Syntax Tree (AST).
class Parser {
public:
    // Constructor: Initializes the Parser with a reference to a Lexer.
    explicit Parser(tokens::Lexer& lexer);

    // Parses the entire source file and returns the root of the AST (a ProgramNode).
    // This is the main entry point for parsing.
    std::unique_ptr<ast::ProgramNode> parseProgram();

private:
    tokens::Lexer& lexer_;
    tokens::Token current_token_;
    tokens::Token next_token_;
    ast::ExecutionDomain current_execution_domain_;

    // Private helper methods for token stream management and error reporting.
    void advance();
    void match(tokens::TokenType expected_type);
    void matchStatementTerminator(const std::string& statement_name);
    std::string match_and_get_lexeme(tokens::TokenType expected_type);
    template<typename T>
    T match_and_get_literal(tokens::TokenType expected_type);
    tokens::TokenType peek_type() const;
    tokens::TokenType peek_next_type() const;
    [[noreturn]] void error(const std::string& message);

    // --- Modularized Parsing Functions (declared as Parser members) ---

    // Parses a single top-level declaration (dispatcher).
    std::unique_ptr<ast::AstNode> parseDeclaration();

    // Core parsing functions
    std::unique_ptr<ast::ItemDeclarationNode> parseItemDeclaration();
    std::unique_ptr<ast::ItemDeclarationNode> parseSemanticItemDeclaration();
    std::unique_ptr<ast::TermDeclarationNode> parseTermDeclaration();
    std::unique_ptr<ast::KeyDeclarationNode> parseKeyDeclaration();
    std::unique_ptr<ast::ContainerNode> parseContainer();
    std::unique_ptr<ast::DictionaryDeclarationNode> parseDictionaryDeclaration();
    std::unique_ptr<ast::DictionaryEntryNode> parseDictionaryEntry();
    std::unique_ptr<ast::CausalDefinitionNode> parseCausalDefinition(
        int line,
        int column);
    std::unique_ptr<ast::CausalRelationshipNode> parseCausalRelationship();
    std::unique_ptr<ast::CausalRelationshipNode::CausalSide> parseCausalSide();
    std::unique_ptr<ast::CalculationNode> parseCalculation();
    std::unique_ptr<ast::TestDeclarationNode> parseTestDeclaration();
    std::unique_ptr<ast::AstNode> parseBracedExecutionConstruct();
    std::unique_ptr<ast::ExecutionDefinitionNode>
    parseExecutionDefinition(
        int line,
        int column,
        ast::ExecutionDomain domain);
    std::unique_ptr<ast::ExecutionCallNode> parseExecutionCall(
        int line,
        int column);
    std::unique_ptr<ast::AstNode> parseExecutionDefinitionStatement();
    std::unique_ptr<ast::ItemDeclarationNode> parseExecutionDefinitionInput();
    std::string parseExecutionIdentifier(bool& identifier_is_numeric);
    bool isExecutionDefinitionInputBoundary() const;
    std::unique_ptr<ast::TermDeclarationNode> parseExecutionTermStatement();
    std::unique_ptr<ast::ExecutionActionNode> parseExecutionActionInvocation(
        std::unique_ptr<ast::AstNode> source);
    std::unique_ptr<ast::ContainerNode> parseExecutionActionParameters();
    std::unique_ptr<ast::AstNode> parseExpression();
    std::unique_ptr<ast::AstNode> parseOrExpression();
    std::unique_ptr<ast::AstNode> parseAndExpression();
    std::unique_ptr<ast::AstNode> parseNotExpression();
    std::unique_ptr<ast::AstNode> parseComparisonExpression();
    std::unique_ptr<ast::AstNode> parsePrimaryExpression();
    std::unique_ptr<ast::AstNode> parseMultiplicativeExpression();
    std::unique_ptr<ast::AstNode> parseAdditiveExpression();
    std::unique_ptr<ast::ClassDeclarationNode> parseClassDeclaration();
    std::unique_ptr<ast::FunctionDeclarationNode> parseFunctionDeclaration();
    std::unique_ptr<ast::FunctionCallNode> parseFunctionCall();
    std::unique_ptr<ast::PathReferenceNode> parsePathReference();
    std::unique_ptr<ast::SymbolReferenceNode> parseSymbolReference();
    std::unique_ptr<ast::AstNode> parseLiteral();

    // --- Statement Parsing Functions ---
    // NEW: Central dispatcher for statements within an execution block.
    std::unique_ptr<ast::AstNode> parseStatement(); // This will replace the large if-else if in parseExecutionBlock

    // Individual statement parsers
    std::unique_ptr<ast::LetStatementNode> parseLetStatement();
    std::unique_ptr<ast::SetStatementNode> parseSetStatement();
    std::unique_ptr<ast::AssertStatementNode> parseAssertStatement();
    std::unique_ptr<ast::FailStatementNode> parseFailStatement();
    std::unique_ptr<ast::RaisesStatementNode> parseRaisesStatement();
    std::unique_ptr<ast::BreakStatementNode> parseBreakStatement();
    std::unique_ptr<ast::ContinueStatementNode> parseContinueStatement();
    std::unique_ptr<ast::ElifStatementNode> parseElifStatement();
    std::unique_ptr<ast::ElseStatementNode> parseElseStatement();
    std::unique_ptr<ast::ForStatementNode> parseForStatement();
    std::unique_ptr<ast::IfStatementNode> parseIfStatement();
    std::unique_ptr<ast::LoopStatementNode> parseLoopStatement();
    std::unique_ptr<ast::PrintStatementNode> parsePrintStatement();
    std::unique_ptr<ast::ReturnStatementNode> parseReturnStatement();
    std::unique_ptr<ast::RaiseStatementNode> parseRaiseStatement();
    std::unique_ptr<ast::TryStatementNode> parseTryStatement();
    std::unique_ptr<ast::WhileStatementNode> parseWhileStatement();
    std::unique_ptr<ast::PassStatementNode> parsePassStatement();

    // Other core parsing functions
    std::unique_ptr<ast::ExecutionBlockNode> parseExecutionBlock();

    // Library/module manifest parsing
    std::unique_ptr<ast::AstNode> parseModuleManifest();
};

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_H_INDEX_HPP
