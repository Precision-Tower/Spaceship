#include "engineering/geometry/qps_geometry_adapter.hpp"

#include "runtime/h/geometry_action_resolver.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"

#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cassert>
#include <cmath>
#include <memory>
#include <stdexcept>
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


void cylinderTranslatesWithoutSourceDependency() {
    qps::runtime::ResolvedGeometryAction action;

    action.action_name = "cylinder";
    action.active_target = "impeller";
    action.result_stage_name = "shaft";

    action.parameters = {
        {
            "radius",
            5.0,
            false
        },
        {
            "width",
            10.0,
            true
        },
    };

    const auto feature =
        engineering::geometry::makeFeatureNode(
            action);

    assert(feature.id == "shaft");

    assert(
        feature.kind ==
        engineering::geometry::FeatureKind::PRIMITIVE);

    assert(feature.operation == "cylinder");

    assert(feature.parameters.size() == 2);

    assert(feature.parameters[0].name == "radius");
    assert(feature.parameters[0].numeric_value == 5.0);

    assert(feature.parameters[1].name == "width");
    assert(feature.parameters[1].numeric_value == 10.0);

    assert(feature.dependencies.empty());
}


void structuralCylinderUsesAuthoredBodyQuantities() {
    auto owned_program =
        std::shared_ptr<qps::ast::ProgramNode>(
            parseSource(R"qps(pus.
pu_master: dimensions:
(body: radius- 5/in;, depth- 1/in;\;);;
)qps").release());

    assert(owned_program->statements.size() == 1);

    auto* key =
        dynamic_cast<qps::ast::KeyDeclarationNode*>(
            owned_program->statements.front().get());

    assert(key != nullptr);
    assert(key->identifier_ == "pus");

    qps::ast::TermDeclarationNode* dimensions = nullptr;

    for (const auto& node : key->content_) {
        auto* pu_master =
            dynamic_cast<qps::ast::TermDeclarationNode*>(
                node.get());

        if (pu_master == nullptr ||
            pu_master->identifier_ != "pu_master") {
            continue;
        }

        for (const auto& child : pu_master->content_) {
            auto* candidate =
                dynamic_cast<qps::ast::TermDeclarationNode*>(
                    child.get());

            if (candidate != nullptr &&
                candidate->identifier_ == "dimensions") {
                dimensions = candidate;
                break;
            }
        }
    }

    assert(dimensions != nullptr);

    qps::runtime::ResolvedSymbol structure;
    structure.symbol = "pus.pu_master.dimensions";
    structure.semantic_path = {
        "pus",
        "pu_master",
        "dimensions"
    };
    structure.target_type = "TERM_DECLARATION";
    structure.target_identifier = "dimensions";
    structure.document_owner = owned_program;
    structure.target_node = dimensions;

    qps::runtime::ResolvedGeometryAction action;
    action.action_name = "cylinder";
    action.active_target = "pus_model";
    action.result_stage_name = "masterpulley";
    action.structural_arguments.push_back(
        std::move(structure));

    const auto feature =
        engineering::geometry::makeFeatureNode(
            action);

    assert(feature.id == "masterpulley");
    assert(feature.operation == "cylinder");
    assert(feature.parameters.size() == 2);

    assert(feature.parameters[0].name == "radius");
    assert(
        std::abs(
            feature.parameters[0].numeric_value -
            127.0) < 0.0000001);

    assert(feature.parameters[1].name == "width");
    assert(
        std::abs(
            feature.parameters[1].numeric_value -
            25.4) < 0.0000001);
}

void boreTranslatesSourceStageIntoDependency() {
    qps::runtime::ResolvedGeometryAction action;

    action.action_name = "bore";
    action.active_target = "impeller";

    action.result_stage_name = "shaft_bored";
    action.source_stage_name = "shaft";

    qps::runtime::GeometryHandle source;
    source.id = 1;
    source.action_name = "cylinder";
    source.active_target = "impeller";
    source.stage_name = "shaft";

    action.source_geometry = source;

    action.parameters = {
        {
            "radius",
            1.0,
            false
        },
    };

    const auto feature =
        engineering::geometry::makeFeatureNode(
            action);

    assert(feature.id == "shaft_bored");

    assert(
        feature.kind ==
        engineering::geometry::FeatureKind::BOOLEAN);

    assert(feature.operation == "bore");

    assert(feature.dependencies.size() == 1);
    assert(feature.dependencies[0] == "shaft");

    assert(feature.parameters.size() == 1);
    assert(feature.parameters[0].name == "radius");
    assert(feature.parameters[0].numeric_value == 1.0);
}

void missingResultStageIsRejected() {
    qps::runtime::ResolvedGeometryAction action;

    action.action_name = "cylinder";
    action.active_target = "impeller";

    action.parameters = {
        {
            "radius",
            5.0,
            false
        },
        {
            "width",
            10.0,
            false
        },
    };

    bool rejected = false;

    try {
        (void)engineering::geometry::makeFeatureNode(
            action);
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

void unknownActionIsRejected() {
    qps::runtime::ResolvedGeometryAction action;

    action.action_name = "warp_drive";
    action.active_target = "impeller";
    action.result_stage_name = "nonsense";

    bool rejected = false;

    try {
        (void)engineering::geometry::makeFeatureNode(
            action);
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}


void liveQpsExecutionBuildsDependencyOrderedFeatureDAG() {
    auto program = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;

body: -cylinder;

bored_body: body -bore(
radius- 0.5/n;\
);

-return bored_body;
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

    const auto result =
        interpreter.executeForResult(
            *definition.body_);

    assert(result.has_value());
    assert(result->isGeometry());

    // QPS runtime state remains capable of geometry chaining.
    assert(scope.contains("body"));
    assert(scope.contains("bored_body"));

    assert(
        scope.get("body").value.isGeometry());

    assert(
        scope.get("bored_body").value.isGeometry());

    const auto& body_handle =
        scope.get("body")
            .value
            .asGeometry("body");

    const auto& bored_handle =
        scope.get("bored_body")
            .value
            .asGeometry("bored_body");

    assert(
        bored_handle.source_handle_id.has_value());

    assert(
        *bored_handle.source_handle_id ==
        body_handle.id);

    // Engineering owns the structural result.
    const auto& dag =
        dispatcher.featureDAG();

    assert(dag.size() == 2);

    const auto& body =
        dag.feature("body");

    assert(
        body.kind ==
        engineering::geometry::FeatureKind::PRIMITIVE);

    assert(body.operation == "cylinder");
    assert(body.dependencies.empty());

    const auto& bored =
        dag.feature("bored_body");

    assert(
        bored.kind ==
        engineering::geometry::FeatureKind::BOOLEAN);

    assert(bored.operation == "bore");

    assert(bored.dependencies.size() == 1);
    assert(bored.dependencies[0] == "body");

    const auto ordered =
        dag.orderedFeatures();

    assert(ordered.size() == 2);
    assert(ordered[0]->id == "body");
    assert(ordered[1]->id == "bored_body");
}

} // namespace

int main() {
    cylinderTranslatesWithoutSourceDependency();
    structuralCylinderUsesAuthoredBodyQuantities();
    boreTranslatesSourceStageIntoDependency();
    missingResultStageIsRejected();
    unknownActionIsRejected();
    liveQpsExecutionBuildsDependencyOrderedFeatureDAG();

    return 0;
}
