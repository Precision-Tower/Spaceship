#include "engineering/geometry/feature_dag.hpp"

#include <functional>
#include <stdexcept>
#include <unordered_map>

namespace engineering::geometry {

void FeatureDAG::addFeature(FeatureNode feature) {
    if (feature.id.empty()) {
        throw std::runtime_error(
            "Geometry feature ID cannot be empty.");
    }

    if (features_.find(feature.id) != features_.end()) {
        throw std::runtime_error(
            "Duplicate geometry feature ID '" +
            feature.id +
            "'.");
    }

    const std::string id = feature.id;

    features_.emplace(
        id,
        std::move(feature));

    insertion_order_.push_back(id);
}

bool FeatureDAG::contains(
    const std::string& id) const {

    return features_.find(id) != features_.end();
}

const FeatureNode& FeatureDAG::feature(
    const std::string& id) const {

    const auto found = features_.find(id);

    if (found == features_.end()) {
        throw std::runtime_error(
            "Unknown geometry feature '" +
            id +
            "'.");
    }

    return found->second;
}

std::size_t FeatureDAG::size() const {
    return features_.size();
}

std::vector<const FeatureNode*>
FeatureDAG::orderedFeatures() const {

    enum class VisitState {
        UNVISITED,
        VISITING,
        VISITED
    };

    std::unordered_map<std::string, VisitState> states;

    for (const auto& id : insertion_order_) {
        states.emplace(
            id,
            VisitState::UNVISITED);
    }

    std::vector<const FeatureNode*> ordered;
    ordered.reserve(features_.size());

    std::function<void(const std::string&)> visit;

    visit = [&](const std::string& id) {
        const auto feature_found =
            features_.find(id);

        if (feature_found == features_.end()) {
            throw std::runtime_error(
                "Geometry feature dependency '" +
                id +
                "' does not exist.");
        }

        auto& state = states[id];

        if (state == VisitState::VISITED) {
            return;
        }

        if (state == VisitState::VISITING) {
            throw std::runtime_error(
                "Geometry feature dependency cycle detected at '" +
                id +
                "'.");
        }

        state = VisitState::VISITING;

        for (const auto& dependency :
             feature_found->second.dependencies) {

            if (features_.find(dependency) ==
                features_.end()) {

                throw std::runtime_error(
                    "Geometry feature '" +
                    id +
                    "' depends on missing feature '" +
                    dependency +
                    "'.");
            }

            visit(dependency);
        }

        state = VisitState::VISITED;

        ordered.push_back(
            &feature_found->second);
    };

    for (const auto& id : insertion_order_) {
        visit(id);
    }

    return ordered;
}

} // namespace engineering::geometry
