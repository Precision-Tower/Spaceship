#include "engineering/geometry/build_plan.hpp"
#include "engineering/geometry/native/geometry_executor.hpp"
#include "engineering/geometry/qps_geometry_adapter.hpp"

#include "runtime/h/interpreter.hpp"
#include "runtime/h/execution_engine.hpp"
#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/path_resolver.hpp"
#include "runtime/h/symbol_resolver.hpp"
#include "runtime/h/symbol_table.hpp"

#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>

namespace {

std::unique_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream stream(source);
    qps::tokens::Lexer lexer(stream);
    qps::parser::Parser parser(lexer);

    return parser.parseProgram();
}

const qps::ast::ExecutionDefinitionNode&
requireDefinition(
    const qps::ast::ProgramNode& program) {

    assert(program.statements.size() == 1);

    auto* definition =
        dynamic_cast<
            qps::ast::ExecutionDefinitionNode*>(
                program.statements.front().get());

    assert(definition != nullptr);
    assert(definition->body_ != nullptr);

    return *definition;
}

} // namespace

void legacyGeometryExecutionBuildsNativeSolid() {
    auto program = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;

body: -cylinder;

-return body;
})qps");

    const auto& definition =
        requireDefinition(*program);

    assert(
        definition.domain_ ==
        qps::ast::ExecutionDomain::GEOMETRY);

    qps::runtime::ExecutionScope scope;

    engineering::geometry::EngineeringGeometryDispatcher
        dispatcher;

    qps::runtime::InterpreterOptions options;
    options.domain =
        qps::ast::ExecutionDomain::GEOMETRY;
    options.active_target =
        definition.identifier_;
    options.geometry_dispatcher =
        &dispatcher;
    options.allow_return = true;

    qps::runtime::Interpreter interpreter(
        scope,
        qps::runtime::FunctionTable{},
        options);

    const auto qps_result =
        interpreter.executeForResult(
            *definition.body_);

    assert(qps_result.has_value());
    assert(qps_result->isGeometry());

    const auto& dag =
        dispatcher.featureDAG();

    assert(dag.size() == 1);
    assert(dag.contains("body"));

    const auto plan =
        engineering::geometry::GeometryBuildPlan::
            fromFeatureDAG(dag);

    assert(plan.size() == 1);

    engineering::geometry::NativeGeometryExecutor
        native_executor;

    const auto native_result =
        native_executor.execute(plan);

    assert(native_result.features.size() == 1);
    assert(native_result.features.contains("body"));

    const auto native_id =
        native_result.features.at("body");

    assert(native_id.value != 0);
    assert(native_executor.contains(native_id));
    assert(native_executor.geometryCount() == 1);

    const auto info =
        native_executor.inspect(native_id);

    assert(info.valid);

    assert(
        info.kind ==
        engineering::geometry::NativeGeometryKind::SOLID);

}


void authoredStructuralCylinderBuildsNativeSolid() {
    auto program = parseSource(R"qps({pus_model:
master: [>pus.pu_master.dimensions];
@masterpulley: -cylinder(master);
})qps");

    const auto& definition =
        requireDefinition(*program);

    assert(
        definition.domain_ ==
        qps::ast::ExecutionDomain::GENERIC);

    const std::filesystem::path engineering_root =
        std::filesystem::path(__FILE__)
            .parent_path()  // tests
            .parent_path()  // geometry
            .parent_path()  // cpp
            .parent_path(); // Engineering

    qps::runtime::PathResolver paths(
        engineering_root / "qps");

    qps::runtime::DocumentLoader loader;
    qps::runtime::DocumentStore documents(loader);

    qps::runtime::SymbolResolver symbols(
        paths,
        documents);

    engineering::geometry::EngineeringGeometryDispatcher
        dispatcher;

    qps::runtime::ExecutionEngine engine(
        symbols,
        dispatcher);

    engine.registerDefinition(
        definition,
        "defs/semantic_walk/pulley_master.qps");

    const auto execution =
        engine.instantiate(
            "pus_model",
            {});

    assert(execution.scope.contains("master"));

    const auto& master =
        execution.scope.get("master").value;

    assert(
        master.kind() ==
        qps::runtime::RuntimeValue::Kind::STRUCTURE);

    assert(execution.scope.contains("masterpulley"));

    const auto& masterpulley =
        execution.scope.get("masterpulley").value;

    assert(masterpulley.isGeometry());

    const auto& dag =
        dispatcher.featureDAG();

    assert(dag.size() == 1);
    assert(dag.contains("masterpulley"));

    const auto& feature =
        dag.feature("masterpulley");

    assert(
        feature.kind ==
        engineering::geometry::FeatureKind::PRIMITIVE);

    assert(feature.operation == "cylinder");
    assert(feature.dependencies.empty());

    bool found_radius = false;
    bool found_width = false;

    for (const auto& parameter : feature.parameters) {
        if (parameter.name == "radius") {
            assert(parameter.numeric_value == 127.0);
            found_radius = true;
        }

        if (parameter.name == "width") {
            assert(parameter.numeric_value == 25.4);
            found_width = true;
        }
    }

    assert(found_radius);
    assert(found_width);

    const auto plan =
        engineering::geometry::GeometryBuildPlan::
            fromFeatureDAG(dag);

    assert(plan.size() == 1);

    engineering::geometry::NativeGeometryExecutor
        native_executor;

    const auto native_result =
        native_executor.execute(plan);

    assert(native_result.features.size() == 1);

    assert(
        native_result.features.contains(
            "masterpulley"));

    const auto native_id =
        native_result.features.at(
            "masterpulley");

    assert(native_id.value != 0);
    assert(native_executor.contains(native_id));
    assert(native_executor.geometryCount() == 1);

    const auto info =
        native_executor.inspect(native_id);

    assert(info.valid);

    assert(
        info.kind ==
        engineering::geometry::
            NativeGeometryKind::SOLID);

    const auto mesh =
        native_executor.triangulate(
            native_id);

    assert(!mesh.vertices.empty());
    assert(!mesh.indices.empty());
    assert(mesh.indices.size() % 3 == 0);

    for (const auto index : mesh.indices) {
        assert(index < mesh.vertices.size());
    }

    const std::filesystem::path dashboard_root =
        engineering_root.parent_path();

    const std::filesystem::path viewer_root =
        dashboard_root /
        "local" /
        "Godot_QPS_Viewer";

    std::filesystem::create_directories(
        viewer_root);

    const auto mesh_path =
        viewer_root /
        "masterpulley.json";

    std::ofstream out(mesh_path);

    if (!out) {
        throw std::runtime_error(
            "Failed to open Godot mesh output: " +
            mesh_path.string());
    }

    out << "{\n";

    out << "  \"vertices\": [\n";

    for (std::size_t i = 0;
         i < mesh.vertices.size();
         ++i) {

        const auto& vertex =
            mesh.vertices[i];

        out
            << "    ["
            << vertex.x << ", "
            << vertex.y << ", "
            << vertex.z << "]";

        if (i + 1 != mesh.vertices.size()) {
            out << ",";
        }

        out << "\n";
    }

    out << "  ],\n";

    out << "  \"indices\": [";

    for (std::size_t i = 0;
         i < mesh.indices.size();
         ++i) {

        if (i != 0) {
            out << ", ";
        }

        out << mesh.indices[i];
    }

    out << "]\n";
    out << "}\n";

    std::cout
        << "Wrote QPS master pulley mesh: "
        << mesh_path
        << "\n";

    std::cout
        << "Vertices: "
        << mesh.vertices.size()
        << ", triangles: "
        << mesh.indices.size() / 3
        << "\n";
}


int main() {
    legacyGeometryExecutionBuildsNativeSolid();
    authoredStructuralCylinderBuildsNativeSolid();

    return 0;
}
