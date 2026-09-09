// qps/core/src/visitors/print.cpp

#include "../h/print.hpp"
#include "../../ast/ast_node.hpp" // Need concrete AST node definitions to access members
#include <iostream>
#include <string>

namespace qps {
namespace visitors {

// Helper to get the current indentation string based on indent_level_.
std::string PrintVisitor::getIndent() const {
    return std::string(indent_level_ * 2, ' '); // 2 spaces per indent level
}

// --- Concrete visit implementations for each AST node type ---

void PrintVisitor::visit(ast::ProgramNode* node) {
    std::cout << getIndent() << "PROGRAM (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    for (const auto& stmt : node->statements) {
        stmt->accept(*this); // Recursively visit child statements
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::ItemDeclarationNode* node) {
    std::cout << getIndent()
              << "ITEM_DECLARATION (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";

    indent_level_++;

    std::cout << getIndent()
              << "Type Hint: ";

    if (!node->type_hint_) {
        std::cout << "<none>\n";
    } else {
        switch (*node->type_hint_) {
            case tokens::TokenType::TYPE_PATH:
                std::cout << "PATH\n";
                break;
            case tokens::TokenType::TYPE_NUMERIC:
                std::cout << "NUMERIC\n";
                break;
            case tokens::TokenType::TYPE_ALPHANUM:
                std::cout << "ALPHANUM\n";
                break;
            case tokens::TokenType::TYPE_BOOLEAN:
                std::cout << "BOOLEAN\n";
                break;
            case tokens::TokenType::TYPE_NULL:
                std::cout << "NULL\n";
                break;
            default:
                std::cout << "<unknown>\n";
                break;
        }
    }

    std::cout << getIndent()
              << "Target:\n";

    indent_level_++;

    if (node->target_) {
        node->target_->accept(*this);
    } else {
        std::cout << getIndent()
                  << "<none>\n";
    }

    indent_level_--;

    std::cout << getIndent()
              << "Value:\n";

    indent_level_++;

    if (node->value_node_) {
        node->value_node_->accept(*this);
    } else {
        std::cout << getIndent()
                  << "<none>\n";
    }

    indent_level_--;

    indent_level_--;
}

void PrintVisitor::visit(ast::TermDeclarationNode* node) {
    std::cout << getIndent() << "TERM_DECLARATION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Identifier: " << node->identifier_ << "\n";
    std::cout << getIndent() << "Content:\n";
    for (const auto& child : node->content_) {
        child->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::KeyDeclarationNode* node) {
    std::cout << getIndent() << "KEY_DECLARATION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Identifier: " << node->identifier_ << "\n";
    std::cout << getIndent() << "Content:\n";
    for (const auto& child : node->content_) {
        child->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::DictionaryDeclarationNode* node) {
    std::cout << getIndent() << "DICTIONARY_DECLARATION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Entries:\n";
    for (const auto& entry : node->entries) {
        entry->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::DictionaryEntryNode* node) {
    std::cout << getIndent() << "DICTIONARY_ENTRY (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "ID: " << node->id_ << "\n";
    std::cout << getIndent() << "Value:\n";
    node->value_node_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::ContainerNode* node) {
    std::cout << getIndent() << "CONTAINER (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Elements:\n";
    for (const auto& element : node->elements) {
        element->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::CausalDefinitionNode* node) {
    std::cout << getIndent()
              << "CAUSAL_DEFINITION "
              << node->identifier_
              << " (L" << node->getLine()
              << ", C" << node->getColumn() << ")\n";

    indent_level_++;
    for (const auto& relationship : node->relationships) {
        relationship->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::CausalRelationshipNode* node) {
    std::cout << getIndent() << "CAUSAL_RELATIONSHIP (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;

    for (const auto& side : node->sides_) {
        std::cout << getIndent() << "Side:\n";
        indent_level_++;
        std::cout << getIndent() << "Entity:\n";
        side->entity->accept(*this);
        std::cout << getIndent() << "Domain Chain:\n";
        indent_level_++;
        for (const auto& domain : side->domain_chain) {
            domain->accept(*this);
        }
        indent_level_--;
        indent_level_--;
    }

    indent_level_--;
}

void PrintVisitor::visit(ast::FunctionDeclarationNode* node) {
    std::cout << getIndent() << "FUNCTION_DECLARATION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Name: " << node->name_ << "\n";
    std::cout << getIndent() << "Parameters:\n";
    node->params_node_->accept(*this);
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::ClassDeclarationNode* node) {
    std::cout << getIndent() << "CLASS_DECLARATION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Name: " << node->name_ << "\n";
    std::cout << getIndent() << "Members:\n";
    for (const auto& member : node->members) {
        member->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::StringLiteralNode* node) {
    std::cout << getIndent() << "STRING_LITERAL (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Value: \"" << node->value_ << "\"\n";
    indent_level_--;
}

void PrintVisitor::visit(ast::NumericLiteralNode* node) {
    std::cout << getIndent() << "NUMERIC_LITERAL (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Value: " << node->value_ << "\n";
    indent_level_--;
}

void PrintVisitor::visit(ast::BooleanLiteralNode* node) {
    std::cout << getIndent() << "BOOLEAN_LITERAL (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Value: " << (node->value_ ? "true" : "false") << "\n";
    indent_level_--;
}

void PrintVisitor::visit(ast::NullLiteralNode* node) {
    std::cout << getIndent() << "NULL_LITERAL (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Value: null\n";
    indent_level_--;
}

void PrintVisitor::visit(ast::PathReferenceNode* node) {
    std::cout << getIndent() << "PATH_REFERENCE (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Segments: ";
    for (size_t i = 0; i < node->getPathSegments().size(); ++i) {
        std::cout << node->getPathSegments()[i] << (i == node->getPathSegments().size() - 1 ? "" : ".");
    }
    std::cout << "\n";
    indent_level_--;
}


void PrintVisitor::visit(ast::SymbolReferenceNode* node) {
    std::cout << getIndent()
              << "SYMBOL_REFERENCE (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";

    indent_level_++;
    std::cout << getIndent()
              << "Symbol: "
              << node->getSymbol()
              << "\n";
    indent_level_--;
}

void PrintVisitor::visit(ast::IdentifierNode* node) {
    std::cout << getIndent() << "IDENTIFIER (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Name: " << node->name_ << "\n";
    indent_level_--;
}

void PrintVisitor::visit(ast::UnaryExpressionNode* node) {
    std::cout << getIndent()
              << "UNARY_EXPRESSION (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Operator: NOT\n";
    std::cout << getIndent() << "Operand:\n";
    node->getOperand()->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::BinaryExpressionNode* node) {
    std::cout << getIndent() << "BINARY_EXPRESSION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Operator: ";
    switch (node->getOperator()) {
        case ast::BinaryExpressionNode::Operator::ADD: std::cout << "ADD\n"; break;
        case ast::BinaryExpressionNode::Operator::SUBTRACT: std::cout << "SUBTRACT\n"; break;
        case ast::BinaryExpressionNode::Operator::MULTIPLY: std::cout << "MULTIPLY\n"; break;
        case ast::BinaryExpressionNode::Operator::DIVIDE: std::cout << "DIVIDE\n"; break;
        case ast::BinaryExpressionNode::Operator::EQUAL: std::cout << "EQUAL\n"; break;
        case ast::BinaryExpressionNode::Operator::LESS: std::cout << "LESS\n"; break;
        case ast::BinaryExpressionNode::Operator::AND: std::cout << "AND\n"; break;
        case ast::BinaryExpressionNode::Operator::OR: std::cout << "OR\n"; break;
    }
    std::cout << getIndent() << "Left Operand:\n";
    node->getLeft()->accept(*this);
    std::cout << getIndent() << "Right Operand:\n";
    node->getRight()->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::FunctionCallNode* node) {
    std::cout << getIndent() << "FUNCTION_CALL (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Name: " << node->name_ << "\n";
    std::cout << getIndent() << "Arguments:\n";
    indent_level_++;
    for (const auto& argument : node->arguments_) {
        argument->accept(*this);
    }
    indent_level_--;
    indent_level_--;
}

void PrintVisitor::visit(ast::CalculationNode* node) {
    std::cout << getIndent()
              << "CALCULATION (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";

    indent_level_++;

    std::cout << getIndent() << "Target:\n";
    indent_level_++;

    if (node->hasTarget()) {
        node->getTarget()->accept(*this);
    } else {
        std::cout << getIndent() << "<none>\n";
    }

    indent_level_--;

    std::cout << getIndent() << "Expression:\n";
    indent_level_++;

    node->getExpression()->accept(*this);

    indent_level_--;
    indent_level_--;
}

void PrintVisitor::visit(ast::ExecutionBlockNode* node) {
    std::cout << getIndent() << "EXECUTION_BLOCK (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    for (const auto& stmt : node->statements) {
        stmt->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::ExecutionDefinitionNode* node) {
    std::cout << getIndent()
              << "EXECUTION_DEFINITION (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";

    indent_level_++;
    std::cout << getIndent()
              << "Identifier: "
              << node->identifier_
              << (node->identifier_is_numeric_ ? " (numeric)" : "")
              << "\n";
    std::cout << getIndent() << "Body:\n";
    indent_level_++;
    if (node->body_) {
        node->body_->accept(*this);
    }
    indent_level_--;
    indent_level_--;
}

void PrintVisitor::visit(ast::ExecutionCallNode* node) {
    std::cout << getIndent()
              << "EXECUTION_CALL (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";

    indent_level_++;
    std::cout << getIndent()
              << "Identifier: "
              << node->identifier_
              << (node->identifier_is_numeric_ ? " (numeric)" : "")
              << "\n";
    std::cout << getIndent() << "Arguments:\n";
    indent_level_++;
    for (const auto& argument : node->arguments_) {
        argument->accept(*this);
    }
    indent_level_--;
    indent_level_--;
}

void PrintVisitor::visit(ast::ExecutionActionNode* node) {
    std::cout << getIndent()
              << "EXECUTION_ACTION (L"
              << node->getLine()
              << ", C"
              << node->getColumn()
              << ")\n";

    indent_level_++;
    std::cout << getIndent() << "Name: -" << node->action_name_ << "\n";
    if (node->getSource()) {
        std::cout << getIndent() << "Source:\n";
        indent_level_++;
        node->getSource()->accept(*this);
        indent_level_--;
    }
    if (node->getParameters()) {
        std::cout << getIndent() << "Parameters:\n";
        indent_level_++;
        node->getParameters()->accept(*this);
        indent_level_--;
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::TestDeclarationNode* node) {
    std::cout << getIndent() << "TEST_DECLARATION (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    if (node->body_) {
        node->body_->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::LetStatementNode* node) {
    std::cout << getIndent() << "LET_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Identifier: " << node->identifier_ << "\n";
    if (node->initial_value_) {
        std::cout << getIndent() << "Initial Value:\n";
        node->initial_value_->accept(*this);
    } else {
        std::cout << getIndent() << "Initial Value: (None)\n";
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::SetStatementNode* node) {
    std::cout << getIndent() << "SET_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Target:\n";
    node->target_->accept(*this);
    std::cout << getIndent() << "Value:\n";
    node->value_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::AssertStatementNode* node) {
    std::cout << getIndent() << "ASSERT_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Condition:\n";
    node->condition_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::FailStatementNode* node) {
    std::cout << getIndent() << "FAIL_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    if (node->message_) {
        std::cout << getIndent() << "Message:\n";
        node->message_->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::RaisesStatementNode* node) {
    std::cout << getIndent() << "RAISES_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Expected: \"" << node->expected_message_ << "\"\n";
    if (node->body_) {
        std::cout << getIndent() << "Body:\n";
        node->body_->accept(*this);
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::BreakStatementNode* node) {
    std::cout << getIndent() << "BREAK_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    // Break statements have no children, just print and return.
}

void PrintVisitor::visit(ast::ContinueStatementNode* node) {
    std::cout << getIndent() << "CONTINUE_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    // Continue statements have no children.
}

void PrintVisitor::visit(ast::ElifStatementNode* node) {
    std::cout << getIndent() << "ELIF_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Condition:\n";
    node->condition_->accept(*this);
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::ElseStatementNode* node) {
    std::cout << getIndent() << "ELSE_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::ForStatementNode* node) {
    std::cout << getIndent() << "FOR_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Loop Control:\n";
    node->loop_control_->accept(*this);
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::IfStatementNode* node) {
    std::cout << getIndent() << "IF_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Condition:\n";
    node->condition_->accept(*this);
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    for (const auto& elif_block : node->elif_blocks_) {
        elif_block->accept(*this); // Visit each elif block
    }
    if (node->else_block_) {
        node->else_block_->accept(*this); // Visit the else block if it exists
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::LoopStatementNode* node) {
    std::cout << getIndent() << "LOOP_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::PrintStatementNode* node) {
    std::cout << getIndent() << "PRINT_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Expression to Print:\n";
    node->expression_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::ReturnStatementNode* node) {
    std::cout << getIndent() << "RETURN_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    if (node->expression_) {
        std::cout << getIndent() << "Expression to Return:\n";
        node->expression_->accept(*this);
    } else {
        std::cout << getIndent() << "Expression to Return: (None)\n";
    }
    indent_level_--;
}

void PrintVisitor::visit(ast::RaiseStatementNode* node) {
    std::cout << getIndent() << "RAISE_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Message to Raise:\n";
    node->message_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::TryStatementNode* node) {
    std::cout << getIndent() << "TRY_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Try Body:\n";
    node->try_body_->accept(*this);
    // TODO: Add logic to visit catch/finally blocks if implemented
    indent_level_--;
}

void PrintVisitor::visit(ast::WhileStatementNode* node) {
    std::cout << getIndent() << "WHILE_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    indent_level_++;
    std::cout << getIndent() << "Condition:\n";
    node->condition_->accept(*this);
    std::cout << getIndent() << "Body:\n";
    node->body_->accept(*this);
    indent_level_--;
}

void PrintVisitor::visit(ast::PassStatementNode* node) {
    std::cout << getIndent() << "PASS_STATEMENT (L" << node->getLine() << ", C" << node->getColumn() << ")\n";
    // Pass statements have no children.
}

} // namespace visitors
} // namespace qps
