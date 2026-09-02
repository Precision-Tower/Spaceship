#pragma once

#include "engineering/port.hpp"

#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace engineering {

enum class BindingDeclaredType {
    NUMERIC
};

enum class BindingProvenance {
    UNRESOLVED,
    SUPPLIED,
    SUPPLIED_OR_DEFAULT,
    DERIVED
};

struct EngineeringBinding {
    std::string name;

    std::optional<BindingDeclaredType> declared_type;
    bool has_default = false;

    // Engineering-owned explicit instance override.
    //
    // Absence means the instance has not explicitly diverged from
    // its QPS definition for this binding.
    std::optional<double> explicit_numeric_value;

    // Current evaluated value observed from the latest execution.
    //
    // This may originate from either an explicit override, a QPS
    // default, or a derived semantic result. It is not itself
    // authority for the next execution.
    bool resolved = false;
    std::optional<double> numeric_value;

    BindingProvenance provenance =
        BindingProvenance::UNRESOLVED;

    bool operator==(const EngineeringBinding&) const = default;
};

struct EngineeringSourceIdentity {
    // Workspace-relative source document identity.
    //
    // This is source provenance, not revision identity.
    std::string source_document;

    bool operator==(const EngineeringSourceIdentity&) const = default;
};

struct Placement {
    Vector3 position;
    Vector3 rotation_degrees;

    bool operator==(const Placement&) const = default;
};

class DesignInstance {
public:
    DesignInstance(
        std::string instance_id,
        std::string definition_ref);

    const std::string& instanceId() const;
    const std::string& definitionRef() const;

    void setDefinitionSource(
        const EngineeringSourceIdentity& source);
    const std::optional<EngineeringSourceIdentity>&
    definitionSource() const;

    void setEvaluatedFrom(
        const EngineeringSourceIdentity& source);
    void clearEvaluatedFrom();
    const std::optional<EngineeringSourceIdentity>&
    evaluatedFrom() const;

    void setBinding(const EngineeringBinding& binding);
    bool hasBinding(const std::string& name) const;
    const EngineeringBinding& binding(const std::string& name) const;

    const std::unordered_map<std::string, EngineeringBinding>&
    bindings() const;

    void setPlacement(const Placement& placement);
    const Placement& placement() const;

    void addPort(const Port& port);
    bool hasPort(const std::string& port_id) const;
    const Port& port(const std::string& port_id) const;
    Port& port(const std::string& port_id);

    const std::vector<Port>& ports() const;

private:
    std::string instance_id_;
    std::string definition_ref_;

    std::optional<EngineeringSourceIdentity> definition_source_;
    std::optional<EngineeringSourceIdentity> evaluated_from_;

    std::unordered_map<std::string, EngineeringBinding> bindings_;
    Placement placement_;
    std::vector<Port> ports_;
};

} // namespace engineering
