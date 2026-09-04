// qps/core/src/parser/h/item.hpp

#ifndef QPS_PARSER_ITEM_HPP
#define QPS_PARSER_ITEM_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For ItemDeclarationNode and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The parseItemDeclaration function will be a member of the Parser class.
class Parser;

// This header will define the interface for parsing Item- declarations.
// While parseItemDeclaration is a method of the Parser class,
// defining its signature here (if it were a standalone function) or simply
// documenting its purpose within the module's header helps clarify responsibilities.

// For now, as parseItemDeclaration is a member of Parser, this file will
// mainly serve to logically group Item-related parsing concerns.
// In a very large project, you might have helper functions here,
// but for our current structure, it's primarily a marker.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_ITEM_HPP
