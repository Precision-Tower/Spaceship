// qps/core/src/parser/c/statements/elif.cpp

#include "../h/statements/elif.hpp"  // Include the elif statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'elif.cpp'.

// Parses an '-elif' statement: '-elif condition { body }'
std::unique_ptr<ast::ElifStatementNode> Parser::parseElifStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_ELIF); // Consume '-elif'

    // The condition for the elif block
    std::unique_ptr<ast::AstNode> condition_expr = parseAdditiveExpression(); // Condition is an expression

    // The body of the elif block
    std::unique_ptr<ast::ExecutionBlockNode> body_block = parseExecutionBlock();

    // No specific terminator like '_' or ';' for elif as it's part of an if-else chain.
    // The main 'if' statement parsing will manage the overall flow.

    return ast::createElifStatementNode(std::move(condition_expr), std::move(body_block), line, column);
}

} // namespace parser
} // namespace qps
