// qps/core/src/parser/h/class.hpp

#ifndef QPS_PARSER_CLASS_HPP
#define QPS_PARSER_CLASS_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For ClassDeclarationNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Class parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing Class (-class) declarations.
// It serves to logically group Class-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_CLASS_HPP
