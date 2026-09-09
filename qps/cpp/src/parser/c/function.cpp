// qps/core/src/parser/c/function.cpp

#include "../h/function.hpp"   // Include the function parsing header
#include "../h/_index.hpp"     // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'function.cpp'.

// Parses a Function declaration:
//
//   -func name(
//   param-/n;,
//   param-/n;\
//   ){ ... }
std::unique_ptr<ast::FunctionDeclarationNode> Parser::parseFunctionDeclaration() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_FUNC);

    std::string function_name =
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    std::unique_ptr<ast::AstNode> params_node = parseContainer();
    std::unique_ptr<ast::ExecutionBlockNode> body_node = parseExecutionBlock();

    // Older parser scaffolding expected a semicolon after function bodies.
    // The V1 function contract does not require one, but accepting it keeps
    // existing experimental fixtures from becoming invalid.
    if (peek_type() == tokens::TokenType::SEMICOLON) {
        match(tokens::TokenType::SEMICOLON);
    }

    return ast::createFunctionDeclarationNode(
        function_name,
        std::move(params_node),
        std::move(body_node),
        line,
        column);
}

std::unique_ptr<ast::FunctionCallNode> Parser::parseFunctionCall() {
    int line = current_token_.line;
    int column = current_token_.column;

    std::string function_name =
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    auto call =
        ast::createFunctionCallNode(function_name, line, column);

    match(tokens::TokenType::OPEN_PAREN);

    if (peek_type() != tokens::TokenType::CLOSE_PAREN) {
        while (true) {
            if (peek_type() == tokens::TokenType::IDENTIFIER &&
                peek_next_type() == tokens::TokenType::OP_SUBTRACT) {
                const std::string argument_name =
                    match_and_get_lexeme(tokens::TokenType::IDENTIFIER);
                match(tokens::TokenType::OP_SUBTRACT);
                call->addNamedArgument(
                    argument_name,
                    parseExpression());
            } else {
                call->addArgument(parseExpression());
            }

            if (peek_type() == tokens::TokenType::COMMA) {
                match(tokens::TokenType::COMMA);
                continue;
            }

            break;
        }
    }

    match(tokens::TokenType::CLOSE_PAREN);
    return call;
}

} // namespace parser
} // namespace qps
