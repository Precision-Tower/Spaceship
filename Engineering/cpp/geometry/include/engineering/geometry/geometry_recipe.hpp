#pragma once

#include "engineering/geometry/feature_dag.hpp"

#include <string>
#include <vector>

namespace engineering::geometry {

// References an Engineering binding by semantic name.
//
// The recipe owns geometric intent.
// The DesignInstance owns the value.
struct GeometryParameterBinding {
    std::string parameter;
    std::string binding;
};

struct GeometryRecipeFeature {
    std::string id;
    FeatureKind kind = FeatureKind::CUSTOM;
    std::string operation;

    std::vector<std::string> dependencies;
    std::vector<GeometryParameterBinding> parameters;
};

struct GeometryRecipe {
    std::vector<GeometryRecipeFeature> features;
};

} // namespace engineering::geometry
