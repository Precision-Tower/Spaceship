// qps/core/src/parser/h/key.hpp

#ifndef QPS_PARSER_KEY_HPP
#define QPS_PARSER_KEY_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For KeyDeclarationNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The parseKeyDeclaration function will be a member of the Parser class.
class Parser;

// This header defines the interface for parsing Key. declarations.
// It serves to logically group Key-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_KEY_HPP
