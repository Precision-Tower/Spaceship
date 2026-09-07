// qps/core/src/parser/c/key.cpp

#include "../h/key.hpp"       // Include the key parsing header
#include "../h/_index.hpp"    // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'key.cpp'.

// Parses a Key declaration: 'identifier. <content>;'
std::unique_ptr<ast::KeyDeclarationNode> Parser::parseKeyDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;

    std::string identifier =
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER);
    match(tokens::TokenType::DOT); // Structural Key suffix '.'

    auto key_node = ast::createKeyDeclarationNode(identifier, line, column);

    // Key content can be a Definition String, Container, Dictionary, Term:, Item:, etc.
    // Continue parsing elements until the end of the key block (semicolon),
    // or a closing parenthesis/bracket indicating it's nested within another structure.
    while (peek_type() != tokens::TokenType::SEMICOLON &&
           peek_type() != tokens::TokenType::PARAGRAPH_BREAK &&
           peek_type() != tokens::TokenType::END_OF_FILE &&
           peek_type() != tokens::TokenType::CLOSE_PAREN &&
           peek_type() != tokens::TokenType::CLOSE_BRACKET) {

        if (peek_type() == tokens::TokenType::KW_DEF) {
            // A Key may directly contain definition text.
            match(tokens::TokenType::KW_DEF); // Consume 'def"'

            key_node->content_.push_back(
                ast::createStringLiteralNode(
                    match_and_get_literal<std::string>(
                        tokens::TokenType::DEFINITION_TEXT),
                    line,
                    column));

            break;
        } else if (peek_type() == tokens::TokenType::OPEN_PAREN) {
            // Parse a nested Container ()
            key_node->content_.push_back(parseContainer()); // Assuming parseContainer exists
        } else if (peek_type() == tokens::TokenType::OPEN_BRACKET) {
            // Parse a nested Dictionary []
            key_node->content_.push_back(parseDictionaryDeclaration()); // Assuming parseDictionaryDeclaration exists
        } else if (peek_type() == tokens::TokenType::IDENTIFIER &&
                   (peek_next_type() == tokens::TokenType::DOT ||
                    peek_next_type() == tokens::TokenType::COLON ||
                    peek_next_type() == tokens::TokenType::OP_SUBTRACT)) {
            // All nested QPS primitives use the same declaration grammar.
            key_node->content_.push_back(parseDeclaration());
        } else if (peek_type() == tokens::TokenType::EQUALS) {
            // This is likely a Causal Relationship.
            // TODO: Implement parseCausalRelationship();
            error("Causal relationship parsing not yet implemented for Key content: " + current_token_.toString());
        } else {
            // Handle lists within Key content, which should be comma-separated
            // If it's a comma, consume it and expect another element.
            if (peek_type() == tokens::TokenType::COMMA) {
                 match(tokens::TokenType::COMMA);
            }
            // Attempt to parse another declaration within the key's content block.
            // This might lead to an infinite loop if not careful with the grammar.
            // For now, let's assume it attempts to parse another declaration.
            auto nested_decl = parseDeclaration();
            if (nested_decl) {
                key_node->content_.push_back(std::move(nested_decl));
            } else {
                error("Unexpected token within Key declaration content: " + current_token_.toString());
            }
        }
    }
    // KEY_SOURCE_SPAN_FINALIZATION
    //
    // PARAGRAPH_BREAK is emitted from the source position immediately
    // following the final owned token, before blank-line whitespace is
    // discarded. Its line therefore identifies the final source line
    // owned by this Key paragraph.
    if (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
        key_node->setEndLine(current_token_.line);
    }

    // EOF has no structural delimiter. If EOF is positioned at column 1
    // after one trailing newline, the previous physical line is the final
    // line owned by the Key. Otherwise EOF remains on the final owned line.
    if (peek_type() == tokens::TokenType::END_OF_FILE) {
        int end_line = current_token_.line;

        if (current_token_.column == 1 &&
            end_line > line) {

            --end_line;
        }

        key_node->setEndLine(end_line);
    }

    // A Key is a paragraph of information.
    //
    // Child declarations own their own ';' terminators.
    // At the surface, PARAGRAPH_BREAK or EOF completes the Key.
    //
    // '\' is reserved for collection closure and is never a Key closer.
    if (peek_type() == tokens::TokenType::PARAGRAPH_BREAK ||
        peek_type() == tokens::TokenType::END_OF_FILE) {
        return key_node;
    }

    // Keep explicit ';' available for nested/explicitly terminated Keys.
    if (peek_type() == tokens::TokenType::SEMICOLON) {
        key_node->setEndLine(current_token_.line);
        match(tokens::TokenType::SEMICOLON);
        return key_node;
    }

    error(
        "Expected blank-line boundary or ';' after Key content. Found: " +
        current_token_.toString());
}

} // namespace parser
} // namespace qps
