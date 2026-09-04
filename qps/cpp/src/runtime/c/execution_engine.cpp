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
                // Identifier-target Items are local runtime state.
                // Only semantic [>...] Items define the execution interface.
                continue;
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

        // Non-input execution body statements are runtime content.
        // Their validity belongs to the parser/interpreter, not input
        // inspection.
        continue;
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

RuntimeValue evaluateValue(
    const ast::AstNode& node,
    ExecutionScope& scope) {

    Interpreter interpreter(scope);
    return interpreter.evaluateValue(node);
}

std::string causalName(
    const ast::AstNode* node,
    const std::string& context) {

    if (node == nullptr) {
        throw std::runtime_error(
            "Causal relationship " +
            context +
            " is missing.");
    }

    if (auto* identifier =
            dynamic_cast<const ast::IdentifierNode*>(
                node)) {

        return identifier->name_;
    }

    if (auto* reference =
            dynamic_cast<const ast::SymbolReferenceNode*>(
                node)) {

        return reference->getSymbol();
    }

    throw std::runtime_error(
        "Causal relationship " +
        context +
        " must be an identifier or semantic reference.");
}

CausalRelationshipInfo inspectCausalRelationship(
    const std::string& causal_definition_id,
    const ast::CausalRelationshipNode& relationship) {

    if (!relationship.left_side_ ||
        !relationship.right_side_) {

        throw std::runtime_error(
            "Causal definition '" +
            causal_definition_id +
            "' contains an incomplete relationship.");
    }

    CausalRelationshipInfo info;
    info.causal_definition_id = causal_definition_id;

    info.source_entity =
        causalName(
            relationship.left_side_->entity.get(),
            "source entity");
    info.source_input_state =
        causalName(
            relationship.left_side_->input.get(),
            "source input state");
    info.source_output_state =
        causalName(
            relationship.left_side_->output.get(),
            "source output state");

    info.destination_entity =
        causalName(
            relationship.right_side_->entity.get(),
            "destination entity");
    info.destination_input_state =
        causalName(
            relationship.right_side_->input.get(),
            "destination input state");
    info.destination_output_state =
        causalName(
            relationship.right_side_->output.get(),
            "destination output state");

    return info;
}

bool definitionMatchesCausalEntity(
    const std::string& definition_id,
    const std::string& entity) {

    if (definition_id == entity) {
        return true;
    }

    const std::string entity_prefix =
        entity + "_";

    return definition_id.rfind(entity_prefix, 0) == 0;
}

bool canTransferAcross(
    const CausalRelationshipInfo& relationship) {

    return relationship.source_output_state ==
           relationship.destination_input_state;
}

std::unordered_set<std::string> explicitOverrideNames(
    const ast::ExecutionCallNode& call) {

    std::unordered_set<std::string> names;

    for (const auto& argument : call.arguments_) {
        names.insert(overrideName(*argument));
    }

    return names;
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

    return instantiate(
        call,
        std::unordered_map<std::string, CausalInput>{});
}

ExecutionInstance ExecutionEngine::instantiate(
    const ast::ExecutionCallNode& call,
    const std::unordered_map<std::string, CausalInput>&
        causal_inputs) const {

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

    std::unordered_map<std::string, RuntimeValue> overrides;
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

    return instantiate(
        call.identifier_,
        overrides,
        causal_inputs);
}

ExecutionInstance ExecutionEngine::instantiateNumeric(
    const std::string& definition_id,
    const std::unordered_map<std::string, double>& overrides) const {

    std::unordered_map<std::string, RuntimeValue>
        runtime_overrides;

    for (const auto& [name, value] : overrides) {
        runtime_overrides.emplace(
            name,
            RuntimeValue::numeric(value));
    }

    return instantiate(
        definition_id,
        runtime_overrides);
}

ExecutionInstance ExecutionEngine::instantiate(
    const std::string& definition_id,
    const std::unordered_map<std::string, RuntimeValue>& overrides) const {

    return instantiate(
        definition_id,
        overrides,
        std::unordered_map<std::string, CausalInput>{});
}

ExecutionInstance ExecutionEngine::instantiate(
    const std::string& definition_id,
    const std::unordered_map<std::string, RuntimeValue>& overrides,
    const std::unordered_map<std::string, CausalInput>&
        causal_inputs) const {

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

    for (const auto& causal_entry : causal_inputs) {
        if (input_index.find(causal_entry.first) == input_index.end()) {
            throw std::runtime_error(
                "Unknown causal input '" +
                causal_entry.first +
                "' for execution definition '" +
                definition.identifier_ +
                "'.");
        }
    }

    for (const auto& input : inputs) {
        if (!input.info.has_default &&
            overrides.find(input.info.name) == overrides.end() &&
            causal_inputs.find(input.info.name) ==
                causal_inputs.end()) {

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

        const auto causal_input =
            causal_inputs.find(input.info.name);

        RuntimeValue value;

        if (override != overrides.end()) {
            value = override->second;
        } else if (causal_input != causal_inputs.end()) {
            value = RuntimeValue::numeric(
                causal_input->second.value);
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

        if (override == overrides.end() &&
            causal_input != causal_inputs.end()) {

            CausalTransferTrace trace =
                causal_input->second.trace;
            trace.destination_definition_id =
                definition.identifier_;
            trace.destination_origin =
                BindingOrigin::SUPPLIED;

            instance.causal_transfers.push_back(
                std::move(trace));
        }
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

    std::vector<CausalRelationshipInfo> causal_relationships;

    for (const auto& statement : program.statements) {
        if (auto* definition =
                dynamic_cast<const ast::ExecutionDefinitionNode*>(
                    statement.get())) {

            registerDefinition(*definition);
            continue;
        }

        if (auto* causal_definition =
                dynamic_cast<const ast::CausalDefinitionNode*>(
                    statement.get())) {

            for (const auto& relationship_node :
                 causal_definition->relationships) {

                auto* relationship =
                    dynamic_cast<const ast::CausalRelationshipNode*>(
                        relationship_node.get());

                if (!relationship) {
                    throw std::runtime_error(
                        "Causal definition '" +
                        causal_definition->identifier_ +
                        "' contains an unsupported relationship node.");
                }

                causal_relationships.push_back(
                    inspectCausalRelationship(
                        causal_definition->identifier_,
                        *relationship));
            }
        }
    }

    std::vector<ExecutionInstance> instances;

    for (const auto& statement : program.statements) {
        if (auto* call =
                dynamic_cast<const ast::ExecutionCallNode*>(
                    statement.get())) {

            std::unordered_map<std::string, CausalInput>
                causal_inputs;

            const auto definition =
                definitions_.find(call->identifier_);

            if (definition != definitions_.end()) {
                const auto inputs =
                    collectInputSpecs(
                        *definition->second.definition);

                const auto explicit_overrides =
                    explicitOverrideNames(*call);

                for (const auto& relationship :
                     causal_relationships) {

                    if (!canTransferAcross(relationship) ||
                        !definitionMatchesCausalEntity(
                            call->identifier_,
                            relationship.destination_entity)) {

                        continue;
                    }

                    for (const auto& input : inputs) {
                        if (input.info.has_default ||
                            explicit_overrides.find(input.info.name) !=
                                explicit_overrides.end()) {

                            continue;
                        }

                        const ExecutionInstance* source_instance =
                            nullptr;
                        const RuntimeBinding* source_binding =
                            nullptr;

                        for (const auto& previous : instances) {
                            if (!definitionMatchesCausalEntity(
                                    previous.definition_id,
                                    relationship.source_entity)) {

                                continue;
                            }

                            if (!previous.scope.contains(
                                    input.info.name)) {

                                continue;
                            }

                            const RuntimeBinding& candidate =
                                previous.scope.get(input.info.name);

                            if (candidate.origin !=
                                BindingOrigin::DERIVED) {

                                continue;
                            }

                            if (!candidate.semantic_symbol ||
                                *candidate.semantic_symbol !=
                                    input.info.name) {

                                continue;
                            }

                            if (source_binding != nullptr) {
                                throw std::runtime_error(
                                    "Ambiguous causal transfer for input '" +
                                    input.info.name +
                                    "' into execution definition '" +
                                    call->identifier_ +
                                    "'.");
                            }

                            source_instance = &previous;
                            source_binding = &candidate;
                        }

                        if (source_binding == nullptr ||
                            source_instance == nullptr) {

                            continue;
                        }

                        if (causal_inputs.find(input.info.name) !=
                            causal_inputs.end()) {

                            throw std::runtime_error(
                                "Ambiguous causal transfer for input '" +
                                input.info.name +
                                "' into execution definition '" +
                                call->identifier_ +
                                "'.");
                        }

                        CausalInput causal_input;
                        causal_input.value =
                            source_binding->value.asNumber(
                                "Causal transfer '" +
                                relationship.causal_definition_id +
                                "' semantic '" +
                                input.info.name +
                                "'");

                        causal_input.trace.relationship =
                            relationship;
                        causal_input.trace.source_definition_id =
                            source_instance->definition_id;
                        causal_input.trace.destination_definition_id =
                            call->identifier_;
                        causal_input.trace.semantic_symbol =
                            input.info.name;
                        causal_input.trace.source_semantic_symbol =
                            source_binding->semantic_symbol;
                        causal_input.trace.value =
                            causal_input.value;
                        causal_input.trace.source_origin =
                            source_binding->origin;
                        causal_input.trace.destination_origin =
                            BindingOrigin::SUPPLIED;

                        causal_inputs.emplace(
                            input.info.name,
                            std::move(causal_input));
                    }
                }
            }

            instances.push_back(
                instantiate(
                    *call,
                    causal_inputs));
            continue;
        }

        if (dynamic_cast<const ast::ExecutionDefinitionNode*>(
                statement.get()) ||
            dynamic_cast<const ast::CausalDefinitionNode*>(
                statement.get())) {
            continue;
        }

        throw std::runtime_error(
            "ExecutionEngine supports execution definitions, "
            "causal definitions, and calls only.");
    }

    return instances;
}

std::size_t ExecutionEngine::registeredDefinitionCount() const {
    return definitions_.size();
}

} // namespace runtime
} // namespace qps
