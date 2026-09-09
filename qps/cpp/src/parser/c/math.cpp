// qps/core/src/parser/c/math.cpp

#include "../h/math.hpp"       // Include the math parsing header
#include "../h/_index.hpp"     // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers
#include <stdexcept>           // For std::runtime_error

namespace qps {
namespace parser {

// Note: In the final integrated parser, these functions will remain members of the Parser class.
// They are defined here to represent the content of 'math.cpp'.

// Parses an expression (e.g., for dictionary values or mathematical expressions).
// This will follow operator precedence rules using a Pratt-like or recursive descent parser.
// Currently handles: {#ID: <expression> _} form and basic arithmetic.
std::unique_ptr<ast::CalculationNode> Parser::parseCalculation() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::CALCULATION_MARKER);

    std::unique_ptr<ast::AstNode> target = nullptr;

    // Local symbolic target:
    //
    //   %a: expression
    //
    if (peek_type() == tokens::TokenType::IDENTIFIER &&
        peek_next_type() == tokens::TokenType::COLON) {

        const int target_line = current_token_.line;
        const int target_column = current_token_.column;

        std::string label =
            match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

        target = ast::createIdentifierNode(
            label,
            target_line,
            target_column);

        match(tokens::TokenType::COLON);
    }

    // Numeric labels are labels, not numeric values:
    //
    //   %1: expression
    //
    // Structurally, 1 and a serve the same role.
    else if (peek_type() == tokens::TokenType::NUMERIC_LITERAL &&
             peek_next_type() == tokens::TokenType::COLON) {

        const int target_line = current_token_.line;
        const int target_column = current_token_.column;

        std::string label =
            match_and_get_lexeme(tokens::TokenType::NUMERIC_LITERAL);

        target = ast::createIdentifierNode(
            label,
            target_line,
            target_column);

        match(tokens::TokenType::COLON);
    }

    // Semantic target:
    //
    //   %[>a]: expression
    //
    else if (peek_type() == tokens::TokenType::OPEN_BRACKET &&
             peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) {

        target = parseSymbolReference();
        match(tokens::TokenType::COLON);
    }

    // For V1 calculations, a target is required.
    else {
        error(
            "Expected calculation target after '%'. "
            "Valid forms include %a:, %1:, or %[>a]:");
    }

    auto expression_body = parseExpression();

    // No dedicated calculation closer is required.
    //
    // The expression naturally stops when it reaches a token that cannot
    // continue the expression. Inside an execution block that will normally
    // be the next '%' calculation marker or the closing '}'.
    return ast::createCalculationNode(
        std::move(target),
        std::move(expression_body),
        line,
        column);
}

// Parses a mathematical expression without owning execution-block syntax.
// Expression precedence is handled by the additive/multiplicative layers below.
std::unique_ptr<ast::AstNode> Parser::parseExpression() {
    return parseOrExpression();
}

std::unique_ptr<ast::AstNode> Parser::parseOrExpression() {
    auto left = parseAndExpression();

    while (peek_type() == tokens::TokenType::OP_OR) {
        const int op_line = current_token_.line;
        const int op_column = current_token_.column;
        advance();

        auto right = parseAndExpression();

        left = ast::createBinaryExpressionNode(
            std::move(left),
            ast::BinaryExpressionNode::Operator::OR,
            std::move(right),
            op_line,
            op_column);
    }

    return left;
}

std::unique_ptr<ast::AstNode> Parser::parseAndExpression() {
    auto left = parseNotExpression();

    while (peek_type() == tokens::TokenType::OP_AND) {
        const int op_line = current_token_.line;
        const int op_column = current_token_.column;
        advance();

        auto right = parseNotExpression();

        left = ast::createBinaryExpressionNode(
            std::move(left),
            ast::BinaryExpressionNode::Operator::AND,
            std::move(right),
            op_line,
            op_column);
    }

    return left;
}

std::unique_ptr<ast::AstNode> Parser::parseNotExpression() {
    if (peek_type() == tokens::TokenType::OP_NOT) {
        const int op_line = current_token_.line;
        const int op_column = current_token_.column;
        advance();

        return ast::createUnaryExpressionNode(
            ast::UnaryExpressionNode::Operator::NOT,
            parseNotExpression(),
            op_line,
            op_column);
    }

    return parseComparisonExpression();
}

std::unique_ptr<ast::AstNode> Parser::parseComparisonExpression() {
    auto left = parseAdditiveExpression();

    while (peek_type() == tokens::TokenType::OP_EQUAL ||
           peek_type() == tokens::TokenType::OP_LESS) {
        const int op_line = current_token_.line;
        const int op_column = current_token_.column;
        const tokens::TokenType op_type = peek_type();
        advance();

        auto right = parseAdditiveExpression();

        const auto op =
            op_type == tokens::TokenType::OP_EQUAL
                ? ast::BinaryExpressionNode::Operator::EQUAL
                : ast::BinaryExpressionNode::Operator::LESS;

        left = ast::createBinaryExpressionNode(
            std::move(left),
            op,
            std::move(right),
            op_line,
            op_column);
    }

    return left;
}

// Parses primary expressions: literals, path references, or parenthesized expressions.
std::unique_ptr<ast::AstNode> Parser::parsePrimaryExpression() {
    int line = current_token_.line;
    int column = current_token_.column;

    if (peek_type() == tokens::TokenType::OPEN_BRACE) {
        auto construct =
            parseBracedExecutionConstruct();

        if (!dynamic_cast<ast::ExecutionCallNode*>(
                construct.get())) {

            error(
                "Only an execution call may be used "
                "as a braced value expression.");
        }

        return construct;
    }

    if (peek_type() == tokens::TokenType::OPEN_PAREN) {
        match(tokens::TokenType::OPEN_PAREN);
        auto expr = parseExpression();
        match(tokens::TokenType::CLOSE_PAREN);
        return expr;
    } else if (
        peek_type() == tokens::TokenType::OPEN_BRACKET &&
        peek_next_type() != tokens::TokenType::REFERENCE_OPERATOR &&
        peek_next_type() != tokens::TokenType::IDENTIFIER) {

        return parseDictionaryDeclaration();
    } else if (
        peek_type() == tokens::TokenType::OPEN_BRACKET &&
        (peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR ||
         peek_next_type() == tokens::TokenType::IDENTIFIER)) {

        // Structural navigation used as an expression operand:
        //
        //   [>shape.dimensions]  external/document root
        //   [v.bore1]            local binding root
        return parseSymbolReference();
    } else if (peek_type() == tokens::TokenType::NUMERIC_LITERAL ||
               peek_type() == tokens::TokenType::STRING_LITERAL ||
               peek_type() == tokens::TokenType::BOOLEAN_LITERAL ||
               peek_type() == tokens::TokenType::NULL_LITERAL) {
        return parseLiteral();
    } else if (peek_type() == tokens::TokenType::IDENTIFIER) {
        if (peek_next_type() == tokens::TokenType::OPEN_PAREN) {
            return parseFunctionCall();
        }

        // If it's an identifier, it can be a simple variable reference or the start of a path.
        // It could also be a dictionary output reference if followed by a dot.
        // Rule: 'file.key.[>.ID]'
        if (peek_next_type() == tokens::TokenType::DOT) { // This indicates a path or a complex reference.
            // Check for dictionary output reference explicitly
            if (current_token_.lexeme == "[>" && peek_next_type() == tokens::TokenType::NUMERIC_LITERAL) {
                // This scenario (like `[>1]`) is handled by the lexer tokenizing `[>` as `DICT_OUTPUT_REF`.
                // If lexer emits `DICT_OUTPUT_REF` for `[>`, then we check that.
                // Re-evaluate: `[>1.1:]` is an example. The lexer should emit `OPEN_BRACKET`, `DICT_OUTPUT_REF`, NUMERIC_LITERAL, DOT, NUMERIC_LITERAL, COLON, CLOSE_BRACKET.
                // The current `peek_type() == tokens::TokenType::IDENTIFIER` won't catch `[>`.
                // The `parsePathReference` should be robust enough to handle the segments.
                // For direct `[>ID]` in expressions, it implies the lexer will emit `DICT_OUTPUT_REF` followed by `NUMERIC_LITERAL`.
                // For now, if we're in `parsePrimaryExpression` and `peek_type()` is `DICT_OUTPUT_REF`, it's a direct reference.
                // Let's add that case here.
            }
            return parsePathReference(); // Treat identifiers potentially as path starts
        } else {
             // Single identifier acting as a variable name or simple reference.
             return ast::createIdentifierNode(match_and_get_lexeme(tokens::TokenType::IDENTIFIER), line, column);
        }
    } else if (peek_type() == tokens::TokenType::DICT_OUTPUT_REF) { // For expressions like `[>1] * 2`
        match(tokens::TokenType::DICT_OUTPUT_REF); // Consume `>.`
        // Assuming the ID is numeric after the >. for simplicity in expression context.
        // A full parser might allow identifiers for dictionary keys too.
        double dict_id = match_and_get_literal<double>(tokens::TokenType::NUMERIC_LITERAL);
        // For now, just return a NumericLiteralNode for the ID; the runtime will resolve it.
        // A specific `DictOutputReferenceNode` might be better.
        return ast::createNumericLiteralNode(dict_id, line, column);
    }
    else {
        error("Expected primary expression (literal, identifier, path reference, or parenthesized expression): " + current_token_.toString());
    }
    return nullptr; // Should not be reached
}

// Parses multiplicative expressions (*, /).
// Higher precedence than additive.
std::unique_ptr<ast::AstNode> Parser::parseMultiplicativeExpression() {
    // Start by parsing a primary expression (base unit of an expression).
    auto left = parsePrimaryExpression();

    // Loop as long as the current token is a multiplication or division operator.
    while (peek_type() == tokens::TokenType::OP_MULTIPLY || peek_type() == tokens::TokenType::SLASH) {
        tokens::TokenType op_type = peek_type(); // Store the operator type
        advance(); // Consume the operator token

        // Parse the right-hand side, which is also a primary expression (due to precedence).
        auto right = parsePrimaryExpression();

        // Determine the AST operator enum.
        ast::BinaryExpressionNode::Operator op;
        if (op_type == tokens::TokenType::OP_MULTIPLY) {
            op = ast::BinaryExpressionNode::Operator::MULTIPLY;
        } else { // TokenType::SLASH in mathematical-expression context
            op = ast::BinaryExpressionNode::Operator::DIVIDE;
        }
        // Create a new BinaryExpressionNode, making the previously parsed 'left'
        // become the left child, the new 'right' become the right child.
        // The result of this binary expression then becomes the new 'left' for chaining.
        left = ast::createBinaryExpressionNode(std::move(left), op, std::move(right),
                                             current_token_.line, current_token_.column);
    }
    return left; // Return the root of the parsed multiplicative expression.
}

// Parses additive expressions (+, -).
// Lower precedence than multiplicative.
std::unique_ptr<ast::AstNode> Parser::parseAdditiveExpression() {
    // Start by parsing a multiplicative expression (handle higher precedence first).
    auto left = parseMultiplicativeExpression();

    // Loop as long as the current token is an addition or subtraction operator.
    while (peek_type() == tokens::TokenType::OP_ADD || peek_type() == tokens::TokenType::OP_SUBTRACT) {
        tokens::TokenType op_type = peek_type(); // Store the operator type
        advance(); // Consume the operator token

        // Parse the right-hand side, which is also a multiplicative expression (due to precedence).
        auto right = parseMultiplicativeExpression();

        // Determine the AST operator enum.
        ast::BinaryExpressionNode::Operator op;
        if (op_type == tokens::TokenType::OP_ADD) {
            op = ast::BinaryExpressionNode::Operator::ADD;
        } else { // TokenType::OP_SUBTRACT
            op = ast::BinaryExpressionNode::Operator::SUBTRACT;
        }
        // Create a new BinaryExpressionNode, making the previously parsed 'left'
        // become the left child, the new 'right' become the right child.
        // The result of this binary expression then becomes the new 'left' for chaining.
        left = ast::createBinaryExpressionNode(std::move(left), op, std::move(right),
                                             current_token_.line, current_token_.column);
    }
    return left; // Return the root of the parsed additive expression.
}

} // namespace parser
} // namespace qps
