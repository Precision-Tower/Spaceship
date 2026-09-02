#pragma once

#include "engineering/quantity.hpp"

#include <optional>
#include <string>
#include <unordered_map>

namespace engineering {

struct Vector3 {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;

    bool operator==(const Vector3&) const = default;
};

struct PortConnectionRef {
    std::string object_id;
    std::string port_id;

    bool operator==(const PortConnectionRef&) const = default;
};

enum class PortState {
    OPEN,
    CONNECTED
};

struct Port {
    std::string owner_id;
    std::string port_id;

    std::string domain;
    std::string connection_type;

    Vector3 local_position;
    Vector3 local_direction;

    std::unordered_map<std::string, Quantity> nominal_values;

    PortState state = PortState::OPEN;
    std::optional<PortConnectionRef> connected_to;

    bool isOpen() const;
    bool isConnected() const;

    void connect(const PortConnectionRef& target);
    void disconnect();
};

} // namespace engineering
