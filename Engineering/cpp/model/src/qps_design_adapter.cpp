#include "engineering/qps_design_adapter.hpp"

#include "tokens/h/token.hpp"

#include <stdexcept>
#include <unordered_map>

namespace engineering {

namespace {

std::optional<BindingDeclaredType> translateDeclaredType(
    const std::optional<qps::tokens::TokenType>& type_hint) {

    if (!type_hint.has_value()) {
        return std::nullopt;
    }

    if (*type_hint == qps::tokens::TokenType::TYPE_NUMERIC) {
        return BindingDeclaredType::NUMERIC;
    }

    throw std::runtime_error(
        "QPS Design adapter currently supports only explicitly "
        "numeric Engineering bindings.");
}

} // namespace

DesignInstance makeDesignInstance(
    const std::string& instance_id,
    const qps::runtime::ExecutionDefinitionInfo& definition) {

    DesignInstance design(
        instance_id,
        definition.identifier);

    if (definition.source.has_value()) {
        design.setDefinitionSource({
            .source_document =
                definition.source->source_document,
        });
    }

    for (const auto& input : definition.inputs) {
        design.setBinding({
            .name = input.name,
            .declared_type =
                translateDeclaredType(input.type_hint),
            .has_default = input.has_default,
            .explicit_numeric_value = std::nullopt,
            .resolved = false,
            .numeric_value = std::nullopt,
            .provenance =
                BindingProvenance::UNRESOLVED,
        });
    }

    return design;
}

qps::runtime::ExecutionInstance executeDesignInstance(
    const DesignInstance& design,
    const qps::runtime::ExecutionEngine& engine) {

    std::unordered_map<std::string, double> overrides;

    for (const auto& [name, binding] :
         design.bindings()) {

        // Only explicit Engineering-owned instance state crosses
        // into QPS as an override.
        //
        // An evaluated value obtained from a QPS default must not
        // silently become an override on the next execution.
        if (!binding.explicit_numeric_value.has_value()) {
            continue;
        }

        if (binding.provenance ==
            BindingProvenance::DERIVED) {
            throw std::runtime_error(
                "Derived Engineering binding '" +
                name +
                "' cannot own an explicit execution override.");
        }

        overrides.emplace(
            name,
            *binding.explicit_numeric_value);
    }

    return engine.instantiate(
        design.definitionRef(),
        overrides);
}

void applyExecutionResult(
    DesignInstance& design,
    const qps::runtime::ExecutionInstance& execution) {

    if (execution.definition_id != design.definitionRef()) {
        throw std::runtime_error(
            "Execution result definition '" +
            execution.definition_id +
            "' does not match DesignInstance definition '" +
            design.definitionRef() +
            "'.");
    }

    if (execution.source.has_value()) {
        design.setEvaluatedFrom({
            .source_document =
                execution.source->source_document,
        });
    } else {
        design.clearEvaluatedFrom();
    }

    for (const auto& runtime_binding :
         execution.scope.bindings()) {

        if (!runtime_binding.semantic_symbol.has_value()) {
            continue;
        }

        const std::string& name =
            *runtime_binding.semantic_symbol;

        EngineeringBinding binding;

        if (design.hasBinding(name)) {
            binding = design.binding(name);
        } else {
            binding.name = name;
        }

        binding.name = name;
        binding.resolved = true;
        binding.numeric_value = runtime_binding.value;

        if (runtime_binding.origin ==
            qps::runtime::BindingOrigin::DERIVED) {

            binding.provenance =
                BindingProvenance::DERIVED;

        } else if (
            runtime_binding.origin ==
            qps::runtime::BindingOrigin::SUPPLIED) {

            binding.provenance =
                BindingProvenance::SUPPLIED_OR_DEFAULT;

        } else {
            throw std::runtime_error(
                "Semantic QPS binding '" +
                name +
                "' has unsupported LOCAL origin.");
        }

        design.setBinding(binding);
    }
}

} // namespace engineering
