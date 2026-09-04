#include "../h/geometry_actions.hpp"
#include "../h/geometry_action_resolver.hpp"

#include <utility>

namespace qps {
namespace runtime {

RuntimeValue
FakeGeometryActionDispatcher::invoke(
    const ResolvedGeometryAction& action) {

    GeometryHandle handle;

    handle.id = next_handle_id_++;
    handle.action_name =
        action.action_name;
    handle.active_target =
        action.active_target;
    handle.stage_name =
        action.result_stage_name;
    handle.source_stage_name =
        action.source_stage_name;

    handle.parameters.reserve(
        action.parameters.size());

    for (const auto& resolved_parameter :
         action.parameters) {

        GeometryParameterValue parameter;

        parameter.name =
            resolved_parameter.name;
        parameter.value =
            resolved_parameter.value;
        parameter.explicit_override =
            resolved_parameter.explicit_override;

        handle.parameters.push_back(
            std::move(parameter));
    }

    if (action.source_geometry.has_value()) {
        handle.source_handle_id =
            action.source_geometry->id;
    }

    return RuntimeValue::geometry(
        std::move(handle));
}

} // namespace runtime
} // namespace qps
