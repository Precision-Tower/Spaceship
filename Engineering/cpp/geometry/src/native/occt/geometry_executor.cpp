#include "engineering/geometry/native/geometry_executor.hpp"

#include <BRepCheck_Analyzer.hxx>
#include <BRepMesh_IncrementalMesh.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRep_Tool.hxx>
#include <Poly_Triangulation.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Shape.hxx>
#include <TopLoc_Location.hxx>
#include <TopAbs_Orientation.hxx>
#include <TopAbs_ShapeEnum.hxx>
#include <gp_Ax2.hxx>
#include <gp_Dir.hxx>
#include <gp_Pnt.hxx>

#include <stdexcept>
#include <unordered_map>
#include <utility>

namespace engineering::geometry {

namespace {

double requiredParameter(
    const GeometryBuildStep& step,
    const std::string& name) {

    for (const auto& parameter : step.parameters) {
        if (parameter.name == name) {
            return parameter.numeric_value;
        }
    }

    throw std::runtime_error(
        "Geometry feature '" +
        step.feature_id +
        "' is missing required parameter '" +
        name +
        "'.");
}

} // namespace

class NativeGeometryExecutor::Impl {
public:
    GeometryExecutionResult execute(
        const GeometryBuildPlan& plan) {

        GeometryExecutionResult result;

        // Build into transaction-local state first.
        //
        // No native geometry becomes durable executor state until
        // every feature in the plan has completed successfully.
        std::unordered_map<
            std::uint64_t,
            TopoDS_Shape> pending_shapes;

        std::uint64_t pending_next_id =
            next_id_;

        for (const auto& step : plan.steps()) {
            if (step.operation != "cylinder") {
                throw std::runtime_error(
                    "Unsupported native geometry operation '" +
                    step.operation +
                    "'.");
            }

            const double radius =
                requiredParameter(step, "radius");

            const double width =
                requiredParameter(step, "width");

            if (radius <= 0.0) {
                throw std::runtime_error(
                    "Cylinder radius must be greater than zero.");
            }

            if (width <= 0.0) {
                throw std::runtime_error(
                    "Cylinder width must be greater than zero.");
            }

            BRepPrimAPI_MakeCylinder builder(
                radius,
                width);

            const TopoDS_Shape shape =
                builder.Shape();

            if (shape.IsNull()) {
                throw std::runtime_error(
                    "OCCT cylinder construction returned a null shape.");
            }

            const BRepCheck_Analyzer analyzer(shape);

            if (!analyzer.IsValid()) {
                throw std::runtime_error(
                    "OCCT cylinder construction produced an invalid B-rep.");
            }

            const NativeGeometryId id{
                pending_next_id++
            };

            pending_shapes.emplace(
                id.value,
                shape);

            result.features.emplace(
                step.feature_id,
                id);
        }

        // Commit only after the complete plan succeeds.
        for (auto& [id, shape] : pending_shapes) {
            shapes_.emplace(
                id,
                std::move(shape));
        }

        next_id_ =
            pending_next_id;

        return result;
    }

    bool contains(
        NativeGeometryId id) const {

        return shapes_.contains(id.value);
    }

    NativeGeometryInfo inspect(
        NativeGeometryId id) const {

        const auto found =
            shapes_.find(id.value);

        if (found == shapes_.end()) {
            throw std::runtime_error(
                "Unknown native geometry ID.");
        }

        const TopoDS_Shape& shape =
            found->second;

        NativeGeometryInfo info;

        info.valid =
            !shape.IsNull() &&
            BRepCheck_Analyzer(shape).IsValid();

        if (shape.ShapeType() == TopAbs_SOLID) {
            info.kind =
                NativeGeometryKind::SOLID;
        }

        return info;
    }

    NativeTriangleMesh triangulate(
        NativeGeometryId id,
        double deflection) const {

        if (deflection <= 0.0) {
            throw std::runtime_error(
                "Native triangulation deflection must be greater than zero.");
        }

        const auto found =
            shapes_.find(id.value);

        if (found == shapes_.end()) {
            throw std::runtime_error(
                "Unknown native geometry ID.");
        }

        const TopoDS_Shape& shape =
            found->second;

        BRepMesh_IncrementalMesh mesher(
            shape,
            deflection);

        mesher.Perform();

        if (!mesher.IsDone()) {
            throw std::runtime_error(
                "OCCT triangulation failed.");
        }

        NativeTriangleMesh mesh;

        for (TopExp_Explorer explorer(
                 shape,
                 TopAbs_FACE);
             explorer.More();
             explorer.Next()) {

            const TopoDS_Face face =
                TopoDS::Face(
                    explorer.Current());

            TopLoc_Location location;

            const Handle(Poly_Triangulation) triangulation =
                BRep_Tool::Triangulation(
                    face,
                    location);

            if (triangulation.IsNull()) {
                continue;
            }

            const std::uint32_t vertex_offset =
                static_cast<std::uint32_t>(
                    mesh.vertices.size());

            const auto transform =
                location.Transformation();

            for (Standard_Integer i = 1;
                 i <= triangulation->NbNodes();
                 ++i) {

                gp_Pnt point =
                    triangulation->Node(i);

                point.Transform(transform);

                mesh.vertices.push_back({
                    point.X(),
                    point.Y(),
                    point.Z()
                });
            }

            for (Standard_Integer i = 1;
                 i <= triangulation->NbTriangles();
                 ++i) {

                Standard_Integer n1 = 0;
                Standard_Integer n2 = 0;
                Standard_Integer n3 = 0;

                triangulation
                    ->Triangle(i)
                    .Get(
                        n1,
                        n2,
                        n3);

                // Respect face orientation so downstream rendering
                // receives consistent winding.
                if (face.Orientation() ==
                    TopAbs_REVERSED) {

                    std::swap(
                        n2,
                        n3);
                }

                mesh.indices.push_back(
                    vertex_offset +
                    static_cast<std::uint32_t>(
                        n1 - 1));

                mesh.indices.push_back(
                    vertex_offset +
                    static_cast<std::uint32_t>(
                        n2 - 1));

                mesh.indices.push_back(
                    vertex_offset +
                    static_cast<std::uint32_t>(
                        n3 - 1));
            }
        }

        if (mesh.vertices.empty() ||
            mesh.indices.empty()) {

            throw std::runtime_error(
                "OCCT triangulation produced no mesh data.");
        }

        return mesh;
    }

    std::size_t geometryCount() const {
        return shapes_.size();
    }

private:
    std::uint64_t next_id_ = 1;

    std::unordered_map<
        std::uint64_t,
        TopoDS_Shape> shapes_;
};

NativeGeometryExecutor::NativeGeometryExecutor()
    : impl_(std::make_unique<Impl>()) {}

NativeGeometryExecutor::~NativeGeometryExecutor() =
    default;

NativeGeometryExecutor::NativeGeometryExecutor(
    NativeGeometryExecutor&&) noexcept =
    default;

NativeGeometryExecutor&
NativeGeometryExecutor::operator=(
    NativeGeometryExecutor&&) noexcept =
    default;

GeometryExecutionResult
NativeGeometryExecutor::execute(
    const GeometryBuildPlan& plan) {

    return impl_->execute(plan);
}

bool NativeGeometryExecutor::contains(
    NativeGeometryId id) const {

    return impl_->contains(id);
}

NativeGeometryInfo
NativeGeometryExecutor::inspect(
    NativeGeometryId id) const {

    return impl_->inspect(id);
}

NativeTriangleMesh
NativeGeometryExecutor::triangulate(
    NativeGeometryId id,
    double deflection) const {

    return impl_->triangulate(
        id,
        deflection);
}

std::size_t
NativeGeometryExecutor::geometryCount() const {

    return impl_->geometryCount();
}

} // namespace engineering::geometry
