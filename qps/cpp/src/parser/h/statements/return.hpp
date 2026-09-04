// qps/core/src/parser/h/statements/return.hpp

#ifndef QPS_PARSER_STATEMENTS_RETURN_HPP
#define QPS_PARSER_STATEMENTS_RETURN_HPP

#include <memory>    // For std::unique_ptr
#include "../../../ast/ast_node.hpp" // For ReturnStatementNode and other AST nodes
#include "../../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The parseReturnStatement function will be a member of the Parser class.
class Parser;

// This header defines the interface for parsing '-return-' statements.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_STATEMENTS_RETURN_HPP
