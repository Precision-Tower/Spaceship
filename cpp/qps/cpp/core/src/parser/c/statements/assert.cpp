// qps/core/src/parser/c/statements/assert.cpp

#include "../h/statements/assert.hpp" // Include the assert statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'assert.cpp'.

// Parses an '-assert' statement: '-assert condition;'
std::unique_ptr<ast::AssertStatementNode> Parser::parseAssertStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_ASSERT);

    std::unique_ptr<ast::AstNode> condition_expr = parseExpression();

    matchStatementTerminator("-assert");

    return ast::createAssertStatementNode(std::move(condition_expr), line, column);
}

} // namespace parser
} // namespace qps
