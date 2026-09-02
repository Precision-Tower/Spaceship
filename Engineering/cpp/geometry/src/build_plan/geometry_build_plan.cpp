#include "engineering/geometry/build_plan.hpp"

namespace engineering::geometry {

GeometryBuildPlan GeometryBuildPlan::fromFeatureDAG(
    const FeatureDAG& dag) {

    GeometryBuildPlan plan;

    for (const auto* feature :
         dag.orderedFeatures()) {

        plan.steps_.push_back({
            .feature_id = feature->id,
            .kind = feature->kind,
            .operation = feature->operation,
            .parameters = feature->parameters,
            .dependencies = feature->dependencies,
        });
    }

    return plan;
}

const std::vector<GeometryBuildStep>&
GeometryBuildPlan::steps() const {

    return steps_;
}

std::size_t GeometryBuildPlan::size() const {
    return steps_.size();
}

} // namespace engineering::geometry
