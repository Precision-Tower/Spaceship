// qps/core/src/parser/h/math.hpp

#ifndef QPS_PARSER_MATH_HPP
#define QPS_PARSER_MATH_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For BinaryExpressionNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Math expression parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing mathematical expressions.
// It serves to logically group math-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_MATH_HPP
