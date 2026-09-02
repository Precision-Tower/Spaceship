#include "engineering/port.hpp"

#include <cassert>
#include <stdexcept>

int main() {
    using namespace engineering;

    Port port{
        .owner_id = "pipe_001",
        .port_id = "A",
        .domain = "hydraulic",
        .connection_type = "pipe_end",
        .local_position = {0.0, -0.5, 0.0},
        .local_direction = {0.0, -1.0, 0.0},
    };

    port.nominal_values["diameter"] = {
        25.4,
        "length",
        "mm"
    };

    assert(port.isOpen());
    assert(!port.isConnected());

    port.connect({"elbow_001", "A"});

    assert(!port.isOpen());
    assert(port.isConnected());
    assert(port.connected_to.has_value());
    assert(port.connected_to->object_id == "elbow_001");
    assert(port.connected_to->port_id == "A");

    bool duplicate_connection_rejected = false;

    try {
        port.connect({"pipe_002", "B"});
    } catch (const std::runtime_error&) {
        duplicate_connection_rejected = true;
    }

    assert(duplicate_connection_rejected);

    port.disconnect();

    assert(port.isOpen());
    assert(!port.connected_to.has_value());

    return 0;
}
