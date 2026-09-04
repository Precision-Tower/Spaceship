// qps/core/src/parser/c/statements/break.cpp

#include "../h/statements/break.hpp" // Include the break statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'break.cpp'.

// Parses a '-break' statement: '-break_;'
std::unique_ptr<ast::BreakStatementNode> Parser::parseBreakStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_BREAK); // Consume '-break'

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createBreakStatementNode(line, column);
}

} // namespace parser
} // namespace qps
