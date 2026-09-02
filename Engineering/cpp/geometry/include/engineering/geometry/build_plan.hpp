#pragma once

#include "engineering/geometry/feature_dag.hpp"

#include <string>
#include <vector>

namespace engineering::geometry {

struct GeometryBuildStep {
    std::string feature_id;
    FeatureKind kind = FeatureKind::CUSTOM;
    std::string operation;
    std::vector<FeatureParameter> parameters;
    std::vector<std::string> dependencies;
};

class GeometryBuildPlan {
public:
    static GeometryBuildPlan fromFeatureDAG(
        const FeatureDAG& dag);

    const std::vector<GeometryBuildStep>&
    steps() const;

    std::size_t size() const;

private:
    std::vector<GeometryBuildStep> steps_;
};

} // namespace engineering::geometry
