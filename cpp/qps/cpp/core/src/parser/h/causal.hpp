// qps/core/src/parser/h/causal.hpp

#ifndef QPS_PARSER_CAUSAL_HPP
#define QPS_PARSER_CAUSAL_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For CausalRelationshipNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Causal relationship parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing Causal Relationship (=) declarations.
// It serves to logically group Causal-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_CAUSAL_HPP
