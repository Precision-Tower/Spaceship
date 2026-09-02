// qps/core/src/tokens/c/token.cpp

#include "../h/token.hpp"

#include <sstream>
#include <utility>

namespace qps {
namespace tokens {

Token::Token(
    TokenType type_param,
    std::string lexeme_param,
    int line_param,
    int column_param,
    std::variant<std::monostate, double, std::string, bool> literal_param
)
    : type(type_param),
      lexeme(std::move(lexeme_param)),
      line(line_param),
      column(column_param),
      literal(std::move(literal_param))
{}

Token::Token()
    : type(TokenType::UNKNOWN),
      lexeme(""),
      line(0),
      column(0),
      literal(std::monostate())
{}

std::string Token::toString() const {
    std::ostringstream out;

    out << "Token(" << static_cast<int>(type)
        << ", \"" << lexeme << "\""
        << ", L" << line
        << ", C" << column
        << ")";

    return out.str();
}

} // namespace tokens
} // namespace qps
