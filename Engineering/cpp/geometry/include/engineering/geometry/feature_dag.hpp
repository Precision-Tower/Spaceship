#pragma once

#include <string>
#include <unordered_map>
#include <vector>

namespace engineering::geometry {

enum class FeatureKind {
    PRIMITIVE,
    TRANSFORM,
    BOOLEAN,
    PATTERN,
    CUSTOM
};

struct FeatureParameter {
    std::string name;
    double numeric_value = 0.0;
};

struct FeatureNode {
    std::string id;
    FeatureKind kind = FeatureKind::CUSTOM;

    // CE-OS semantic operation name.
    // Examples later may include cylinder, extrude, cut, fillet, etc.
    // This is intentionally not an OCCT class or function name.
    std::string operation;

    // Concrete values resolved from Engineering state by the
    // GeometryCompiler.
    //
    // These are build inputs, not authored instance authority.
    std::vector<FeatureParameter> parameters;

    // Feature IDs whose results are required before this feature
    // can be evaluated.
    std::vector<std::string> dependencies;
};

class FeatureDAG {
public:
    void addFeature(FeatureNode feature);

    bool contains(const std::string& id) const;

    const FeatureNode& feature(
        const std::string& id) const;

    std::size_t size() const;

    // Returns features in dependency-safe deterministic order.
    //
    // Throws when:
    // - a dependency is missing
    // - a dependency cycle exists
    std::vector<const FeatureNode*> orderedFeatures() const;

private:
    std::unordered_map<std::string, FeatureNode> features_;
    std::vector<std::string> insertion_order_;
};

} // namespace engineering::geometry
