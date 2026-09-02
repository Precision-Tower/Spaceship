// qps/core/src/parser/h/container.hpp

#ifndef QPS_PARSER_CONTAINER_HPP
#define QPS_PARSER_CONTAINER_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For ContainerNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The parseContainer function will be a member of the Parser class.
class Parser;

// This header defines the interface for parsing Container (()) blocks.
// It serves to logically group Container-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_CONTAINER_HPP
