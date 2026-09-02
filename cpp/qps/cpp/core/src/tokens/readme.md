gravitus_principia/core/src/tokens/README.md

# Gravitus Principia: tokens/ Module
The tokens/ module is the foundational layer of the Gravitus Principia engine's parsing pipeline. Its primary role is to perform lexical analysis, converting the raw .grav source code text into a stream of meaningful tokens. Think of it as the "ears" of the compiler, responsible for recognizing the individual "words" (tokens) of the Gravitus Principia language.

# Core Principles
This module adheres to the overarching Gravitus Principia design principles:

Human-First Conciseness: While primarily machine-focused, the token definitions and recognition logic are designed to directly reflect the human-readable syntax of .grav files.
Machine-Optimized Precision: Every character sequence is unambiguously mapped to a specific token type, ensuring predictable and efficient processing for the subsequent parser.
Semantic Layering: Even at this low level, tokens are designed to carry basic semantic intent (e.g., TYPE_NUMERIC, KW_ITEM), laying the groundwork for deeper interpretation.
Hierarchical Flexibility: The module handles various token types, from single characters to complex keywords and literals, reflecting the nested structure of the .grav language.

# Architecture Overview
The tokens/ module is composed of four main components, each playing a distinct role in the lexical analysis process:

# CharStream
Files: h/char_stream.hpp, c/char_stream.cpp
Role: This is the low-level input reader. It provides efficient character-by-character access to the raw source code string. It can peek() at the current character, peek_ahead() to look at upcoming characters without consuming them, and advance() to move the reading position forward. Crucially, it tracks the current line and column numbers for precise error reporting.
# Token
Files: h/token.hpp
Role: This defines the fundamental unit of lexical analysis. The Token struct encapsulates all the essential information about a recognized "word" from the source code: its TokenType (what kind of word it is), its lexeme (the actual text string), its line and column (its position in the source), and its literal value (for numeric, string, boolean, or null tokens). The TokenType enum provides the complete vocabulary of the Gravitus Principia language.
# TokenRecognizer
Files: h/recognizer.hpp, c/recognizer.cpp
Role: This component contains the specific logic for identifying different patterns in the CharStream and converting them into Token objects. It includes specialized methods for recognizing identifiers/keywords, numeric literals (including floats and scientific notation), string literals (handling escape sequences), and Gravitus Principia's unique type suffixes (like /n;, /p;). It utilizes static maps for efficient lookup of reserved keywords and type suffixes.
# Lexer
Files: h/lexer.hpp, c/lexer.cpp
Role: The Lexer is the orchestrator of the tokenization process. It takes a CharStream as input and uses the TokenRecognizer to extract tokens. Its primary public method, getNextToken(), is called repeatedly by the parser to obtain the next meaningful token. The Lexer handles overall lexical concerns such as:
Skipping whitespace.
Processing single-line (#) and multi-line (## ... ##) comments.
Implementing the "longest match first" rule to correctly identify multi-character tokens (e.g., ## over #, /. over /).
Error handling for unrecognized characters or unclosed comments/strings.

# How It Works
The lexical analysis process flows as follows:
- A CharStream is initialized with the raw .grav source code.
- A Lexer is created, which in turn initializes a TokenRecognizer with access to the CharStream and current line/column information.
- When the parser needs the next token, it calls Lexer::getNextToken().
- The Lexer first skips any whitespace or comments.
- It then peeks at the current and next few characters in the CharStream to determine the potential token type.
- Based on the lookahead, it delegates to the appropriate TokenRecognizer method (e.g., recognizeNumericLiteral(), recognizeTypeSuffix()).
- The TokenRecognizer consumes the characters forming the token from the CharStream, converts them into the correct Token struct (stamping its type, lexeme, and position), and returns it to the Lexer.
- The Lexer then returns this Token to the calling parser.
- This process continues until the Lexer encounters the end of the input stream and returns an END_OF_FILE token.
This modular design ensures a clear separation of concerns, making the lexical analysis robust, maintainable, and highly efficient.