Phase 0: Project Setup & Core Foundation

## Project Setup & Base Directory:
Create the gravitus_principia/ root directory.
Create the core/, core/src/, core/src/ast/, core/src/parser/, core/src/parser/c/, core/src/parser/h/, core/src/runtime/, core/src/runtime/c/, core/src/runtime/h/, core/src/tokens/, core/src/tokens/c/, core/src/tokens/h/ directories.
Self-Correction: I'll ensure .cpp files are generated, even though the list used c/ in paths.

# core/src/common.hpp:
Define core common utilities (e.g., global error reporting mechanisms, possibly forward declarations for core classes if needed).
Checklist Item 0.1: core/src/common.hpp
Purpose: To serve as a central header for fundamental, engine-wide definitions that are broadly shared across multiple modules. This includes basic C++ library includes, core namespaces, and forward declarations that prevent circular dependencies.
Key C++ Design Considerations:
Header Guards: Essential to prevent multiple inclusions.
Minimalism: Keep this file as light as possible to reduce compilation times. Only include what is strictly necessary for basic types or forward declarations that many other headers rely on.
Namespace: All Gravitus Principia code will reside within the Gravitus namespace for organization and to prevent name collisions.
Dependencies: None (it's the root of the dependency tree for core types).
Expected Content:
C++
// gravitus_principia/core/src/common.hpp
#ifndef GRAVITUS_COMMON_HPP
#define GRAVITUS_COMMON_HPP
// --- Standard Library Includes for Fundamental Types ---
// These are broadly used and defining them here avoids repetitive includes.
#include <string>     // For std::string
#include <vector>     // For std::vector
#include <memory>     // For std::unique_ptr, std::shared_ptr (for ownership semantics)
#include <variant>    // For std::variant (C++17: for type-safe unions like AstLiteralValue)
#include <optional>   // For std::optional (C++17: for nullable values, e.g., optional<long long> index_id)
#include <iostream>   // For basic diagnostic output (e.g., error messages to std::cerr)
#include <stdexcept>  // For standard exceptions (e.g., std::runtime_error)
#include <utility>    // For std::move and std::forward (used with smart pointers)
// --- Core Gravitus Namespace ---
// All Gravitus Principia code will be nested within this namespace.
namespace Gravitus {

    // --- Forward Declarations ---
    // Declare core classes here to allow cross-module references without full includes,
    // preventing circular dependencies and speeding up compilation.
    class AstNode;
    class Token;
    class Lexer;
    // Add more as needed (e.g., Parser, Interpreter)
}
#endif // GRAVITUS_COMMON_HPP
Notes: This file sets up the foundation for using modern C++ features across our entire codebase. It also establishes our main namespace.

# core/src/ast/ast_node.hpp:
Define the AstNodeType enum (expanded to include all new node types like CAUSAL_RELATION, MATH_EXPRESSION, REFERENCE, FUNCTION_DECL, CLASS_DECL, TERM, KEY).
Define the AstLiteralValue union.
Define the AstNode class (using C++ features like constructors, potentially virtual functions if we make it polymorphic, smart pointers like std::unique_ptr for children/siblings). This will be our core AST structure.
Checklist Item 0.2: core/src/ast/ast_node.hpp
Purpose: To define the core AstNode class, which serves as the universal building block for the Abstract Syntax Tree (AST). Every element of a parsed Gravitus Principia program (like a literal value, an item, a dictionary, a function declaration) will be represented as an instance of, or derived from, this AstNode class.
Key C++ Design Considerations:
AstNodeType Enum Class: Use enum class for strong typing, preventing implicit conversions to int. This clearly categorizes different types of AST nodes.
AstLiteralValue (std::variant): This is a critical C++17 feature for type safety. It allows a single AstNode instance (when it's a ValueLiteral) to hold one of several distinct value types (integer, float, string, boolean, null) without manual type tracking or union-related pitfalls. std::monostate represents the null state explicitly.
AstNode Class Structure:
Member Variables: Will store the node's type, identifier, optional index, source location, and the actual value if it's a literal.
Tree Pointers (std::unique_ptr): Crucially, std::unique_ptr<AstNode> will be used for first_child and next_sibling to establish ownership and enable automatic, recursive memory management of the AST. This is a huge win for preventing memory leaks.
Raw parent Pointer: The parent pointer will be a raw AstNode* because the parent does not own its children's memory via this backward link; children own themselves via unique_ptr.
Constructors/Destructors: Provide appropriate constructors for easy initialization. The destructor will be simple, as std::unique_ptr handles child/sibling destruction.
Move Semantics: Implement move constructor and move assignment operator (AstNode(AstNode&&) noexcept;, AstNode& operator=(AstNode&&) noexcept;). This ensures efficient transfer of unique_ptr ownership when AST nodes are passed around (e.g., from parser functions).
Delete Copy Semantics: Explicitly delete the copy constructor and copy assignment operator to prevent accidental deep copies, which are generally undesirable and error-prone for ASTs managed by unique_ptr.
Dependencies: common.hpp (for std::string, std::vector, std::unique_ptr, std::variant, std::optional).
Expected Content:
C++
// gravitus_principia/core/src/ast/ast_node.hpp
#ifndef GRAVITUS_AST_NODE_HPP
#define GRAVITUS_AST_NODE_HPP
#include "../common.hpp" // Includes all necessary fundamental types like std::string, std::variant, std::unique_ptr, std::optional
namespace Gravitus {
    // --- AstNodeType Enum Class ---
    // Strongly-typed enumeration for all possible AST node types.
    enum class AstNodeType {
        Unknown = 0,            // Default/error state
        // Literals & Primitives
        ValueLiteral,           // e.g., 10 /n;, "hello" /a;, true /b;, null /null;
        Identifier,             // e.g., myVariable, ME, AC (these are now generic identifiers)
        // Core Structural Nodes
        Item,                   // 'item: value;'
        Dictionary,             // '[]'
        Container,              // '()'
        Key,                    // 'key.'
        Term,                   // 'term:'
        Library,                // '{}' (top-level file/module)
        // Special Reference & Relationship Nodes
        Reference,              // 'folder/file.key', 'file.key.[>.1]', 'Ec_comp.em:AC:sm:'
        CausalRelation,         // 'A = B' (for transformations)
        MathExpression,         // '[#ID: math expression]' (e.g., 'value1 * value2')
        // Declarations & Definitions
        FunctionDeclaration,    // 'func-'
        ClassDeclaration,       // 'class-'
        DefinitionString,       // 'def"..."' (represents the parsed content of def"")
        // Control Flow & Statements (from rules.md)
        IfStatement,
        ElseIfStatement,
        ElseStatement,
        ReturnStatement,
        PrintStatement,
        TryBlock,               // The 'try-' part of try-raise
        RaiseStatement,
        AssertStatement,
        WhileLoop,
        ForLoop,
        LoopStatement,          // 'loop-'
        LetStatement,           // 'let-'
        SetStatement,           // 'set-'
        BreakStatement,
        ContinueStatement,
        PassStatement
    };
    // --- AstLiteralValue (std::variant) ---
    // Type-safe union for value literal data. std::monostate indicates a null value.
    using AstLiteralValue = std::variant<long long, double, bool, std::string, std::monostate>; // std::monostate for 'null'
    // --- AstNode Class ---
    class AstNode {
    public:
        // --- Node Properties ---
        AstNodeType type;                   // What kind of AST node this is
        std::string identifier;             // For named nodes (Key, Item, Term, Function, Class, Identifiers)
        std::optional<long long> index_id;  // For nodes with a numeric index (e.g., Dictionary [1:])
        int line;                           // Line number from source for error reporting
        int column;                         // Column number from source for error reporting
        // --- Value Literal Data (if type is ValueLiteral) ---
        AstLiteralValue value;              // Holds the actual value if type == AstNodeType::ValueLiteral
        // --- Tree Pointers for Hierarchy ---
        AstNode* parent;                                     // Pointer to the parent node (non-owning)
        std::vector<std::unique_ptr<AstNode>> children;      // Owning pointers to children nodes. Using vector simplifies add/removal compared to linked list (first_child/next_sibling).
        // --- Constructors ---
        // Main constructor for any AST node
        AstNode(AstNodeType type, int line, int column);
        // Special constructor for nodes that are identifiers
        AstNode(AstNodeType type, const std::string& identifier, int line, int column);
        // Special constructor for value literals
        AstNode(AstNodeType type, const AstLiteralValue& value, int line, int column);
        // --- Destructor ---
        // std::unique_ptr handles automatic destruction of children. std::string handles its own memory.
        ~AstNode() = default; // Default destructor is fine because unique_ptr manages memory
        // --- Move Semantics ---
        // Allow moving AstNode objects, essential for unique_ptr ownership transfer
        AstNode(AstNode&& other) noexcept;
        AstNode& operator=(AstNode&& other) noexcept;
        // --- Delete Copy Semantics ---
        // Prevent accidental copying (deep copies are complex with unique_ptr ownership)
        AstNode(const AstNode&) = delete;
        AstNode& operator=(const AstNode&) = delete;
        // --- Utility Methods (implemented in ast_utils.cpp) ---
        // For example:
        // void AddChild(std::unique_ptr<AstNode> child); // Add child directly as a method
    };
} // namespace Gravitus
#endif // GRAVITUS_AST_NODE_HPP
Notes:
AstNodeType expanded: Includes all keywords from rules.md.
std::vector<std::unique_ptr<AstNode>> children;: This is a major change from first_child/next_sibling and is the standard, much cleaner way to manage children in modern C++. It simplifies adding children and traversal. parent remains a raw pointer.
Constructors Overloaded: For common initialization patterns (generic, identifier-based, value-based).
Move Semantics (noexcept): Explicitly defined for efficiency with std::unique_ptr.
Deleted Copy Semantics: Prevents errors related to copying unique_ptrs.

# core/src/ast/ast_utils.cpp:
Implement static helper functions or methods for an AstUtils class to create, manage, and recursively free AstNode objects. This will leverage C++ features (e.g., std::unique_ptr for ownership).
Checklist Item 0.3: core/src/ast/ast_utils.cpp
Purpose: To implement the methods of the AstNode class and potentially provide static helper functions related to AST management (e.g., factory methods for node creation if constructors are private, or printing utilities).
Key C++ Design Considerations:
AstNode Constructor/Destructor: Implement the constructors and the move constructor/assignment operator. The destructor remains defaulted.
Node Creation: We'll implement AstNode's constructors. The AstUtils::createNode static method concept can be removed if AstNode's constructors are public and return std::unique_ptr using std::make_unique<AstNode>(...). This is the more idiomatic C++ way.
Adding Children: Implement AstNode::AddChild() method.
Dependencies: ast_node.hpp, <stdexcept> (for exceptions).
Expected Content:
C++
// gravitus_principia/core/src/ast/ast_utils.cpp (Renamed from ast_utils.cpp if it's only implementing AstNode methods)
// Alternatively, this file could be named ast_node.cpp if it contains the implementation for ast_node.hpp
#include "ast_node.hpp" // Includes AstNode class definition
namespace Gravitus {
    // --- AstNode Constructors ---
    AstNode::AstNode(AstNodeType type, int line, int column)
        : type(type), line(line), column(column), parent(nullptr), index_id(std::nullopt) {
        // identifier, value, children are default-constructed (empty string, monostate, empty vector)
    }
    AstNode::AstNode(AstNodeType type, const std::string& identifier, int line, int column)
        : type(type), identifier(identifier), line(line), column(column), parent(nullptr), index_id(std::nullopt) {
        // value, children are default-constructed
    }
    AstNode::AstNode(AstNodeType type, const AstLiteralValue& value, int line, int column)
        : type(type), value(value), line(line), column(column), parent(nullptr), index_id(std::nullopt) {
        // identifier, children are default-constructed
    }
    // --- Move Constructor ---
    AstNode::AstNode(AstNode&& other) noexcept
        : type(other.type),
          identifier(std::move(other.identifier)),
          index_id(std::move(other.index_id)),
          line(other.line),
          column(other.column),
          value(std::move(other.value)),
          parent(other.parent), // Non-owning pointer simply copied
          children(std::move(other.children)) {
        // Ensure other's parent is null to avoid dangling pointers if it was a child somewhere
        // This is handled by the AddChild method if we only ever pass unique_ptr
        other.parent = nullptr;
    }
    // --- Move Assignment Operator ---
    AstNode& AstNode::operator=(AstNode&& other) noexcept {
        if (this != &other) { // Self-assignment check
            type = other.type;
            identifier = std::move(other.identifier);
            index_id = std::move(other.index_id);
            line = other.line;
            column = other.column;
            value = std::move(other.value);
            parent = other.parent; // Non-owning pointer simply copied
            children = std::move(other.children); // Transfer ownership of children

            // Ensure other's parent is null after move
            other.parent = nullptr;
        }
        return *this;
    }
    // --- Node Management Method (AddChild) ---
    void AstNode::AddChild(std::unique_ptr<AstNode> child) {
        if (!child) {
            // Not necessarily an error, but we won't add a null child
            return;
        }
        child->parent = this; // Set the child's parent pointer to current node
        children.push_back(std::move(child)); // Add to vector, transferring ownership
    }
} // namespace Gravitus
Notes: This file will actually be named ast_node.cpp to align with ast_node.hpp. It implements the AstNode class's methods. The AstUtils:: static factory methods are removed in favor of std::make_unique<AstNode>(...) directly. AddChild is now a method of AstNode.

# core/src/utils.hpp / core/src/utils.cpp:
Define and implement general-purpose utilities that are not specific to AST, tokens, parser, or runtime (e.g., shared constants, utility functions for string manipulation if std::string isn't enough).
Checklist Item 0.4: core/src/utils.hpp / core/src/utils.cpp
Purpose: To define and implement general-purpose utilities that are not specific to AST, Tokens, Parser, or Runtime, but are used across the engine (e.g., global error logging, assertion helpers).
Key C++ Design Considerations:
Use a dedicated namespace Gravitus::Utils.
Functions should be static or part of a Utils class if they don't operate on member data.
Error logging functions should use std::cerr for standard error output.
Dependencies: common.hpp (for std::string).
Expected Content: (Remains the same as outlined in the previous response for this item).

## Phase 1: Lexical Analysis (Tokens)
core/src/tokens/h/token.hpp:
Define the TokenType enum (updated based on our rules.md and new keywords, ensuring TOKEN_EQUALS, TOKEN_ASTERISK, TOKEN_SLASH, TOKEN_DOT, TOKEN_COLON are correct, and all control flow keywords like print-, for-, let-, etc., are TOKEN_KEYWORD types).
Define the Token class (using std::string for lexeme, constructors).

# core/src/tokens/c/token.cpp: (Implementation for token.hpp's methods/utilities).
Implement Token class constructors.
Implement token_type_to_string helper.

# core/src/tokens/h/char_stream.hpp:
Define the CharStream class (managing file input, current char, line/column tracking).
Provide methods like init, consume, peek, get_line, get_column, close.

# core/src/tokens/c/char_stream.cpp:
Implement the CharStream class methods.

# core/src/tokens/h/lexer.hpp: (This will serve as the public interface for the Lexer)
Define the Lexer class.
Provide public methods: Lexer(const std::string& filename), Token getNextToken(), const Token& peekNextToken(), ~Lexer() (for cleanup).
Declare private helper methods for internal lexing (e.g., lexIdentifierOrKeyword, lexNumber, lexStringLiteral).
Include a std::unique_ptr<Token> peeked_token_ member for lookahead.

# core/src/tokens/c/lexer.cpp:
Implement the Lexer class methods defined in lexer.hpp, including its internal lexing logic (the lex_next_raw_token equivalent).
Implement skipWhitespace.

## Phase 2: Syntactic Analysis (Parser - Core Building Blocks)

# core/src/parser/h/value.hpp:
Define ValueParser class (or static methods).
Provide std::unique_ptr<AstNode> parse(Lexer& lexer); method.

# core/src/parser/c/value.cpp:
Implement ValueParser logic. This will use Lexer's get and peek methods, and ast_utils for creating AstNodes.

# core/src/parser/h/item.hpp:
Define ItemParser class.
Provide std::unique_ptr<AstNode> parse(Lexer& lexer); method.

# core/src/parser/c/item.cpp:
Implement ItemParser logic (handles item: value; and lists of identifiers like mv, rpm;).

# core/src/parser/h/dictionary.hpp:
Define DictionaryParser class.
Provide std::unique_ptr<AstNode> parse(Lexer& lexer); method.

# core/src/parser/c/dictionary.cpp:
Implement DictionaryParser logic ([], #ID: math, [<>,:] references).

# core/src/parser/h/container.hpp:
Define ContainerParser class.
Provide std::unique_ptr<AstNode> parse(Lexer& lexer); method.

# core/src/parser/c/container.cpp:
Implement ContainerParser logic (()).

## Phase 3: Higher-Order Structures & Causal Syntax

# core/src/parser/h/key.hpp & key.cpp
Parse key. definitions
Handle inline containers, dictionaries, and assignments inside keys

# core/src/parser/h/term.hpp & term.cpp
Parse term: inside key.
Recognize definitions (def" ...;), lists, and nested terms

# core/src/parser/h/reference.hpp & reference.cpp
Handle [>.1], [<.1], [1:] reference patterns
Ensure support for implicit library resolution

# core/src/parser/h/class.hpp & class.cpp
Parse class- key. and capture nested func- definitions
Prepare nodes for runtime execution

# core/src/parser/h/function.hpp & function.cpp
Parse func- greet[> name].(...)
Handle control flow inside functions (if-, return-, print-, etc.)

# core/src/parser/h/causal.hpp & causal.cpp
Parse and validate EntityA = EntityB style syntax
Create CAUSAL_RELATION nodes in AST

## Phase 4: Runtime Execution Engine

# core/src/runtime/h/interpreter.hpp & interpreter.cpp
Core interpreter for .grav execution
Traverse AST and evaluate expressions
Support control flow (if-, return-, etc.)

# core/src/runtime/h/symbol_table.hpp & symbol_table.cpp
Track variables, scopes, and references
Handle declarations like let-, set-, and closures

# core/src/runtime/h/path_resolver.hpp & path_resolver.cpp
Handle file-based references like folder/file.key.[>.1]
Enable recursive and modular loading

# core/src/runtime/h/builtins.hpp & builtins.cpp
Define default Gravitus functions (print-, assert-, etc.)
Register with the interpreter runtime

## Phase 5: .grav Loader & Entry Point

# core/src/main.cpp
Load a .grav file
Initialize Lexer → Parser → Interpreter
Provide CLI options for executing, debugging, and tracing

# core/src/utils.hpp & utils.cpp
Utility functions (string parsing, file loading, debug logging)

## Phase 6: AI Embedding & Execution Hooks
Add core/src/ai/ (later phase)
coder.hpp/cpp: Embed AI logic for self-modifying .grav behavior
Link to quantized weights using GGML, ONNX, or preloaded flatbuffer blobs

## Optional: Phase 7+ Ideas
Feature	Description
.grav Linter/Validator	Static analyzer for dev tools
Gravitus Playground	Interactive REPL/GUI
.gravmod packages	Zip+manifest modules
Embedded .wav, .jpg, .json support	Allow Gravitus to process binary/structured files
Cross-target compiler (Web, Android)	Use Emscripten or JNI to deploy Gravitus