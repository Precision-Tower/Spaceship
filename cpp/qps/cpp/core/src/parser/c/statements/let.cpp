// qps/core/src/parser/c/statements/let.cpp

#include "../h/statements/let.hpp" // Include the let statement parsing header
#include "../../h/_index.hpp"      // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'let.cpp'.

// Parses a '-let' statement: '-let identifier initial_value/type_;' or '-let identifier_;'
std::unique_ptr<ast::LetStatementNode> Parser::parseLetStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_LET); // Consume '-let'

    std::string identifier = match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    std::unique_ptr<ast::AstNode> initial_value = nullptr;

    // Check if there's an initial value (not terminated by EXEC_DELIMITER immediately)
    if (peek_type() != tokens::TokenType::EXEC_DELIMITER) {
        // The value can be a literal, path reference, or an expression.
        if (peek_type() == tokens::TokenType::STRING_LITERAL ||
            peek_type() == tokens::TokenType::NUMERIC_LITERAL ||
            peek_type() == tokens::TokenType::BOOLEAN_LITERAL ||
            peek_type() == tokens::TokenType::NULL_LITERAL) {
            initial_value = parseLiteral(); // Parse the literal value
        } else if (peek_type() == tokens::TokenType::IDENTIFIER ||
                   peek_type() == tokens::TokenType::DICT_OUTPUT_REF) {
            initial_value = parsePathReference();
        } else {
            // If it's not a known literal or identifier/expression start, it's an error for value.
            error("Expected an initial value (literal, path, or expression) for '-let' statement. Found: " + current_token_.toString());
        }

        // After the value, we expect a type suffix if it's a literal value, or nothing for references.
        // For -let, the grammar shows `value/type_` so the type suffix is expected.
        if (initial_value && (initial_value->getType() == ast::AstNodeType::NUMERIC_LITERAL ||
                              initial_value->getType() == ast::AstNodeType::STRING_LITERAL ||
                              initial_value->getType() == ast::AstNodeType::BOOLEAN_LITERAL ||
                              initial_value->getType() == ast::AstNodeType::NULL_LITERAL)) {
            // For actual literals, a type suffix is required by the example.
            // Check for and consume the specific type suffix.
            if (peek_type() == tokens::TokenType::TYPE_PATH ||
                peek_type() == tokens::TokenType::TYPE_NUMERIC ||
                peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
                peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
                peek_type() == tokens::TokenType::TYPE_NULL) {
                advance(); // Consume the type suffix
            } else {
                error("Expected a type suffix for '-let' statement's literal value. Found: " + current_token_.toString());
            }
        }
    }

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createLetStatementNode(identifier, std::move(initial_value), line, column);
}

} // namespace parser
} // namespace qps
