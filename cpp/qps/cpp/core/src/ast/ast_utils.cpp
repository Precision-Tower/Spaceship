// qps/core/src/ast/ast_utils.cpp

#include "ast_utils.hpp"
#include <iostream>

#include <utility>


namespace qps {
namespace ast {

// --- Factory functions for creating AST Nodes using unique_ptr ---
// These functions will be the primary way to construct AST nodes from the parser.
// Their implementations are now in the modular .cpp files (e.g., c/declarations.cpp)

std::unique_ptr<ProgramNode> createProgramNode(int line, int column) {
    return std::make_unique<ProgramNode>(line, column);
}

std::unique_ptr<ItemDeclarationNode> createItemDeclarationNode(
    std::unique_ptr<AstNode> target,
    int line,
    int column) {

    return std::make_unique<ItemDeclarationNode>(
        std::move(target),
        line,
        column);
}

std::unique_ptr<StringLiteralNode> createStringLiteralNode(const std::string& value, int line, int column) {
    return std::make_unique<StringLiteralNode>(value, line, column);
}

std::unique_ptr<NumericLiteralNode> createNumericLiteralNode(double value, int line, int column) {
    return std::make_unique<NumericLiteralNode>(value, line, column);
}

std::unique_ptr<BooleanLiteralNode> createBooleanLiteralNode(bool value, int line, int column) {
    return std::make_unique<BooleanLiteralNode>(value, line, column);
}

std::unique_ptr<NullLiteralNode> createNullLiteralNode(int line, int column) {
    return std::make_unique<NullLiteralNode>(line, column);
}

std::unique_ptr<PathReferenceNode> createPathReferenceNode(const std::string& path, int line, int column) {
    return std::make_unique<PathReferenceNode>(path, line, column);
}


std::unique_ptr<SymbolReferenceNode> createSymbolReferenceNode(
    const std::string& symbol,
    SymbolReferenceOrigin origin,
    int parent_depth,
    std::vector<SymbolReferenceSegment> segments,
    bool selects_item_value,
    int line,
    int column) {

    return std::make_unique<SymbolReferenceNode>(
        symbol,
        origin,
        parent_depth,
        std::move(segments),
        selects_item_value,
        line,
        column);
}


std::unique_ptr<IdentifierNode> createIdentifierNode(const std::string& name, int line, int column) {
    return std::make_unique<IdentifierNode>(name, line, column);
}

std::unique_ptr<FunctionCallNode> createFunctionCallNode(
    const std::string& name,
    int line,
    int column) {
    return std::make_unique<FunctionCallNode>(name, line, column);
}

std::unique_ptr<TermDeclarationNode> createTermDeclarationNode(const std::string& identifier, int line, int column) {
    return std::make_unique<TermDeclarationNode>(identifier, line, column);
}

std::unique_ptr<KeyDeclarationNode> createKeyDeclarationNode(const std::string& identifier, int line, int column) {
    return std::make_unique<KeyDeclarationNode>(identifier, line, column);
}

std::unique_ptr<ContainerNode> createContainerNode(int line, int column) {
    return std::make_unique<ContainerNode>(line, column);
}

std::unique_ptr<DictionaryEntryNode> createDictionaryEntryNode(int id, int line, int column) {
    return std::make_unique<DictionaryEntryNode>(id, line, column);
}

std::unique_ptr<DictionaryDeclarationNode> createDictionaryDeclarationNode(int line, int column) {
    return std::make_unique<DictionaryDeclarationNode>(line, column);
}

std::unique_ptr<BinaryExpressionNode> createBinaryExpressionNode(
    std::unique_ptr<AstNode> left, BinaryExpressionNode::Operator op, std::unique_ptr<AstNode> right,
    int line, int column) {
    return std::make_unique<BinaryExpressionNode>(std::move(left), op, std::move(right), line, column);
}

std::unique_ptr<CalculationNode> createCalculationNode(
    std::unique_ptr<AstNode> target,
    std::unique_ptr<AstNode> expression,
    int line, int column) {
    return std::make_unique<CalculationNode>(
        std::move(target),
        std::move(expression),
        line,
        column);
}

std::unique_ptr<ExecutionBlockNode> createExecutionBlockNode(int line, int column) {
    return std::make_unique<ExecutionBlockNode>(line, column);
}

std::unique_ptr<ExecutionDefinitionNode> createExecutionDefinitionNode(
    const std::string& identifier,
    bool identifier_is_numeric,
    ExecutionDomain domain,
    std::unique_ptr<ExecutionBlockNode> body,
    int line,
    int column) {

    return std::make_unique<ExecutionDefinitionNode>(
        identifier,
        identifier_is_numeric,
        domain,
        std::move(body),
        line,
        column);
}

std::unique_ptr<ExecutionCallNode> createExecutionCallNode(
    const std::string& identifier,
    bool identifier_is_numeric,
    int line,
    int column) {

    return std::make_unique<ExecutionCallNode>(
        identifier,
        identifier_is_numeric,
        line,
        column);
}

std::unique_ptr<ExecutionActionNode> createExecutionActionNode(
    const std::string& action_name,
    std::unique_ptr<AstNode> source,
    std::unique_ptr<ContainerNode> parameters,
    int line,
    int column) {

    return std::make_unique<ExecutionActionNode>(
        action_name,
        std::move(source),
        std::move(parameters),
        line,
        column);
}

std::unique_ptr<TestDeclarationNode> createTestDeclarationNode(
    std::unique_ptr<ExecutionBlockNode> body,
    int line,
    int column) {

    return std::make_unique<TestDeclarationNode>(
        std::move(body),
        line,
        column);
}

std::unique_ptr<CausalRelationshipNode::CausalSide> createCausalSide(
    std::unique_ptr<AstNode> entity, std::unique_ptr<AstNode> input, std::unique_ptr<AstNode> output) {
    return std::make_unique<CausalRelationshipNode::CausalSide>(
        CausalRelationshipNode::CausalSide{std::move(entity), std::move(input), std::move(output)});
}

std::unique_ptr<CausalRelationshipNode> createCausalRelationshipNode(
    std::unique_ptr<CausalRelationshipNode::CausalSide> left,
    std::unique_ptr<CausalRelationshipNode::CausalSide> right,
    int line, int column) {
    return std::make_unique<CausalRelationshipNode>(std::move(left), std::move(right), line, column);
}

std::unique_ptr<ClassDeclarationNode> createClassDeclarationNode(const std::string& name, int line, int column) {
    return std::make_unique<ClassDeclarationNode>(name, line, column);
}

std::unique_ptr<FunctionDeclarationNode> createFunctionDeclarationNode(
    const std::string& name, std::unique_ptr<AstNode> params_node,
    std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<FunctionDeclarationNode>(name, std::move(params_node), std::move(body), line, column);
}

std::unique_ptr<LetStatementNode> createLetStatementNode(
    const std::string& identifier, std::unique_ptr<AstNode> initial_value, int line, int column) {
    auto node = std::make_unique<LetStatementNode>(identifier, line, column);
    node->initial_value_ = std::move(initial_value);
    return node;
}

std::unique_ptr<SetStatementNode> createSetStatementNode(
    std::unique_ptr<AstNode> target, std::unique_ptr<AstNode> value, int line, int column) {
    return std::make_unique<SetStatementNode>(std::move(target), std::move(value), line, column);
}

std::unique_ptr<AssertStatementNode> createAssertStatementNode(
    std::unique_ptr<AstNode> condition, int line, int column) {
    return std::make_unique<AssertStatementNode>(std::move(condition), line, column);
}

std::unique_ptr<FailStatementNode> createFailStatementNode(
    std::unique_ptr<AstNode> message, int line, int column) {
    return std::make_unique<FailStatementNode>(std::move(message), line, column);
}

std::unique_ptr<RaisesStatementNode> createRaisesStatementNode(
    const std::string& expected_message,
    std::unique_ptr<ExecutionBlockNode> body,
    int line, int column) {
    return std::make_unique<RaisesStatementNode>(expected_message, std::move(body), line, column);
}

std::unique_ptr<BreakStatementNode> createBreakStatementNode(int line, int column) {
    return std::make_unique<BreakStatementNode>(line, column);
}

std::unique_ptr<ContinueStatementNode> createContinueStatementNode(int line, int column) {
    return std::make_unique<ContinueStatementNode>(line, column);
}

std::unique_ptr<ElifStatementNode> createElifStatementNode(
    std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<ElifStatementNode>(std::move(condition), std::move(body), line, column);
}

std::unique_ptr<ElseStatementNode> createElseStatementNode(
    std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<ElseStatementNode>(std::move(body), line, column);
}

std::unique_ptr<ForStatementNode> createForStatementNode(
    std::unique_ptr<AstNode> loop_control, std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<ForStatementNode>(std::move(loop_control), std::move(body), line, column);
}

std::unique_ptr<IfStatementNode> createIfStatementNode(
    std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<IfStatementNode>(std::move(condition), std::move(body), line, column);
}

std::unique_ptr<LoopStatementNode> createLoopStatementNode(
    std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<LoopStatementNode>(std::move(body), line, column);
}

std::unique_ptr<PrintStatementNode> createPrintStatementNode(
    std::unique_ptr<AstNode> expression, int line, int column) {
    return std::make_unique<PrintStatementNode>(std::move(expression), line, column);
}

std::unique_ptr<ReturnStatementNode> createReturnStatementNode(
    std::unique_ptr<AstNode> expression, int line, int column) {
    return std::make_unique<ReturnStatementNode>(std::move(expression), line, column);
}

std::unique_ptr<RaiseStatementNode> createRaiseStatementNode(
    std::unique_ptr<AstNode> message, int line, int column) {
    return std::make_unique<RaiseStatementNode>(std::move(message), line, column);
}

std::unique_ptr<TryStatementNode> createTryStatementNode(
    std::unique_ptr<ExecutionBlockNode> try_body, int line, int column) {
    return std::make_unique<TryStatementNode>(std::move(try_body), line, column);
}

std::unique_ptr<WhileStatementNode> createWhileStatementNode(
    std::unique_ptr<AstNode> condition, std::unique_ptr<ExecutionBlockNode> body, int line, int column) {
    return std::make_unique<WhileStatementNode>(std::move(condition), std::move(body), line, column);
}

std::unique_ptr<PassStatementNode> createPassStatementNode(int line, int column) {
    return std::make_unique<PassStatementNode>(line, column);
}


// --- Other utility functions (example, will be replaced by PrintVisitor) ---

// This function could be used to print a simplified representation of the AST
// for debugging purposes. It's a placeholder for more comprehensive AST traversal.
void printAst(const AstNode* node, int indent_level) {
    if (!node) {
        return;
    }

    std::string indent(indent_level * 2, ' '); // 2 spaces per indent level
    std::cout << indent << "- " << static_cast<int>(node->getType()) << " (L" << node->getLine() << ", C" << node->getColumn() << ")\n";

    // Example of how to iterate through child nodes for specific types
    if (auto program_node = dynamic_cast<const ProgramNode*>(node)) {
        for (const auto& stmt : program_node->statements) {
            printAst(stmt.get(), indent_level + 1);
        }
    } else if (auto item_node = dynamic_cast<const ItemDeclarationNode*>(node)) {
        std::cout << indent << "  Target:\n";
        printAst(item_node->target_.get(), indent_level + 2);
        std::cout << indent << "  Value:\n";
        printAst(item_node->value_node_.get(), indent_level + 2);
    } else if (auto string_node = dynamic_cast<const StringLiteralNode*>(node)) {
        std::cout << indent << "  Value: \"" << string_node->value_ << "\"\n";
    } else if (auto numeric_node = dynamic_cast<const NumericLiteralNode*>(node)) {
        std::cout << indent << "  Value: " << numeric_node->value_ << "\n";
    } else if (auto identifier_node = dynamic_cast<const IdentifierNode*>(node)) {
        std::cout << indent << "  Name: " << identifier_node->name_ << "\n";
    } else if (auto call_node = dynamic_cast<const FunctionCallNode*>(node)) {
        std::cout << indent << "  Function: " << call_node->name_ << "\n";
        std::cout << indent << "  Arguments:\n";

        for (const auto& argument : call_node->arguments_) {
            printAst(argument.get(), indent_level + 2);
        }

    } else if (auto term_node = dynamic_cast<const TermDeclarationNode*>(node)) {
        std::cout << indent << "  Identifier: " << term_node->identifier_ << "\n";
        std::cout << indent << "  Content:\n";
        for (const auto& child : term_node->content_) {
            printAst(child.get(), indent_level + 2);
        }
    } else if (auto key_node = dynamic_cast<const KeyDeclarationNode*>(node)) {
        std::cout << indent << "  Identifier: " << key_node->identifier_ << "\n";
        std::cout << indent << "  Content:\n";
        for (const auto& child : key_node->content_) {
            printAst(child.get(), indent_level + 2);
        }
    } else if (auto container_node = dynamic_cast<const ContainerNode*>(node)) {
        std::cout << indent << "  Elements:\n";
        for (const auto& child : container_node->elements) {
            printAst(child.get(), indent_level + 2);
        }
    } else if (auto dict_decl_node = dynamic_cast<const DictionaryDeclarationNode*>(node)) {
        std::cout << indent << "  Entries:\n";
        for (const auto& entry : dict_decl_node->entries) {
            printAst(entry.get(), indent_level + 2);
        }
    } else if (auto dict_entry_node = dynamic_cast<const DictionaryEntryNode*>(node)) {
        std::cout << indent << "  Entry ID: " << dict_entry_node->id_ << "\n";
        std::cout << indent << "  Value:\n";
        printAst(dict_entry_node->value_node_.get(), indent_level + 2);
    } else if (auto bin_expr_node = dynamic_cast<const BinaryExpressionNode*>(node)) {
        std::cout << indent << "  Operator: ";
        switch(bin_expr_node->getOperator()) {
            case BinaryExpressionNode::Operator::ADD: std::cout << "ADD\n"; break;
            case BinaryExpressionNode::Operator::SUBTRACT: std::cout << "SUBTRACT\n"; break;
            case BinaryExpressionNode::Operator::MULTIPLY: std::cout << "MULTIPLY\n"; break;
            case BinaryExpressionNode::Operator::DIVIDE: std::cout << "DIVIDE\n"; break;
            case BinaryExpressionNode::Operator::EQUAL: std::cout << "EQUAL\n"; break;
        }
        std::cout << indent << "  Left:\n";
        printAst(bin_expr_node->getLeft(), indent_level + 2);
        std::cout << indent << "  Right:\n";
        printAst(bin_expr_node->getRight(), indent_level + 2);
    } else if (auto exec_block_node = dynamic_cast<const ExecutionBlockNode*>(node)) {
        std::cout << indent << "  Statements:\n";
        for (const auto& stmt : exec_block_node->statements) {
            printAst(stmt.get(), indent_level + 2);
        }
    } else if (auto causal_node = dynamic_cast<const CausalRelationshipNode*>(node)) {
        std::cout << indent << "    Left Side:\n";
        printAst(causal_node->left_side_->entity.get(), indent_level + 3);
        std::cout << indent << "      Input:\n";
        printAst(causal_node->left_side_->input.get(), indent_level + 3);
        std::cout << indent << "      Output:\n";
        printAst(causal_node->left_side_->output.get(), indent_level + 3);
        std::cout << indent << "    Right Side:\n";
        printAst(causal_node->right_side_->entity.get(), indent_level + 3);
        std::cout << indent << "      Input:\n";
        printAst(causal_node->right_side_->input.get(), indent_level + 3);
        std::cout << indent << "      Output:\n";
        printAst(causal_node->right_side_->output.get(), indent_level + 3);
    } else if (auto class_node = dynamic_cast<const ClassDeclarationNode*>(node)) {
        std::cout << indent << "  Name: " << class_node->name_ << "\n";
        std::cout << indent << "  Members:\n";
        for (const auto& member : class_node->members) {
            printAst(member.get(), indent_level + 2);
        }
    } else if (auto func_node = dynamic_cast<const FunctionDeclarationNode*>(node)) {
        std::cout << indent << "  Name: " << func_node->name_ << "\n";
        std::cout << indent << "  Parameters:\n";
        printAst(func_node->params_node_.get(), indent_level + 2);
        std::cout << indent << "  Body:\n";
        printAst(func_node->body_.get(), indent_level + 2);
    } else if (auto action_node = dynamic_cast<const ExecutionActionNode*>(node)) {
        std::cout << indent << "  Action: -" << action_node->action_name_ << "\n";
        if (action_node->getSource()) {
            std::cout << indent << "  Source:\n";
            printAst(action_node->getSource(), indent_level + 2);
        }
        if (action_node->getParameters()) {
            std::cout << indent << "  Parameters:\n";
            printAst(action_node->getParameters(), indent_level + 2);
        }
    } else if (auto let_node = dynamic_cast<const LetStatementNode*>(node)) {
        std::cout << indent << "  Identifier: " << let_node->identifier_ << "\n";
        if (let_node->initial_value_) {
            std::cout << indent << "  Initial Value:\n";
            printAst(let_node->initial_value_.get(), indent_level + 2);
        } else {
            std::cout << indent << "  Initial Value: (None)\n";
        }
    } else if (auto set_node = dynamic_cast<const SetStatementNode*>(node)) {
        std::cout << indent << "  Target:\n";
        printAst(set_node->target_.get(), indent_level + 2);
        std::cout << indent << "  Value:\n";
        printAst(set_node->value_.get(), indent_level + 2);
    } else if (auto assert_node = dynamic_cast<const AssertStatementNode*>(node)) {
        std::cout << indent << "  Condition:\n";
        printAst(assert_node->condition_.get(), indent_level + 2);
    } else if (dynamic_cast<const BreakStatementNode*>(node)) {
        std::cout << indent << "  // Break statement\n";
    } else if (dynamic_cast<const ContinueStatementNode*>(node)) {
        std::cout << indent << "  // Continue statement\n";
    } else if (auto elif_node = dynamic_cast<const ElifStatementNode*>(node)) {
        std::cout << indent << "  Condition:\n";
        printAst(elif_node->condition_.get(), indent_level + 2);
        std::cout << indent << "  Body:\n";
        printAst(elif_node->body_.get(), indent_level + 2);
    } else if (auto else_node = dynamic_cast<const ElseStatementNode*>(node)) {
        std::cout << indent << "  Body:\n";
        printAst(else_node->body_.get(), indent_level + 2);
    } else if (auto for_node = dynamic_cast<const ForStatementNode*>(node)) {
        std::cout << indent << "  Loop Control:\n";
        printAst(for_node->loop_control_.get(), indent_level + 2);
        std::cout << indent << "  Body:\n";
        printAst(for_node->body_.get(), indent_level + 2);
    } else if (auto if_node = dynamic_cast<const IfStatementNode*>(node)) {
        std::cout << indent << "  Condition:\n";
        printAst(if_node->condition_.get(), indent_level + 2);
        std::cout << indent << "  Body:\n";
        printAst(if_node->body_.get(), indent_level + 2);
        if (!if_node->elif_blocks_.empty()) {
            std::cout << indent << "  Elif Blocks:\n";
            for (const auto& elif_block : if_node->elif_blocks_) {
                printAst(elif_block.get(), indent_level + 2);
            }
        }
        if (if_node->else_block_) {
            printAst(if_node->else_block_.get(), indent_level + 2);
        }
    } else if (auto loop_node = dynamic_cast<const LoopStatementNode*>(node)) {
        std::cout << indent << "  Body:\n";
        printAst(loop_node->body_.get(), indent_level + 2);
    } else if (auto print_node = dynamic_cast<const PrintStatementNode*>(node)) {
        std::cout << indent << "  Expression to Print:\n";
        printAst(print_node->expression_.get(), indent_level + 2);
    } else if (auto return_node = dynamic_cast<const ReturnStatementNode*>(node)) {
        std::cout << indent << "  Expression to Return:\n";
        if (return_node->expression_) {
            printAst(return_node->expression_.get(), indent_level + 2);
        } else {
            std::cout << indent << "  (None)\n";
        }
    } else if (auto raise_node = dynamic_cast<const RaiseStatementNode*>(node)) {
        std::cout << indent << "  Message to Raise:\n";
        printAst(raise_node->message_.get(), indent_level + 2);
    } else if (auto try_node = dynamic_cast<const TryStatementNode*>(node)) {
        std::cout << indent << "  Try Body:\n";
        printAst(try_node->try_body_.get(), indent_level + 2);
        // Add printing for catch/finally blocks if they are implemented later
    } else if (auto while_node = dynamic_cast<const WhileStatementNode*>(node)) {
        std::cout << indent << "  Condition:\n";
        printAst(while_node->condition_.get(), indent_level + 2);
        std::cout << indent << "  Body:\n";
        printAst(while_node->body_.get(), indent_level + 2);
    } else if (dynamic_cast<const PassStatementNode*>(node)) {
        std::cout << indent << "  // Pass statement (no-op)\n";
    }
    // Add more cases for other node types as they are implemented and need printing.
}

} // namespace ast
} // namespace qps
