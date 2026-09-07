// qps/core/src/parser/c/term.cpp

#include "../h/term.hpp"
#include "../h/_index.hpp"
#include "../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

// Parses a Term:
//
//   dimensions: (
//       radius- 5/in;
//       depth- 1/in;
//   );
//
// Canonical QPS:
//   ':' opens Term content.
//   ';' closes the Term.
//
// Child declarations own their own termination.
// ',' and '\' are accepted only as legacy separators during migration.
std::unique_ptr<ast::TermDeclarationNode>
Parser::parseTermDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;

    std::string identifier =
        match_and_get_lexeme(
            tokens::TokenType::IDENTIFIER);

    match(tokens::TokenType::COLON);

    auto term_node =
        ast::createTermDeclarationNode(
            identifier,
            line,
            column);

    while (peek_type() != tokens::TokenType::SEMICOLON &&
           peek_type() != tokens::TokenType::END_OF_FILE &&
           peek_type() != tokens::TokenType::CLOSE_PAREN &&
           peek_type() != tokens::TokenType::CLOSE_BRACKET) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::SEMICOLON ||
            peek_type() == tokens::TokenType::END_OF_FILE ||
            peek_type() == tokens::TokenType::CLOSE_PAREN ||
            peek_type() == tokens::TokenType::CLOSE_BRACKET) {
            break;
        }

        if (peek_type() == tokens::TokenType::KW_TEST) {
            term_node->content_.push_back(
                parseTestDeclaration());
            continue;
        }

        if (peek_type() == tokens::TokenType::OPEN_BRACE) {
            // A brace directly owned by a Term is that Term's
            // executable body:
            //
            //   kinetic_energy: {
            //   [>mass-]
            //   -return mass;
            //   };
            //
            // The Term owns identity. The braces own executable
            // contents; they do not introduce a second identity.
            const int body_line = current_token_.line;
            const int body_column = current_token_.column;

            match(tokens::TokenType::OPEN_BRACE);

            auto body =
                ast::createExecutionBlockNode(
                    body_line,
                    body_column);

            while (peek_type() != tokens::TokenType::CLOSE_BRACE &&
                   peek_type() != tokens::TokenType::END_OF_FILE) {

                while (peek_type() ==
                       tokens::TokenType::PARAGRAPH_BREAK) {

                    match(tokens::TokenType::PARAGRAPH_BREAK);
                }

                if (peek_type() == tokens::TokenType::CLOSE_BRACE ||
                    peek_type() == tokens::TokenType::END_OF_FILE) {
                    break;
                }

                auto statement =
                    parseExecutionDefinitionStatement();

                if (!statement) {
                    error(
                        "Failed to parse statement within "
                        "Term execution body: " +
                        current_token_.toString());
                }

                body->statements.push_back(
                    std::move(statement));
            }

            match(tokens::TokenType::CLOSE_BRACE);

            term_node->content_.push_back(
                std::move(body));

            continue;
        }

        if (peek_type() == tokens::TokenType::KW_DEF) {
            match(tokens::TokenType::KW_DEF);

            term_node->content_.push_back(
                ast::createStringLiteralNode(
                    match_and_get_literal<std::string>(
                        tokens::TokenType::DEFINITION_TEXT),
                    line,
                    column));

            continue;
        }

        if (peek_type() == tokens::TokenType::IDENTIFIER) {
            const auto next = peek_next_type();

            if (next == tokens::TokenType::DOT ||
                next == tokens::TokenType::COLON ||
                next == tokens::TokenType::OP_SUBTRACT) {

                term_node->content_.push_back(
                    parseDeclaration());
            } else {
                term_node->content_.push_back(
                    parsePrimaryExpression());
            }

            continue;
        }

        if (peek_type() == tokens::TokenType::OPEN_PAREN) {
            term_node->content_.push_back(
                parseContainer());
            continue;
        }

        if (peek_type() == tokens::TokenType::OPEN_BRACKET) {
            if (peek_next_type() ==
                tokens::TokenType::REFERENCE_OPERATOR) {

                term_node->content_.push_back(
                    parseSymbolReference());
            } else {
                term_node->content_.push_back(
                    parseDictionaryDeclaration());
            }

            continue;
        }

        if (peek_type() == tokens::TokenType::EQUALS) {
            error(
                "Causal relationship parsing not yet implemented "
                "for Term content: " +
                current_token_.toString());
        }

        error(
            "Unexpected token in Term content: " +
            current_token_.toString());
    }

    const int end_line = current_token_.line;
    match(tokens::TokenType::SEMICOLON);
    term_node->setEndLine(end_line);

    return term_node;
}

} // namespace parser
} // namespace qps
