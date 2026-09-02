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