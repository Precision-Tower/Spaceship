# // gravitus_principia/core/src/tokens/c/char_stream.cpp

#include "../h/char_stream.hpp" // Corrected: points to its header in tokens/h/
#include <algorithm>
#include <stdexcept>

namespace gravitus {
namespace tokens {

CharStream::CharStream(const std::string& source_code)
    : source_(source_code.begin(), source_code.end()),
      current_position_(0),
      current_line_(1),
      current_column_(1)
{}

char CharStream::peek() const {
    if (isAtEnd()) {
        return '\0';
    }
    return source_[current_position_];
}

char CharStream::peek_ahead(int n) const {
    int target_pos = current_position_ + n;
    if (target_pos >= static_cast<int>(source_.size())) {
        return '\0';
    }
    return source_[target_pos];
}

char CharStream::advance() {
    if (isAtEnd()) {
        return '\0';
    }

    char consumed_char = source_[current_position_];
    current_position_++;

    if (consumed_char == '\n') {
        current_line_++;
        current_column_ = 1;
    } else {
        current_column_++;
    }

    return consumed_char;
}

bool CharStream::isAtEnd() const {
    return current_position_ >= static_cast<int>(source_.size());
}

int CharStream::getCurrentLine() const {
    return current_line_;
}

int CharStream::getCurrentColumn() const {
    return current_column_;
}

} // namespace tokens
} // namespace gravitus

# // gravitus_principia/core/src/tokens/c/lexer.cpp

#include "../h/lexer.hpp"
#include <cctype> // For isspace etc.
#include <stdexcept> // For std::runtime_error
#include <string> // For std::string, std::to_string

namespace gravitus {
namespace tokens {

// Lexer constructor: Initializes the CharStream reference and creates the TokenRecognizer.
Lexer::Lexer(CharStream& stream)
    : stream_(stream), 
      current_line_(1), 
      current_column_(1),
      // Initialize the recognizer, passing it the stream and references to Lexer's line/column.
      // The recognizer needs to know the *start* position for each token.
      recognizer_(std::make_unique<TokenRecognizer>(stream, current_line_, current_column_)) 
{}

// Helper to skip whitespace. It operates directly on the stream.
void Lexer::skipWhitespace() {
    // FIX: Updated consume_while call to use lambda with std::function
    consume_while([](char c) {
        return std::isspace(static_cast<unsigned char>(c));
    });
}

// Helper to handle single-line comments.
void Lexer::handleSingleLineComment() {
    while (!stream_.isAtEnd() && stream_.peek() != '\n') {
        stream_.advance();
    }
}

// Helper to handle multi-line comments. Returns true if successfully closed.
bool Lexer::handleMultiLineComment() {
    int initial_line = stream_.getCurrentLine();
    int initial_column = stream_.getCurrentColumn();

    while (!stream_.isAtEnd()) {
        if (stream_.peek() == '#' && stream_.peek_ahead(1) == '#') {
            stream_.advance(); // Consume first '#'
            stream_.advance(); // Consume second '#'
            return true; // Comment successfully closed
        }
        stream_.advance();
    }
    // If we reach end of file and didn't find closing '##'
    throw std::runtime_error("Unclosed multi-line comment starting at L" +
                             std::to_string(initial_line) + ", C" + std::to_string(initial_column));
}

// Main function to get the next token. This is the orchestrator.
Token Lexer::getNextToken() {
    // Update the line/column references in the recognizer to the current stream position
    // before attempting to recognize a token. This ensures accurate token positioning.
    current_line_ = stream_.getCurrentLine();
    current_column_ = stream_.getCurrentColumn();

    skipWhitespace(); // Always skip whitespace before trying to find the next token

    // Check for EOF first, after skipping any trailing whitespace.
    if (stream_.isAtEnd()) {
        return Token(TokenType::END_OF_FILE, "", current_line_, current_column_);
    }

    char current_char = stream_.peek();
    char next_char = stream_.peek_ahead(1); // Peek ahead for multi-character tokens

    // --- Complex Multi-character Token Checks (Longest Match First) ---
    // Type suffixes (e.g., /p;, /n;, /null;)
    auto type_suffix_token = recognizer_->recognizeTypeSuffix();
    if (type_suffix_token.has_value()) {
        return type_suffix_token.value();
    }

    // Comments '##'
    if (current_char == '#' && next_char == '#') {
        stream_.advance(); // Consume first '#'
        stream_.advance(); // Consume second '#'
        handleMultiLineComment(); // Handle the comment
        return getNextToken(); // Recursively call to get the *next* actual token
    }

    // Dictionary input/output refs '<.' and '>.'
    if (current_char == '<' && next_char == '.') {
        stream_.advance(); // Consume '<'
        stream_.advance(); // Consume '.'
        return Token(TokenType::DICT_INPUT_REF, "<.", current_line_, current_column_);
    } else if (current_char == '>' && next_char == '.') {
        stream_.advance(); // Consume '>'
        stream_.advance(); // Consume '.'
        return Token(TokenType::DICT_OUTPUT_REF, ">.", current_line_, current_column_);
    }

    // --- Literal and Keyword Checks ---
    // Numeric literals (including those starting with +/- if followed by a digit)
    // Check if it starts with a digit OR a sign followed by a digit
    if (std::isdigit(static_cast<unsigned char>(current_char)) || // Direct check for digit
        ((current_char == '+' || current_char == '-') && std::isdigit(static_cast<unsigned char>(next_char)))) { // Sign followed by digit
        return recognizer_->recognizeNumericLiteral();
    }
    // String literals
    if (current_char == '"') {
        stream_.advance(); // Consume the opening quote before calling recognizer
        return recognizer_->recognizeStringLiteral();
    }
    // Identifiers or Keywords (including boolean/null literals like "true", "false", "null")
    if (std::isalpha(static_cast<unsigned char>(current_char)) || current_char == '_' || current_char == '-') {
        return recognizer_->recognizeIdentifierOrKeyword();
    }

    // --- Single-Character Token Checks ---
    // If it's not a multi-char, complex literal, or identifier, check single chars.
    switch (current_char) {
        case '(': stream_.advance(); return Token(TokenType::OPEN_PAREN, "(", current_line_, current_column_);
        case ')': stream_.advance(); return Token(TokenType::CLOSE_PAREN, ")", current_line_, current_column_);
        case '[': stream_.advance(); return Token(TokenType::OPEN_BRACKET, "[", current_line_, current_column_);
        case ']': stream_.advance(); return Token(TokenType::CLOSE_BRACKET, "]", current_line_, current_column_);
        case '{': stream_.advance(); return Token(TokenType::OPEN_BRACE, "{", current_line_, current_column_);
        case '}': stream_.advance(); return Token(TokenType::CLOSE_BRACE, "}", current_line_, current_column_);
        case ':': stream_.advance(); return Token(TokenType::COLON, ":", current_line_, current_column_);
        case ';': stream_.advance(); return Token(TokenType::SEMICOLON, ";", current_line_, current_column_);
        case ',': stream_.advance(); return Token(TokenType::COMMA, ",", current_line_, current_column_);
        case '.': stream_.advance(); return Token(TokenType::DOT, ".", current_line_, current_column_);
        case '/': stream_.advance(); return Token(TokenType::SLASH, "/", current_line_, current_column_); 
        case '=': stream_.advance(); return Token(TokenType::EQUALS, "=", current_line_, current_column_);
        case '|': stream_.advance(); return Token(TokenType::PIPE, "|", current_line_, current_column_);
        case '+': stream_.advance(); return Token(TokenType::OP_ADD, "+", current_line_, current_column_);
        case '-': stream_.advance(); return Token(TokenType::OP_SUBTRACT, "-", current_line_, current_column_);
        case '*': stream_.advance(); return Token(TokenType::OP_MULTIPLY, "*", current_line_, current_column_);
        case '_': stream_.advance(); return Token(TokenType::EXEC_DELIMITER, "_", current_line_, current_column_);
        case '#': // Single-line comment '#'
            stream_.advance(); // Consume '#'
            handleSingleLineComment(); // Handle the comment
            return getNextToken(); // Recursively call to get the *next* actual token
    }

    // If we reach here, it's an unrecognized character.
    char unrecognized_char = stream_.advance();
    throw std::runtime_error("Unrecognized character: '" + std::string(1, unrecognized_char) +
                             "' at L" + std::to_string(current_line_) + ", C" + std::to_string(current_column_));
}

} // namespace tokens
} // namespace gravitus

# // gravitus_principia/core/src/tokens/c/recognizer.cpp

#include "../h/recognizer.hpp"
#include <cctype>    // For isalnum, isdigit, isalpha, isspace
#include <stdexcept> // For std::runtime_error, std::out_of_range, std::invalid_argument
#include <string>    // For std::string, std::to_string

namespace gravitus {
namespace tokens {

// Static member initialization for keywords_ and type_suffixes_ maps.
// These maps are initialized once when the program starts.
const std::unordered_map<std::string, TokenType> TokenRecognizer::keywords_ = {
    {"def\"", TokenType::KW_DEF}, // Special case for def"
    {"item-", TokenType::KW_ITEM},
    {"term:", TokenType::KW_TERM}, // Term: needs its own handling due to ':'
    {"key.", TokenType::KW_KEY},   // Key. needs its own handling due to '.'
    {"-func", TokenType::KW_FUNC},
    {"-class", TokenType::KW_CLASS},
    {"-let", TokenType::KW_LET},
    {"-if", TokenType::KW_IF},
    {"-else", TokenType::KW_ELSE},
    {"-elif", TokenType::KW_ELIF},
    {"-try", TokenType::KW_TRY},
    {"-raise", TokenType::KW_RAISE},
    {"-loop", TokenType::KW_LOOP},
    {"-while", TokenType::KW_WHILE},
    {"-for", TokenType::KW_FOR},
    {"-return-", TokenType::KW_RETURN},
    {"-print", TokenType::KW_PRINT},
    {"-assert", TokenType::KW_ASSERT},
    {"-set", TokenType::KW_SET},
    {"-break", TokenType::KW_BREAK},
    {"-continue", TokenType::KW_CONTINUE},
    {"-pass", TokenType::KW_PASS},
    {"true", TokenType::BOOLEAN_LITERAL}, // Handled as keywords for explicit typing
    {"false", TokenType::BOOLEAN_LITERAL},// Handled as keywords for explicit typing
    {"null", TokenType::NULL_LITERAL}      // Handled as keywords for explicit typing
};

const std::unordered_map<std::string, TokenType> TokenRecognizer::type_suffixes_ = {
    {"/p;", TokenType::TYPE_PATH},
    {"/n;", TokenType::TYPE_NUMERIC},
    {"/a;", TokenType::TYPE_ALPHANUM},
    {"/b;", TokenType::TYPE_BOOLEAN},
    {"/null;", TokenType::TYPE_NULL}
};

// Constructor: Initializes the TokenRecognizer with references to the CharStream
// and the current line/column from the main Lexer.
TokenRecognizer::TokenRecognizer(CharStream& stream, int& current_line, int& current_column)
    : stream_(stream), start_line_(current_line), start_column_(current_column) {
    // Static maps are initialized implicitly.
}

// Consumes characters from the stream as long as the predicate returns true.
// Returns the consumed string. This is a local helper for recognition functions.
std::string TokenRecognizer::consume_while(std::function<bool(char)> predicate) {
    std::string result;
    while (!stream_.isAtEnd() && predicate(stream_.peek())) {
        result += stream_.advance();
    }
    return result;
}

// Peeks a string of 'n' characters from the stream without advancing it.
std::string TokenRecognizer::peek_string(int n) {
    std::string result;
    for (int i = 0; i < n && !stream_.isAtEnd(); ++i) {
        // Use peek_ahead to read characters without moving the stream pointer
        result += stream_.peek_ahead(i);
    }
    return result;
}

// Recognizes an identifier or a keyword.
// This function determines if a sequence of characters forms a reserved keyword
// or a user-defined identifier. It also handles special keyword endings.
Token TokenRecognizer::recognizeIdentifierOrKeyword() {
    std::string text;
    // Consume characters that are alphanumeric or underscore or hyphen
    // FIX: Use lambda directly with std::function, cast char to unsigned char for cctype functions
    text += consume_while([](char c){
        return std::isalnum(static_cast<unsigned char>(c)) || c == '_' || c == '-';
    });

    // Special handling for keywords that have a trailing delimiter as part of their lexeme
    // e.g., "item-", "term:", "key.", "def\""
    if (!stream_.isAtEnd()) {
        if (stream_.peek() == ':' && keywords_.count(text + ":")) { // For "term:"
            text += stream_.advance();
        } else if (stream_.peek() == '.' && keywords_.count(text + ".")) { // For "key."
            text += stream_.advance();
        } else if (stream_.peek() == '"' && keywords_.count(text + "\"")) { // For "def\""
            text += stream_.advance();
        }
    }

    // Look up the text in the keywords map.
    // If found, it's a keyword (including true, false, null); otherwise, it's an IDENTIFIER.
    auto it = keywords_.find(text);
    if (it != keywords_.end()) {
        // For boolean and null literals, ensure the token value is set correctly.
        // The value helps the parser/interpreter avoid re-parsing the string.
        if (it->second == TokenType::BOOLEAN_LITERAL) {
            return Token(it->second, text, start_line_, start_column_, (text == "true"));
        }
        if (it->second == TokenType::NULL_LITERAL) {
            return Token(it->second, text, start_line_, start_column_, std::monostate());
        }
        return Token(it->second, text, start_line_, start_column_);
    }

    return Token(TokenType::IDENTIFIER, text, start_line_, start_column_);
}

// Recognizes numeric literals (integers, floats, scientific notation).
// This function parses sequences of digits, decimal points, and exponents
// to form a numeric token, handling potential errors in format or range.
Token TokenRecognizer::recognizeNumericLiteral() {
    std::string num_str;
    
    // Check for optional leading sign (+ or -)
    // Only consume if it's followed by a digit to avoid misinterpreting lone signs
    if ((stream_.peek() == '+' || stream_.peek() == '-') && std::isdigit(static_cast<unsigned char>(stream_.peek_ahead(1)))) {
        num_str += stream_.advance();
    }

    // Consume digits before the decimal point
    // FIX: Use lambda directly with std::function, cast char to unsigned char for cctype functions
    num_str += consume_while([](char c){ return std::isdigit(static_cast<unsigned char>(c)); });

    // Handle decimal point: Must be followed by at least one digit
    if (stream_.peek() == '.' && !stream_.isAtEnd() && std::isdigit(static_cast<unsigned char>(stream_.peek_ahead(1)))) {
        num_str += stream_.advance(); // Consume '.'
        // FIX: Use lambda directly with std::function, cast char to unsigned char for cctype functions
        num_str += consume_while([](char c){ return std::isdigit(static_cast<unsigned char>(c)); }); // Consume digits after '.'
    }

    // Handle exponent (e or E): Must be followed by optional sign and then digits
    if (!stream_.isAtEnd() && (stream_.peek() == 'e' || stream_.peek() == 'E')) {
        char exponent_char = stream_.advance(); // Consume 'e' or 'E'
        num_str += exponent_char;

        if (!stream_.isAtEnd() && (stream_.peek() == '+' || stream_.peek() == '-')) {
            num_str += stream_.advance(); // Consume sign (+ or -)
        }
        
        // FIX: Use lambda directly with std::function, cast char to unsigned char for cctype functions
        std::string exponent_digits = consume_while([](char c){ return std::isdigit(static_cast<unsigned char>(c)); });
        if (exponent_digits.empty()) {
            throw std::runtime_error("Invalid numeric literal: exponent without digits at L" +
                                     std::to_string(start_line_) + ", C" + std::to_string(start_column_));
        }
        num_str += exponent_digits;
    }

    // Edge case: if only a sign was consumed (e.g., '+') or nothing at all
    // This check is important after parsing the full number string.
    if (num_str.empty() || (num_str.length() == 1 && (num_str[0] == '+' || num_str[0] == '-'))) {
           throw std::runtime_error("Invalid numeric literal format: empty or just sign at L" +
                                    std::to_string(start_line_) + ", C" + std::to_string(start_column_));
    }

    // Attempt to convert to double and create the token.
    try {
        double value = std::stod(num_str);
        return Token(TokenType::NUMERIC_LITERAL, num_str, start_line_, start_column_, value);
    } catch (const std::out_of_range& e) {
        throw std::runtime_error("Numeric literal out of range: " + num_str + " at L" +
                                 std::to_string(start_line_) + ", C" + std::to_string(start_column_));
    } catch (const std::invalid_argument& e) {
        // This catch block might be redundant if the initial parsing logic prevents invalid formats,
        // but it provides an extra layer of safety against `stod` failures.
        throw std::runtime_error("Invalid numeric literal format (stod conversion error): " + num_str + " at L" +
                                 std::to_string(start_line_) + ", C" + std::to_string(start_column_));
    }
}


// Recognizes string literals enclosed in double quotes.
// Handles escape sequences: \n, \t, \r, \", \\.
// Assumes the opening quote (") has already been consumed by the caller (Lexer).
Token TokenRecognizer::recognizeStringLiteral() {
    std::string str_val;
    int current_line = start_line_;
    int current_column = start_column_;

    // Consume characters until the closing double quote or end of file.
    while (!stream_.isAtEnd() && stream_.peek() != '"') {
        char c = stream_.advance();
        // Handle escape sequences starting with a backslash
        if (c == '\\') {
            if (stream_.isAtEnd()) {
                throw std::runtime_error("Unterminated escape sequence at end of file in string literal at L" +
                                         std::to_string(current_line) + ", C" + std::to_string(current_column));
            }
            char next_c = stream_.advance(); // Consume the character after backslash
            if (next_c == 'n') { str_val += '\n'; }
            else if (next_c == 't') { str_val += '\t'; }
            else if (next_c == 'r') { str_val += '\r'; }
            else if (next_c == '"') { str_val += '"'; }   // Allow escaping quotes within string
            else if (next_c == '\\') { str_val += '\\'; } // Allow escaping backslashes
            else {
                // For unrecognized escape sequences, treat the backslash and the character literally.
                // Or, throw an error if strict adherence to defined escapes is required.
                str_val += c;       // Add the backslash back
                str_val += next_c;  // Add the unrecognized escaped character
            }
        } else {
            str_val += c;
        }
    }

    if (stream_.isAtEnd()) {
        throw std::runtime_error("Unterminated string literal starting at L" +
                                 std::to_string(current_line) + ", C" + std::to_string(current_column));
    }

    stream_.advance(); // Consume the closing '"'

    // The lexeme includes quotes, the value is just the inner string content.
    return Token(TokenType::STRING_LITERAL, "\"" + str_val + "\"", current_line, current_column, str_val);
}

// Attempts to recognize a type suffix like /p;, /n;, /null;.
// This function is called when the current character is '/'. It tries to match
// a known type suffix by peeking ahead. If a full match is found, it consumes
// the characters and returns the corresponding Token. If not, it does not
// advance the stream and returns std::nullopt.
std::optional<Token> TokenRecognizer::recognizeTypeSuffix() {
    int original_line = start_line_;
    int original_column = start_column_;

    if (stream_.peek() != '/') { // Should not happen if called correctly, but safety check.
        return std::nullopt;
    }

    // Iterate through known type suffixes to find the longest match first.
    // Iterate over the map to find a match. unordered_map does not guarantee order,
    // so we must be careful with longest match. For the current fixed set,
    // iterating and checking string equality will work fine.
    // If suffixes could overlap (e.g., /long; and /longest;), one would sort
    // the keys by length descending or use a Trie for more efficiency.
    
    // Manual check for /null; first as it's the longest, then other 3-char suffixes.
    if (peek_string(6) == "/null;") {
        for (int i = 0; i < 6; ++i) stream_.advance(); // Consume "/null;"
        return Token(TokenType::TYPE_NULL, "/null;", original_line, original_column);
    } else if (peek_string(3) == "/p;") {
        for (int i = 0; i < 3; ++i) stream_.advance(); // Consume "/p;"
        return Token(TokenType::TYPE_PATH, "/p;", original_line, original_column);
    } else if (peek_string(3) == "/n;") {
        for (int i = 0; i < 3; ++i) stream_.advance(); // Consume "/n;"
        return Token(TokenType::TYPE_NUMERIC, "/n;", original_line, original_column);
    } else if (peek_string(3) == "/a;") {
        for (int i = 0; i < 3; ++i) stream_.advance(); // Consume "/a;"
        return Token(TokenType::TYPE_ALPHANUM, "/a;", original_line, original_column);
    } else if (peek_string(3) == "/b;") {
        for (int i = 0; i < 3; ++i) stream_.advance(); // Consume "/b;"
        return Token(TokenType::TYPE_BOOLEAN, "/b;", original_line, original_column);
    }
    
    // No type suffix matched. The Lexer's getNextToken will then interpret
    // the leading '/' as a standalone TokenType::SLASH.
    return std::nullopt; 
}

} // namespace tokens
} // namespace gravitus