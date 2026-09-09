// qps/core/src/parser/c/_index.cpp

#include "../h/_index.hpp" // Include the corresponding header for the Parser class
#include "../../ast/ast_utils.hpp" // For AST node creation helpers
#include <iostream>        // For potential debug output
#include <sstream>         // For building error messages

namespace qps {
namespace parser {

// Constructor: Initializes the Parser with a lexer and fetches the first two tokens.
Parser::Parser(tokens::Lexer& lexer)
    : lexer_(lexer),
      current_execution_domain_(ast::ExecutionDomain::GENERIC) {
    // Initialize current_token_ and next_token_ by advancing twice.
    // This primes the parser with the first token in current_token_ and
    // the second token in next_token_ for lookahead.
    advance(); // current_token_ = first token
    advance(); // next_token_ = second token
}

// Advances the parser's token stream.
// Consumes the current_token_ and makes next_token_ the new current_token_.
// Also fetches a new token from the lexer into next_token_.
void Parser::advance() {
    current_token_ = next_token_;
    next_token_ = lexer_.getNextToken();
}

// Matches the current token against an expected TokenType.
// If it matches, advances the token stream. Otherwise, throws a parsing error.
void Parser::match(tokens::TokenType expected_type) {
    if (current_token_.type == expected_type) {
        advance();
    } else {
        error("Expected token type " + tokens::Token(expected_type, "", 0, 0).toString() +
              " but found " + current_token_.toString() + ".");
    }
}

void Parser::matchStatementTerminator(const std::string& statement_name) {
    if (peek_type() == tokens::TokenType::SEMICOLON) {
        match(tokens::TokenType::SEMICOLON);
        return;
    }

    if (peek_type() == tokens::TokenType::EXEC_DELIMITER) {
        match(tokens::TokenType::EXEC_DELIMITER);
        return;
    }

    error("Expected ';' after " + statement_name + " statement. Found: " + current_token_.toString());
}

// Matches the current token against an expected TokenType and returns its lexeme.
// Useful for identifiers.
std::string Parser::match_and_get_lexeme(tokens::TokenType expected_type) {
    if (current_token_.type == expected_type) {
        std::string lexeme = current_token_.lexeme;
        advance();
        return lexeme;
    } else {
        error("Expected token type " + tokens::Token(expected_type, "", 0, 0).toString() +
              " but found " + current_token_.toString() + ".");
    }
}

// Matches the current token against an expected TokenType and returns its literal value.
// Uses a template to correctly retrieve the variant type.
template<typename T>
T Parser::match_and_get_literal(tokens::TokenType expected_type) {
    if (current_token_.type == expected_type) {
        try {
            T value = std::get<T>(current_token_.literal);
            advance();
            return value;
        } catch (const std::bad_variant_access& e) {
            error("Internal Error: Mismatched literal type for token " + current_token_.lexeme +
                  ". Expected " + typeid(T).name() + " but got a different type in literal variant.");
        }
    } else {
        error("Expected token type " + tokens::Token(expected_type, "", 0, 0).toString() +
              " but found " + current_token_.toString() + ".");
    }
    // This part should not be reached due to error() throwing.
    // Added to satisfy compiler return type requirement.
    throw std::runtime_error("Unexpected code path in match_and_get_literal.");
}

// Explicit template instantiations for literal types the parser will use.
// This is necessary because templates are compiled only when used, and we're
// using them in a separate .cpp file.
template double Parser::match_and_get_literal<double>(tokens::TokenType);
template std::string Parser::match_and_get_literal<std::string>(tokens::TokenType);
template bool Parser::match_and_get_literal<bool>(tokens::TokenType);

// Peeks at the current token's type without consuming it.
tokens::TokenType Parser::peek_type() const {
    return current_token_.type;
}

// Peeks at the next token's type without consuming it.
tokens::TokenType Parser::peek_next_type() const {
    return next_token_.type;
}

// Reports a parsing error, including line and column number.
[[noreturn]] void Parser::error(const std::string& message) {
    std::stringstream ss;
    ss << "Parsing Error at L" << current_token_.line << ", C" << current_token_.column
       << ": " << message;
    throw std::runtime_error(ss.str());
}

// Parses the entire source file and returns the root of the AST (a ProgramNode).
std::unique_ptr<ast::ProgramNode> Parser::parseProgram() {
    auto program = ast::createProgramNode(current_token_.line, current_token_.column);

    while (peek_type() != tokens::TokenType::END_OF_FILE) {
        // Allow leading paragraph boundaries, including empty lines at file start
        // or multiple blank-line runs normalized by the lexer.
        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        // Parse exactly one complete surface declaration.
        auto declaration = parseDeclaration();
        if (!declaration) {
            error("Unexpected token at library/module surface: " +
                  current_token_.toString());
        }

        program->statements.push_back(std::move(declaration));

        // A peer surface declaration must be separated by a paragraph boundary.
        if (peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        if (peek_type() != tokens::TokenType::PARAGRAPH_BREAK) {
            error("Expected blank-line boundary between surface declarations. Found: " +
                  current_token_.toString());
        }

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }
    }

    return program;
}

// Parses a single top-level declaration.
// This function acts as a dispatcher based on the current token type.
std::unique_ptr<ast::AstNode> Parser::parseDeclaration() {
    // QPS primitive declaration grammar:
    //
    //   identifier.  -> Key
    //   identifier:  -> Term
    //   identifier-  -> Item
    //
    // The words "key.", "term:", and "item-" are generic examples of
    // these forms, not reserved declaration prefixes.

    if (peek_type() == tokens::TokenType::IDENTIFIER) {
        const auto next = peek_next_type();

        if (next == tokens::TokenType::DOT) {
            return parseKeyDeclaration();
        }

        if (next == tokens::TokenType::COLON) {
            return parseTermDeclaration();
        }

        if (next == tokens::TokenType::OP_SUBTRACT) {
            return parseItemDeclaration();
        }
    }

    if (peek_type() == tokens::TokenType::OPEN_BRACKET) {
        if (peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) {
            return parseSymbolReference();
        }

        return parseDictionaryDeclaration();
    }

    if (peek_type() == tokens::TokenType::OPEN_PAREN) {
        return parseContainer();
    }

    if (peek_type() == tokens::TokenType::OPEN_BRACE) {
        return parseBracedExecutionConstruct();
    }

    if (peek_type() == tokens::TokenType::KW_FUNC) {
        return parseFunctionDeclaration();
    }

    if (peek_type() == tokens::TokenType::KW_CLASS) {
        return parseClassDeclaration();
    }

    // Executable statements may also appear where the grammar permits
    // declarations/statements at the current level.
    if (peek_type() == tokens::TokenType::KW_LET ||
        peek_type() == tokens::TokenType::KW_SET ||
        peek_type() == tokens::TokenType::KW_IF ||
        peek_type() == tokens::TokenType::KW_ELSE ||
        peek_type() == tokens::TokenType::KW_ELIF ||
        peek_type() == tokens::TokenType::KW_LOOP ||
        peek_type() == tokens::TokenType::KW_WHILE ||
        peek_type() == tokens::TokenType::KW_FOR ||
        peek_type() == tokens::TokenType::KW_RETURN ||
        peek_type() == tokens::TokenType::KW_PRINT ||
        peek_type() == tokens::TokenType::KW_ASSERT ||
        peek_type() == tokens::TokenType::KW_TRY ||
        peek_type() == tokens::TokenType::KW_RAISE ||
        peek_type() == tokens::TokenType::KW_BREAK ||
        peek_type() == tokens::TokenType::KW_CONTINUE ||
        peek_type() == tokens::TokenType::KW_PASS) {
        return parseStatement();
    }

    error("Unexpected token for declaration or statement: " +
          current_token_.toString());
    return nullptr;
}


// Parses an Execution Block: '{ ... }'
// Assumes this is called after '{' has been peeked, and consumes '{' and '}'.
std::unique_ptr<ast::ExecutionBlockNode> Parser::parseExecutionBlock() {
    int line = current_token_.line;
    int column = current_token_.column;
    match(tokens::TokenType::OPEN_BRACE); // Consume '{'

    auto exec_block_node = ast::createExecutionBlockNode(line, column);

    // Parse statements within the block until '}' or EOF.
    while (peek_type() != tokens::TokenType::CLOSE_BRACE &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        // Blank lines are formatting boundaries, not executable statements.
        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        // A paragraph break may have moved us directly onto the block closer.
        if (peek_type() == tokens::TokenType::CLOSE_BRACE ||
            peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        auto statement = parseStatement();

        if (statement) {
            exec_block_node->statements.push_back(std::move(statement));
        } else {
            error(
                "Failed to parse statement within execution block: " +
                current_token_.toString());
        }
    }

    match(tokens::TokenType::CLOSE_BRACE); // Consume '}'
    return exec_block_node;
}

// NEW: Central dispatcher for parsing individual statements.
std::unique_ptr<ast::AstNode> Parser::parseStatement() {
    if (peek_type() == tokens::TokenType::OPEN_BRACKET &&
        peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) {

        return parseSemanticItemDeclaration();

    } else if (peek_type() == tokens::TokenType::CALCULATION_MARKER) {
        return parseCalculation();
    } else if (peek_type() == tokens::TokenType::KW_LET) {
        return parseLetStatement();
    } else if (peek_type() == tokens::TokenType::KW_SET) {
        return parseSetStatement();
    } else if (peek_type() == tokens::TokenType::KW_ASSERT) {
        return parseAssertStatement();
    } else if (peek_type() == tokens::TokenType::KW_FAIL) {
        return parseFailStatement();
    } else if (peek_type() == tokens::TokenType::KW_RAISES) {
        return parseRaisesStatement();
    } else if (peek_type() == tokens::TokenType::KW_BREAK) {
        return parseBreakStatement();
    } else if (peek_type() == tokens::TokenType::KW_CONTINUE) {
        return parseContinueStatement();
    } else if (peek_type() == tokens::TokenType::KW_ELIF) {
        return parseElifStatement();
    } else if (peek_type() == tokens::TokenType::KW_ELSE) {
        return parseElseStatement();
    } else if (peek_type() == tokens::TokenType::KW_FOR) {
        return parseForStatement();
    } else if (peek_type() == tokens::TokenType::KW_IF) {
        return parseIfStatement();
    } else if (peek_type() == tokens::TokenType::KW_LOOP) {
        return parseLoopStatement();
    } else if (peek_type() == tokens::TokenType::KW_PRINT) {
        return parsePrintStatement();
    } else if (peek_type() == tokens::TokenType::KW_RETURN) {
        return parseReturnStatement();
    } else if (peek_type() == tokens::TokenType::KW_RAISE) {
        return parseRaiseStatement();
    } else if (peek_type() == tokens::TokenType::KW_TRY) {
        return parseTryStatement();
    } else if (peek_type() == tokens::TokenType::KW_WHILE) {
        return parseWhileStatement();
    } else if (peek_type() == tokens::TokenType::KW_PASS) {
        return parsePassStatement();
    } else if (peek_type() == tokens::TokenType::IDENTIFIER &&
               peek_next_type() == tokens::TokenType::COLON) {
        // Execution Terms are shared workspace statements.
        // Structural bindings are valid independently of execution domain.
        // Domain-specific validity is enforced by the interpreter.
        return parseExecutionTermStatement();
    } else if (peek_type() == tokens::TokenType::EXECUTION_ACTION) {
        // ExecutionActionNode is domain-neutral syntax.
        // The active execution domain selects runtime dispatch.
        auto action = parseExecutionActionInvocation(nullptr);
        match(tokens::TokenType::SEMICOLON);
        return action;
    } else if (
        peek_type() == tokens::TokenType::IDENTIFIER &&
        peek_next_type() == tokens::TokenType::OPEN_PAREN
    ) {
        // A function call is already a RuntimeValue expression node.
        // As a statement its returned value is intentionally discarded.
        auto call = parseFunctionCall();
        match(tokens::TokenType::SEMICOLON);
        return call;
    }

    // If we reach here, it means the current token does not start a recognized statement.
    error("Unrecognized statement: " + current_token_.toString());
    return nullptr; // Should not be reached
}


} // namespace parser
} // namespace qps
