#include "../h/geometry_action_resolver.hpp"

#include <algorithm>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace qps {
namespace runtime {

namespace {

struct GeometryActionSpec {
    std::vector<std::string> required_parameters;
    bool requires_source = false;
};

const GeometryActionSpec& actionSpec(
    const std::string& action_name) {

    static const std::unordered_map<
        std::string,
        GeometryActionSpec
    > specs = {
        {
            "cylinder",
            GeometryActionSpec{
                {"radius", "width"},
                false
            }
        },
        {
            "bore",
            GeometryActionSpec{
                {"radius"},
                true
            }
        }
    };

    const auto found = specs.find(action_name);

    if (found == specs.end()) {
        throw std::runtime_error(
            "Unknown GEOMETRY action '-" +
            action_name +
            "'.");
    }

    return found->second;
}

bool isExpectedParameter(
    const GeometryActionSpec& spec,
    const std::string& name) {

    return std::find(
        spec.required_parameters.begin(),
        spec.required_parameters.end(),
        name) != spec.required_parameters.end();
}

void validateExplicitParameters(
    const GeometryActionInvocation& invocation,
    const GeometryActionSpec& spec) {

    for (const auto& entry :
         invocation.explicit_parameters) {

        if (!isExpectedParameter(spec, entry.first)) {
            throw std::runtime_error(
                "Unknown GEOMETRY parameter '" +
                entry.first +
                "' for action '-" +
                invocation.action_name +
                "'.");
        }
    }
}

ResolvedGeometryParameter resolveParameter(
    const GeometryActionInvocation& invocation,
    const std::string& parameter_name) {

    const auto explicit_value =
        invocation.explicit_parameters.find(
            parameter_name);

    if (explicit_value !=
        invocation.explicit_parameters.end()) {

        return {
            parameter_name,
            explicit_value->second.asNumber(
                "GEOMETRY action '-" +
                invocation.action_name +
                "' parameter '" +
                parameter_name +
                "'"),
            true
        };
    }

    if (invocation.scope != nullptr &&
        invocation.scope->contains(parameter_name)) {

        return {
            parameter_name,
            invocation.scope
                ->get(parameter_name)
                .value
                .asNumber(
                    "GEOMETRY action '-" +
                    invocation.action_name +
                    "' context parameter '" +
                    parameter_name +
                    "'"),
            false
        };
    }

    throw std::runtime_error(
        "Missing required GEOMETRY parameter '" +
        parameter_name +
        "' for action '-" +
        invocation.action_name +
        "' in target '" +
        invocation.active_target +
        "'.");
}

} // namespace

ResolvedGeometryAction
GeometryActionResolver::resolve(
    const GeometryActionInvocation& invocation) const {

    const auto& spec =
        actionSpec(invocation.action_name);

    validateExplicitParameters(
        invocation,
        spec);

    if (spec.requires_source &&
        !invocation.source_geometry.has_value()) {

        throw std::runtime_error(
            "GEOMETRY action '-" +
            invocation.action_name +
            "' requires a geometry source.");
    }

    ResolvedGeometryAction resolved;

    resolved.action_name =
        invocation.action_name;
    resolved.active_target =
        invocation.active_target;
    resolved.result_stage_name =
        invocation.result_stage_name;
    resolved.source_stage_name =
        invocation.source_stage_name;
    resolved.source_geometry =
        invocation.source_geometry;

    resolved.structural_arguments =
        invocation.structural_arguments;

    // Structural primitive arguments are interpreted downstream by the
    // Engineering geometry adapter. Preserve the existing eager numeric
    // parameter path when no structural package was supplied.
    if (resolved.structural_arguments.empty()) {
        resolved.parameters.reserve(
            spec.required_parameters.size());

        for (const auto& parameter_name :
             spec.required_parameters) {

            resolved.parameters.push_back(
                resolveParameter(
                    invocation,
                    parameter_name));
        }
    }

    return resolved;
}

} // namespace runtime
} // namespace qps
