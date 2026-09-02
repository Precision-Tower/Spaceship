#pragma once

namespace engineering::geometry {

// Geometry-system policy.
//
// Values are supplied by Engineering configuration later;
// this type deliberately does not invent application defaults.
struct ModelingPolicy {
    double linear_tolerance;
    double angular_tolerance_degrees;
    bool require_closed_solids;

    void validate() const;
};

} // namespace engineering::geometry
