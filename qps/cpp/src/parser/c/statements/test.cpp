// qps/core/src/parser/c/statements/test.cpp

#include "../../h/statements/test.hpp"
#include "../../h/_index.hpp"
#include "../../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

std::unique_ptr<ast::TestDeclarationNode> Parser::parseTestDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::KW_TEST);

    auto body = parseExecutionBlock();

    return ast::createTestDeclarationNode(
        std::move(body),
        line,
        column);
}

} // namespace parser
} // namespace qps
