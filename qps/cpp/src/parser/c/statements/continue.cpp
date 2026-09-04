// qps/core/src/parser/c/statements/continue.cpp

#include "../h/statements/continue.hpp" // Include the continue statement parsing header
#include "../../h/_index.hpp"          // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp"   // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'continue.cpp'.

// Parses a '-continue' statement: '-continue_;'
std::unique_ptr<ast::ContinueStatementNode> Parser::parseContinueStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_CONTINUE); // Consume '-continue'

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createContinueStatementNode(line, column);
}

} // namespace parser
} // namespace qps
