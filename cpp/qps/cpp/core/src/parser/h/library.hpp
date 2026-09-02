// qps/core/src/parser/h/library.hpp

#ifndef QPS_PARSER_LIBRARY_HPP
#define QPS_PARSER_LIBRARY_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For AST nodes related to modules/libraries
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// Library-related parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing Library/Module-specific declarations.
// This might include handling of implicit modules or explicit module manifest files (<index.qps).

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_LIBRARY_HPP
