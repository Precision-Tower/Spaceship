#include "../h/interpreter.hpp"
#include "../h/symbol_resolver.hpp"
#include "../h/geometry_action_resolver.hpp"
#include "../h/host_actions.hpp"

#include "../../ast/ast_node.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace qps {
namespace runtime {

namespace {

struct ReturnSignal {
    explicit ReturnSignal(
        RuntimeValue returned_value)
        : value(std::move(returned_value)) {}

    RuntimeValue value;
};

std::string numberToString(double value) {
    std::ostringstream out;
    out << value;
    return out.str();
}

struct FunctionParameterSpec {
    std::string name;
    const ast::ItemDeclarationNode* item = nullptr;
};

std::string functionNameForError(
    const std::string& name) {

    return name.empty()
        ? "<anonymous>"
        : name;
}

std::vector<FunctionParameterSpec>
collectParameterSpecs(
    const ast::FunctionDeclarationNode& function) {

    if (!function.params_node_) {
        throw std::runtime_error(
            "Function '" +
            function.name_ +
            "' has no parameter list.");
    }

    auto* params =
        dynamic_cast<const ast::ContainerNode*>(
            function.params_node_.get());

    if (!params) {
        throw std::runtime_error(
            "Function '" +
            function.name_ +
            "' parameter list must be a QPS container.");
    }

    std::vector<FunctionParameterSpec> specs;
    std::unordered_set<std::string> seen;

    for (const auto& element :
         params->elements) {

        auto* item =
            dynamic_cast<
                const ast::ItemDeclarationNode*>(
                    element.get());

        if (!item) {
            throw std::runtime_error(
                "Function '" +
                function.name_ +
                "' parameters must use Item declaration syntax.");
        }

        auto* target =
            dynamic_cast<
                const ast::IdentifierNode*>(
                    item->getTarget());

        if (!target) {
            throw std::runtime_error(
                "Function '" +
                function.name_ +
                "' parameter targets must be local identifiers.");
        }

        if (item->value_node_) {
            throw std::runtime_error(
                "Function parameter defaults are not implemented for '" +
                target->name_ +
                "' in function '" +
                function.name_ +
                "'.");
        }

        if (!seen.insert(
                target->name_).second) {

            throw std::runtime_error(
                "Duplicate function parameter '" +
                target->name_ +
                "' in function '" +
                function.name_ +
                "'.");
        }

        FunctionParameterSpec spec;
        spec.name = target->name_;
        spec.item = item;

        specs.push_back(spec);
    }

    return specs;
}

} // namespace

Interpreter::Interpreter(
    ExecutionScope& scope)
    : scope_(scope) {}

Interpreter::Interpreter(
    ExecutionScope& scope,
    FunctionTable functions)
    : scope_(scope),
      functions_(std::move(functions)) {}

Interpreter::Interpreter(
    ExecutionScope& scope,
    FunctionTable functions,
    InterpreterOptions options)
    : scope_(scope),
      functions_(std::move(functions)),
      options_(std::move(options)) {}

Interpreter::Interpreter(
    ExecutionScope& scope,
    FunctionTable functions,
    std::vector<std::string> active_functions,
    std::string current_function)
    : scope_(scope),
      functions_(std::move(functions)),
      active_functions_(
          std::move(active_functions)),
      current_function_(
          std::move(current_function)) {}

void Interpreter::registerFunction(
    const ast::FunctionDeclarationNode&
        function) {

    if (functions_.find(function.name_) !=
        functions_.end()) {

        throw std::runtime_error(
            "Duplicate function declaration '" +
            function.name_ +
            "'.");
    }

    (void)collectParameterSpecs(function);

    if (!function.body_) {
        throw std::runtime_error(
            "Function '" +
            function.name_ +
            "' has no body.");
    }

    functions_.emplace(
        function.name_,
        &function);
}

void Interpreter::executeProgram(
    const ast::ProgramNode& program) {

    for (const auto& statement :
         program.statements) {

        if (auto* function =
                dynamic_cast<
                    const ast::FunctionDeclarationNode*>(
                        statement.get())) {

            registerFunction(*function);
        }
    }

    for (const auto& statement :
         program.statements) {

        if (dynamic_cast<
                const ast::FunctionDeclarationNode*>(
                    statement.get())) {
            continue;
        }

        if (auto* block =
                dynamic_cast<
                    const ast::ExecutionBlockNode*>(
                        statement.get())) {

            execute(*block);
            continue;
        }

        executeLocatedStatement(*statement);
    }
}

void Interpreter::execute(
    const ast::ExecutionBlockNode& block) {

    for (const auto& statement :
         block.statements) {

        executeLocatedStatement(*statement);
    }
}

std::optional<RuntimeValue>
Interpreter::executeForResult(
    const ast::ExecutionBlockNode& block,
    bool skip_item_declarations) {

    try {
        for (const auto& statement :
             block.statements) {

            if (skip_item_declarations &&
                dynamic_cast<
                    const ast::ItemDeclarationNode*>(
                        statement.get())) {
                continue;
            }

            executeLocatedStatement(*statement);
        }
    } catch (const ReturnSignal& returned) {
        return returned.value;
    }

    return std::nullopt;
}

void Interpreter::executeLocatedStatement(
    const ast::AstNode& statement) {

    try {
        executeStatement(statement);
    } catch (const RuntimeDiagnostic&) {
        throw;
    } catch (const std::exception& e) {
        throw ExecutionError(
            e.what(),
            statement.getLine(),
            statement.getColumn());
    }
}

void Interpreter::executeStatement(
    const ast::AstNode& statement) {

    if (auto* item =
            dynamic_cast<
                const ast::ItemDeclarationNode*>(
                    &statement)) {

        executeItem(*item);
        return;
    }

    if (auto* calculation =
            dynamic_cast<
                const ast::CalculationNode*>(
                    &statement)) {

        executeCalculation(*calculation);
        return;
    }

    if (auto* if_statement =
            dynamic_cast<
                const ast::IfStatementNode*>(
                    &statement)) {

        executeIf(*if_statement);
        return;
    }

    if (auto* assert_statement =
            dynamic_cast<
                const ast::AssertStatementNode*>(
                    &statement)) {

        executeAssert(*assert_statement);
        return;
    }

    if (auto* fail_statement =
            dynamic_cast<
                const ast::FailStatementNode*>(
                    &statement)) {

        executeFail(*fail_statement);
        return;
    }

    if (auto* raises_statement =
            dynamic_cast<
                const ast::RaisesStatementNode*>(
                    &statement)) {

        executeRaises(*raises_statement);
        return;
    }

    if (auto* term =
            dynamic_cast<
                const ast::TermDeclarationNode*>(
                    &statement)) {

        // Structural bindings belong to the shared execution workspace
        // and are independent of any execution domain.
        if (term->content_.size() == 1 &&
            dynamic_cast<
                const ast::SymbolReferenceNode*>(
                    term->content_.front().get())) {

            executeStructuralBinding(*term);
            return;
        }

        // Statement-level '@' qualification is the authority for
        // geometry inside a shared execution definition.
        //
        // Whole-definition GEOMETRY remains supported for legacy
        // {@foo: ...} definitions.
        if (term->geometry_qualified_ ||
            options_.domain ==
                ast::ExecutionDomain::GEOMETRY) {

            executeGeometryFeature(*term);
            return;
        }

        if (term->content_.size() == 1) {
            if (auto* action =
                    dynamic_cast<
                        const ast::ExecutionActionNode*>(
                            term->content_.front().get())) {

                const HostActionResult result =
                    executeHostAction(*action);

                scope_.bind(
                    term->identifier_ + "_exit_code",
                    RuntimeValue::numeric(
                        static_cast<double>(
                            result.exit_code)),
                    std::nullopt,
                    BindingOrigin::LOCAL);

                scope_.bind(
                    term->identifier_ + "_stdout",
                    RuntimeValue::string(
                        result.stdout_text),
                    std::nullopt,
                    BindingOrigin::LOCAL);

                scope_.bind(
                    term->identifier_ + "_stderr",
                    RuntimeValue::string(
                        result.stderr_text),
                    std::nullopt,
                    BindingOrigin::LOCAL);

                if (result.value.has_value()) {
                    scope_.bind(
                        term->identifier_,
                        *result.value,
                        std::nullopt,
                        BindingOrigin::LOCAL);
                }

                return;
            }
        }

        throw std::runtime_error(
            "Unqualified execution Term '" +
            term->identifier_ +
            "' has no runtime domain.");
    }

    if (auto* action =
            dynamic_cast<
                const ast::ExecutionActionNode*>(
                    &statement)) {

        if (options_.domain ==
            ast::ExecutionDomain::GEOMETRY) {

            (void)executeGeometryAction(
                *action,
                std::nullopt);

            return;
        }

        if (options_.domain ==
            ast::ExecutionDomain::GENERIC) {

            (void)executeHostAction(*action);
            return;
        }

        throw std::runtime_error(
            "Execution action '-" +
            action->action_name_ +
            "' has no runtime dispatcher.");
    }

    if (dynamic_cast<const ast::PassStatementNode*>(&statement)) {
        return;
    }

    if (auto* return_statement =
            dynamic_cast<
                const ast::ReturnStatementNode*>(
                    &statement)) {

        if (current_function_.empty() &&
            !options_.allow_return) {

            throw std::runtime_error(
                "Return statement outside function or return-capable execution definition.");
        }

        throw ReturnSignal(
            evaluateReturn(
                *return_statement));
    }

    throw std::runtime_error(
        "Interpreter does not yet support AST node type in execution block.");
}

void Interpreter::executeIf(
    const ast::IfStatementNode& statement) {

    if (!statement.condition_) {
        throw std::runtime_error(
            "If statement requires a condition.");
    }

    if (!statement.body_) {
        throw std::runtime_error(
            "If statement requires a body.");
    }

    if (evaluateTruth(*statement.condition_)) {
        execute(*statement.body_);
        return;
    }

    if (statement.else_block_) {
        if (!statement.else_block_->body_) {
            throw std::runtime_error(
                "Else statement requires a body.");
        }

        execute(*statement.else_block_->body_);
    }
}

void Interpreter::executeAssert(
    const ast::AssertStatementNode& statement) const {

    if (!statement.condition_) {
        throw std::runtime_error(
            "Assert statement requires a condition.");
    }

    if (evaluateTruth(*statement.condition_)) {
        return;
    }

    throw AssertionFailure(
        "assertion failed",
        statement.getLine(),
        statement.getColumn());
}

void Interpreter::executeFail(
    const ast::FailStatementNode& statement) const {

    std::string message = evaluateMessage(statement.message_.get());

    if (message.empty()) {
        message = "explicit test failure";
    }

    throw AssertionFailure(
        message,
        statement.getLine(),
        statement.getColumn());
}

void Interpreter::executeRaises(
    const ast::RaisesStatementNode& statement) {

    if (!statement.body_) {
        throw std::runtime_error(
            "Raises statement requires a body.");
    }

    try {
        execute(*statement.body_);
    } catch (const AssertionFailure&) {
        throw;
    } catch (const RuntimeDiagnostic& e) {
        const std::string message = e.what();

        if (message.find(statement.expected_message_) !=
            std::string::npos) {
            return;
        }

        throw AssertionFailure(
            "expected error containing \"" +
            statement.expected_message_ +
            "\"; got \"" +
            message +
            "\"",
            statement.getLine(),
            statement.getColumn());
    } catch (const std::exception& e) {
        const std::string message = e.what();

        if (message.find(statement.expected_message_) !=
            std::string::npos) {
            return;
        }

        throw AssertionFailure(
            "expected error containing \"" +
            statement.expected_message_ +
            "\"; got \"" +
            message +
            "\"",
            statement.getLine(),
            statement.getColumn());
    }

    throw AssertionFailure(
        "expected error containing \"" +
        statement.expected_message_ +
        "\"; no error was raised",
        statement.getLine(),
        statement.getColumn());
}

void Interpreter::executeItem(
    const ast::ItemDeclarationNode& item) {

    if (!item.getTarget()) {
        throw std::runtime_error(
            "Item binding has no target.");
    }

    if (!item.value_node_) {
        throw std::runtime_error(
            "Item binding has no value.");
    }

    RuntimeValue value =
        evaluateValue(*item.value_node_);

    bindTarget(
        *item.getTarget(),
        std::move(value),
        false);
}

void Interpreter::executeCalculation(
    const ast::CalculationNode&
        calculation) {

    if (!calculation.getTarget()) {
        throw std::runtime_error(
            "Calculation has no target.");
    }

    if (!calculation.getExpression()) {
        throw std::runtime_error(
            "Calculation has no expression.");
    }

    const double value =
        evaluate(
            *calculation.getExpression());

    bindTarget(
        *calculation.getTarget(),
        value,
        true);
}

void Interpreter::executeStructuralBinding(
    const ast::TermDeclarationNode& term) {

    if (term.content_.size() != 1) {
        throw std::runtime_error(
            "Structural binding '" +
            term.identifier_ +
            "' must contain exactly one structural reference.");
    }

    auto* reference =
        dynamic_cast<
            const ast::SymbolReferenceNode*>(
                term.content_.front().get());

    if (!reference) {
        throw std::runtime_error(
            "Structural binding '" +
            term.identifier_ +
            "' does not contain a structural reference.");
    }

    if (options_.symbol_resolver == nullptr) {
        throw std::runtime_error(
            "Structural binding '" +
            term.identifier_ +
            "' requires a SymbolResolver.");
    }

    if (reference->getOrigin() ==
        ast::SymbolReferenceOrigin::LOCAL_BINDING) {

        const auto& segments =
            reference->getSegments();

        if (segments.empty()) {
            throw std::runtime_error(
                "Local structural binding '" +
                term.identifier_ +
                "' has no root binding name.");
        }

        const std::string& root_name =
            segments.front().name;

        if (!scope_.contains(root_name)) {
            throw std::runtime_error(
                "Unknown local structural binding '" +
                root_name +
                "' while evaluating '" +
                term.identifier_ +
                "'.");
        }

        const auto& root_binding =
            scope_.get(root_name);

        const ResolvedSymbol& root =
            root_binding.value.asStructure(
                "Local structural binding '" +
                root_name +
                "'");

        ResolvedSymbol resolved =
            options_.symbol_resolver->resolveFrom(
                root,
                *reference);

        scope_.bind(
            term.identifier_,
            RuntimeValue::structure(
                std::move(resolved)),
            reference->getSymbol(),
            BindingOrigin::LOCAL);

        return;
    }

    if (options_.current_document.empty()) {
        throw std::runtime_error(
            "Structural binding '" +
            term.identifier_ +
            "' requires current document context.");
    }

    ResolvedSymbol resolved =
        options_.symbol_resolver->resolve(
            *reference,
            StructuralReferenceContext{
                options_.current_document
            });

    scope_.bind(
        term.identifier_,
        RuntimeValue::structure(
            std::move(resolved)),
        reference->getSymbol(),
        BindingOrigin::LOCAL);
}

void Interpreter::executeGeometryFeature(
    const ast::TermDeclarationNode& term) {

    if (term.content_.size() != 1) {
        throw std::runtime_error(
            "GEOMETRY feature stage '" +
            term.identifier_ +
            "' must contain exactly one execution action.");
    }

    auto* action =
        dynamic_cast<
            const ast::ExecutionActionNode*>(
                term.content_.front().get());

    if (!action) {
        throw std::runtime_error(
            "GEOMETRY feature stage '" +
            term.identifier_ +
            "' does not contain an execution action.");
    }

    RuntimeValue result =
        executeGeometryAction(
            *action,
            term.identifier_);

    scope_.bind(
        term.identifier_,
        std::move(result),
        std::nullopt,
        BindingOrigin::LOCAL);
}

HostActionResult Interpreter::executeHostAction(
    const ast::ExecutionActionNode& action) {

    HostActionInvocation invocation;
    invocation.action_name =
        action.action_name_;

    if (action.getParameters()) {
        for (const auto& element :
             action.getParameters()->elements) {

            auto* item =
                dynamic_cast<
                    const ast::ItemDeclarationNode*>(
                        element.get());

            if (!item) {
                throw std::runtime_error(
                    "Host action parameter must use Item syntax.");
            }

            auto* target =
                dynamic_cast<
                    const ast::IdentifierNode*>(
                        item->getTarget());

            if (!target) {
                throw std::runtime_error(
                    "Host action parameter target must be a local Item identifier.");
            }

            if (!item->value_node_) {
                throw std::runtime_error(
                    "Host action parameter '" +
                    target->name_ +
                    "' has no value.");
            }

            if (invocation.parameters.find(
                    target->name_) !=
                invocation.parameters.end()) {

                throw std::runtime_error(
                    "Duplicate host action parameter '" +
                    target->name_ +
                    "'.");
            }

            invocation.parameters.emplace(
                target->name_,
                evaluateValue(
                    *item->value_node_));
        }
    }

    HostActionDispatcher host;
    return host.execute(invocation);
}

RuntimeValue
Interpreter::executeGeometryAction(
    const ast::ExecutionActionNode& action,
    const std::optional<std::string>&
        result_stage_name) {

    // Geometry action validity is established by its enclosing
    // statement qualification or by legacy whole-definition GEOMETRY
    // dispatch before this function is called.

    if (options_.geometry_dispatcher ==
        nullptr) {

        throw std::runtime_error(
            "GEOMETRY execution has no action dispatcher.");
    }

    GeometryActionInvocation invocation;

    invocation.action_name =
        action.action_name_;

    invocation.active_target =
        options_.active_target;

    invocation.result_stage_name =
        result_stage_name;

    invocation.scope =
        &scope_;

    if (action.getSource()) {
        auto* source =
            dynamic_cast<
                const ast::IdentifierNode*>(
                    action.getSource());

        if (!source) {
            throw std::runtime_error(
                "GEOMETRY action source must be a named feature stage.");
        }

        if (!scope_.contains(
                source->name_)) {

            throw std::runtime_error(
                "Unknown GEOMETRY source stage '" +
                source->name_ +
                "'.");
        }

        invocation.source_stage_name =
            source->name_;

        invocation.source_geometry =
            scope_
                .get(source->name_)
                .value
                .asGeometry(
                    "GEOMETRY source stage '" +
                    source->name_ +
                    "'");
    }

    if (action.getParameters()) {
        for (const auto& element :
             action.getParameters()->elements) {

            if (auto* identifier =
                    dynamic_cast<
                        const ast::IdentifierNode*>(
                            element.get())) {

                if (!scope_.contains(identifier->name_)) {
                    throw std::runtime_error(
                        "Unknown GEOMETRY structural argument '" +
                        identifier->name_ +
                        "'.");
                }

                invocation.structural_arguments.push_back(
                    scope_
                        .get(identifier->name_)
                        .value
                        .asStructure(
                            "GEOMETRY structural argument '" +
                            identifier->name_ +
                            "'"));

                continue;
            }

            auto* item =
                dynamic_cast<
                    const ast::ItemDeclarationNode*>(
                        element.get());

            if (!item) {
                throw std::runtime_error(
                    "GEOMETRY action parameter must be a structural binding or use Item syntax.");
            }

            auto* target =
                dynamic_cast<
                    const ast::IdentifierNode*>(
                        item->getTarget());

            if (!target) {
                throw std::runtime_error(
                    "GEOMETRY action parameter target must be a local Item identifier.");
            }

            if (!item->value_node_) {
                throw std::runtime_error(
                    "GEOMETRY action override '" +
                    target->name_ +
                    "' has no value.");
            }

            if (invocation.explicit_parameters.find(
                    target->name_) !=
                invocation.explicit_parameters.end()) {

                throw std::runtime_error(
                    "Duplicate GEOMETRY action override '" +
                    target->name_ +
                    "'.");
            }

            invocation.explicit_parameters.emplace(
                target->name_,
                RuntimeValue::numeric(
                    evaluate(
                        *item->value_node_)));
        }
    }

    GeometryActionResolver resolver;

    const ResolvedGeometryAction resolved =
        resolver.resolve(invocation);

    RuntimeValue result =
        options_
            .geometry_dispatcher
            ->invoke(resolved);

    if (!result.isGeometry()) {
        throw std::runtime_error(
            "GEOMETRY action '-" +
            action.action_name_ +
            "' returned a non-geometry value.");
    }

    return result;
}

RuntimeValue Interpreter::evaluateValue(
    const ast::AstNode& node) const {

    if (auto* string =
            dynamic_cast<
                const ast::StringLiteralNode*>(
                    &node)) {

        return RuntimeValue::string(
            string->value_);
    }

    if (auto* identifier =
            dynamic_cast<
                const ast::IdentifierNode*>(
                    &node)) {

        return scope_
            .get(identifier->name_)
            .value;
    }

    if (auto* binary =
            dynamic_cast<
                const ast::BinaryExpressionNode*>(
                    &node)) {

        if (binary->getOperator() ==
            ast::BinaryExpressionNode::Operator::ADD) {

            const RuntimeValue left =
                evaluateValue(
                    *binary->getLeft());

            const RuntimeValue right =
                evaluateValue(
                    *binary->getRight());

            if (left.isNumeric() &&
                right.isNumeric()) {

                return RuntimeValue::numeric(
                    left.asNumber("addition left") +
                    right.asNumber("addition right"));
            }

            if (left.isString() &&
                right.isString()) {

                return RuntimeValue::string(
                    left.asString("addition left") +
                    right.asString("addition right"));
            }

            throw std::runtime_error(
                "Runtime addition requires matching NUMERIC or STRING values.");
        }
    }

    if (auto* path =
            dynamic_cast<
                const ast::PathReferenceNode*>(
                    &node)) {

        const auto& segments =
            path->getPathSegments();

        if (segments.size() == 1) {
            return scope_
                .get(segments.front())
                .value;
        }
    }

    return RuntimeValue::numeric(
        evaluate(node));
}

double Interpreter::evaluate(
    const ast::AstNode& node) const {

    if (auto* numeric =
            dynamic_cast<
                const ast::NumericLiteralNode*>(
                    &node)) {

        return numeric->value_;
    }

    if (auto* identifier =
            dynamic_cast<
                const ast::IdentifierNode*>(
                    &node)) {

        return scope_
            .get(identifier->name_)
            .value
            .asNumber(
                "Identifier '" +
                identifier->name_ +
                "'");
    }

    if (auto* call =
            dynamic_cast<
                const ast::FunctionCallNode*>(
                    &node)) {

        return invokeFunction(*call);
    }

    if (auto* binary =
            dynamic_cast<
                const ast::BinaryExpressionNode*>(
                    &node)) {

        const double left =
            evaluate(
                *binary->getLeft());

        const double right =
            evaluate(
                *binary->getRight());

        switch (
            binary->getOperator()) {

            case ast::BinaryExpressionNode::
                Operator::ADD:

                return left + right;

            case ast::BinaryExpressionNode::
                Operator::SUBTRACT:

                return left - right;

            case ast::BinaryExpressionNode::
                Operator::MULTIPLY:

                return left * right;

            case ast::BinaryExpressionNode::
                Operator::DIVIDE:

                if (right == 0.0) {
                    throw std::runtime_error(
                        "Division by zero.");
                }

                return left / right;

            case ast::BinaryExpressionNode::
                Operator::EQUAL:

                throw std::runtime_error(
                    "Equality comparison is boolean and cannot be evaluated as numeric.");
        }
    }

    if (auto* reference =
            dynamic_cast<
                const ast::SymbolReferenceNode*>(
                    &node)) {

        if (!reference->selectsItemValue()) {
            throw std::runtime_error(
                "Structural semantic reference '" +
                reference->getSymbol() +
                "' cannot be used as a numeric operand. "
                "Select an Item value with '-'.");
        }

        if (options_.symbol_resolver == nullptr) {
            throw std::runtime_error(
                "Semantic Item-value reference '" +
                reference->getSymbol() +
                "' requires a SymbolResolver.");
        }

        ResolvedSymbol resolved;

        if (reference->getOrigin() ==
            ast::SymbolReferenceOrigin::LOCAL_BINDING) {

            const auto& segments =
                reference->getSegments();

            if (segments.empty()) {
                throw std::runtime_error(
                    "Local semantic Item-value reference '" +
                    reference->getSymbol() +
                    "' has no root binding.");
            }

            const std::string& root_name =
                segments.front().name;

            if (!scope_.contains(root_name)) {
                throw std::runtime_error(
                    "Unknown local structural binding '" +
                    root_name +
                    "' while evaluating Item value '" +
                    reference->getSymbol() +
                    "'.");
            }

            const ResolvedSymbol& root =
                scope_
                    .get(root_name)
                    .value
                    .asStructure(
                        "Local structural binding '" +
                        root_name +
                        "'");

            resolved =
                options_.symbol_resolver->resolveFrom(
                    root,
                    *reference);
        }
        else {
            if (options_.current_document.empty()) {
                throw std::runtime_error(
                    "Semantic Item-value reference '" +
                    reference->getSymbol() +
                    "' requires current document context.");
            }

            resolved =
                options_.symbol_resolver->resolve(
                    *reference,
                    StructuralReferenceContext{
                        options_.current_document
                    });
        }

        auto* item =
            dynamic_cast<
                ast::ItemDeclarationNode*>(
                    resolved.target_node);

        if (!item) {
            throw std::runtime_error(
                "Semantic Item-value reference '" +
                reference->getSymbol() +
                "' did not resolve to an Item.");
        }

        if (!item->value_node_) {
            throw std::runtime_error(
                "Semantic Item-value reference '" +
                reference->getSymbol() +
                "' resolved to an Item with no value.");
        }

        return evaluate(
            *item->value_node_);
    }

    throw std::runtime_error(
        "Unsupported expression node in numeric evaluator.");
}

RuntimeValue Interpreter::evaluateReturn(
    const ast::ReturnStatementNode&
        statement) const {

    const std::string execution_name =
        current_function_.empty()
            ? options_.active_target
            : functionNameForError(
                current_function_);

    if (!statement.expression_) {
        throw std::runtime_error(
            "Execution '" +
            execution_name +
            "' return statement requires a value.");
    }

    if (auto* identifier =
            dynamic_cast<
                const ast::IdentifierNode*>(
                    statement.expression_.get())) {

        if (!scope_.contains(identifier->name_)) {
            throw std::runtime_error(
                "Undefined return identifier '" +
                identifier->name_ +
                "' in execution '" +
                execution_name +
                "'.");
        }
    }

    return evaluateValue(
        *statement.expression_);
}

double Interpreter::invokeFunction(
    const ast::FunctionCallNode& call) const {

    auto found =
        functions_.find(call.name_);

    if (found == functions_.end()) {
        throw std::runtime_error(
            "Undefined function '" +
            call.name_ +
            "'.");
    }

    if (std::find(
            active_functions_.begin(),
            active_functions_.end(),
            call.name_) !=
        active_functions_.end()) {

        throw std::runtime_error(
            "Recursive function calls are not implemented for function '" +
            call.name_ +
            "'.");
    }

    const auto& function =
        *found->second;

    const auto parameters =
        collectParameterSpecs(function);

    if (call.arguments_.size() <
        parameters.size()) {

        throw std::runtime_error(
            "Too few arguments for function '" +
            call.name_ +
            "': expected " +
            std::to_string(
                parameters.size()) +
            ", got " +
            std::to_string(
                call.arguments_.size()) +
            ".");
    }

    if (call.arguments_.size() >
        parameters.size()) {

        throw std::runtime_error(
            "Too many arguments for function '" +
            call.name_ +
            "': expected " +
            std::to_string(
                parameters.size()) +
            ", got " +
            std::to_string(
                call.arguments_.size()) +
            ".");
    }

    std::vector<double> argument_values;

    argument_values.reserve(
        call.arguments_.size());

    for (const auto& argument :
         call.arguments_) {

        argument_values.push_back(
            evaluate(*argument));
    }

    ExecutionScope function_scope;

    for (std::size_t i = 0;
         i < parameters.size();
         ++i) {

        function_scope.bind(
            parameters[i].name,
            argument_values[i],
            std::nullopt,
            BindingOrigin::SUPPLIED);
    }

    auto active_functions =
        active_functions_;

    active_functions.push_back(
        call.name_);

    Interpreter interpreter(
        function_scope,
        functions_,
        std::move(active_functions),
        call.name_);

    try {
        interpreter.execute(
            *function.body_);

    } catch (const ReturnSignal& returned) {

        return returned.value.asNumber(
            "Function '" +
            call.name_ +
            "' return value");
    }

    throw std::runtime_error(
        "Function '" +
        call.name_ +
        "' completed without return.");
}

bool Interpreter::evaluateTruth(
    const ast::AstNode& node) const {

    if (auto* boolean =
            dynamic_cast<
                const ast::BooleanLiteralNode*>(
                    &node)) {

        return boolean->value_;
    }

    if (auto* binary =
            dynamic_cast<
                const ast::BinaryExpressionNode*>(
                    &node)) {

        if (binary->getOperator() ==
            ast::BinaryExpressionNode::Operator::EQUAL) {

            const RuntimeValue left =
                evaluateValue(*binary->getLeft());

            const RuntimeValue right =
                evaluateValue(*binary->getRight());

            if (left.kind() != right.kind()) {
                return false;
            }

            if (left.kind() ==
                RuntimeValue::Kind::NUMERIC) {

                return std::fabs(
                    left.asNumber("equality left") -
                    right.asNumber("equality right")) <=
                    0.000000001;
            }

            if (left.kind() ==
                RuntimeValue::Kind::STRING) {

                return left.asString("equality left") ==
                    right.asString("equality right");
            }

            throw std::runtime_error(
                "Equality is not defined for this runtime value kind.");
        }
    }

    throw std::runtime_error(
        "Condition must be a boolean literal or supported equality expression.");
}

std::string Interpreter::evaluateMessage(
    const ast::AstNode* node) const {

    if (node == nullptr) {
        return "";
    }

    if (auto* string = dynamic_cast<const ast::StringLiteralNode*>(node)) {
        return string->value_;
    }

    if (auto* numeric = dynamic_cast<const ast::NumericLiteralNode*>(node)) {
        return numberToString(numeric->value_);
    }

    if (auto* boolean = dynamic_cast<const ast::BooleanLiteralNode*>(node)) {
        return boolean->value_ ? "true" : "false";
    }

    if (dynamic_cast<const ast::NullLiteralNode*>(node)) {
        return "null";
    }

    return numberToString(evaluate(*node));
}

void Interpreter::bindTarget(
    const ast::AstNode& target,
    double value,
    bool derived) {

    bindTarget(
        target,
        RuntimeValue::numeric(value),
        derived);
}

void Interpreter::bindTarget(
    const ast::AstNode& target,
    RuntimeValue value,
    bool derived) {

    if (auto* identifier =
            dynamic_cast<
                const ast::IdentifierNode*>(
                    &target)) {

        scope_.bind(
            identifier->name_,
            std::move(value),
            std::nullopt,
            BindingOrigin::LOCAL);

        return;
    }

    if (auto* semantic =
            dynamic_cast<
                const ast::SymbolReferenceNode*>(
                    &target)) {

        const std::string& symbol =
            semantic->getSymbol();

        scope_.bind(
            symbol,
            std::move(value),
            symbol,
            derived
                ? BindingOrigin::DERIVED
                : BindingOrigin::SUPPLIED);

        return;
    }

    throw std::runtime_error(
        "Unsupported execution binding target.");
}

} // namespace runtime
} // namespace qps
