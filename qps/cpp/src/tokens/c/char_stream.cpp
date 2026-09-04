// qps/core/src/tokens/c/char_stream.cpp

#include "../h/char_stream.hpp" // Corrected: points to its header in tokens/h/
#include <algorithm>
#include <stdexcept>

namespace qps {
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
} // namespace qps
