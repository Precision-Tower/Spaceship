// qps/core/src/parser/c/class.cpp

#include "../h/class.hpp" // Include the class parsing header
#include "../h/_index.hpp"     // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'class.cpp'.

// Parses a Class declaration: '-class key. { <member_definitions> };'
std::unique_ptr<ast::ClassDeclarationNode> Parser::parseClassDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_CLASS); // Consume '-class'

    // The class name is a Key. according to the grammar: '-class key.'
    // So we expect an IDENTIFIER followed by a DOT, forming a Key.
    std::string class_name = match_and_get_lexeme(tokens::TokenType::IDENTIFIER);
    match(tokens::TokenType::DOT); // Consume '.'

    auto class_node = ast::createClassDeclarationNode(class_name, line, column);

    match(tokens::TokenType::OPEN_BRACE); // Consume '{'

    // Parse member definitions within the class body.
    // Members can include func- definitions, Key., Term:, Item- definitions.
    while (peek_type() != tokens::TokenType::CLOSE_BRACE && peek_type() != tokens::TokenType::END_OF_FILE) {
        // Try to parse members as general declarations.
        // This makes the class body flexible to contain any top-level declaration.
        auto member = parseDeclaration();
        if (member) {
            class_node->members.push_back(std::move(member));
        } else {
            error("Unexpected token in class member definition: " + current_token_.toString());
        }
        // No commas expected between class members, they are newline separated.
        // The loop will continue as long as it's not the closing brace or EOF.
    }

    match(tokens::TokenType::CLOSE_BRACE); // Consume '}'
    match(tokens::TokenType::SEMICOLON);   // Consume ';' that terminates the class block

    return class_node;
}

} // namespace parser
} // namespace qps
