// qps/core/src/parser/h/statements/while.hpp

#ifndef QPS_PARSER_STATEMENTS_WHILE_HPP
#define QPS_PARSER_STATEMENTS_WHILE_HPP

#include <memory>    // For std::unique_ptr
#include "../../../ast/ast_node.hpp" // For WhileStatementNode and other AST nodes
#include "../../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The parseWhileStatement function will be a member of the Parser class.
class Parser;

// This header defines the interface for parsing '-while' statements.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_STATEMENTS_WHILE_HPP
