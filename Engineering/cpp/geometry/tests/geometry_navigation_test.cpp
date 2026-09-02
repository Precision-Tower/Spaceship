#include "engineering/geometry/build_plan.hpp"
#include "engineering/geometry/feature_dag.hpp"
#include "engineering/geometry/navigation.hpp"

#include <cassert>
#include <stdexcept>

using namespace engineering::geometry;

int main() {
    FeatureDAG dag;

    dag.addFeature({
        .id = "pipe_body",
        .kind = FeatureKind::PRIMITIVE,
        .operation = "cylinder",
        .parameters = {
            {"radius", 1.0},
            {"width", 5.0},
        },
    });

    const auto plan =
        GeometryBuildPlan::fromFeatureDAG(dag);

    assert(plan.size() == 1);

    const auto& body =
        plan.steps().front();

    // Grab +Z face.
    // Tape origin defaults to center of that face.
    const GeometryPoint positive_z_center =
        GeometryNavigator::faceCenter(
            body,
            CardinalDirection::POSITIVE_Z);

    assert(positive_z_center.x == 0.0);
    assert(positive_z_center.y == 0.0);
    assert(positive_z_center.z == 2.5);

    // punch1- z_x- .5;
    //
    // Grab +Z face center and move +X by .5.
    const GeometryPoint punch1 =
        GeometryNavigator::measure(
            positive_z_center,
            CardinalDirection::POSITIVE_X,
            0.5);

    assert(punch1.x == 0.5);
    assert(punch1.y == 0.0);
    assert(punch1.z == 2.5);

    // punch2- punch1(y- .5);
    //
    // Hook the tape at punch1 and move +Y by .5.
    const GeometryPoint punch2 =
        GeometryNavigator::measure(
            punch1,
            CardinalDirection::POSITIVE_Y,
            0.5);

    assert(punch2.x == 0.5);
    assert(punch2.y == 0.5);
    assert(punch2.z == 2.5);

    // Same process from the opposite end face.
    const GeometryPoint negative_z_center =
        GeometryNavigator::faceCenter(
            body,
            CardinalDirection::NEGATIVE_Z);

    assert(negative_z_center.x == 0.0);
    assert(negative_z_center.y == 0.0);
    assert(negative_z_center.z == -2.5);

    const GeometryPoint punch3 =
        GeometryNavigator::measure(
            negative_z_center,
            CardinalDirection::POSITIVE_X,
            0.5);

    const GeometryPoint punch4 =
        GeometryNavigator::measure(
            punch3,
            CardinalDirection::POSITIVE_Y,
            0.5);

    assert(punch4.x == 0.5);
    assert(punch4.y == 0.5);
    assert(punch4.z == -2.5);

    // punch2 and punch4 now define a straight line through
    // the cylinder parallel to local Z.
    assert(punch2.x == punch4.x);
    assert(punch2.y == punch4.y);
    assert(punch2.z == -punch4.z);

    // Negative distance is deliberately forbidden.
    bool negative_rejected = false;

    try {
        (void)GeometryNavigator::measure(
            punch1,
            CardinalDirection::POSITIVE_X,
            -1.0);
    } catch (const std::runtime_error&) {
        negative_rejected = true;
    }

    assert(negative_rejected);

    return 0;
}
