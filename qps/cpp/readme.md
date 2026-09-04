# Directory Rule
When we're discussing directories. instead of building trees as representations, I want us to communicate like this where we show nesting inside of directories with containers, ().
This has nothing to do with parsable data, only to help us have the same language whenever we're talking about directory structure.
example: def"
--
dir.
gravitus_principia/
(core/
(src/
(ast/
(c/ declarations.cpp, expressions.cpp, statements.cpp\),
(h/ declarations.hpp, expressions.hpp, statements.hpp\),
ast_node.hpp, ast_utils.cpp\),
(parser/
(c/
(statements/ assert.cpp, break.cpp, continue.cpp, elif.cpp, else.cpp, for.cpp, if.cpp, let.cpp, loop.cpp, pass.cpp, print.cpp, raise.cpp, return.cpp, set.cpp, try.cpp, while.cpp\),
_index.cpp, causal.cpp, class.cpp, container.cpp, dictionary.cpp, function.cpp, item.cpp, key.cpp, library.cpp, math.cpp, reference.cpp, term.cpp, value.cpp\),
(h/
(statements/ assert.hpp, break.hpp, continue.hpp, elif.hpp, else.hpp, for.hpp, if.hpp, let.hpp, loop.hpp, pass.hpp,print.hpp, raise.hpp, return.hpp, set.hpp, try.hpp, while.hpp\),
_index.hpp, causal.hpp, class.hpp, container.hpp, dictionary.hpp, function.hpp, item.hpp, key.hpp, library.hpp, math.hpp, reference.hpp, term.hpp, value.hpp\)\),
(runtime/
(c/ builtins.cpp, interpreter.cpp, path_resolver.cpp, symbol_table.cpp\),
(h/ builtins.hpp, interpreter.hpp, path_resolver.hpp, symbol_table.hpp\)\),
(tokens/
(c/ char_stream.cpp, handler.cpp, internal.cpp, lexer.cpp, public.cpp, recongnizer.cpp, token.cpp, token_util.cpp\),
(h/ char_stream.hpp, handler.hpp, internal.hpp, lexer.hpp, public.hpp, recongnizer.hpp, token.hpp, token_util.hpp\)\),
(visitors/
(c/ open3d.cpp, print.cpp, type_check.cpp\),
(h/ open3d.hpp, print.hpp, type_check.hpp\),
ast_interface.hpp),
common.hpp, main.cpp, utils.cpp, utils.hpp\)\
)\
CMakeLists.txt;
--
;

# Gravitus Principia Core Engine
This directory contains the core components of the Gravitus Principia engine. It implements the .grav language specification, transforming human-readable engineering system definitions into an executable model for physics simulations and visualization.

# Core Principles
Human-First Conciseness: Prioritizes readability and natural expression without relying on indentation. Structure is explicitly defined through delimiters.
Machine-Optimized Precision: Every symbol has an unambiguous role, making parsing predictable and efficient for automated interpretation.
Semantic Layering: Syntax elements are designed to convey not just data, but also context, association, and causal flow for direct interpretation and visualization.
Hierarchical Flexibility: Data and definitions can be nested to any depth, creating rich associations and detailed explanations for complex systems.

# Architecture Overview
The Gravitus Principia core engine is structured into distinct, modular layers:

# tokens/ (Lexical Analysis)
Role: The lowest layer, responsible for converting raw input text from a .grav file into a stream of tokens.
Components: token.hpp (defines tokens), char_stream.hpp/.cpp (manages file I/O), token_util.hpp/.cpp (token management), lexer_internal.cpp (core lexing logic), and lexer.hpp/.cpp (public lexer interface).

# parser/ (Syntactic Analysis)
Role: Takes the token stream from the lexer and builds an Abstract Syntax Tree (AST). The AST is an in-memory, hierarchical representation of the parsed .grav program, adhering to the language's grammar rules.
Components: Organized into h/ (headers) and cpp/ (implementations) subdirectories for modules like value, item, dictionary, container, key, term, causal_relation, math_expression, reference, function_decl, class_decl, library_parser, and parser_index (main entry).

# ast/ (Abstract Syntax Tree)
Role: Defines the fundamental data structures for the AST and provides utilities for managing them.
Components: ast_node.hpp (defines the generic AstNode structure and node types) and ast_utils.cpp (implements node creation, linking, and recursive freeing).

# runtime/ (Execution Layer)
Role: Interprets and executes the AST. This layer processes the defined system, manages state, resolves references, and prepares data for simulation.
Components: builtins.hpp/.cpp (core operations), interpreter.hpp/.cpp (AST traversal and execution), path_resolver.hpp/.cpp (handles file system and hierarchical references), and symbol_table.hpp/.cpp (manages defined symbols and their scope).

# common.hpp
Role: A central header for widely used, fundamental definitions (e.g., shared enums, simple types) that might not fit directly into AST, Tokens, Parser, or Runtime specific categories.

# utils.hpp/.cpp
Role: Provides general-purpose utilities and helper functions that are not specific to any one core module but are used across the engine.

# Gravitus Principia Core Engine: Abstract Syntax Tree (AST) Module
This directory defines the Abstract Syntax Tree (AST), which serves as the in-memory, hierarchical representation of the parsed .grav source code. It's the central data structure that subsequent compiler phases (like semantic analysis, interpretation, and code generation/visualization) will operate on.

## Core Principles
Hierarchical Representation: The AST accurately mirrors the syntactic structure of the input program, making explicit the relationships between different language constructs.

Memory Management: Utilizes C++11 std::unique_ptr for all child nodes, ensuring robust and automatic memory management within the tree and preventing common memory leaks associated with tree-like structures.

Visitor Pattern Ready: Designed with the Visitor Pattern as its primary interaction mechanism. This means new operations (like type checking or Open3D visualization) can be added by creating new "visitor" classes without modifying the core AST node definitions, promoting high extensibility and maintainability.

## Architecture Overview
The ast/ module is structured for clarity and modularity, balancing granular definition with easy aggregation:

ast_node.hpp:

This is the primary header for the AST module.

It defines the AstNode base class (the polymorphic root for all AST nodes) and the comprehensive AstNodeType enum which classifies every type of node in the tree.

It aggregates all concrete AST node class declarations by including the modular headers from h/. This keeps ast_node.hpp concise while providing a single, convenient include for other modules (like parser/) that need to work with the entire AST.

h/ (Headers for Node Declarations):

Contains sub-headers that logically group the declarations (class definitions) of concrete AST node types.

h/declarations.hpp: Defines nodes for top-level language declarations (e.g., ItemDeclarationNode, TermDeclarationNode, KeyDeclarationNode, DictionaryDeclarationNode, ContainerNode, CausalRelationshipNode, ClassDeclarationNode, FunctionDeclarationNode).

h/expressions.hpp: Defines nodes for literals, identifiers, path references, and mathematical expressions (e.g., StringLiteralNode, NumericLiteralNode, BooleanLiteralNode, NullLiteralNode, PathReferenceNode, IdentifierNode, BinaryExpressionNode).

h/statements.hpp: Defines nodes for all executable statements and control flow structures (e.g., ProgramNode, ExecutionBlockNode, LetStatementNode, SetStatementNode, IfStatementNode, LoopStatementNode, PrintStatementNode, ReturnStatementNode, etc.).

c/ (Implementations of Node Methods):

Contains .cpp files that provide the implementations for the constructors and the accept() methods of the AST nodes declared in h/.

c/declarations.cpp: Implements methods for nodes from h/declarations.hpp.

c/expressions.cpp: Implements methods for nodes from h/expressions.hpp.

c/statements.cpp: Implements methods for nodes from h/statements.hpp.

ast_utils.cpp: This acts as a central aggregation point for the implementations of the factory functions (createXNode(...)) and simply includes the modular c/*.cpp files. This helps manage the number of compilation units and keeps the factory definitions separate from the node implementations.

## Dependencies
The ast/ module primarily depends on:

visitors/ast_interface.hpp: For the AstVisitor interface, which is central to the accept() methods in all AST nodes.

Standard C++ libraries: <vector>, <memory>, <string>, <variant>.

This structured approach ensures that the AST is both powerful and easy to extend or modify as your Gravitus Principia language evolves.

# Gravitus Principia Core Engine: Visitors Module
This directory implements the Visitor Pattern, a powerful design mechanism that allows new operations to be performed on the Abstract Syntax Tree (AST) without modifying the AST nodes themselves. This module is where you'll define and implement all analytical, transformational, and interpretative passes over the parsed .grav source code.

## Core Principles
Separation of Concerns: Operations (like printing, type checking, or Open3D visualization) are strictly separated from the AST's data structure definition.

Open/Closed Principle: The AST nodes are "closed" for modification (you rarely need to change them to add new behavior), but "open" for extension (new behaviors are added by creating new visitor classes).

Extensibility: Adding a new compiler phase or AST-processing task simply requires creating a new concrete visitor class that implements the AstVisitor interface.

Centralized Logic: All logic for a specific operation (e.g., all printing logic, all type-checking rules) is encapsulated within a single visitor class, improving readability and maintainability.

## Architecture Overview
The visitors/ module is structured to organize its core interface and concrete implementations:

ast_interface.hpp:

This is the abstract base class for all visitors, named AstVisitor.

It declares a pure virtual visit() method for every single concrete AST node type (ProgramNode, ItemDeclarationNode, LetStatementNode, BinaryExpressionNode, etc.). Any class wishing to operate on the AST must inherit from AstVisitor and implement all these visit() methods.

h/ (Headers for Concrete Visitors):

Contains headers for specific, concrete visitor implementations. These declare the various specialized visitors that traverse the AST.

h/print.hpp: Declares the PrintVisitor, which will traverse the AST and output its structure to the console.

h/type_check.hpp: Declares the TypeCheckVisitor, responsible for performing semantic analysis and ensuring type correctness.

h/open3d.hpp: Declares the Open3DVisitor, which will translate the AST into Open3D API calls for visualization or simulation.

c/ (Implementations of Concrete Visitors):

Contains the corresponding .cpp files that provide the full implementations of the visit() methods for each concrete visitor declared in h/.

c/print.cpp: Implements the visit() methods for PrintVisitor.

c/type_check.cpp: Implements the visit() methods for TypeCheckVisitor.

c/open3d.cpp: Implements the visit() methods for Open3DVisitor.

## Usage
To use a visitor, you typically:

Create an instance of a concrete visitor (e.g., PrintVisitor my_printer;).

Get the root node of your AST (e.g., std::unique_ptr<ast::ProgramNode> ast_root = parser.parseProgram();).

Initiate the traversal by calling ast_root->accept(my_printer);. The accept() method on the AST nodes will then handle dispatching to the correct visit() method on the visitor, enabling the operation to proceed through the tree.

## Dependencies
The visitors/ module depends primarily on:

The ast/ module: Specifically, the concrete AST node classes (ast_node.hpp indirectly pulls in their declarations) are needed by the visit() methods.

Standard C++ libraries: iostream, string, vector, map.

External libraries: Open3D (for open3d.cpp in particular).