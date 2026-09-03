// qps/core/src/parser/c/statements/fail.cpp

#include "../../h/statements/fail.hpp"
#include "../../h/_index.hpp"
#include "../../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

std::unique_ptr<ast::FailStatementNode> Parser::parseFailStatement() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::KW_FAIL);

    std::unique_ptr<ast::AstNode> message = nullptr;

    if (peek_type() != tokens::TokenType::SEMICOLON &&
        peek_type() != tokens::TokenType::EXEC_DELIMITER) {
        message = parseExpression();
    }

    matchStatementTerminator("-fail");

    return ast::createFailStatementNode(
        std::move(message),
        line,
        column);
}

} // namespace parser
} // namespace qps
