// qps/core/src/parser/h/reference.hpp

#ifndef QPS_PARSER_REFERENCE_HPP
#define QPS_PARSER_REFERENCE_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For PathReferenceNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Reference parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing various types of references,
// primarily path-based references (e.g., folder/file.key.item-).

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_REFERENCE_HPP
