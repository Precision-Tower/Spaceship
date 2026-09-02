// qps/core/src/parser/c/statements/loop.cpp

#include "../h/statements/loop.hpp"  // Include the loop statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'loop.cpp'.

// Parses a '-loop' statement: '-loop { body }_'
std::unique_ptr<ast::LoopStatementNode> Parser::parseLoopStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_LOOP); // Consume '-loop'

    // Parse the loop body (Execution Block)
    std::unique_ptr<ast::ExecutionBlockNode> body_block = parseExecutionBlock();

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createLoopStatementNode(std::move(body_block), line, column);
}

} // namespace parser
} // namespace qps
