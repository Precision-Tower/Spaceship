// qps/core/src/tokens/h/char_stream.hpp

#ifndef QPS_TOKENS_H_CHAR_STREAM_HPP
#define QPS_TOKENS_H_CHAR_STREAM_HPP

#include <string>
#include <vector>

namespace qps {
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
} // namespace qps

#endif // QPS_TOKENS_H_CHAR_STREAM_HPP
