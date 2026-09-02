#pragma once

#include "engineering/geometry/build_plan.hpp"

#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace engineering::geometry {

struct NativeGeometryId {
    std::uint64_t value = 0;

    bool operator==(const NativeGeometryId&) const = default;
};

struct GeometryExecutionResult {
    std::unordered_map<std::string, NativeGeometryId> features;
};

enum class NativeGeometryKind {
    UNKNOWN,
    SOLID
};

struct NativeGeometryInfo {
    NativeGeometryKind kind = NativeGeometryKind::UNKNOWN;
    bool valid = false;
};

struct NativeMeshVertex {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

struct NativeTriangleMesh {
    std::vector<NativeMeshVertex> vertices;
    std::vector<std::uint32_t> indices;
};

class NativeGeometryExecutor {
public:
    NativeGeometryExecutor();
    ~NativeGeometryExecutor();

    NativeGeometryExecutor(NativeGeometryExecutor&&) noexcept;
    NativeGeometryExecutor& operator=(NativeGeometryExecutor&&) noexcept;

    NativeGeometryExecutor(const NativeGeometryExecutor&) = delete;
    NativeGeometryExecutor& operator=(const NativeGeometryExecutor&) = delete;

    GeometryExecutionResult execute(
        const GeometryBuildPlan& plan);

    bool contains(NativeGeometryId id) const;

    NativeGeometryInfo inspect(
        NativeGeometryId id) const;

    NativeTriangleMesh triangulate(
        NativeGeometryId id,
        double deflection = 0.1) const;

    std::size_t geometryCount() const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace engineering::geometry
