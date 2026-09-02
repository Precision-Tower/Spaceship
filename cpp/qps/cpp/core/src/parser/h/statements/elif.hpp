// qps/core/src/parser/h/statements/elif.hpp

#ifndef QPS_PARSER_STATEMENTS_ELIF_HPP
#define QPS_PARSER_STATEMENTS_ELIF_HPP

#include <memory>    // For std::unique_ptr
#include "../../../ast/ast_node.hpp" // For ElifStatementNode and other AST nodes
#include "../../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The parseElifStatement function will be a member of the Parser class.
class Parser;

// This header defines the interface for parsing '-elif' statements.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_STATEMENTS_ELIF_HPP
