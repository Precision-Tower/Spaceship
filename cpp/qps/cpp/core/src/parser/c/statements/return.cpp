// qps/core/src/parser/c/statements/return.cpp

#include "../h/statements/return.hpp" // Include the return statement parsing header
#include "../../h/_index.hpp"         // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp"  // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'return.cpp'.

// Parses a '-return' statement: '-return expression;' or '-return;'
std::unique_ptr<ast::ReturnStatementNode> Parser::parseReturnStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_RETURN);

    std::unique_ptr<ast::AstNode> return_expr = nullptr;

    if (peek_type() != tokens::TokenType::SEMICOLON &&
        peek_type() != tokens::TokenType::EXEC_DELIMITER) {

        return_expr = parseExpression();
    }

    if (peek_type() == tokens::TokenType::SEMICOLON) {
        match(tokens::TokenType::SEMICOLON);
    } else {
        match(tokens::TokenType::EXEC_DELIMITER);
    }

    return ast::createReturnStatementNode(std::move(return_expr), line, column);
}

} // namespace parser
} // namespace qps
