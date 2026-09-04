// qps/core/src/parser/c/statements/if.cpp

#include "../h/statements/if.hpp"    // Include the if statement parsing header
#include "../../h/_index.hpp"        // Include the main Parser header for access to its members
#include "../../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'if.cpp'.

// Parses an '-if' statement: '-if condition { body } [ -elif ... ] [ -else ... ]_'
std::unique_ptr<ast::IfStatementNode> Parser::parseIfStatement() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::KW_IF); // Consume '-if'

    // Parse the condition for the if block
    std::unique_ptr<ast::AstNode> condition_expr = parseAdditiveExpression(); // Condition is an expression

    // Parse the main body of the if block
    std::unique_ptr<ast::ExecutionBlockNode> body_block = parseExecutionBlock();

    auto if_node = ast::createIfStatementNode(std::move(condition_expr), std::move(body_block), line, column);

    // Parse optional -elif blocks
    while (peek_type() == tokens::TokenType::KW_ELIF) {
        if_node->addElifBlock(parseElifStatement()); // Assuming parseElifStatement exists
    }

    // Parse optional -else block
    if (peek_type() == tokens::TokenType::KW_ELSE) {
        if_node->setElseBlock(parseElseStatement()); // Assuming parseElseStatement exists
    }

    match(tokens::TokenType::EXEC_DELIMITER); // Consume '_' that terminates the entire if-elif-else block

    return if_node;
}

} // namespace parser
} // namespace qps
