#pragma once

#include "engineering/geometry/feature_dag.hpp"

#include "runtime/h/geometry_actions.hpp"

#include <cstddef>

namespace engineering::geometry {

// Translate already-resolved QPS geometry execution intent into
// kernel-neutral Engineering geometry structure.
//
// QPS owns execution-context resolution.
// Engineering owns geometry structure.
//
// Runtime GeometryHandle state deliberately does not cross into the
// FeatureDAG. Named QPS stages become structural DAG dependencies.
FeatureNode makeFeatureNode(
    const qps::runtime::ResolvedGeometryAction& action);


// QPS runtime backend that compiles resolved geometry actions into
// an Engineering FeatureDAG.
//
// It also returns opaque QPS GeometryHandles so the existing QPS
// interpreter can preserve stage chaining while Engineering retains
// the authoritative structural graph.
class EngineeringGeometryDispatcher
    : public qps::runtime::GeometryActionDispatcher {

public:
    qps::runtime::RuntimeValue invoke(
        const qps::runtime::ResolvedGeometryAction& action) override;

    const FeatureDAG& featureDAG() const;

private:
    FeatureDAG dag_;
    std::size_t next_handle_id_ = 1;
};

} // namespace engineering::geometry
