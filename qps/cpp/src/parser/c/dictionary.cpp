// qps/core/src/parser/c/dictionary.cpp

#include "../h/dictionary.hpp" // Include the dictionary parsing header
#include "../h/_index.hpp"     // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, these functions will remain members of the Parser class.
// They are defined here to represent the content of 'dictionary.cpp'.

// Parses a Dictionary: '[]' block
std::unique_ptr<ast::DictionaryDeclarationNode>
Parser::parseDictionaryDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::OPEN_BRACKET);

    auto dict_node =
        ast::createDictionaryDeclarationNode(
            line,
            column);

    // Canonical QPS:
    //
    //   '[' opens the Dictionary.
    //   ']' closes the Dictionary.
    //
    // Dictionary entries are parsed until the closing bracket.
    // ',' remains accepted as a legacy/optional separator.
    // LIST_CLOSER remains accepted temporarily for migration,
    // but neither token owns Dictionary closure.
    while (peek_type() != tokens::TokenType::CLOSE_BRACKET &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        // ',' separates Dictionary entries where the entry value
        // does not provide its own structural boundary.
        while (peek_type() == tokens::TokenType::COMMA) {
            match(tokens::TokenType::COMMA);

            while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
                match(tokens::TokenType::PARAGRAPH_BREAK);
            }
        }

        if (peek_type() == tokens::TokenType::CLOSE_BRACKET ||
            peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        dict_node->entries.push_back(
            parseDictionaryEntry());
    }

    match(tokens::TokenType::CLOSE_BRACKET);

    // Dictionary declarations remain self-terminated.
    match(tokens::TokenType::SEMICOLON);

    return dict_node;
}

// Parses a single dictionary entry: 'id: content' or '<.id: content' or '{#ID: expression _}'
std::unique_ptr<ast::DictionaryEntryNode> Parser::parseDictionaryEntry() {
    int line = current_token_.line;
    int column = current_token_.column;
    int entry_id; // Will hold the numeric ID for the dictionary entry

    // Handle dictionary input references like '[<.1: item- value;]'
    if (peek_type() == tokens::TokenType::DICT_INPUT_REF) {
        match(tokens::TokenType::DICT_INPUT_REF); // Consume '<.'

        // The ID for the input reference is expected to be a numeric literal.
        // E.g., [<.1: ...] means ID 1 for input.
        entry_id = static_cast<int>(match_and_get_literal<double>(tokens::TokenType::NUMERIC_LITERAL));
        match(tokens::TokenType::COLON); // Consume ':'

        // Now parse the content of the dictionary input reference.
        // This content can be an Item-, Term:, or even a literal/path reference.
        auto entry_node = ast::createDictionaryEntryNode(entry_id, line, column);
        // Dictionary content may contain structural declarations or data/reference content.
        if (peek_type() == tokens::TokenType::IDENTIFIER &&
            (peek_next_type() == tokens::TokenType::DOT ||
             peek_next_type() == tokens::TokenType::COLON ||
             peek_next_type() == tokens::TokenType::OP_SUBTRACT)) {
            entry_node->value_node_ = parseDeclaration();
        } else if (peek_type() == tokens::TokenType::OPEN_PAREN ||
                   peek_type() == tokens::TokenType::OPEN_BRACKET) {
            entry_node->value_node_ = parseDeclaration();
        } else {
            entry_node->value_node_ = parsePrimaryExpression();
        }
        return entry_node;

    } else if (peek_type() == tokens::TokenType::NUMERIC_LITERAL) {
        // Handle standard numeric ID for dictionary entries, e.g., '[1: content;]'
        entry_id = static_cast<int>(match_and_get_literal<double>(tokens::TokenType::NUMERIC_LITERAL));
        match(tokens::TokenType::COLON); // Consume ':'

        auto entry_node = ast::createDictionaryEntryNode(entry_id, line, column);

        // Dictionary entries contain data/references, not executable calculations.
        if (peek_type() == tokens::TokenType::IDENTIFIER &&
            (peek_next_type() == tokens::TokenType::DOT ||
             peek_next_type() == tokens::TokenType::COLON ||
             peek_next_type() == tokens::TokenType::OP_SUBTRACT)) {
            entry_node->value_node_ = parseDeclaration();
        } else if (peek_type() == tokens::TokenType::OPEN_PAREN ||
                   peek_type() == tokens::TokenType::OPEN_BRACKET) {
            entry_node->value_node_ = parseDeclaration();
        } else {
            entry_node->value_node_ = parsePrimaryExpression();
        }
        return entry_node;
    } else {
        error("Expected dictionary entry ID (numeric literal or input reference <.ID). Found: " + current_token_.toString());
    }
    return nullptr; // Should not be reached
}

} // namespace parser
} // namespace qps
