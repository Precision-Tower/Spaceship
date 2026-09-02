#include "engineering/geometry/modeling_policy.hpp"

#include <stdexcept>

namespace engineering::geometry {

void ModelingPolicy::validate() const {
    if (linear_tolerance <= 0.0) {
        throw std::runtime_error(
            "Modeling linear tolerance must be greater than zero.");
    }

    if (angular_tolerance_degrees <= 0.0) {
        throw std::runtime_error(
            "Modeling angular tolerance must be greater than zero.");
    }
}

} // namespace engineering::geometry
