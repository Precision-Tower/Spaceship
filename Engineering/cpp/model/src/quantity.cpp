#include "engineering/quantity.hpp"

#include <cmath>
#include <numbers>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace engineering {

namespace {

struct UnitDefinition {
    std::string dimension;
    std::string canonical_unit;

    // canonical = authored * scale
    double scale = 1.0;
};

const std::unordered_map<
    std::string,
    UnitDefinition>&
unitDefinitions() {

    static const std::unordered_map<
        std::string,
        UnitDefinition> units = {

        // Length: canonical millimeters.
        {"mm", {"length", "mm", 1.0}},
        {"cm", {"length", "mm", 10.0}},
        {"m",  {"length", "mm", 1000.0}},
        {"in", {"length", "mm", 25.4}},
        {"ft", {"length", "mm", 304.8}},

        // Pressure: canonical pascals.
        {"Pa",  {"pressure", "Pa", 1.0}},
        {"kPa", {"pressure", "Pa", 1000.0}},
        {"MPa", {"pressure", "Pa", 1000000.0}},
        {"psi", {"pressure", "Pa", 6894.757293168}},
        {"bar", {"pressure", "Pa", 100000.0}},

        // Angle: canonical radians.
        {"rad", {
            "angle",
            "rad",
            1.0
        }},
        {"degrees", {
            "angle",
            "rad",
            std::numbers::pi / 180.0
        }},

        // Mass: canonical kilograms.
        {"kg", {"mass", "kg", 1.0}},
        {"g",  {"mass", "kg", 0.001}},
        {"oz", {"mass", "kg", 0.028349523125}},
        {"lb", {"mass", "kg", 0.45359237}},

        // Force: canonical newtons.
        {"N",   {"force", "N", 1.0}},
        {"kN",  {"force", "N", 1000.0}},
        {"lbf", {"force", "N", 4.4482216152605}},

        // Time: canonical seconds.
        {"s",   {"time", "s", 1.0}},
        {"ms",  {"time", "s", 0.001}},
        {"min", {"time", "s", 60.0}},
        {"hr",  {"time", "s", 3600.0}},
    };

    return units;
}

const UnitDefinition& requireUnit(
    const std::string& unit) {

    const auto& units =
        unitDefinitions();

    const auto found =
        units.find(unit);

    if (found == units.end()) {
        throw std::runtime_error(
            "Unknown Engineering unit '" +
            unit +
            "'.");
    }

    return found->second;
}

const UnitDefinition& requireCompatibleUnit(
    const std::string& dimension,
    const std::string& unit) {

    const auto& definition =
        requireUnit(unit);

    if (definition.dimension != dimension) {
        throw std::runtime_error(
            "Engineering unit '" +
            unit +
            "' belongs to dimension '" +
            definition.dimension +
            "', not '" +
            dimension +
            "'.");
    }

    return definition;
}

} // namespace

Quantity Quantity::fromUnit(
    double value,
    const std::string& unit) {

    const auto& definition =
        requireUnit(unit);

    return Quantity{
        value,
        definition.dimension,
        unit
    };
}

double Quantity::canonicalValue() const {

    const auto& definition =
        requireCompatibleUnit(
            dimension,
            unit);

    return value *
           definition.scale;
}

std::string Quantity::canonicalUnit() const {

    const auto& definition =
        requireCompatibleUnit(
            dimension,
            unit);

    return definition.canonical_unit;
}

bool Quantity::isSupported() const {

    try {
        (void)requireCompatibleUnit(
            dimension,
            unit);

        return true;

    } catch (const std::runtime_error&) {
        return false;
    }
}

Quantity Quantity::convertedTo(
    const std::string& target_unit) const {

    const auto& source =
        requireCompatibleUnit(
            dimension,
            unit);

    const auto& target =
        requireCompatibleUnit(
            dimension,
            target_unit);

    const double canonical =
        value *
        source.scale;

    return Quantity{
        canonical / target.scale,
        dimension,
        target_unit
    };
}

} // namespace engineering
