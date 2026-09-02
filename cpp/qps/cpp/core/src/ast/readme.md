# Gravitus Principia Core Engine: Abstract Syntax Tree (AST) Module
This directory defines the Abstract Syntax Tree (AST), which serves as the in-memory, hierarchical representation of the parsed .grav source code. It's the central data structure that subsequent compiler phases (like semantic analysis, interpretation, and code generation/visualization) will operate on.

## Core Principles
- Hierarchical Representation: The AST accurately mirrors the syntactic structure of the input program, making explicit the relationships between different language constructs.
- Memory Management: Utilizes C++11 std::unique_ptr for all child nodes, ensuring robust and automatic memory management within the tree and preventing common memory leaks associated with tree-like structures.
- Visitor Pattern Ready: Designed with the Visitor Pattern as its primary interaction mechanism. This means new operations (like type checking or Open3D visualization) can be added by creating new "visitor" classes without modifying the core AST node definitions, promoting high extensibility and maintainability.

## Architecture Overview
The ast/ module is structured for clarity and modularity, balancing granular definition with easy aggregation:

- ast_node.hpp:
This is the primary header for the AST module.
It defines the AstNode base class (the polymorphic root for all AST nodes) and the comprehensive AstNodeType enum which classifies every type of node in the tree.
It aggregates all concrete AST node class declarations by including the modular headers from h/. This keeps ast_node.hpp concise while providing a single, convenient include for other modules (like parser/) that need to work with the entire AST.

- h/ (Headers for Node Declarations):
Contains sub-headers that logically group the declarations (class definitions) of concrete AST node types.
- h/declarations.hpp: Defines nodes for top-level language declarations (e.g., ItemDeclarationNode, TermDeclarationNode, KeyDeclarationNode, DictionaryDeclarationNode, ContainerNode, CausalRelationshipNode, ClassDeclarationNode, FunctionDeclarationNode).
- h/expressions.hpp: Defines nodes for literals, identifiers, path references, and mathematical expressions (e.g., StringLiteralNode, NumericLiteralNode, BooleanLiteralNode, NullLiteralNode, PathReferenceNode, IdentifierNode, BinaryExpressionNode).
- h/statements.hpp: Defines nodes for all executable statements and control flow structures (e.g., ProgramNode, ExecutionBlockNode, LetStatementNode, SetStatementNode, IfStatementNode, LoopStatementNode, PrintStatementNode, ReturnStatementNode, etc.).

- c/ (Implementations of Node Methods):
Contains .cpp files that provide the implementations for the constructors and the accept() methods of the AST nodes declared in h/.

- c/declarations.cpp: Implements methods for nodes from h/declarations.hpp.
- c/expressions.cpp: Implements methods for nodes from h/expressions.hpp.
- c/statements.cpp: Implements methods for nodes from h/statements.hpp.
- ast_utils.cpp: This acts as a central aggregation point for the implementations of the factory functions (createXNode(...)) and simply includes the modular c/*.cpp files. This helps manage the number of compilation units and keeps the factory definitions separate from the node implementations.

## Dependencies
The ast/ module primarily depends on:
- visitors/ast_interface.hpp: For the AstVisitor interface, which is central to the accept() methods in all AST nodes.
- Standard C++ libraries: <vector>, <memory>, <string>, <variant>.
This structured approach ensures that the AST is both powerful and easy to extend or modify as your Gravitus Principia language evolves.