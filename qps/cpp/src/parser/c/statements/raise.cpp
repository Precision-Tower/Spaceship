// qps/core/src/parser/c/statements/raise.cpp

#include "../h/statements/raise.hpp" // Include the raise statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'raise.cpp'.

// Parses a '-raise' statement: '-raise message_;'
std::unique_ptr<ast::RaiseStatementNode> Parser::parseRaiseStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_RAISE); // Consume '-raise'

    // The message or error object to be raised can be any expression.
    std::unique_ptr<ast::AstNode> raise_message = parseAdditiveExpression(); // Parse the expression

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createRaiseStatementNode(std::move(raise_message), line, column);
}

} // namespace parser
} // namespace qps
