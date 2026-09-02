#include "engineering/design_instance.hpp"

#include <stdexcept>
#include <utility>

namespace engineering {

DesignInstance::DesignInstance(
    std::string instance_id,
    std::string definition_ref)
    : instance_id_(std::move(instance_id)),
      definition_ref_(std::move(definition_ref)) {

    if (instance_id_.empty()) {
        throw std::runtime_error(
            "DesignInstance requires a non-empty instance identity.");
    }

    if (definition_ref_.empty()) {
        throw std::runtime_error(
            "DesignInstance requires a non-empty definition reference.");
    }
}

const std::string& DesignInstance::instanceId() const {
    return instance_id_;
}

const std::string& DesignInstance::definitionRef() const {
    return definition_ref_;
}

void DesignInstance::setDefinitionSource(
    const EngineeringSourceIdentity& source) {

    definition_source_ = source;
}

const std::optional<EngineeringSourceIdentity>&
DesignInstance::definitionSource() const {

    return definition_source_;
}

void DesignInstance::setEvaluatedFrom(
    const EngineeringSourceIdentity& source) {

    evaluated_from_ = source;
}

void DesignInstance::clearEvaluatedFrom() {
    evaluated_from_.reset();
}

const std::optional<EngineeringSourceIdentity>&
DesignInstance::evaluatedFrom() const {

    return evaluated_from_;
}

void DesignInstance::setBinding(
    const EngineeringBinding& binding) {

    if (binding.name.empty()) {
        throw std::runtime_error(
            "Engineering binding requires a non-empty name.");
    }

    bindings_.insert_or_assign(binding.name, binding);
}

bool DesignInstance::hasBinding(
    const std::string& name) const {

    return bindings_.contains(name);
}

const EngineeringBinding& DesignInstance::binding(
    const std::string& name) const {

    const auto found = bindings_.find(name);

    if (found == bindings_.end()) {
        throw std::runtime_error(
            "Unknown engineering binding '" + name + "'.");
    }

    return found->second;
}

const std::unordered_map<
    std::string,
    EngineeringBinding>&
DesignInstance::bindings() const {

    return bindings_;
}

void DesignInstance::setPlacement(
    const Placement& placement) {

    placement_ = placement;
}

const Placement& DesignInstance::placement() const {
    return placement_;
}

void DesignInstance::addPort(const Port& port) {
    if (port.port_id.empty()) {
        throw std::runtime_error(
            "Port requires a non-empty port identity.");
    }

    if (port.owner_id != instance_id_) {
        throw std::runtime_error(
            "Port owner '" + port.owner_id +
            "' does not match DesignInstance '" +
            instance_id_ + "'.");
    }

    if (hasPort(port.port_id)) {
        throw std::runtime_error(
            "Duplicate port '" + port.port_id + "'.");
    }

    ports_.push_back(port);
}

bool DesignInstance::hasPort(
    const std::string& port_id) const {

    for (const Port& candidate : ports_) {
        if (candidate.port_id == port_id) {
            return true;
        }
    }

    return false;
}

const Port& DesignInstance::port(
    const std::string& port_id) const {

    for (const Port& candidate : ports_) {
        if (candidate.port_id == port_id) {
            return candidate;
        }
    }

    throw std::runtime_error(
        "Unknown port '" + port_id + "'.");
}

Port& DesignInstance::port(
    const std::string& port_id) {

    for (Port& candidate : ports_) {
        if (candidate.port_id == port_id) {
            return candidate;
        }
    }

    throw std::runtime_error(
        "Unknown port '" + port_id + "'.");
}

const std::vector<Port>& DesignInstance::ports() const {
    return ports_;
}

} // namespace engineering
