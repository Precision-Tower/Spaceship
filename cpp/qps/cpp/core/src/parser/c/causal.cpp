// qps/core/src/parser/c/causal.cpp

#include "../h/_index.hpp"
#include "../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

std::unique_ptr<ast::CausalRelationshipNode::CausalSide>
Parser::parseCausalSide() {
    const int line = current_token_.line;
    const int column = current_token_.column;

    if (peek_type() != tokens::TokenType::IDENTIFIER) {
        error(
            "Expected causal entity identifier. Found: " +
            current_token_.toString());
    }

    auto entity = ast::createIdentifierNode(
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER),
        line,
        column);

    match(tokens::TokenType::COLON);
    match(tokens::TokenType::OPEN_PAREN);

    auto input = parsePrimaryExpression();

    match(tokens::TokenType::EQUALS);

    auto output = parsePrimaryExpression();

    match(tokens::TokenType::CLOSE_PAREN);

    return ast::createCausalSide(
        std::move(entity),
        std::move(input),
        std::move(output));
}

std::unique_ptr<ast::CausalRelationshipNode>
Parser::parseCausalRelationship() {
    const int line = current_token_.line;
    const int column = current_token_.column;

    auto left = parseCausalSide();

    match(tokens::TokenType::EQUALS);

    auto right = parseCausalSide();

    match(tokens::TokenType::SEMICOLON);

    return ast::createCausalRelationshipNode(
        std::move(left),
        std::move(right),
        line,
        column);
}

} // namespace parser
} // namespace qps
