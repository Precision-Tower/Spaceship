// qps/core/src/tokens/h/recognizer.hpp

#ifndef QPS_TOKENS_H_TOKEN_RECOGNIZER_HPP
#define QPS_TOKENS_H_TOKEN_RECOGNIZER_HPP

#include <string>
#include <unordered_map>
#include <optional>   // Required for std::optional
#include <functional> // NEW: Required for std::function
#include "token.hpp"
#include "char_stream.hpp" // CharStream is needed to operate on the input stream

namespace qps {
namespace tokens {

// TokenRecognizer is responsible for identifying and creating different types of tokens
// based on the input character stream. It holds no state related to the lexer's
// overall position, but is given references to manage the current line/column for tokens.
class TokenRecognizer {
public:
    // Constructor: Takes a reference to the CharStream and references to the
    // lexer's current line and column, so it can correctly set token positions.
    explicit TokenRecognizer(CharStream& stream, int& current_line, int& current_column);

    // Recognizes an identifier or a keyword (like 'item-', 'term:', 'true', 'null').
    Token recognizeIdentifierOrKeyword();

    // Recognizes numeric literals (integers, floats, scientific notation).
    Token recognizeNumericLiteral();

    // Recognizes string literals enclosed in double quotes.
    Token recognizeStringLiteral();

    // Recognizes QPS def" prose until the exact closing sequence ";
    Token recognizeDefinitionText();

    // Attempts to recognize a type suffix (e.g., /p;, /n;, /null;).
    // Returns an optional Token if a match is found, otherwise std::nullopt.
    std::optional<Token> recognizeTypeSuffix();

private:
    CharStream& stream_;     // Reference to the character stream
    int& start_line_;        // Reference to the lexer's current line
    int& start_column_;      // Reference to the lexer's current column

    // Helper to consume characters from the stream as long as a predicate holds true.
    // FIX: Changed signature from bool (*predicate)(char) to std::function<bool(char)>
    std::string consume_while(std::function<bool(char)> predicate);

    // New helper: Peeks a string of 'n' characters without advancing the stream.
    std::string peek_string(int n);

    // Static maps for keywords and type suffixes. These are constant and
    // initialized once, providing efficient lookups for token recognition.
    static const std::unordered_map<std::string, TokenType> keywords_;
    static const std::unordered_map<std::string, TokenType> type_suffixes_;
};

} // namespace tokens
} // namespace qps

#endif // QPS_TOKENS_H_TOKEN_RECOGNIZER_HPP