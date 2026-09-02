// qps/core/src/parser/h/dictionary.hpp

#ifndef QPS_PARSER_DICTIONARY_HPP
#define QPS_PARSER_DICTIONARY_HPP

#include <memory>    // For std::unique_ptr
#include "../../ast/ast_node.hpp" // For DictionaryDeclarationNode, DictionaryEntryNode, and other AST nodes
#include "../../tokens/h/token.hpp" // For token types

namespace qps {
namespace parser {

// Forward declaration of the main Parser class to avoid circular includes.
// The dictionary parsing functions will be members of the Parser class.
class Parser;

// This header defines the interface for parsing Dictionary ([]) declarations.
// It serves to logically group Dictionary-related parsing concerns.

} // namespace parser
} // namespace qps

#endif // QPS_PARSER_DICTIONARY_HPP
