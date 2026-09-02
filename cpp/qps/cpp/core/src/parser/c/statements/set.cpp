// qps/core/src/parser/c/statements/set.cpp

#include "../h/statements/set.hpp" // Include the set statement parsing header
#include "../../h/_index.hpp"      // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'set.cpp'.

// Parses a '-set' statement: '-set target_path value/type_;'
std::unique_ptr<ast::SetStatementNode> Parser::parseSetStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_SET); // Consume '-set'

    // The target of assignment can be an Identifier (for local var) or a PathReference.
    std::unique_ptr<ast::AstNode> target_node;
    if (peek_type() == tokens::TokenType::IDENTIFIER) {
        // If it's an identifier, it could be a simple variable or the start of a path.
        // We'll parse it as a PathReference, which can also handle single identifiers.
        target_node = parsePathReference();
    } else if (peek_type() == tokens::TokenType::DICT_OUTPUT_REF) {
        // Assignment to a dictionary output reference (e.g., -set [>1.1] value;)
        // For now, treat it as part of a path reference.
        target_node = parsePrimaryExpression(); // This will handle the >.ID part, returning a NumericLiteralNode for the ID.
                                                // A dedicated AST node for DictOutputReference might be better here.
    }
    else {
        error("Expected identifier or path reference as target for '-set' statement. Found: " + current_token_.toString());
    }

    // Now parse the value being assigned.
    std::unique_ptr<ast::AstNode> assigned_value;
    if (peek_type() == tokens::TokenType::STRING_LITERAL ||
        peek_type() == tokens::TokenType::NUMERIC_LITERAL ||
        peek_type() == tokens::TokenType::BOOLEAN_LITERAL ||
        peek_type() == tokens::TokenType::NULL_LITERAL) {
        assigned_value = parseLiteral(); // Parse the literal value
    } else if (peek_type() == tokens::TokenType::IDENTIFIER ||
               peek_type() == tokens::TokenType::DICT_OUTPUT_REF) {
        assigned_value = parseExpression();
    } else {
        error("Expected a value (literal, path, or expression) for '-set' statement. Found: " + current_token_.toString());
    }

    // After the value, we expect a type suffix if it's a literal value.
    if (assigned_value && (assigned_value->getType() == ast::AstNodeType::NUMERIC_LITERAL ||
                           assigned_value->getType() == ast::AstNodeType::STRING_LITERAL ||
                           assigned_value->getType() == ast::AstNodeType::BOOLEAN_LITERAL ||
                           assigned_value->getType() == ast::AstNodeType::NULL_LITERAL)) {
        // For actual literals, a type suffix is required by the example.
        if (peek_type() == tokens::TokenType::TYPE_PATH ||
            peek_type() == tokens::TokenType::TYPE_NUMERIC ||
            peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
            peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
            peek_type() == tokens::TokenType::TYPE_NULL) {
            advance(); // Consume the type suffix
        } else {
            error("Expected a type suffix for '-set' statement's literal value. Found: " + current_token_.toString());
        }
    } else {
        // If the value is a path reference or an expression, no explicit type suffix is expected.
        // It's already typed by its AST node.
    }

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createSetStatementNode(std::move(target_node), std::move(assigned_value), line, column);
}

} // namespace parser
} // namespace qps
