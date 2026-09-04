// qps/core/src/tokens/h/lexer.hpp

#ifndef QPS_TOKENS_H_LEXER_HPP
#define QPS_TOKENS_H_LEXER_HPP

#include <memory>     // Required for std::unique_ptr
#include <functional> // NEW: Required for std::function for consume_while
#include "token.hpp"
#include "char_stream.hpp"
#include "recognizer.hpp" // Now Lexer depends on TokenRecognizer

namespace qps {
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
    bool definition_text_pending_ = false;

    // Helper functions for Lexer's own logic (e.g., whitespace/comment skipping)
    // FIX: Changed signature from bool (*predicate)(char) to std::function<bool(char)>
    std::string consume_while(std::function<bool(char)> predicate);
    // Skips non-semantic whitespace.
    // Returns true when a blank-line paragraph boundary is encountered.
    bool skipWhitespace();
    void handleSingleLineComment();
    bool handleMultiLineComment(); // Returns true if a multi-line comment was closed.
};

} // namespace tokens
} // namespace qps

#endif // QPS_TOKENS_H_LEXER_HPP
