// qps/core/src/tokens/c/lexer.cpp

#include "../h/lexer.hpp"
#include <unordered_map>
#include <cctype> // For isspace etc.
#include <stdexcept> // For std::runtime_error
#include <string> // For std::string, std::to_string

namespace qps {
namespace tokens {

// Lexer constructor: Initializes the CharStream reference and creates the TokenRecognizer.
Lexer::Lexer(CharStream& stream)
    : stream_(stream), 
      current_line_(1), 
      current_column_(1),
      // Initialize the recognizer, passing it the stream and references to Lexer's line/column.
      // The recognizer needs to know the *start* position for each token.
      recognizer_(std::make_unique<TokenRecognizer>(stream, current_line_, current_column_))
{
    definition_text_pending_ = false;
}

// Skips non-semantic whitespace.
//
// QPS whitespace contract:
// - spaces/tabs are non-semantic
// - one newline continues the current logical bundle
// - a second newline before the next non-whitespace character creates
//   a paragraph boundary
//
// The paragraph boundary is returned to the parser as PARAGRAPH_BREAK.
bool Lexer::skipWhitespace() {
    int newline_count = 0;

    while (!stream_.isAtEnd()) {
        char c = stream_.peek();

        // Horizontal whitespace is always non-semantic.
        if (c == ' ' || c == '\t' || c == '\r') {
            stream_.advance();
            continue;
        }

        if (c == '\n') {
            stream_.advance();
            ++newline_count;

            if (newline_count >= 2) {
                return true;
            }

            continue;
        }

        break;
    }

    return false;
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
    if (definition_text_pending_) {
        definition_text_pending_ = false;
        current_line_ = stream_.getCurrentLine();
        current_column_ = stream_.getCurrentColumn();
        return recognizer_->recognizeDefinitionText();
    }

    // Update the line/column references in the recognizer to the current stream position
    // before attempting to recognize a token. This ensures accurate token positioning.
    current_line_ = stream_.getCurrentLine();
    current_column_ = stream_.getCurrentColumn();

    // Preserve paragraph boundaries instead of discarding every newline.
    if (skipWhitespace()) {
        return Token(TokenType::PARAGRAPH_BREAK, "\\n\\n",
                     current_line_, current_column_);
    }

    // Refresh position after skipped non-semantic whitespace.
    current_line_ = stream_.getCurrentLine();
    current_column_ = stream_.getCurrentColumn();

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

    // Legacy dictionary input/output references.
    //
    // Numeric dictionary-output syntax retains the compact `>.` token:
    //
    //   [>.1]
    //
    // But `>.identifier` now belongs to structural QPS navigation:
    //
    //   [>.U.p]
    //
    // In that form the lexer must emit:
    //
    //   REFERENCE_OPERATOR, DOT, IDENTIFIER, DOT, IDENTIFIER
    //
    // rather than swallowing `>.` into DICT_OUTPUT_REF.
    if (current_char == '<' && next_char == '.') {
        stream_.advance(); // Consume '<'
        stream_.advance(); // Consume '.'
        return Token(
            TokenType::DICT_INPUT_REF,
            "<.",
            current_line_,
            current_column_);
    }
    else if (
        current_char == '>' &&
        next_char == '.' &&
        std::isdigit(
            static_cast<unsigned char>(
                stream_.peek_ahead(2)))) {

        stream_.advance(); // Consume '>'
        stream_.advance(); // Consume '.'

        return Token(
            TokenType::DICT_OUTPUT_REF,
            ">.",
            current_line_,
            current_column_);
    }

    // QPS leading-hyphen executable keywords.
    // Hyphen is not a generic identifier character.
    if (current_char == '-' &&
        std::isalpha(static_cast<unsigned char>(next_char))) {

        std::string candidate;
        int offset = 0;

        while (true) {
            char c = stream_.peek_ahead(offset);
            if (c == '\0') {
                break;
            }

            if (offset == 0 && c == '-') {
                candidate += c;
                ++offset;
                continue;
            }

            if (std::isalnum(static_cast<unsigned char>(c)) || c == '_') {
                candidate += c;
                ++offset;
                continue;
            }

            break;
        }

        static const std::unordered_map<std::string, TokenType> executable_keywords = {
            {"-func", TokenType::KW_FUNC},
            {"-class", TokenType::KW_CLASS},
            {"-test", TokenType::KW_TEST},
            {"-let", TokenType::KW_LET},
            {"-if", TokenType::KW_IF},
            {"-else", TokenType::KW_ELSE},
            {"-elif", TokenType::KW_ELIF},
            {"-try", TokenType::KW_TRY},
            {"-raise", TokenType::KW_RAISE},
            {"-raises", TokenType::KW_RAISES},
            {"-loop", TokenType::KW_LOOP},
            {"-while", TokenType::KW_WHILE},
            {"-for", TokenType::KW_FOR},
            {"-return", TokenType::KW_RETURN},
            {"-print", TokenType::KW_PRINT},
            {"-assert", TokenType::KW_ASSERT},
            {"-fail", TokenType::KW_FAIL},
            {"-set", TokenType::KW_SET},
            {"-break", TokenType::KW_BREAK},
            {"-continue", TokenType::KW_CONTINUE},
            {"-pass", TokenType::KW_PASS},
        };

        auto it = executable_keywords.find(candidate);
        if (it != executable_keywords.end()) {
            for (std::size_t i = 0; i < candidate.size(); ++i) {
                stream_.advance();
            }

            return Token(it->second, candidate,
                         current_line_, current_column_);
        }

        for (std::size_t i = 0; i < candidate.size(); ++i) {
            stream_.advance();
        }

        return Token(TokenType::EXECUTION_ACTION, candidate,
                     current_line_, current_column_);
    }

    if (current_char == '=' && next_char == '=') {
        stream_.advance();
        stream_.advance();
        return Token(TokenType::OP_EQUAL, "==", current_line_, current_column_);
    }

    // --- Literal and Keyword Checks ---
    // Numeric literals. '-' remains structural QPS syntax so compact
    // Item forms such as radius-3/n; tokenize the same as radius- 3/n;.
    if (std::isdigit(static_cast<unsigned char>(current_char)) ||
        (current_char == '+' && std::isdigit(static_cast<unsigned char>(next_char))) ||
        (current_char == '.' && std::isdigit(static_cast<unsigned char>(next_char)))) {
        return recognizer_->recognizeNumericLiteral();
    }
    // String literals
    if (current_char == '"') {
        stream_.advance(); // Consume the opening quote before calling recognizer
        return recognizer_->recognizeStringLiteral();
    }
    // Identifiers or Keywords (including boolean/null literals like "true", "false", "null")
    if (std::isalpha(static_cast<unsigned char>(current_char)) || current_char == '_') {
        Token token = recognizer_->recognizeIdentifierOrKeyword();

        if (token.type == TokenType::KW_DEF) {
            definition_text_pending_ = true;
        }

        return token;
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
        case '>': stream_.advance(); return Token(TokenType::REFERENCE_OPERATOR, ">", current_line_, current_column_);
        case '<': stream_.advance(); return Token(TokenType::OP_LESS, "<", current_line_, current_column_);
        case '|': stream_.advance(); return Token(TokenType::PIPE, "|", current_line_, current_column_);
        case '%': stream_.advance(); return Token(TokenType::CALCULATION_MARKER, "%", current_line_, current_column_);
        case '@': stream_.advance(); return Token(TokenType::GEOMETRY_MARKER, "@", current_line_, current_column_);
        case '$': stream_.advance(); return Token(TokenType::MODEL_MARKER, "$", current_line_, current_column_);
        case '!': stream_.advance(); return Token(TokenType::CAUSAL_MARKER, "!", current_line_, current_column_);
        case '\\': stream_.advance(); return Token(TokenType::BACKSLASH, "\\", current_line_, current_column_);
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
} // namespace qps