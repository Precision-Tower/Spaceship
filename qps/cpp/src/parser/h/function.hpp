// qps/core/src/parser/h/function.hpp

#ifndef QPS_PARSER_FUNCTION_HPP
#define QPS_PARSER_FUNCTION_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For FunctionDeclarationNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Function parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing Function (-func) declarations.
// It serves to logically group Function-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_FUNCTION_HPP
