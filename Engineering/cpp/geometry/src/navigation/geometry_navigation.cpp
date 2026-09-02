#include "engineering/geometry/navigation.hpp"

#include <stdexcept>
#include <string>

namespace engineering::geometry {

namespace {

double requiredParameter(
    const GeometryBuildStep& feature,
    const std::string& name) {

    for (const auto& parameter : feature.parameters) {
        if (parameter.name == name) {
            return parameter.numeric_value;
        }
    }

    throw std::runtime_error(
        "Geometry feature '" +
        feature.feature_id +
        "' is missing navigation parameter '" +
        name +
        "'.");
}

} // namespace

GeometryPoint GeometryNavigator::faceCenter(
    const GeometryBuildStep& feature,
    CardinalDirection face) {

    if (feature.operation != "cylinder") {
        throw std::runtime_error(
            "Face-center navigation is not implemented for geometry operation '" +
            feature.operation +
            "'.");
    }

    const double width =
        requiredParameter(feature, "width");

    if (width <= 0.0) {
        throw std::runtime_error(
            "Cylinder width must be greater than zero for navigation.");
    }

    switch (face) {
        case CardinalDirection::POSITIVE_Z:
            return {
                0.0,
                0.0,
                width / 2.0
            };

        case CardinalDirection::NEGATIVE_Z:
            return {
                0.0,
                0.0,
                -width / 2.0
            };

        default:
            throw std::runtime_error(
                "Cylinder planar face navigation currently supports only +Z and -Z.");
    }
}

GeometryPoint GeometryNavigator::measure(
    const GeometryPoint& origin,
    CardinalDirection direction,
    double distance) {

    if (distance < 0.0) {
        throw std::runtime_error(
            "Navigation distance cannot be negative; use the opposite cardinal direction.");
    }

    GeometryPoint result =
        origin;

    switch (direction) {
        case CardinalDirection::POSITIVE_X:
            result.x += distance;
            break;

        case CardinalDirection::NEGATIVE_X:
            result.x -= distance;
            break;

        case CardinalDirection::POSITIVE_Y:
            result.y += distance;
            break;

        case CardinalDirection::NEGATIVE_Y:
            result.y -= distance;
            break;

        case CardinalDirection::POSITIVE_Z:
            result.z += distance;
            break;

        case CardinalDirection::NEGATIVE_Z:
            result.z -= distance;
            break;
    }

    return result;
}

} // namespace engineering::geometry
