// qps/core/src/parser/c/statements/raises.cpp

#include "../../h/statements/raises.hpp"
#include "../../h/_index.hpp"
#include "../../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

std::unique_ptr<ast::RaisesStatementNode> Parser::parseRaisesStatement() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::KW_RAISES);

    if (peek_type() != tokens::TokenType::STRING_LITERAL) {
        error("Expected string error fragment after -raises. Found: " + current_token_.toString());
    }

    std::string expected_message =
        match_and_get_literal<std::string>(tokens::TokenType::STRING_LITERAL);

    auto body = parseExecutionBlock();

    matchStatementTerminator("-raises");

    return ast::createRaisesStatementNode(
        expected_message,
        std::move(body),
        line,
        column);
}

} // namespace parser
} // namespace qps
