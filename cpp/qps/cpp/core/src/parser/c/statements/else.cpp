// qps/core/src/parser/c/statements/else.cpp

#include "../h/statements/else.hpp" // Include the else statement parsing header
#include "../../h/_index.hpp"       // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'else.cpp'.

// Parses an '-else' statement: '-else { body }'
std::unique_ptr<ast::ElseStatementNode> Parser::parseElseStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_ELSE); // Consume '-else'

    // The body of the else block
    std::unique_ptr<ast::ExecutionBlockNode> body_block = parseExecutionBlock();

    // No specific terminator like '_' or ';' for else as it's part of an if-else chain.
    // The main 'if' statement parsing will manage the overall flow.

    return ast::createElseStatementNode(std::move(body_block), line, column);
}

} // namespace parser
} // namespace qps
