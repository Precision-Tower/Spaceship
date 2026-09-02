#include "engineering/geometry/build_plan.hpp"
#include "engineering/geometry/feature_dag.hpp"
#include "engineering/geometry/modeling_policy.hpp"

#include <cassert>
#include <stdexcept>

using namespace engineering::geometry;

namespace {

void dependencyOrderingIsDeterministic() {
    FeatureDAG dag;

    // Add out of dependency order deliberately.
    dag.addFeature({
        .id = "cut",
        .kind = FeatureKind::BOOLEAN,
        .operation = "subtract",
        .dependencies = {"shaft", "bore"},
    });

    dag.addFeature({
        .id = "shaft",
        .kind = FeatureKind::PRIMITIVE,
        .operation = "cylinder",
    });

    dag.addFeature({
        .id = "bore",
        .kind = FeatureKind::PRIMITIVE,
        .operation = "cylinder",
    });

    const auto ordered =
        dag.orderedFeatures();

    assert(ordered.size() == 3);

    assert(ordered[0]->id == "shaft");
    assert(ordered[1]->id == "bore");
    assert(ordered[2]->id == "cut");

    const auto plan =
        GeometryBuildPlan::fromFeatureDAG(dag);

    assert(plan.size() == 3);
    assert(plan.steps()[0].feature_id == "shaft");
    assert(plan.steps()[1].feature_id == "bore");
    assert(plan.steps()[2].feature_id == "cut");
}

void duplicateFeatureIdsAreRejected() {
    FeatureDAG dag;

    dag.addFeature({
        .id = "shaft",
        .kind = FeatureKind::PRIMITIVE,
        .operation = "cylinder",
    });

    bool rejected = false;

    try {
        dag.addFeature({
            .id = "shaft",
            .kind = FeatureKind::PRIMITIVE,
            .operation = "cylinder",
        });
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

void missingDependenciesAreRejected() {
    FeatureDAG dag;

    dag.addFeature({
        .id = "cut",
        .kind = FeatureKind::BOOLEAN,
        .operation = "subtract",
        .dependencies = {"shaft", "missing_bore"},
    });

    dag.addFeature({
        .id = "shaft",
        .kind = FeatureKind::PRIMITIVE,
        .operation = "cylinder",
    });

    bool rejected = false;

    try {
        (void)dag.orderedFeatures();
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

void cyclesAreRejected() {
    FeatureDAG dag;

    dag.addFeature({
        .id = "A",
        .kind = FeatureKind::CUSTOM,
        .operation = "A",
        .dependencies = {"B"},
    });

    dag.addFeature({
        .id = "B",
        .kind = FeatureKind::CUSTOM,
        .operation = "B",
        .dependencies = {"A"},
    });

    bool rejected = false;

    try {
        (void)dag.orderedFeatures();
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

void modelingPolicyRejectsInvalidTolerances() {
    {
        ModelingPolicy policy{
            .linear_tolerance = 0.001,
            .angular_tolerance_degrees = 0.01,
            .require_closed_solids = true,
        };

        policy.validate();
    }

    {
        ModelingPolicy policy{
            .linear_tolerance = 0.0,
            .angular_tolerance_degrees = 0.01,
            .require_closed_solids = true,
        };

        bool rejected = false;

        try {
            policy.validate();
        } catch (const std::runtime_error&) {
            rejected = true;
        }

        assert(rejected);
    }
}

} // namespace

int main() {
    dependencyOrderingIsDeterministic();
    duplicateFeatureIdsAreRejected();
    missingDependenciesAreRejected();
    cyclesAreRejected();
    modelingPolicyRejectsInvalidTolerances();

    return 0;
}
