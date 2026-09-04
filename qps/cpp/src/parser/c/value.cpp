// qps/core/src/parser/c/value.cpp

#include "../h/value.hpp"      // Include the value parsing header
#include "../h/_index.hpp"     // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'value.cpp'.

// Parses a literal value (numeric, string, boolean, null).
std::unique_ptr<ast::AstNode> Parser::parseLiteral() {
    int line = current_token_.line;
    int column = current_token_.column;

    if (peek_type() == tokens::TokenType::NUMERIC_LITERAL) {
        return ast::createNumericLiteralNode(
            match_and_get_literal<double>(tokens::TokenType::NUMERIC_LITERAL), line, column);
    } else if (peek_type() == tokens::TokenType::STRING_LITERAL) {
        return ast::createStringLiteralNode(
            match_and_get_literal<std::string>(tokens::TokenType::STRING_LITERAL), line, column);
    } else if (peek_type() == tokens::TokenType::BOOLEAN_LITERAL) {
        return ast::createBooleanLiteralNode(
            match_and_get_literal<bool>(tokens::TokenType::BOOLEAN_LITERAL), line, column);
    } else if (peek_type() == tokens::TokenType::NULL_LITERAL) {
        match(tokens::TokenType::NULL_LITERAL); // Consume 'null'
        return ast::createNullLiteralNode(line, column);
    } else {
        error("Expected a literal value, but found: " + current_token_.toString());
    }
    return nullptr; // Should not be reached
}

} // namespace parser
} // namespace qps
