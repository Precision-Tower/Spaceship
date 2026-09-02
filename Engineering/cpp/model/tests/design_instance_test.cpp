#include "engineering/design_instance.hpp"

#include <cassert>
#include <stdexcept>

int main() {
    using namespace engineering;

    DesignInstance first(
        "turbine_instance_001",
        "defs.KE.U.p");

    DesignInstance second(
        "turbine_instance_002",
        "defs.KE.U.p");

    first.setBinding({
        .name = "radius",
        .declared_type = BindingDeclaredType::NUMERIC,
        .has_default = false,
        .explicit_numeric_value = 125.0,
        .resolved = true,
        .numeric_value = 125.0,
        .provenance = BindingProvenance::SUPPLIED,
    });

    first.setBinding({
        .name = "diameter",
        .declared_type = BindingDeclaredType::NUMERIC,
        .has_default = false,
        .explicit_numeric_value = std::nullopt,
        .resolved = true,
        .numeric_value = 250.0,
        .provenance = BindingProvenance::DERIVED,
    });

    second.setBinding({
        .name = "radius",
        .declared_type = BindingDeclaredType::NUMERIC,
        .has_default = false,
        .explicit_numeric_value = 200.0,
        .resolved = true,
        .numeric_value = 200.0,
        .provenance = BindingProvenance::SUPPLIED,
    });

    assert(first.instanceId() != second.instanceId());
    assert(first.definitionRef() == second.definitionRef());

    assert(first.binding("radius").numeric_value == 125.0);
    assert(
        first.binding("diameter").provenance ==
        BindingProvenance::DERIVED);
    assert(second.binding("radius").numeric_value == 200.0);

    first.setPlacement({
        .position = {1.0, 2.0, 3.0},
        .rotation_degrees = {0.0, 0.0, 90.0},
    });

    assert(first.placement().position.x == 1.0);
    assert(first.placement().rotation_degrees.z == 90.0);

    Port inlet{
        .owner_id = first.instanceId(),
        .port_id = "inlet",
        .domain = "hydraulic",
        .connection_type = "pipe_end",
        .local_position = {-1.0, 0.0, 0.0},
        .local_direction = {-1.0, 0.0, 0.0},
    };

    first.addPort(inlet);

    assert(first.hasPort("inlet"));
    assert(first.port("inlet").isOpen());

    first.port("inlet").connect({
        "supply_pipe_001",
        "B"
    });

    assert(first.port("inlet").isConnected());

    bool wrong_owner_rejected = false;

    try {
        first.addPort({
            .owner_id = "some_other_instance",
            .port_id = "bad_port",
        });
    } catch (const std::runtime_error&) {
        wrong_owner_rejected = true;
    }

    assert(wrong_owner_rejected);

    return 0;
}
