#include "engineering/quantity.hpp"

#include <cassert>
#include <cmath>
#include <stdexcept>

namespace {

void requireNear(
    double actual,
    double expected,
    double tolerance = 1e-9) {

    assert(
        std::abs(actual - expected) <=
        tolerance);
}

} // namespace


void unitInfersDimension() {
    {
        const auto q =
            engineering::Quantity::fromUnit(
                1.0,
                "in");

        assert(q.value == 1.0);
        assert(q.dimension == "length");
        assert(q.unit == "in");
        assert(q.canonicalValue() == 25.4);
        assert(q.canonicalUnit() == "mm");
    }

    {
        const auto q =
            engineering::Quantity::fromUnit(
                120.0,
                "psi");

        assert(q.dimension == "pressure");
        assert(q.unit == "psi");
        assert(q.canonicalUnit() == "Pa");
    }

    {
        const auto q =
            engineering::Quantity::fromUnit(
                90.0,
                "degrees");

        assert(q.dimension == "angle");
        assert(q.unit == "degrees");
        assert(q.canonicalUnit() == "rad");
    }

    bool rejected_unknown = false;

    try {
        (void)engineering::Quantity::fromUnit(
            1.0,
            "definitely_not_a_unit");
    } catch (const std::runtime_error&) {
        rejected_unknown = true;
    }

    assert(rejected_unknown);
}

int main() {
    unitInfersDimension();

    // Existing aggregate construction remains valid.
    const engineering::Quantity diameter{
        25.4,
        "length",
        "mm"
    };

    assert(diameter.value == 25.4);
    assert(diameter.dimension == "length");
    assert(diameter.unit == "mm");
    assert(diameter.isSupported());

    requireNear(
        diameter.canonicalValue(),
        25.4);

    assert(
        diameter.canonicalUnit() ==
        "mm");

    // Imperial length authored naturally, normalized to mm.
    const engineering::Quantity inch{
        1.0,
        "length",
        "in"
    };

    requireNear(
        inch.canonicalValue(),
        25.4);

    const auto inch_as_mm =
        inch.convertedTo("mm");

    requireNear(
        inch_as_mm.value,
        25.4);

    assert(inch_as_mm.unit == "mm");

    // Equivalent authored lengths resolve to identical canonical values.
    const engineering::Quantity foot{
        1.0,
        "length",
        "ft"
    };

    const engineering::Quantity metric_foot{
        304.8,
        "length",
        "mm"
    };

    requireNear(
        foot.canonicalValue(),
        metric_foot.canonicalValue());

    const engineering::Quantity centimeter{
        2.54,
        "length",
        "cm"
    };

    requireNear(
        centimeter.canonicalValue(),
        25.4);

    const engineering::Quantity meter{
        0.0254,
        "length",
        "m"
    };

    requireNear(
        meter.canonicalValue(),
        25.4);

    // Pressure may be authored in PSI while Engineering calculates in Pa.
    const engineering::Quantity pressure{
        120.0,
        "pressure",
        "psi"
    };

    requireNear(
        pressure.canonicalValue(),
        120.0 * 6894.757293168,
        1e-6);

    assert(
        pressure.canonicalUnit() ==
        "Pa");

    const auto pressure_kpa =
        pressure.convertedTo("kPa");

    requireNear(
        pressure_kpa.value,
        pressure.canonicalValue() /
            1000.0,
        1e-9);

    // Angles normalize to radians.
    const engineering::Quantity right_angle{
        90.0,
        "angle",
        "degrees"
    };

    requireNear(
        right_angle.canonicalValue(),
        std::acos(-1.0) / 2.0);

    assert(
        right_angle.canonicalUnit() ==
        "rad");

    // Additional foundational dimensions.
    requireNear(
        engineering::Quantity{
            1.0,
            "mass",
            "lb"
        }.canonicalValue(),
        0.45359237);

    requireNear(
        engineering::Quantity{
            1.0,
            "force",
            "lbf"
        }.canonicalValue(),
        4.4482216152605);

    requireNear(
        engineering::Quantity{
            1.0,
            "time",
            "hr"
        }.canonicalValue(),
        3600.0);

    // Wrong physical dimensions are rejected.
    const engineering::Quantity nonsense{
        10.0,
        "length",
        "psi"
    };

    assert(!nonsense.isSupported());

    bool mismatch_rejected = false;

    try {
        (void)nonsense.canonicalValue();
    } catch (const std::runtime_error&) {
        mismatch_rejected = true;
    }

    assert(mismatch_rejected);

    // Cross-dimension conversion is forbidden.
    bool conversion_rejected = false;

    try {
        (void)inch.convertedTo("psi");
    } catch (const std::runtime_error&) {
        conversion_rejected = true;
    }

    assert(conversion_rejected);

    // Unknown units fail rather than silently becoming dimensionless.
    const engineering::Quantity unknown{
        1.0,
        "length",
        "furlong_of_doom"
    };

    assert(!unknown.isSupported());

    return 0;
}
