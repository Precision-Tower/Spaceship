#include "engineering/geometry/build_plan.hpp"
#include "engineering/geometry/feature_dag.hpp"
#include "engineering/geometry/native/geometry_executor.hpp"

#include <cassert>
#include <iostream>
#include <stdexcept>

using namespace engineering::geometry;

int main() {
    FeatureDAG dag;

    FeatureNode cylinder;
    cylinder.id = "body";
    cylinder.kind = FeatureKind::PRIMITIVE;
    cylinder.operation = "cylinder";
    cylinder.parameters = {
        {"radius", 3.0},
        {"width", 1.0}
    };

    dag.addFeature(cylinder);

    const GeometryBuildPlan plan =
        GeometryBuildPlan::fromFeatureDAG(dag);

    NativeGeometryExecutor executor;

    const GeometryExecutionResult result =
        executor.execute(plan);

    assert(result.features.size() == 1);
    assert(result.features.contains("body"));

    const NativeGeometryId id =
        result.features.at("body");

    assert(id.value != 0);
    assert(executor.contains(id));
    assert(executor.geometryCount() == 1);

    const NativeGeometryInfo info =
        executor.inspect(id);

    assert(info.valid);
    assert(info.kind == NativeGeometryKind::SOLID);

    const NativeTriangleMesh mesh =
        executor.triangulate(id);

    assert(!mesh.vertices.empty());
    assert(!mesh.indices.empty());
    assert(mesh.indices.size() % 3 == 0);

    for (const auto index : mesh.indices) {
        assert(index < mesh.vertices.size());
    }

    bool unknown_rejected = false;

    try {
        (void)executor.inspect(
            NativeGeometryId{999999});
    } catch (const std::runtime_error&) {
        unknown_rejected = true;
    }

    assert(unknown_rejected);

    // Native execution is atomic.
    //
    // A later feature failure must not leave geometry from an
    // incomplete build in the native store.
    FeatureDAG failing_dag;

    FeatureNode valid_first;
    valid_first.id = "candidate_body";
    valid_first.kind = FeatureKind::PRIMITIVE;
    valid_first.operation = "cylinder";
    valid_first.parameters = {
        {"radius", 2.0},
        {"width", 4.0}
    };

    failing_dag.addFeature(valid_first);

    FeatureNode invalid_second;
    invalid_second.id = "unsupported_feature";
    invalid_second.kind = FeatureKind::CUSTOM;
    invalid_second.operation = "unsupported_operation";
    invalid_second.dependencies = {
        "candidate_body"
    };

    failing_dag.addFeature(invalid_second);

    const GeometryBuildPlan failing_plan =
        GeometryBuildPlan::fromFeatureDAG(
            failing_dag);

    const std::size_t count_before_failure =
        executor.geometryCount();

    bool build_rejected = false;

    try {
        (void)executor.execute(
            failing_plan);
    } catch (const std::runtime_error&) {
        build_rejected = true;
    }

    assert(build_rejected);

    assert(
        executor.geometryCount() ==
        count_before_failure);

    // Failed builds must not consume durable native identity.
    FeatureDAG recovery_dag;

    FeatureNode recovery;
    recovery.id = "recovery_body";
    recovery.kind = FeatureKind::PRIMITIVE;
    recovery.operation = "cylinder";
    recovery.parameters = {
        {"radius", 1.0},
        {"width", 2.0}
    };

    recovery_dag.addFeature(recovery);

    const GeometryBuildPlan recovery_plan =
        GeometryBuildPlan::fromFeatureDAG(
            recovery_dag);

    const auto recovery_result =
        executor.execute(
            recovery_plan);

    const NativeGeometryId recovery_id =
        recovery_result.features.at(
            "recovery_body");

    assert(
        recovery_id.value ==
        id.value + 1);

    assert(executor.contains(recovery_id));

    std::cout
        << "native cylinder B-rep constructed and validated\n";

    return 0;
}
