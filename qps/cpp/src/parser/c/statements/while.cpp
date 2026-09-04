// qps/core/src/parser/c/statements/while.cpp

#include "../h/statements/while.hpp" // Include the while statement parsing header
#include "../../h/_index.hpp"         // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp"  // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'while.cpp'.

// Parses a '-while' statement: '-while condition { body }_'
std::unique_ptr<ast::WhileStatementNode> Parser::parseWhileStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_WHILE); // Consume '-while'

    // While conditions use the same expression grammar as -if.
    std::unique_ptr<ast::AstNode> condition_expr =
        parseExpression();

    std::unique_ptr<ast::ExecutionBlockNode> body_block =
        parseExecutionBlock();

    return ast::createWhileStatementNode(
        std::move(condition_expr),
        std::move(body_block),
        line,
        column);
}

} // namespace parser
} // namespace qps
