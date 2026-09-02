# Gravitus Principia Core Engine: Parser Module
This directory contains the syntactic analysis (parsing) components of the Gravitus Principia engine. Its primary responsibility is to consume the stream of tokens produced by the tokens/ (lexical analysis) module and construct an Abstract Syntax Tree (AST) that represents the .grav source code in a hierarchical, machine-understandable format.

# Core Principles
- Modular Design: Each significant grammatical construct of the Gravitus Principia language (e.g., item-, term:, key., [] dictionaries, () containers, = causal relationships, -class, -func) has its own dedicated header (.hpp) and implementation (.cpp) files. This enhances readability, maintainability, and facilitates parallel development.
- Recursive Descent Parsing: The parser largely employs a recursive descent approach, where each grammar rule corresponds to a parsing function that consumes tokens and builds relevant AST nodes.
- Error Reporting: Includes mechanisms for reporting parsing errors with precise line and column information.

# Architecture Overview
The parser/ module is organized into h/ (headers) and c/ (implementations) subdirectories, mirroring the module-per-construct approach.

- Main Parser (_index.hpp, _index.cpp)
- Parser Class: The central orchestrator. It holds a reference to the Lexer, manages the token stream (current_token_, next_token_), and contains the main parsing entry point (parseProgram()).
- Core Helpers: Provides fundamental methods like advance(), match(), match_and_get_lexeme(), match_and_get_literal(), peek_type(), error().
- Declaration Dispatcher: The parseDeclaration() function acts as a dispatcher, directing control to the appropriate parsing function based on the current token (e.g., parseItemDeclaration(), parseTermDeclaration()).

# Modular Parsing Components
Each of these pairs of files encapsulates the logic for parsing a specific Gravitus Principia construct:

- item.hpp / item.cpp: Handles the parsing of item- declarations (item- identifier "value"/type; or item- path/to.ref;).
- term.hpp / term.cpp: Manages the parsing of term: declarations (term: identifier content;), including nested elements and definition strings.
- key.hpp / key.cpp: Deals with key. declarations (key. identifier content;), which serve as named structural sections.
- dictionary.hpp / dictionary.cpp: Contains logic for parsing [] dictionary blocks and their individual entries, including input references (<.ID:).
- container.hpp / container.cpp: Parses () container blocks, handling nested declarations within them.
- causal.hpp / causal.cpp: Implements the parsing of = causal relationships (Entity: (Input = Output)).
- math.hpp / math.cpp: Provides the functions for parsing mathematical expressions ({#ID: expression _}), adhering to operator precedence.
- class.hpp / class.cpp: Handles the parsing of -class declarations, including the class name and its member definitions.
- function.hpp / function.cpp: Deals with the parsing of -func declarations, including function names, parameter definitions, and the executable body.
- reference.hpp / reference.cpp: Focuses on parsing path-based references (folder/file.key.item-).

# Dependencies
This parser module depends heavily on the tokens/ module for its input (Lexer and Token definitions) and the ast/ module for defining and creating the nodes of the Abstract Syntax Tree.