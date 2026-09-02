#include "../h/execution_engine.hpp"

#include "../h/interpreter.hpp"
#include "../../ast/ast_node.hpp"

#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace qps {
namespace runtime {

namespace {

struct InputSpec {
    ExecutionInputInfo info;
    const ast::ItemDeclarationNode* item = nullptr;
};

std::vector<InputSpec> collectInputSpecs(
    const ast::ExecutionDefinitionNode& definition) {

    if (!definition.body_) {
        throw std::runtime_error(
            "Execution definition '" +
            definition.identifier_ +
            "' has no body.");
    }

    std::vector<InputSpec> inputs;
    std::unordered_set<std::string> seen;

    for (const auto& statement : definition.body_->statements) {
        if (auto* item =
                dynamic_cast<const ast::ItemDeclarationNode*>(
                    statement.get())) {

            auto* semantic =
                dynamic_cast<const ast::SymbolReferenceNode*>(
                    item->getTarget());

            if (!semantic) {
                throw std::runtime_error(
                    "Execution definition input must use a semantic target.");
            }

            const std::string& name = semantic->getSymbol();

            if (!seen.insert(name).second) {
                throw std::runtime_error(
                    "Duplicate execution definition input '" +
                    name +
                    "' in definition '" +
                    definition.identifier_ +
                    "'.");
            }

            InputSpec input;
            input.info.name = name;
            input.info.type_hint = item->type_hint_;
            input.info.has_default = item->value_node_ != nullptr;
            input.item = item;
            inputs.push_back(input);
            continue;
        }

        if (dynamic_cast<const ast::CalculationNode*>(statement.get())) {
            continue;
        }

        // Terms are executable workspace statements regardless of the
        // definition's legacy whole-block domain. Their own preserved
        // qualification determines runtime behavior.
        if (dynamic_cast<const ast::TermDeclarationNode*>(
                statement.get())) {

            continue;
        }

        // Preserve legacy whole-definition GEOMETRY forms.
        if (definition.domain_ == ast::ExecutionDomain::GEOMETRY) {
            if (dynamic_cast<const ast::ExecutionActionNode*>(
                    statement.get()) ||
                dynamic_cast<const ast::ReturnStatementNode*>(
                    statement.get())) {

                continue;
            }
        }

        throw std::runtime_error(
            "Unsupported statement in execution definition '" +
            definition.identifier_ +
            "'.");
    }

    return inputs;
}

std::unordered_map<std::string, const InputSpec*> indexInputs(
    const std::vector<InputSpec>& inputs) {

    std::unordered_map<std::string, const InputSpec*> indexed;

    for (const auto& input : inputs) {
        indexed.emplace(input.info.name, &input);
    }

    return indexed;
}

std::string overrideName(
    const ast::ItemDeclarationNode& argument) {

    auto* identifier =
        dynamic_cast<const ast::IdentifierNode*>(
            argument.getTarget());

    if (!identifier) {
        throw std::runtime_error(
            "Execution call override must use a local identifier target.");
    }

    return identifier->name_;
}

double evaluateValue(
    const ast::AstNode& node,
    ExecutionScope& scope) {

    Interpreter interpreter(scope);
    return interpreter.evaluate(node);
}

} // namespace

void ExecutionEngine::registerDefinition(
    const ast::ExecutionDefinitionNode& definition) {

    if (definitions_.find(definition.identifier_) != definitions_.end()) {
        throw std::runtime_error(
            "Duplicate execution definition '" +
            definition.identifier_ +
            "'.");
    }

    RegisteredDefinition registered;
    registered.definition = &definition;
    registered.source = std::nullopt;

    definitions_.emplace(
        definition.identifier_,
        std::move(registered));
}

void ExecutionEngine::registerDefinition(
    const ast::ExecutionDefinitionNode& definition,
    std::string source_document) {

    if (definitions_.find(definition.identifier_) != definitions_.end()) {
        throw std::runtime_error(
            "Duplicate execution definition '" +
            definition.identifier_ +
            "'.");
    }

    if (source_document.empty()) {
        throw std::runtime_error(
            "Execution definition source document cannot be empty.");
    }

    ExecutionDefinitionSourceInfo source;
    source.source_document = std::move(source_document);

    RegisteredDefinition registered;
    registered.definition = &definition;
    registered.source = std::move(source);

    definitions_.emplace(
        definition.identifier_,
        std::move(registered));
}

ExecutionDefinitionInfo ExecutionEngine::inspectDefinition(
    const ast::ExecutionDefinitionNode& definition) const {

    ExecutionDefinitionInfo info;
    info.identifier = definition.identifier_;
    info.identifier_is_numeric = definition.identifier_is_numeric_;

    for (const auto& input : collectInputSpecs(definition)) {
        info.inputs.push_back(input.info);
    }

    return info;
}

ExecutionDefinitionInfo ExecutionEngine::inspectRegisteredDefinition(
    const std::string& definition_id) const {

    const auto found = definitions_.find(definition_id);

    if (found == definitions_.end()) {
        throw std::runtime_error(
            "Unknown execution definition '" +
            definition_id +
            "'.");
    }

    if (found->second.definition == nullptr) {
        throw std::runtime_error(
            "Registered execution definition '" +
            definition_id +
            "' has no definition node.");
    }

    ExecutionDefinitionInfo info =
        inspectDefinition(*found->second.definition);

    info.source = found->second.source;

    return info;
}

ExecutionInstance ExecutionEngine::instantiate(
    const ast::ExecutionCallNode& call) const {

    auto found = definitions_.find(call.identifier_);

    if (found == definitions_.end()) {
        throw std::runtime_error(
            "Unknown execution definition '" +
            call.identifier_ +
            "'.");
    }

    const auto& definition = *found->second.definition;
    const auto inputs = collectInputSpecs(definition);
    const auto input_index = indexInputs(inputs);

    std::unordered_map<std::string, double> overrides;
    ExecutionScope override_scope;

    for (const auto& argument : call.arguments_) {
        const std::string name = overrideName(*argument);

        if (input_index.find(name) == input_index.end()) {
            throw std::runtime_error(
                "Unknown instance override '" +
                name +
                "' for execution definition '" +
                definition.identifier_ +
                "'.");
        }

        if (!argument->value_node_) {
            throw std::runtime_error(
                "Instance override '" +
                name +
                "' has no value.");
        }

        if (overrides.find(name) != overrides.end()) {
            throw std::runtime_error(
                "Duplicate instance override '" +
                name +
                "' for execution definition '" +
                definition.identifier_ +
                "'.");
        }

        overrides.emplace(
            name,
            evaluateValue(
                *argument->value_node_,
                override_scope));
    }

    return instantiate(call.identifier_, overrides);
}

ExecutionInstance ExecutionEngine::instantiate(
    const std::string& definition_id,
    const std::unordered_map<std::string, double>& overrides) const {

    auto found = definitions_.find(definition_id);

    if (found == definitions_.end()) {
        throw std::runtime_error(
            "Unknown execution definition '" +
            definition_id +
            "'.");
    }

    const auto& definition = *found->second.definition;
    const auto inputs = collectInputSpecs(definition);
    const auto input_index = indexInputs(inputs);

    for (const auto& override_entry : overrides) {
        if (input_index.find(override_entry.first) == input_index.end()) {
            throw std::runtime_error(
                "Unknown instance override '" +
                override_entry.first +
                "' for execution definition '" +
                definition.identifier_ +
                "'.");
        }
    }

    for (const auto& input : inputs) {
        if (!input.info.has_default &&
            overrides.find(input.info.name) == overrides.end()) {

            throw std::runtime_error(
                "Missing required execution input '" +
                input.info.name +
                "' for execution definition '" +
                definition.identifier_ +
                "'.");
        }
    }

    ExecutionInstance instance;
    instance.definition_id = definition.identifier_;
    instance.identifier_is_numeric =
        definition.identifier_is_numeric_;
    instance.source = found->second.source;

    for (const auto& input : inputs) {
        const auto override =
            overrides.find(input.info.name);

        double value = 0.0;

        if (override != overrides.end()) {
            value = override->second;
        } else {
            value = evaluateValue(
                *input.item->value_node_,
                instance.scope);
        }

        instance.scope.bind(
            input.info.name,
            value,
            input.info.name,
            BindingOrigin::SUPPLIED);
    }

    FakeGeometryActionDispatcher fallback_geometry_dispatcher;

    GeometryActionDispatcher* geometry_dispatcher =
        geometry_dispatcher_;

    // Preserve legacy whole-definition GEOMETRY behavior when no
    // external backend was supplied.
    if (geometry_dispatcher == nullptr &&
        definition.domain_ ==
            ast::ExecutionDomain::GEOMETRY) {

        geometry_dispatcher =
            &fallback_geometry_dispatcher;
    }

    InterpreterOptions options;
    options.domain =
        definition.domain_;
    options.active_target =
        definition.identifier_;
    options.allow_return = true;
    options.geometry_dispatcher =
        geometry_dispatcher;
    options.symbol_resolver =
        symbol_resolver_;

    if (found->second.source) {
        options.current_document =
            found->second.source->source_document;
    }

    Interpreter interpreter(
        instance.scope,
        FunctionTable{},
        options);

    instance.result =
        interpreter.executeForResult(
            *definition.body_,
            true);

    return instance;
}

std::vector<ExecutionInstance> ExecutionEngine::execute(
    const ast::ProgramNode& program) {

    for (const auto& statement : program.statements) {
        if (auto* definition =
                dynamic_cast<const ast::ExecutionDefinitionNode*>(
                    statement.get())) {

            registerDefinition(*definition);
        }
    }

    std::vector<ExecutionInstance> instances;

    for (const auto& statement : program.statements) {
        if (auto* call =
                dynamic_cast<const ast::ExecutionCallNode*>(
                    statement.get())) {

            instances.push_back(instantiate(*call));
            continue;
        }

        if (dynamic_cast<const ast::ExecutionDefinitionNode*>(
                statement.get())) {
            continue;
        }

        throw std::runtime_error(
            "ExecutionEngine supports execution definitions and calls only.");
    }

    return instances;
}

std::size_t ExecutionEngine::registeredDefinitionCount() const {
    return definitions_.size();
}

} // namespace runtime
} // namespace qps
