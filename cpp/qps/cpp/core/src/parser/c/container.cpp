// qps/core/src/parser/c/container.cpp

#include "../h/container.hpp"
#include "../h/_index.hpp"
#include "../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

// Parses a Container:
//
//   (
//       radius- 5/in;
//       depth- 1/in;
//   )
//
// Canonical QPS:
//   '(' opens the Container.
//   ')' closes the Container.
//   Child declarations own their own termination.
//
// Legacy ',' and '\' collection punctuation is accepted during migration,
// but neither is required and neither owns Container closure.
std::unique_ptr<ast::ContainerNode> Parser::parseContainer() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::OPEN_PAREN);

    auto container_node =
        ast::createContainerNode(
            line,
            column);

    while (peek_type() != tokens::TokenType::CLOSE_PAREN &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        // Whitespace / paragraph formatting is not structural here.
        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::CLOSE_PAREN ||
            peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        auto element =
            parseDeclaration();

        if (!element) {
            error(
                "Unexpected token within Container: " +
                current_token_.toString());
        }

        container_node->elements.push_back(
            std::move(element));
    }

    match(tokens::TokenType::CLOSE_PAREN);

    return container_node;
}

} // namespace parser
} // namespace qps
