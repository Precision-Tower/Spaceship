#include "engineering/geometry/geometry_compiler.hpp"

#include <stdexcept>
#include <unordered_set>

namespace engineering::geometry {

FeatureDAG GeometryCompiler::compile(
    const engineering::DesignInstance& design,
    const GeometryRecipe& recipe) const {

    FeatureDAG dag;
    std::unordered_set<std::string> recipe_ids;

    // Validate recipe identity independently of DAG insertion so
    // dependency diagnostics remain about dependency structure.
    for (const auto& feature : recipe.features) {
        if (feature.id.empty()) {
            throw std::runtime_error(
                "Geometry recipe feature ID cannot be empty.");
        }

        if (!recipe_ids.insert(feature.id).second) {
            throw std::runtime_error(
                "Duplicate geometry recipe feature ID '" +
                feature.id +
                "'.");
        }
    }

    for (const auto& recipe_feature : recipe.features) {
        FeatureNode feature;
        feature.id = recipe_feature.id;
        feature.kind = recipe_feature.kind;
        feature.operation = recipe_feature.operation;
        feature.dependencies = recipe_feature.dependencies;

        std::unordered_set<std::string> parameter_names;

        for (const auto& parameter :
             recipe_feature.parameters) {

            if (parameter.parameter.empty()) {
                throw std::runtime_error(
                    "Geometry parameter name cannot be empty.");
            }

            if (parameter.binding.empty()) {
                throw std::runtime_error(
                    "Geometry parameter '" +
                    parameter.parameter +
                    "' has no Engineering binding reference.");
            }

            if (!parameter_names
                     .insert(parameter.parameter)
                     .second) {

                throw std::runtime_error(
                    "Duplicate geometry parameter '" +
                    parameter.parameter +
                    "' on feature '" +
                    recipe_feature.id +
                    "'.");
            }

            if (!design.hasBinding(parameter.binding)) {
                throw std::runtime_error(
                    "Geometry parameter '" +
                    parameter.parameter +
                    "' references missing Engineering binding '" +
                    parameter.binding +
                    "'.");
            }

            const auto& binding =
                design.binding(parameter.binding);

            if (!binding.resolved ||
                !binding.numeric_value.has_value()) {

                throw std::runtime_error(
                    "Geometry parameter '" +
                    parameter.parameter +
                    "' requires resolved numeric Engineering binding '" +
                    parameter.binding +
                    "'.");
            }

            feature.parameters.push_back({
                .name = parameter.parameter,
                .numeric_value =
                    *binding.numeric_value,
            });
        }

        dag.addFeature(std::move(feature));
    }

    // Force dependency validation now. A successful compile returns
    // a structurally executable graph, not a graph containing a
    // deferred known error.
    (void)dag.orderedFeatures();

    return dag;
}

} // namespace engineering::geometry
