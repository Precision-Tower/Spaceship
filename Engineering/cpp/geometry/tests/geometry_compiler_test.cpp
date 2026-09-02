#include "engineering/design_instance.hpp"
#include "engineering/geometry/build_plan.hpp"
#include "engineering/geometry/geometry_compiler.hpp"

#include <cassert>
#include <stdexcept>

namespace {

engineering::EngineeringBinding resolvedNumeric(
    const std::string& name,
    double value) {

    return {
        .name = name,
        .declared_type =
            engineering::BindingDeclaredType::NUMERIC,
        .has_default = false,
        .explicit_numeric_value = value,
        .resolved = true,
        .numeric_value = value,
        .provenance =
            engineering::BindingProvenance::SUPPLIED,
    };
}

void cylinderRecipeCompilesFromEngineeringState() {
    engineering::DesignInstance design(
        "shaft_A",
        "Shaft");

    design.setBinding(
        resolvedNumeric("radius", 50.0));

    design.setBinding(
        resolvedNumeric("length", 200.0));

    engineering::geometry::GeometryRecipe recipe{
        .features = {
            {
                .id = "shaft_body",
                .kind =
                    engineering::geometry::FeatureKind::PRIMITIVE,
                .operation = "cylinder",
                .parameters = {
                    {
                        .parameter = "radius",
                        .binding = "radius",
                    },
                    {
                        .parameter = "height",
                        .binding = "length",
                    },
                },
            },
        },
    };

    engineering::geometry::GeometryCompiler compiler;

    const auto dag =
        compiler.compile(design, recipe);

    assert(dag.size() == 1);

    const auto& feature =
        dag.feature("shaft_body");

    assert(feature.operation == "cylinder");
    assert(feature.parameters.size() == 2);

    assert(feature.parameters[0].name == "radius");
    assert(
        feature.parameters[0].numeric_value ==
        50.0);

    assert(feature.parameters[1].name == "height");
    assert(
        feature.parameters[1].numeric_value ==
        200.0);

    const auto plan =
        engineering::geometry::GeometryBuildPlan::
            fromFeatureDAG(dag);

    assert(plan.size() == 1);
    assert(plan.steps()[0].operation == "cylinder");
    assert(plan.steps()[0].parameters.size() == 2);
}

void unresolvedGeometryInputIsRejected() {
    engineering::DesignInstance design(
        "shaft_unresolved",
        "Shaft");

    engineering::EngineeringBinding radius;
    radius.name = "radius";
    radius.declared_type =
        engineering::BindingDeclaredType::NUMERIC;

    design.setBinding(radius);

    engineering::geometry::GeometryRecipe recipe{
        .features = {
            {
                .id = "shaft_body",
                .kind =
                    engineering::geometry::FeatureKind::PRIMITIVE,
                .operation = "cylinder",
                .parameters = {
                    {
                        .parameter = "radius",
                        .binding = "radius",
                    },
                },
            },
        },
    };

    engineering::geometry::GeometryCompiler compiler;

    bool rejected = false;

    try {
        (void)compiler.compile(design, recipe);
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

void missingGeometryBindingIsRejected() {
    engineering::DesignInstance design(
        "shaft_missing",
        "Shaft");

    engineering::geometry::GeometryRecipe recipe{
        .features = {
            {
                .id = "shaft_body",
                .kind =
                    engineering::geometry::FeatureKind::PRIMITIVE,
                .operation = "cylinder",
                .parameters = {
                    {
                        .parameter = "radius",
                        .binding = "radius",
                    },
                },
            },
        },
    };

    engineering::geometry::GeometryCompiler compiler;

    bool rejected = false;

    try {
        (void)compiler.compile(design, recipe);
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

} // namespace

int main() {
    cylinderRecipeCompilesFromEngineeringState();
    unresolvedGeometryInputIsRejected();
    missingGeometryBindingIsRejected();

    return 0;
}
