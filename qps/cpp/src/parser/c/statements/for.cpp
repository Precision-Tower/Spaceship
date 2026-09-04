// qps/core/src/parser/c/statements/for.cpp

#include "../h/statements/for.hpp"   // Include the for statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'for.cpp'.

// Parses a '-for' statement: '-for (loop_control_expression) { body }_'
std::unique_ptr<ast::ForStatementNode> Parser::parseForStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_FOR); // Consume '-for'

    // The loop control can be an expression or a more complex structure (e.g., an implicit tuple for C-style for-loops).
    // For now, let's assume it's enclosed in parentheses `()` and we parse the content within.
    match(tokens::TokenType::OPEN_PAREN); // Consume '('

    // Parse the content inside the parentheses as a general expression or declaration.
    // This provides flexibility for different loop control syntaxes (e.g., 'i < 10', 'element in collection', 'init;cond;inc').
    std::unique_ptr<ast::AstNode> loop_control_expr = parseAdditiveExpression(); // Start with expression parsing.
                                                                                // If it needs to contain multiple semicolon-separated parts,
                                                                                // `parseExpression` would need to be enhanced for that or a `ContainerNode` might be used.

    match(tokens::TokenType::CLOSE_PAREN); // Consume ')'

    // Parse the loop body (Execution Block)
    std::unique_ptr<ast::ExecutionBlockNode> body_block = parseExecutionBlock();

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createForStatementNode(std::move(loop_control_expr), std::move(body_block), line, column);
}

} // namespace parser
} // namespace qps
