// qps/core/src/parser/c/causal.cpp

#include "../h/_index.hpp"
#include "../../ast/ast_utils.hpp"

#include <vector>

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

    std::vector<std::unique_ptr<ast::AstNode>> domain_chain;
    domain_chain.push_back(parsePrimaryExpression());

    while (peek_type() == tokens::TokenType::EQUALS) {
        match(tokens::TokenType::EQUALS);
        domain_chain.push_back(parsePrimaryExpression());
    }

    match(tokens::TokenType::CLOSE_PAREN);

    return ast::createCausalSide(
        std::move(entity),
        std::move(domain_chain));
}

std::unique_ptr<ast::CausalRelationshipNode>
Parser::parseCausalRelationship() {
    const int line = current_token_.line;
    const int column = current_token_.column;

    std::vector<
        std::unique_ptr<ast::CausalRelationshipNode::CausalSide>
    > sides;

    sides.push_back(parseCausalSide());

    while (peek_type() == tokens::TokenType::EQUALS) {
        match(tokens::TokenType::EQUALS);
        sides.push_back(parseCausalSide());
    }

    if (sides.size() < 2) {
        error(
            "Causal relationship requires at least two component sides.");
    }

    match(tokens::TokenType::SEMICOLON);

    return ast::createCausalRelationshipNode(
        std::move(sides),
        line,
        column);
}

} // namespace parser
} // namespace qps
