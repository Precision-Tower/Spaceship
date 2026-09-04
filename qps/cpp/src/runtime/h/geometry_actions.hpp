#ifndef QPS_RUNTIME_H_GEOMETRY_ACTIONS_HPP
#define QPS_RUNTIME_H_GEOMETRY_ACTIONS_HPP

#include "symbol_table.hpp"

#include <cstddef>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qps {
namespace runtime {

struct GeometryActionInvocation {
    std::string action_name;
    std::string active_target;

    std::optional<std::string> result_stage_name;
    std::optional<std::string> source_stage_name;
    std::optional<GeometryHandle> source_geometry;

    std::unordered_map<
        std::string,
        RuntimeValue
    > explicit_parameters;

    // Named structural packages supplied as action arguments.
    // QPS resolves execution-scope names but does not interpret
    // Engineering geometry structure here.
    std::vector<StructuralHandle> structural_arguments;

    const ExecutionScope* scope = nullptr;
};

struct ResolvedGeometryAction;

class GeometryActionDispatcher {
public:
    virtual ~GeometryActionDispatcher() = default;

    virtual RuntimeValue invoke(
        const ResolvedGeometryAction& action) = 0;
};

/*
 * This is intentionally fake.
 *
 * It proves backend-independent QPS geometry execution
 * without importing OCCT.
 *
 * QPS geometry semantics are resolved before dispatch.
 *
 * Future:
 *
 *     QPS
 *       -> GeometryActionResolver
 *       -> GeometryActionDispatcher
 *       -> Engineering/cpp/geometry
 *       -> OCCT
 */
class FakeGeometryActionDispatcher
    : public GeometryActionDispatcher {

public:
    RuntimeValue invoke(
        const ResolvedGeometryAction& action) override;

private:
    std::size_t next_handle_id_ = 1;
};

} // namespace runtime
} // namespace qps

#endif
