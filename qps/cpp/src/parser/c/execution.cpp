#include "../h/_index.hpp"
#include "../../ast/ast_utils.hpp"

namespace qps {
namespace parser {

std::unique_ptr<ast::AstNode> Parser::parseBracedExecutionConstruct() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::OPEN_BRACE);

    if (peek_type() == tokens::TokenType::REFERENCE_OPERATOR) {
        return parseExecutionCall(line, column);
    }

    if (peek_type() == tokens::TokenType::CAUSAL_MARKER) {
        match(tokens::TokenType::CAUSAL_MARKER);
        return parseCausalDefinition(line, column);
    }

    // Geometry is the first explicit domain-qualified
    // execution definition:
    //
    //   {@foo: ...}  -> GEOMETRY
    //
    // '%' remains exclusively existing QPS calculation syntax.
    if (peek_type() == tokens::TokenType::GEOMETRY_MARKER) {
        match(tokens::TokenType::GEOMETRY_MARKER);

        return parseExecutionDefinition(
            line,
            column,
            ast::ExecutionDomain::GEOMETRY);
    }

    if ((peek_type() == tokens::TokenType::IDENTIFIER ||
         peek_type() == tokens::TokenType::NUMERIC_LITERAL) &&
        peek_next_type() == tokens::TokenType::COLON) {

        return parseExecutionDefinition(
            line,
            column,
            ast::ExecutionDomain::GENERIC);
    }

    auto exec_block_node =
        ast::createExecutionBlockNode(line, column);

    while (peek_type() != tokens::TokenType::CLOSE_BRACE &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

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

    match(tokens::TokenType::CLOSE_BRACE);
    return exec_block_node;
}

std::unique_ptr<ast::ExecutionDefinitionNode>
Parser::parseExecutionDefinition(
    int line,
    int column,
    ast::ExecutionDomain domain) {

    bool identifier_is_numeric = false;
    std::string identifier =
        parseExecutionIdentifier(identifier_is_numeric);

    const ast::ExecutionDomain previous_domain = current_execution_domain_;
    current_execution_domain_ = domain;

    match(tokens::TokenType::COLON);

    auto body =
        ast::createExecutionBlockNode(line, column);

    while (peek_type() != tokens::TokenType::CLOSE_BRACE &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::CLOSE_BRACE ||
            peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        auto statement = parseExecutionDefinitionStatement();

        if (statement) {
            body->statements.push_back(std::move(statement));
        } else {
            error(
                "Failed to parse statement within execution definition: " +
                current_token_.toString());
        }
    }

    match(tokens::TokenType::CLOSE_BRACE);

    current_execution_domain_ = previous_domain;

    return ast::createExecutionDefinitionNode(
        identifier,
        identifier_is_numeric,
        domain,
        std::move(body),
        line,
        column);
}

std::unique_ptr<ast::ExecutionCallNode>
Parser::parseExecutionCall(
    int line,
    int column) {

    match(tokens::TokenType::REFERENCE_OPERATOR);

    bool identifier_is_numeric = false;
    std::string identifier =
        parseExecutionIdentifier(identifier_is_numeric);

    match(tokens::TokenType::COLON);

    auto call =
        ast::createExecutionCallNode(
            identifier,
            identifier_is_numeric,
            line,
            column);

    while (peek_type() != tokens::TokenType::CLOSE_BRACE &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::CLOSE_BRACE ||
            peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        if (peek_type() == tokens::TokenType::IDENTIFIER &&
            peek_next_type() == tokens::TokenType::OP_SUBTRACT) {

            call->addArgument(parseItemDeclaration());
            continue;
        }

        error(
            "Expected local item override inside execution call. Found: " +
            current_token_.toString());
    }

    match(tokens::TokenType::CLOSE_BRACE);
    return call;
}

std::unique_ptr<ast::AstNode>
Parser::parseExecutionDefinitionStatement() {
    // Ordinary executable control flow belongs to the common statement
    // grammar. Execution definitions retain only their definition-specific
    // input and domain-qualified parsing below.
    if (peek_type() == tokens::TokenType::KW_IF ||
        peek_type() == tokens::TokenType::KW_WHILE ||
        peek_type() == tokens::TokenType::KW_FOR ||
        peek_type() == tokens::TokenType::KW_LOOP ||
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

    if (peek_type() == tokens::TokenType::OPEN_BRACKET &&
        peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) {

        return parseExecutionDefinitionInput();
    }

    if (peek_type() == tokens::TokenType::IDENTIFIER &&
        peek_next_type() == tokens::TokenType::OP_SUBTRACT) {

        return parseItemDeclaration();
    }

    // Local structural bindings belong to the shared execution workspace,
    // not to any one execution domain:
    //
    //   master: [>pus.pu_master.dimensions];
    //   groove: [master.groove];
    //
    // Domain-prefixed operations may consume these bindings later.
    if (peek_type() == tokens::TokenType::IDENTIFIER &&
        peek_next_type() == tokens::TokenType::COLON) {

        return parseExecutionTermStatement();
    }

    // Domain markers inside a shared execution definition qualify the
    // individual statement rather than the whole surrounding definition.
    //
    //   {model:
    //   v: [>structure];
    //   @object: -cylinder(v);
    //   }
    //
    // Preserve the surrounding definition domain after parsing the
    // GEOMETRY-qualified statement.
    if (peek_type() == tokens::TokenType::GEOMETRY_MARKER) {
        match(tokens::TokenType::GEOMETRY_MARKER);

        const ast::ExecutionDomain previous_domain =
            current_execution_domain_;

        current_execution_domain_ =
            ast::ExecutionDomain::GEOMETRY;

        auto statement =
            parseExecutionTermStatement();

        // Preserve the statement-level '@' qualification on the AST.
        // This is deliberately independent of the surrounding
        // execution definition domain.
        statement->geometry_qualified_ = true;

        current_execution_domain_ =
            previous_domain;

        return statement;
    }

    if (peek_type() == tokens::TokenType::CALCULATION_MARKER) {
        return parseCalculation();
    }

    // Execution actions and explicit runtime raises are
    // domain-neutral execution statements.
    if (peek_type() == tokens::TokenType::EXECUTION_ACTION ||
        peek_type() == tokens::TokenType::KW_RAISE) {

        return parseStatement();
    }

    if (current_execution_domain_ == ast::ExecutionDomain::GEOMETRY) {
        return parseStatement();
    }

    error(
        "Unrecognized statement in execution definition: " +
        current_token_.toString());
    return nullptr;
}

std::unique_ptr<ast::ItemDeclarationNode>
Parser::parseExecutionDefinitionInput() {
    int line = current_token_.line;
    int column = current_token_.column;

    auto target = parseSymbolReference();

    if (!target->selectsItemValue()) {
        error(
            "Execution-definition Item input must include '-' "
            "inside the structural reference, for example [>x-].");
    }

    auto item_node =
        ast::createItemDeclarationNode(
            std::move(target),
            line,
            column);

    // Execution-definition inputs follow Item semantics:
    //
    //   [>x-]
    //       required, untyped
    //
    //   [>x-]/n;
    //       required, explicitly numeric
    //
    //   [>x-] 3;
    //       defaulted, no explicit type hint
    //
    //   [>x-] 3/n;
    //       defaulted, explicitly numeric
    //
    // A definition boundary may terminate an untyped empty input
    // without a semicolon.
    if (isExecutionDefinitionInputBoundary()) {
        return item_node;
    }

    const bool typed_empty =
        peek_type() == tokens::TokenType::TYPE_PATH ||
        peek_type() == tokens::TokenType::TYPE_NUMERIC ||
        peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
        peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
        peek_type() == tokens::TokenType::TYPE_NULL;

    if (!typed_empty) {
        if (peek_type() == tokens::TokenType::STRING_LITERAL ||
            peek_type() == tokens::TokenType::NUMERIC_LITERAL ||
            peek_type() == tokens::TokenType::BOOLEAN_LITERAL ||
            peek_type() == tokens::TokenType::NULL_LITERAL) {

            item_node->value_node_ = parseLiteral();

        } else if (peek_type() == tokens::TokenType::IDENTIFIER) {

            item_node->value_node_ = parsePathReference();

        } else if (peek_type() == tokens::TokenType::OPEN_BRACKET &&
                   peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) {

            item_node->value_node_ = parseSymbolReference();

        } else {

            error(
                "Expected a default literal, reference, type hint, or execution-definition boundary. Found: " +
                current_token_.toString());
        }
    }

    if (peek_type() == tokens::TokenType::TYPE_PATH ||
        peek_type() == tokens::TokenType::TYPE_NUMERIC ||
        peek_type() == tokens::TokenType::TYPE_ALPHANUM ||
        peek_type() == tokens::TokenType::TYPE_BOOLEAN ||
        peek_type() == tokens::TokenType::TYPE_NULL) {

        item_node->type_hint_ = peek_type();
        advance();

    } else {

        match(tokens::TokenType::SEMICOLON);
    }

    return item_node;
}

std::unique_ptr<ast::TermDeclarationNode>
Parser::parseExecutionTermStatement() {
    int line = current_token_.line;
    int column = current_token_.column;

    std::string identifier =
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    match(tokens::TokenType::COLON);

    while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
        match(tokens::TokenType::PARAGRAPH_BREAK);
    }

    // Native structural Term in executable scope:
    //
    //   inputs: (
    //   mass_kg- mass_kg;
    //   gravity_m_s2- gravity_m_s2;
    //   );
    //
    // This is ordinary QPS Term/Container structure, not an execution
    // action and not a separate mapping runtime representation.
    if (peek_type() == tokens::TokenType::OPEN_PAREN) {
        auto term_node =
            ast::createTermDeclarationNode(
                identifier,
                line,
                column);

        term_node->content_.push_back(
            parseContainer());

        match(tokens::TokenType::SEMICOLON);

        return term_node;
    }

    // Shared structural execution binding:
    //
    //   master: [>pus.pu_master.dimensions];
    //   groove: [master.groove];
    if (peek_type() == tokens::TokenType::OPEN_BRACKET &&
        (peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR ||
         peek_next_type() == tokens::TokenType::IDENTIFIER)) {

        auto term_node =
            ast::createTermDeclarationNode(
                identifier,
                line,
                column);

        term_node->content_.push_back(
            parseSymbolReference());

        match(tokens::TokenType::SEMICOLON);

        return term_node;
    }

    std::unique_ptr<ast::AstNode> source = nullptr;

    if (peek_type() == tokens::TokenType::IDENTIFIER &&
        peek_next_type() == tokens::TokenType::EXECUTION_ACTION) {

        const int source_line = current_token_.line;
        const int source_column = current_token_.column;

        source =
            ast::createIdentifierNode(
                match_and_get_lexeme(
                    tokens::TokenType::IDENTIFIER),
                source_line,
                source_column);
    }

    while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
        match(tokens::TokenType::PARAGRAPH_BREAK);
    }

    if (peek_type() != tokens::TokenType::EXECUTION_ACTION) {
        error(
            "Expected GEOMETRY execution action after Term stage target. Found: " +
            current_token_.toString());
    }

    auto term_node =
        ast::createTermDeclarationNode(
            identifier,
            line,
            column);

    term_node->content_.push_back(
        parseExecutionActionInvocation(
            std::move(source)));

    // ',' separates multiple actions.
    // ';' closes the geometry Term.
    //
    // '\' is accepted temporarily for legacy QPS but has
    // no canonical closure role.
    while (peek_type() == tokens::TokenType::COMMA) {
        match(tokens::TokenType::COMMA);

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() != tokens::TokenType::EXECUTION_ACTION) {
            error(
                "Expected GEOMETRY action after ','. Found: " +
                current_token_.toString());
        }

        term_node->content_.push_back(
            parseExecutionActionInvocation(nullptr));
    }

    match(tokens::TokenType::SEMICOLON);

    return term_node;
}

std::unique_ptr<ast::ExecutionActionNode>
Parser::parseExecutionActionInvocation(
    std::unique_ptr<ast::AstNode> source) {

    int line = current_token_.line;
    int column = current_token_.column;

    std::string action_name =
        match_and_get_lexeme(tokens::TokenType::EXECUTION_ACTION);

    if (!action_name.empty() && action_name.front() == '-') {
        action_name.erase(0, 1);
    }

    std::unique_ptr<ast::ContainerNode> parameters = nullptr;

    if (peek_type() == tokens::TokenType::OPEN_PAREN) {
        parameters = parseExecutionActionParameters();
    }

    return ast::createExecutionActionNode(
        action_name,
        std::move(source),
        std::move(parameters),
        line,
        column);
}

std::unique_ptr<ast::ContainerNode>
Parser::parseExecutionActionParameters() {
    int line = current_token_.line;
    int column = current_token_.column;

    match(tokens::TokenType::OPEN_PAREN);

    auto parameters =
        ast::createContainerNode(
            line,
            column);

    while (peek_type() != tokens::TokenType::CLOSE_PAREN &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::CLOSE_PAREN ||
            peek_type() == tokens::TokenType::END_OF_FILE) {
            break;
        }

        if (peek_type() == tokens::TokenType::IDENTIFIER &&
            peek_next_type() == tokens::TokenType::OP_SUBTRACT) {

            // Item overrides terminate themselves with ';'.
            parameters->elements.push_back(
                parseItemDeclaration());

        } else if (peek_type() == tokens::TokenType::IDENTIFIER) {

            // Bare structural names do not self-terminate, so comma
            // remains the separator where multiple names are supplied.
            const int parameter_line =
                current_token_.line;
            const int parameter_column =
                current_token_.column;

            parameters->elements.push_back(
                ast::createIdentifierNode(
                    match_and_get_lexeme(
                        tokens::TokenType::IDENTIFIER),
                    parameter_line,
                    parameter_column));

        } else {

            error(
                "Expected local Item override or structural binding name "
                "inside GEOMETRY action parameters. Found: " +
                current_token_.toString());
        }

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::COMMA) {
            match(tokens::TokenType::COMMA);
            continue;
        }

        if (peek_type() == tokens::TokenType::CLOSE_PAREN) {
            break;
        }

        // Consecutive Item declarations are unambiguous because each
        // Item owns its ';'. Bare identifiers still require comma.
        if (peek_type() == tokens::TokenType::IDENTIFIER &&
            peek_next_type() == tokens::TokenType::OP_SUBTRACT) {
            continue;
        }

        error(
            "Expected ',', another Item override, or ')' in "
            "GEOMETRY action parameters. Found: " +
            current_token_.toString());
    }

    match(tokens::TokenType::CLOSE_PAREN);

    return parameters;
}

std::string Parser::parseExecutionIdentifier(
    bool& identifier_is_numeric) {

    if (peek_type() == tokens::TokenType::IDENTIFIER) {
        identifier_is_numeric = false;
        return match_and_get_lexeme(tokens::TokenType::IDENTIFIER);
    }

    if (peek_type() == tokens::TokenType::NUMERIC_LITERAL) {
        identifier_is_numeric = true;
        return match_and_get_lexeme(tokens::TokenType::NUMERIC_LITERAL);
    }

    error(
        "Expected execution definition or call identifier. Found: " +
        current_token_.toString());
    return "";
}

bool Parser::isExecutionDefinitionInputBoundary() const {
    return peek_type() == tokens::TokenType::CLOSE_BRACE ||
           peek_type() == tokens::TokenType::END_OF_FILE ||
           peek_type() == tokens::TokenType::PARAGRAPH_BREAK ||
           peek_type() == tokens::TokenType::CALCULATION_MARKER ||
           (peek_type() == tokens::TokenType::OPEN_BRACKET &&
            peek_next_type() == tokens::TokenType::REFERENCE_OPERATOR) ||
           (current_execution_domain_ == ast::ExecutionDomain::GEOMETRY &&
            (peek_type() == tokens::TokenType::EXECUTION_ACTION ||
             peek_type() == tokens::TokenType::KW_RETURN ||
             (peek_type() == tokens::TokenType::IDENTIFIER &&
              peek_next_type() == tokens::TokenType::COLON)));
}


std::unique_ptr<ast::CausalDefinitionNode>
Parser::parseCausalDefinition(
    int line,
    int column) {

    const std::string identifier =
        match_and_get_lexeme(tokens::TokenType::IDENTIFIER);

    match(tokens::TokenType::COLON);

    auto definition =
        ast::createCausalDefinitionNode(
            identifier,
            line,
            column);

    while (peek_type() != tokens::TokenType::CLOSE_BRACE &&
           peek_type() != tokens::TokenType::END_OF_FILE) {

        while (peek_type() == tokens::TokenType::PARAGRAPH_BREAK) {
            match(tokens::TokenType::PARAGRAPH_BREAK);
        }

        if (peek_type() == tokens::TokenType::CLOSE_BRACE) {
            break;
        }

        definition->relationships.push_back(
            parseCausalRelationship());
    }

    match(tokens::TokenType::CLOSE_BRACE);
    return definition;
}


} // namespace parser
} // namespace qps
