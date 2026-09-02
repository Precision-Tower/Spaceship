#pragma once

#include "engineering/design_instance.hpp"
#include "engineering/geometry/feature_dag.hpp"
#include "engineering/geometry/geometry_recipe.hpp"

namespace engineering::geometry {

class GeometryCompiler {
public:
    FeatureDAG compile(
        const engineering::DesignInstance& design,
        const GeometryRecipe& recipe) const;
};

} // namespace engineering::geometry
