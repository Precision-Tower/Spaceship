# // gravitus_principia/core/src/tokens/h/char_stream.hpp

#ifndef GRAVITUS_TOKENS_H_CHAR_STREAM_HPP
#define GRAVITUS_TOKENS_H_CHAR_STREAM_HPP

#include <string>
#include <vector>

namespace gravitus {
namespace tokens {

class CharStream {
public:
    explicit CharStream(const std::string& source_code);
    char peek() const;
    char peek_ahead(int n) const;
    char advance();
    bool isAtEnd() const;
    int getCurrentLine() const;
    int getCurrentColumn() const;

private:
    const std::vector<char> source_;
    int current_position_;
    int current_line_;
    int current_column_;
};

} // namespace tokens
} // namespace gravitus

#endif // GRAVITUS_TOKENS_H_CHAR_STREAM_HPP

# // gravitus_principia/core/src/tokens/h/lexer.hpp

#ifndef GRAVITUS_TOKENS_H_LEXER_HPP
#define GRAVITUS_TOKENS_H_LEXER_HPP

#include <memory>     // Required for std::unique_ptr
#include <functional> // NEW: Required for std::function for consume_while
#include "token.hpp"
#include "char_stream.hpp"
#include "recognizer.hpp" // Now Lexer depends on TokenRecognizer

namespace gravitus {
namespace tokens {

class Lexer {
public:
    // The Lexer takes a CharStream by reference, it doesn't own it.
    explicit Lexer(CharStream& stream);
    
    // Primary public method to get the next token from the stream.
    Token getNextToken();

private:
    CharStream& stream_; // Reference to the underlying character stream
    int current_line_;   // Current line number in the source code
    int current_column_; // Current column number in the source code

    // The Lexer now *owns* or *uses* a TokenRecognizer instance to do the actual recognition.
    std::unique_ptr<TokenRecognizer> recognizer_;

    // Helper functions for Lexer's own logic (e.g., whitespace/comment skipping)
    // FIX: Changed signature from bool (*predicate)(char) to std::function<bool(char)>
    std::string consume_while(std::function<bool(char)> predicate);
    void skipWhitespace();
    void handleSingleLineComment();
    bool handleMultiLineComment(); // Returns true if a multi-line comment was closed.
};

} // namespace tokens
} // namespace gravitus

#endif // GRAVITUS_TOKENS_H_LEXER_HPP

# // gravitus_principia/core/src/tokens/h/recognizer.hpp

#ifndef GRAVITUS_TOKENS_H_TOKEN_RECOGNIZER_HPP
#define GRAVITUS_TOKENS_H_TOKEN_RECOGNIZER_HPP

#include <string>
#include <unordered_map>
#include <optional>   // Required for std::optional
#include <functional> // NEW: Required for std::function
#include "token.hpp"
#include "char_stream.hpp" // CharStream is needed to operate on the input stream

namespace gravitus {
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
} // namespace gravitus

#endif // GRAVITUS_TOKENS_H_TOKEN_RECOGNIZER_HPP

# // gravitus_principia/core/src/tokens/h/token.hpp

#ifndef GRAVITUS_TOKENS_H_TOKEN_HPP
#define GRAVITUS_TOKENS_H_TOKEN_HPP

#include <string>
#include <variant> // For std::variant to hold different literal types

namespace gravitus {
namespace tokens {

enum class TokenType {
    OPEN_PAREN, CLOSE_PAREN, OPEN_BRACKET, CLOSE_BRACKET, OPEN_BRACE, CLOSE_BRACE,
    COLON, SEMICOLON, COMMA, DOT, SLASH, HASH, DOUBLE_HASH, BACKSLASH, EQUALS,
    KW_DEF, KW_ITEM, KW_TERM, KW_KEY, KW_FUNC, KW_CLASS, KW_LET, KW_IF, KW_ELSE, KW_ELIF,
    KW_TRY, KW_RAISE, KW_LOOP, KW_WHILE, KW_FOR, KW_RETURN, KW_PRINT, KW_ASSERT, KW_SET,
    KW_BREAK, KW_CONTINUE, KW_PASS, PIPE,
    TYPE_PATH, TYPE_NUMERIC, TYPE_ALPHANUM, TYPE_BOOLEAN, TYPE_NULL,
    IDENTIFIER, NUMERIC_LITERAL, STRING_LITERAL, BOOLEAN_LITERAL, NULL_LITERAL,
    OP_ADD, OP_SUBTRACT, OP_MULTIPLY, OP_DIVIDE,
    EXEC_DELIMITER, DICT_INPUT_REF, DICT_OUTPUT_REF,
    END_OF_FILE, UNKNOWN
};

struct Token {
    TokenType type;
    std::string lexeme;
    int line;
    int column;
    std::variant<std::monostate, double, std::string, bool> literal;

    Token(TokenType type_param, std::string lexeme_param, int line_param, int column_param,
          std::variant<std::monostate, double, std::string, bool> literal_param = std::monostate());
    Token(); // Default constructor
    std::string toString() const;
};

} // namespace tokens
} // namespace gravitus

#endif // GRAVITUS_TOKENS_H_TOKEN_HPP
