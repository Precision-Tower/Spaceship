// qps/core/src/parser/c/reference.cpp

#include "../h/reference.hpp" // Include the reference parsing header
#include "../h/_index.hpp"    // Include the main Parser header for access to its members
#include "../../ast/ast_utils.hpp" // For AST node creation helpers
#include <string>             // For string manipulation
#include <vector>             // For path segments

namespace qps {
namespace parser {

// Note: In the final integrated parser, this function will remain a member of the Parser class.
// It is defined here to represent the content of 'reference.cpp'.

// Parses a PathReference (e.g., folder/file.key.item-).
// This function assumes it's called when the current token is the start of a path (an IDENTIFIER).
std::unique_ptr<ast::PathReferenceNode> Parser::parsePathReference() {
    int line = current_token_.line;
    int column = current_token_.column;
    std::string path_str; // Will accumulate the full path string

    // A path must start with an IDENTIFIER.
    path_str += match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    // Consume subsequent path separators (SLASH or DOT) and identifiers.
    // Loop as long as the next token is a path separator.
    while (peek_type() == tokens::TokenType::SLASH || peek_type() == tokens::TokenType::DOT) {
        // Append the separator to the path string.
        path_str += match_and_get_lexeme(peek_type()); // Consume '/' or '.'

        // After a separator, an identifier segment is expected.
        path_str += match_and_get_lexeme(tokens::TokenType::IDENTIFIER);
    }

    // Now, let's consider the special case where a path can end with a keyword like 'item-' or 'term:'.
    // Example: 'folder/file.key.item-'
    // The `recognizeIdentifierOrKeyword` in the lexer will already tokenize 'item-' as `KW_ITEM`.
    // So, if the parser is building a path and encounters KW_ITEM, KW_TERM, KW_KEY, etc.,
    // it needs to decide if these are keywords in their own right, or the *name* part of a path segment.
    // The grammar implies `path/to.key.term:` means `term` is the segment, and `:` is part of its lexical token.
    // If the lexer produces `KW_ITEM` or `KW_TERM` (e.g., `item-`, `term:`) as single tokens,
    // and they appear as the *last segment* of a path, we need to handle that.
    // For now, assume a path consists only of IDENTIFIERs separated by '.' or '/'.
    // If a path segment itself is a keyword like 'item', 'term', 'key', that implies specific semantic meaning
    // that the path needs to capture, or that the path stops before such a keyword.

    // Given the `QPS Syntax Rules` example `folder/file.key.`, the `key.` itself is a token.
    // If a path like `folder/file.key.` is encountered, the `key.` token will be consumed separately.
    // For now, this function will build a path string from sequential IDENTIFIER, SLASH/DOT, IDENTIFIER.

    return ast::createPathReferenceNode(path_str, line, column);
}


std::unique_ptr<ast::SymbolReferenceNode>
Parser::parseSymbolReference() {

    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::OPEN_BRACKET);

    int parent_depth = 0;
    std::string symbol;

    ast::SymbolReferenceOrigin origin;

    // Bracket navigation has two roots:
    //
    //   [>shape.dimensions]
    //       external/document navigation
    //
    //   [v.bore1]
    //       local navigation rooted at binding v
    if (peek_type() == tokens::TokenType::REFERENCE_OPERATOR) {
        match(tokens::TokenType::REFERENCE_OPERATOR);

        origin =
            ast::SymbolReferenceOrigin::CURRENT_FILE;
    }
    else if (peek_type() == tokens::TokenType::IDENTIFIER) {
        origin =
            ast::SymbolReferenceOrigin::LOCAL_BINDING;
    }
    else {
        error(
            "Expected '>' or local binding name after '[' in structural reference. Found: " +
            current_token_.toString());
    }

    // A leading '.' explicitly leaves the current file while remaining
    // in its containing module:
    //
    //   [>.file.name]
    if (peek_type() == tokens::TokenType::DOT) {
        symbol +=
            match_and_get_lexeme(
                tokens::TokenType::DOT);

        origin =
            ast::SymbolReferenceOrigin::CURRENT_FOLDER_FILE;
    }

    // Leading slash count is explicit parent traversal:
    //
    //   /file...   -> one parent
    //   //file...  -> two parents
    while (peek_type() == tokens::TokenType::SLASH) {
        symbol +=
            match_and_get_lexeme(
                tokens::TokenType::SLASH);

        ++parent_depth;

        origin =
            ast::SymbolReferenceOrigin::RELATIVE_MODULE;
    }

    std::vector<ast::SymbolReferenceSegment>
        segments;

    const std::string first =
        match_and_get_lexeme(
            tokens::TokenType::IDENTIFIER);

    symbol += first;

    segments.push_back({
        first,
        ast::SymbolReferenceSeparator::ROOT
    });

    while (peek_type() == tokens::TokenType::DOT ||
           peek_type() == tokens::TokenType::SLASH) {

        const auto separator_type =
            peek_type();

        symbol +=
            match_and_get_lexeme(
                separator_type);

        const std::string name =
            match_and_get_lexeme(
                tokens::TokenType::IDENTIFIER);

        symbol += name;

        const auto separator =
            separator_type == tokens::TokenType::DOT
                ? ast::SymbolReferenceSeparator::DOT
                : ast::SymbolReferenceSeparator::SLASH;

        if (separator ==
                ast::SymbolReferenceSeparator::SLASH &&
            origin ==
                ast::SymbolReferenceOrigin::CURRENT_FILE) {

            origin =
                ast::SymbolReferenceOrigin::RELATIVE_MODULE;
        }

        segments.push_back({
            name,
            separator
        });
    }

    bool selects_item_value = false;

    // Item-value selection is explicit and belongs inside the reference:
    //
    //   [>key.dimensions.body.radius-]
    //
    // Without '-', the reference selects structural content:
    //
    //   [>key.dimensions]
    if (peek_type() == tokens::TokenType::OP_SUBTRACT) {
        symbol +=
            match_and_get_lexeme(
                tokens::TokenType::OP_SUBTRACT);

        selects_item_value = true;
    }

    match(tokens::TokenType::CLOSE_BRACKET);

    return ast::createSymbolReferenceNode(
        symbol,
        origin,
        parent_depth,
        std::move(segments),
        selects_item_value,
        line,
        column);
}

} // namespace parser
} // namespace qps
