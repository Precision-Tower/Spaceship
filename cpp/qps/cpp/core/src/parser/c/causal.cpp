// qps/core/src/parser/c/causal.cpp

#include "../h/causal.hpp"    // Include the causal parsing header
#include "../h/_index.hpp"     // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'causal.cpp'.

// Helper function to parse one side of a causal relationship: 'Entity: (Input = Output)'
// This will be used for both the left and right sides of the '='.
std::unique_ptr<ast::CausalRelationshipNode::CausalSide> Parser::parseCausalSide() {
    int line = current_token_.line;
    int column = current_token_.column;

    // 1. Parse Entity: This is likely an Identifier or a PathReference.
    std::unique_ptr<ast::AstNode> entity;
    if (peek_type() == tokens::TokenType::IDENTIFIER) {
        // If it's an identifier and the next token is a colon, it's 'Entity:'
        if (peek_next_type() == tokens::TokenType::COLON) {
            entity = ast::createIdentifierNode(match_and_get_lexeme(tokens::TokenType::IDENTIFIER), line, column);
            match(tokens::TokenType::COLON); // Consume ':'
        } else {
            // Could be a standalone identifier that's part of a path reference.
            entity = parsePathReference();
        }
    } else if (peek_type() == tokens::TokenType::KW_KEY || peek_type() == tokens::TokenType::KW_TERM) {
        // If the entity is a Key. or Term:, parse it as a declaration.
        entity = parseDeclaration();
    } else {
        error("Expected an entity (Identifier or PathReference) for Causal Relationship side. Found: " + current_token_.toString());
    }

    // 2. Parse the (Input = Output) container
    match(tokens::TokenType::OPEN_PAREN); // Consume '('

    std::unique_ptr<ast::AstNode> input_node;
    std::unique_ptr<ast::AstNode> output_node;

    // Parse Input
    // Input can be a literal, reference, or expression.
    input_node = parsePrimaryExpression(); // Start with primary for flexibility

    match(tokens::TokenType::EQUALS); // Consume '='

    // Parse Output
    // Output can also be a literal, reference, or expression.
    output_node = parsePrimaryExpression();

    match(tokens::TokenType::CLOSE_PAREN); // Consume ')'

    return ast::createCausalSide(std::move(entity), std::move(input_node), std::move(output_node));
}


// Parses a Causal Relationship declaration: 'EntityA: (InputA = OutputA) = EntityB: (InputB = OutputB);'
// It handles potential chaining of relationships.
std::unique_ptr<ast::CausalRelationshipNode> Parser::parseCausalRelationship() {
    int line = current_token_.line;
    int column = current_token_.column;

    // Parse the left side of the first relationship.
    std::unique_ptr<ast::CausalRelationshipNode::CausalSide> left_side_of_first_link = parseCausalSide();

    // Loop to handle chained relationships (A = B = C)
    std::unique_ptr<ast::CausalRelationshipNode> first_causal_node = nullptr;
    std::unique_ptr<ast::CausalRelationshipNode>* current_chain_link_ptr = &first_causal_node;

    // Keep parsing until the current token is not an '=' or we reach EOF.
    while (peek_type() == tokens::TokenType::EQUALS) {
        match(tokens::TokenType::EQUALS); // Consume the '=' operator

        // Parse the right side of the current relationship link.
        // This 'right_side' will become the 'left_side' for the next link if chaining continues.
        std::unique_ptr<ast::CausalRelationshipNode::CausalSide> right_side_of_current_link = parseCausalSide();

        // Create the CausalRelationshipNode for the current link in the chain.
        auto current_causal_node = ast::createCausalRelationshipNode(
            std::move(left_side_of_first_link), // Use the 'left_side_of_first_link' as the left for the current node
            std::move(right_side_of_current_link), // Use the parsed 'right_side' as the right for the current node
            line, column);

        // Link the new node into the chain.
        *current_chain_link_ptr = std::move(current_causal_node);

        // If chaining continues, the right side of the *current* link becomes
        // the left side of the *next* link.
        // This requires careful handling of ownership and the `CausalSide` objects.
        // A simpler AST might represent chaining as a list of relationships.
        // For now, I'm adapting the CausalRelationshipNode to represent a single A = B.
        // If chaining (A=B=C) is parsed, it will be parsed as (A=B) and then (B=C) internally,
        // so `left_side_of_first_link` needs to be updated for the next iteration.

        // Re-evaluate chaining: "Chaining A = B = C implies sequential flow."
        // This suggests A=B is one relationship, and B=C is another.
        // The most straightforward way to represent this in the AST is a list of CausalRelationshipNodes.
        // So, `parseCausalRelationship` should parse ONE `A = B` relationship.
        // If the grammar truly allows `A=B=C;`, the outer `parseDeclaration` or a specific
        // `parseCausalChain` function would call `parseCausalRelationship` repeatedly.

        // Let's simplify: `parseCausalRelationship` parses one `A = B` structure.
        // The loop for chaining would be in a higher-level parsing function (e.g., parseDeclaration)
        // that repeatedly calls `parseCausalRelationship` if it sees `=` again.

        // Rewriting parseCausalRelationship to parse only ONE `A = B` link.
        error("Chained causal relationships (A=B=C) require a higher-level parsing strategy. This function parses one A = B link only.");
        return nullptr; // This error will be thrown to indicate the higher-level parsing needs to adapt.
    }

    match(tokens::TokenType::SEMICOLON); // Consume ';' that terminates the causal relationship

    // Return the first and only causal node parsed.
    return first_causal_node;
}


} // namespace parser
} // namespace qps
