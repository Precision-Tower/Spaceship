#include "engineering/port.hpp"

#include <stdexcept>

namespace engineering {

bool Port::isOpen() const {
    return state == PortState::OPEN && !connected_to.has_value();
}

bool Port::isConnected() const {
    return state == PortState::CONNECTED && connected_to.has_value();
}

void Port::connect(const PortConnectionRef& target) {
    if (!isOpen()) {
        throw std::runtime_error(
            "Cannot connect port '" + owner_id + "." + port_id +
            "': port is not open.");
    }

    if (target.object_id.empty() || target.port_id.empty()) {
        throw std::runtime_error(
            "Cannot connect port '" + owner_id + "." + port_id +
            "': target reference is incomplete.");
    }

    connected_to = target;
    state = PortState::CONNECTED;
}

void Port::disconnect() {
    connected_to.reset();
    state = PortState::OPEN;
}

} // namespace engineering
