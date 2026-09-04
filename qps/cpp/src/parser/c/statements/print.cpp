// qps/core/src/parser/c/statements/print.cpp

#include "../h/statements/print.hpp" // Include the print statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'print.cpp'.

// Parses a '-print' statement: '-print expression_;'
std::unique_ptr<ast::PrintStatementNode> Parser::parsePrintStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_PRINT); // Consume '-print'

    // The expression to be printed can be any valid expression (literal, path, arithmetic, etc.).
    std::unique_ptr<ast::AstNode> expr_to_print = parseAdditiveExpression(); // Start with lowest precedence expression parsing.

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the statement

    return ast::createPrintStatementNode(std::move(expr_to_print), line, column);
}

} // namespace parser
} // namespace qps
