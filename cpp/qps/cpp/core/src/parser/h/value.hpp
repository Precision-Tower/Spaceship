// qps/core/src/parser/h/value.hpp

#ifndef QPS_PARSER_VALUE_HPP
#define QPS_PARSER_VALUE_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For literal AST nodes (StringLiteralNode, NumericLiteralNode, etc.)
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Value parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing literal values.
// It serves to logically group literal value parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_VALUE_HPP
