#ifndef QPS_RUNTIME_H_GEOMETRY_ACTION_RESOLVER_HPP
#define QPS_RUNTIME_H_GEOMETRY_ACTION_RESOLVER_HPP

#include "geometry_actions.hpp"

#include <optional>
#include <string>
#include <vector>

namespace qps {
namespace runtime {

struct ResolvedGeometryParameter {
    std::string name;
    double value = 0.0;
    bool explicit_override = false;
};

struct ResolvedGeometryAction {
    std::string action_name;
    std::string active_target;

    std::optional<std::string> result_stage_name;
    std::optional<std::string> source_stage_name;
    std::optional<GeometryHandle> source_geometry;

    std::vector<ResolvedGeometryParameter> parameters;

    // Structural packages remain intact across the QPS/Engineering
    // dispatch boundary. Engineering decides how a primitive consumes them.
    std::vector<StructuralHandle> structural_arguments;
};

class GeometryActionResolver {
public:
    ResolvedGeometryAction resolve(
        const GeometryActionInvocation& invocation) const;
};

} // namespace runtime
} // namespace qps

#endif
