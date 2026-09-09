// qps/core/src/tokens/h/token.hpp

#ifndef QPS_TOKENS_H_TOKEN_HPP
#define QPS_TOKENS_H_TOKEN_HPP

#include <string>
#include <variant> // For std::variant to hold different literal types

namespace qps {
namespace tokens {

enum class TokenType {
    OPEN_PAREN, CLOSE_PAREN, OPEN_BRACKET, CLOSE_BRACKET, OPEN_BRACE, CLOSE_BRACE,
    COLON, SEMICOLON, COMMA, DOT, SLASH, HASH, DOUBLE_HASH, BACKSLASH, EQUALS,
    CALCULATION_MARKER, GEOMETRY_MARKER,
    MODEL_MARKER, CAUSAL_MARKER, LIST_CLOSER, PARAGRAPH_BREAK,
    KW_DEF, KW_ITEM, KW_TERM, KW_KEY, KW_FUNC, KW_CLASS, KW_TEST, KW_LET, KW_IF, KW_ELSE, KW_ELIF,
    KW_TRY, KW_RAISE, KW_RAISES, KW_LOOP, KW_WHILE, KW_FOR, KW_RETURN, KW_PRINT, KW_ASSERT, KW_FAIL, KW_SET,
    KW_BREAK, KW_CONTINUE, KW_PASS, EXECUTION_ACTION, PIPE,
    TYPE_PATH, TYPE_NUMERIC, TYPE_ALPHANUM, TYPE_BOOLEAN, TYPE_NULL,
    IDENTIFIER, NUMERIC_LITERAL, STRING_LITERAL, DEFINITION_TEXT, BOOLEAN_LITERAL, NULL_LITERAL,
    OP_ADD, OP_SUBTRACT, OP_MULTIPLY, OP_EQUAL, OP_LESS, OP_AND, OP_OR, OP_NOT,
    REFERENCE_OPERATOR,
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
} // namespace qps

#endif // QPS_TOKENS_H_TOKEN_HPP
