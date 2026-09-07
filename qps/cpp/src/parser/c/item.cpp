// qps/core/src/parser/c/item.cpp

#include "../h/item.hpp"       // Include the item parsing header
#include "../h/_index.hpp"     // Include the main Parser header
#include "../../ast/ast_utils.hpp"
#include <optional> // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will be a member of the Parser class.
// For now, it's defined here to represent the content of 'item.cpp'.

// Parses an Item declaration: 'identifier- <value>;'
std::unique_ptr<ast::ItemDeclarationNode> Parser::parseItemDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;

    const int target_line = current_token_.line;
    const int target_column = current_token_.column;

    std::string identifier =
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    auto target =
        ast::createIdentifierNode(
            identifier,
            target_line,
            target_column);

    match(tokens::TokenType::OP_SUBTRACT);

    std::unique_ptr<ast::AstNode> value_node;
    int end_line = line;

    // An Item may be declared without a supplied value:
    //
    //   radius-;
    //   radius-/n;
    //
    // This is distinct from assigning null:
    //
    //   radius- null;
    //
    // A typed empty Item preserves the expected type for downstream
    // consumers such as design tooling and Workbench.
    const bool empty_item =
        peek_type() == tokens::TokenType::SEMICOLON ||
        peek_type() == tokens::TokenType::TYPE_PATH ||
        peek_type() == tokens::TokenType::TYPE_NUMERIC ||
        peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
        peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
        peek_type() == tokens::TokenType::TYPE_NULL;

    if (!empty_item) {
        // Item values use the shared QPS expression grammar.
        //
        // Examples:
        //   energy- 0.5 * mass * velocity * velocity;
        //   total- base + offset;
        //   ratio- left / right;
        //
        // Item suffix parsing remains below and continues to own
        // authored type/unit metadata.
        value_node = parseExpression();
    }

    // Typed suffixes remain optional. They may annotate either a populated
    // Item or an empty Item.
    std::optional<tokens::TokenType> type_hint;
    std::optional<std::string> unit_hint;

    if (peek_type() == tokens::TokenType::SLASH &&
        peek_next_type() == tokens::TokenType::IDENTIFIER) {

        match(tokens::TokenType::SLASH);

        unit_hint =
            match_and_get_lexeme(
                tokens::TokenType::IDENTIFIER);

        end_line = current_token_.line;
        match(tokens::TokenType::SEMICOLON);

    } else if (peek_type() == tokens::TokenType::TYPE_PATH ||
        peek_type() == tokens::TokenType::TYPE_NUMERIC ||
        peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
        peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
        peek_type() == tokens::TokenType::TYPE_NULL) {

        type_hint = peek_type();
        end_line = current_token_.line;
        advance();

    } else {

        end_line = current_token_.line;
        match(tokens::TokenType::SEMICOLON);
    }

    auto item_node =
        ast::createItemDeclarationNode(
            std::move(target),
            line,
            column);

    item_node->value_node_ =
        std::move(value_node);

    item_node->type_hint_ =
        type_hint;

    item_node->unit_hint_ =
        unit_hint;

    item_node->setEndLine(end_line);

    return item_node;
}


// Semantic Item binding:
//
//   [>v-] 30/n;
//
// This binds a supplied value to a canonical semantic identity.
std::unique_ptr<ast::ItemDeclarationNode>
Parser::parseSemanticItemDeclaration() {

    int line = current_token_.line;
    int column = current_token_.column;

    auto target =
        parseSymbolReference();

    if (!target->selectsItemValue()) {
        error(
            "Semantic Item target must include '-' "
            "inside the structural reference.");
    }

    std::unique_ptr<ast::AstNode> value_node;
    int end_line = line;

    if (peek_type() == tokens::TokenType::STRING_LITERAL ||
        peek_type() == tokens::TokenType::NUMERIC_LITERAL ||
        peek_type() == tokens::TokenType::BOOLEAN_LITERAL ||
        peek_type() == tokens::TokenType::NULL_LITERAL) {

        value_node = parseLiteral();

    } else if (peek_type() == tokens::TokenType::IDENTIFIER) {

        value_node = parsePathReference();

    } else if (peek_type() == tokens::TokenType::OPEN_BRACKET &&
               peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) {

        value_node = parseSymbolReference();

    } else {

        error(
            "Expected a literal or reference after semantic Item target. Found: " +
            current_token_.toString());
    }

    // Item values may compose through '+' without surrendering '/' to the
    // mathematical parser. '/' remains available for Item unit suffixes such
    // as 30/n;.
    while (value_node &&
           peek_type() == tokens::TokenType::OP_ADD) {

        const int op_line = current_token_.line;
        const int op_column = current_token_.column;

        match(tokens::TokenType::OP_ADD);

        auto right =
            parsePrimaryExpression();

        value_node =
            ast::createBinaryExpressionNode(
                std::move(value_node),
                ast::BinaryExpressionNode::Operator::ADD,
                std::move(right),
                op_line,
                op_column);
    }

    std::optional<std::string> unit_hint;

    if (peek_type() == tokens::TokenType::SLASH &&
        peek_next_type() == tokens::TokenType::IDENTIFIER) {

        match(tokens::TokenType::SLASH);

        unit_hint =
            match_and_get_lexeme(
                tokens::TokenType::IDENTIFIER);

        end_line = current_token_.line;
        match(tokens::TokenType::SEMICOLON);

    } else if (
        peek_type() == tokens::TokenType::TYPE_PATH ||
        peek_type() == tokens::TokenType::TYPE_NUMERIC ||
        peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
        peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
        peek_type() == tokens::TokenType::TYPE_NULL) {

        end_line = current_token_.line;
        advance();

    } else {

        end_line = current_token_.line;
        match(tokens::TokenType::SEMICOLON);
    }

    auto item_node =
        ast::createItemDeclarationNode(
            std::move(target),
            line,
            column);

    item_node->value_node_ =
        std::move(value_node);

    item_node->unit_hint_ =
        unit_hint;

    item_node->setEndLine(end_line);

    return item_node;
}

} // namespace parser
} // namespace qps
