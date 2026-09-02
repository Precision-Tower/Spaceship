#pragma once

#include "engineering/geometry/build_plan.hpp"

namespace engineering::geometry {

struct GeometryPoint {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;

    bool operator==(const GeometryPoint&) const = default;
};

enum class CardinalDirection {
    POSITIVE_X,
    NEGATIVE_X,
    POSITIVE_Y,
    NEGATIVE_Y,
    POSITIVE_Z,
    NEGATIVE_Z
};

class GeometryNavigator {
public:
    // Resolve the center of a cardinal planar face belonging to
    // a feature.
    //
    // The first implementation supports the +/-Z end faces of
    // the default cylinder primitive.
    static GeometryPoint faceCenter(
        const GeometryBuildStep& feature,
        CardinalDirection face);

    // Hook the tape at an existing point and measure in one of
    // the object's local cardinal directions.
    static GeometryPoint measure(
        const GeometryPoint& origin,
        CardinalDirection direction,
        double distance);
};

} // namespace engineering::geometry
