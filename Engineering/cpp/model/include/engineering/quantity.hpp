#pragma once

#include <string>

namespace engineering {

struct Quantity {
    // Authored representation.
    //
    // Example:
    //   value     = 1.0
    //   dimension = "length"
    //   unit      = "in"
    //
    // canonicalValue() then resolves to 25.4 mm.
    double value = 0.0;
    std::string dimension;
    std::string unit;

    // Construct an Engineering quantity from an authored value/unit
    // pair. The authoritative Engineering unit registry determines the
    // physical dimension.
    //
    // Example:
    //   Quantity::fromUnit(1.0, "in")
    //   -> Quantity{1.0, "length", "in"}
    static Quantity fromUnit(
        double value,
        const std::string& unit);

    // Convert the authored value into the canonical Engineering unit
    // for its physical dimension.
    double canonicalValue() const;

    // Canonical Engineering unit for this quantity's dimension.
    std::string canonicalUnit() const;

    // Returns true when the dimension/unit pair is recognized.
    bool isSupported() const;

    // Convert this quantity to another compatible unit.
    //
    // The returned Quantity preserves the same physical dimension but
    // uses the requested authored representation.
    Quantity convertedTo(
        const std::string& target_unit) const;

    bool operator==(const Quantity&) const = default;
};

} // namespace engineering
