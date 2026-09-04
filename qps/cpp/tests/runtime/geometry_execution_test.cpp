#include "ast/ast_node.hpp"
#include "ast/ast_utils.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/execution_engine.hpp"
#include "runtime/h/geometry_actions.hpp"
#include "runtime/h/geometry_action_resolver.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <functional>
#include <initializer_list>
#include <iostream>
#include <memory>
#include <optional>
#include <cassert>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string& message) {
    if (!condition) {
        fail(message);
    }
}

std::string numberToString(double value) {
    std::ostringstream out;
    out << value;
    return out.str();
}

void assertNear(
    double actual,
    double expected,
    const std::string& context) {

    if (std::fabs(actual - expected) > 0.0000001) {
        fail(
            context + ": expected " + numberToString(expected) +
            ", got " + numberToString(actual) + ".");
    }
}

std::unique_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);
    return parser.parseProgram();
}

void expectFailure(
    const std::function<void()>& run,
    const std::vector<std::string>& message_fragments) {

    try {
        run();
    } catch (const std::exception& e) {
        const std::string message = e.what();

        for (const auto& fragment : message_fragments) {
            require(
                message.find(fragment) != std::string::npos,
                "Expected failure containing " + fragment +
                ", got " + message + ".");
        }

        return;
    }

    fail("Expected failure did not occur.");
}

void expectParseFailure(
    const std::string& source,
    const std::vector<std::string>& message_fragments) {

    expectFailure(
        [&]() {
            (void)parseSource(source);
        },
        message_fragments);
}

const qps::ast::ExecutionDefinitionNode& requireDefinition(
    const qps::ast::ProgramNode& program,
    std::size_t index = 0) {

    require(
        program.statements.size() > index,
        "Expected execution definition at index " +
        std::to_string(index) + ".");

    auto* definition =
        dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
            program.statements[index].get());

    require(definition != nullptr, "Expected ExecutionDefinitionNode.");
    return *definition;
}

const qps::ast::TermDeclarationNode& requireTerm(
    const qps::ast::ExecutionDefinitionNode& definition,
    std::size_t index,
    const std::string& name) {

    require(definition.body_ != nullptr, "Definition body missing.");
    require(
        definition.body_->statements.size() > index,
        "Expected definition statement at index " +
        std::to_string(index) + ".");

    auto* term =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            definition.body_->statements[index].get());

    require(term != nullptr, "Expected TermDeclarationNode.");
    require(term->identifier_ == name, "Expected Term named " + name + ".");
    return *term;
}

const qps::ast::ExecutionActionNode& requireAction(
    const qps::ast::TermDeclarationNode& term) {

    require(
        term.content_.size() == 1,
        "Geometry Term should contain exactly one action.");

    auto* action =
        dynamic_cast<qps::ast::ExecutionActionNode*>(
            term.content_.front().get());

    require(action != nullptr, "Expected ExecutionActionNode in Term.");
    return *action;
}

const qps::ast::IdentifierNode& requireIdentifier(
    const qps::ast::AstNode* node,
    const std::string& context) {

    auto* identifier =
        dynamic_cast<const qps::ast::IdentifierNode*>(node);

    require(identifier != nullptr, context + " should be an IdentifierNode.");
    return *identifier;
}

const qps::runtime::RuntimeBinding& requireBinding(
    const qps::runtime::ExecutionScope& scope,
    const std::string& name) {

    require(scope.contains(name), "Expected binding named " + name + ".");
    return scope.get(name);
}

const qps::runtime::GeometryHandle& requireGeometryBinding(
    const qps::runtime::ExecutionScope& scope,
    const std::string& name) {

    const auto& binding = requireBinding(scope, name);
    require(binding.value.isGeometry(), name + " should be geometry.");
    return binding.value.asGeometry(name);
}

const qps::runtime::GeometryParameterValue& requireParameter(
    const qps::runtime::GeometryHandle& handle,
    const std::string& name) {

    for (const auto& parameter : handle.parameters) {
        if (parameter.name == name) {
            return parameter;
        }
    }

    fail("Expected geometry parameter named " + name + ".");
}

void assertParameter(
    const qps::runtime::GeometryHandle& handle,
    const std::string& name,
    double expected_value,
    bool expected_explicit_override) {

    const auto& parameter = requireParameter(handle, name);
    assertNear(parameter.value, expected_value, name + " parameter");
    require(
        parameter.explicit_override == expected_explicit_override,
        name + " explicit override flag mismatch.");
}

qps::runtime::ExecutionInstance instantiateGeometry(
    const std::string& definition_source,
    const std::unordered_map<std::string, double>& overrides = {}) {

    auto program = parseSource(definition_source);
    const auto& definition = requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    engine.registerDefinition(definition);
    return engine.instantiateNumeric(definition.identifier_, overrides);
}

std::vector<qps::runtime::ExecutionInstance> executeProgram(
    const std::string& source) {

    auto program = parseSource(source);
    qps::runtime::ExecutionEngine engine;
    return engine.execute(*program);
}

void expectRuntimeFailure(
    const std::string& source,
    const std::vector<std::string>& message_fragments) {

    expectFailure(
        [&]() {
            (void)executeProgram(source);
        },
        message_fragments);
}

std::string typeHintName(
    const std::optional<qps::tokens::TokenType>& hint) {

    if (!hint.has_value()) {
        return "none";
    }

    switch (*hint) {
        case qps::tokens::TokenType::TYPE_NUMERIC:
            return "numeric";
        case qps::tokens::TokenType::TYPE_PATH:
            return "path";
        case qps::tokens::TokenType::TYPE_ALPHANUM:
            return "alphanum";
        case qps::tokens::TokenType::TYPE_BOOLEAN:
            return "boolean";
        case qps::tokens::TokenType::TYPE_NULL:
            return "null";
        default:
            return "other";
    }
}

std::string targetSignature(const qps::ast::AstNode& target) {
    if (auto* symbol =
            dynamic_cast<const qps::ast::SymbolReferenceNode*>(
                &target)) {
        return "semantic:" + symbol->getSymbol();
    }

    if (auto* identifier =
            dynamic_cast<const qps::ast::IdentifierNode*>(
                &target)) {
        return "identifier:" + identifier->name_;
    }

    return "target:other";
}

std::string valueSignature(const qps::ast::AstNode* value) {
    if (value == nullptr) {
        return "required";
    }

    if (auto* numeric =
            dynamic_cast<const qps::ast::NumericLiteralNode*>(
                value)) {
        return "number:" + numberToString(numeric->value_);
    }

    if (auto* identifier =
            dynamic_cast<const qps::ast::IdentifierNode*>(
                value)) {
        return "identifier:" + identifier->name_;
    }

    if (auto* symbol =
            dynamic_cast<const qps::ast::SymbolReferenceNode*>(
                value)) {
        return "semantic:" + symbol->getSymbol();
    }

    return "value:other";
}

std::string returnSignature(
    const qps::ast::ReturnStatementNode& statement) {

    if (!statement.expression_) {
        return "return:none";
    }

    return "return:" + valueSignature(statement.expression_.get());
}

std::vector<std::string> semanticStructure(
    const qps::ast::ExecutionDefinitionNode& definition) {

    std::vector<std::string> result;
    result.push_back(
        "definition:" + definition.identifier_ + ":domain:" +
        (definition.domain_ == qps::ast::ExecutionDomain::GEOMETRY
             ? "geometry"
             : "generic"));

    for (const auto& statement : definition.body_->statements) {
        if (auto* item =
                dynamic_cast<const qps::ast::ItemDeclarationNode*>(
                    statement.get())) {
            result.push_back(
                "item:" + targetSignature(*item->getTarget()) +
                ":value:" + valueSignature(item->value_node_.get()) +
                ":type:" + typeHintName(item->type_hint_));
            continue;
        }

        if (auto* term =
                dynamic_cast<const qps::ast::TermDeclarationNode*>(
                    statement.get())) {
            const auto& action = requireAction(*term);
            std::string signature =
                "term:" + term->identifier_ + ":action:" +
                action.action_name_;

            if (action.getSource()) {
                signature +=
                    ":source:" +
                    requireIdentifier(action.getSource(), "action source").name_;
            } else {
                signature += ":source:none";
            }

            signature +=
                ":params:" +
                std::to_string(
                    action.getParameters()
                        ? action.getParameters()->elements.size()
                        : 0);

            result.push_back(signature);
            continue;
        }

        if (auto* action =
                dynamic_cast<const qps::ast::ExecutionActionNode*>(
                    statement.get())) {
            result.push_back("action:" + action->action_name_);
            continue;
        }

        if (auto* return_statement =
                dynamic_cast<const qps::ast::ReturnStatementNode*>(
                    statement.get())) {
            result.push_back(returnSignature(*return_statement));
            continue;
        }

        if (auto* calculation =
                dynamic_cast<const qps::ast::CalculationNode*>(
                    statement.get())) {
            result.push_back(
                "calculation:" +
                targetSignature(*calculation->getTarget()));
            continue;
        }

        result.push_back("statement:other");
    }

    return result;
}

void geometryDomainParsing() {
    auto program = parseSource(R"qps({@geometry_case:
})qps");

    const auto& definition = requireDefinition(*program);
    require(
        definition.domain_ == qps::ast::ExecutionDomain::GEOMETRY,
        "Expected GEOMETRY execution domain.");
}

void whitespaceIsNonSemantic() {
    auto compact = parseSource(
        R"qps({@pu1:[>radius]-3/n;[>width]-1/n;body:-cylinder;-return body;})qps");

    auto expanded = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;

body: -cylinder;

-return body;
})qps");

    require(
        semanticStructure(requireDefinition(*compact)) ==
            semanticStructure(requireDefinition(*expanded)),
        "Compact and expanded geometry definitions should match semantically.");
}

void semicolonRemainsStatementDelimiter() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
-return body;
})qps");

    require(instance.result.has_value(), "Valid semicolon-delimited geometry should execute.");

    expectParseFailure(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder
-return body;
})qps",
        {"Expected token type", "-return"});
}

void namedFeatureStageParses() {
    auto program = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
})qps");

    const auto& term = requireTerm(requireDefinition(*program), 2, "body");
    const auto& action = requireAction(term);

    require(action.action_name_ == "cylinder", "Expected cylinder action.");
    require(action.getSource() == nullptr, "Cylinder should not have a source stage.");
}

void sourceFeatureStageParses() {
    auto program = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
bored_body: body -bore(
radius- 0.5/n;
);
})qps");

    const auto& term = requireTerm(requireDefinition(*program), 3, "bored_body");
    const auto& action = requireAction(term);

    require(action.action_name_ == "bore", "Expected bore action.");
    require(
        requireIdentifier(action.getSource(), "bore source").name_ == "body",
        "Expected source stage named body.");
}

void contextParameterResolution() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]-
[>width]-
body: -cylinder;
-return body;
})qps",
        {{"radius", 3.0}, {"width", 1.0}});

    const auto& body = requireGeometryBinding(instance.scope, "body");
    require(body.action_name == "cylinder", "Expected cylinder result.");
    assertParameter(body, "radius", 3.0, false);
    assertParameter(body, "width", 1.0, false);
}

void explicitItemOverrideWins() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]-
[>width]-
body: -cylinder(
radius- 4/n;
);
-return body;
})qps",
        {{"radius", 3.0}, {"width", 1.0}});

    const auto& body = requireGeometryBinding(instance.scope, "body");
    assertParameter(body, "radius", 4.0, true);
    assertParameter(body, "width", 1.0, false);
}

void missingRequiredParameterFailsClearly() {
    expectFailure(
        [&]() {
            (void)instantiateGeometry(
                R"qps({@pu1:
[>radius]-
body: -cylinder;
})qps",
                {{"radius", 3.0}});
        },
        {"Missing required GEOMETRY parameter", "width", "-cylinder"});
}

void unknownActionFailsAtRuntime() {
    expectFailure(
        [&]() {
            (void)instantiateGeometry(
                R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -dragon_cannon;
})qps");
        },
        {"Unknown GEOMETRY action", "-dragon_cannon"});
}

void geometryPrimitiveIsNotAHostPrimitive() {
    auto program = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
})qps");

    const auto& action = requireAction(
        requireTerm(requireDefinition(*program), 2, "body"));

    qps::runtime::ExecutionScope scope;
    qps::runtime::Interpreter interpreter(scope);

    expectFailure(
        [&]() {
            interpreter.executeStatement(action);
        },
        {"Unknown host execution action", "-cylinder"});
}

void geometryResultTypeIsOpaqueGeometry() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
-return body;
})qps");

    require(instance.result.has_value(), "Expected geometry result.");
    require(
        instance.result->kind() == qps::runtime::RuntimeValue::Kind::GEOMETRY,
        "Result kind should be GEOMETRY.");
    require(instance.result->isGeometry(), "Result should report isGeometry().");

    const auto& handle = instance.result->asGeometry("result");
    require(handle.id != 0, "Geometry handle should be opaque and nonzero.");
}

void featureStageStoredInScope() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
})qps");

    require(instance.scope.contains("body"), "Expected body feature in scope.");
    require(
        instance.scope.get("body").value.isGeometry(),
        "Feature-stage binding should store geometry.");
}

void sourceChainingPreservesFeatureHistory() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
bored_body: body -bore(
radius- 0.5/n;
);
-return bored_body;
})qps");

    const auto& body = requireGeometryBinding(instance.scope, "body");
    const auto& bored = requireGeometryBinding(instance.scope, "bored_body");

    require(bored.id != body.id, "Chained stage should receive a new handle.");
    require(
        bored.source_stage_name.has_value() &&
            *bored.source_stage_name == "body",
        "Bore should preserve source stage name.");
    require(
        bored.source_handle_id.has_value() &&
            *bored.source_handle_id == body.id,
        "Bore should preserve source handle id.");
}

void geometryReturnYieldsReturnedStage() {
    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
bored_body: body -bore(
radius- 0.5/n;
);
-return bored_body;
})qps");

    const auto& bored = requireGeometryBinding(instance.scope, "bored_body");

    require(instance.result.has_value(), "Expected returned geometry value.");
    require(instance.result->isGeometry(), "Return should be geometry.");
    require(
        instance.result->asGeometry("return").id == bored.id,
        "Return handle should match bored_body handle.");
}

void geometryDoesNotBecomeNumeric() {
    qps::runtime::GeometryHandle handle;
    handle.id = 42;
    handle.action_name = "cylinder";
    handle.active_target = "pu1";
    handle.stage_name = "body";

    qps::runtime::ExecutionScope scope;
    scope.bind(
        "body",
        qps::runtime::RuntimeValue::geometry(handle),
        std::nullopt,
        qps::runtime::BindingOrigin::LOCAL);

    auto identifier =
        qps::ast::createIdentifierNode("body", 1, 1);
    qps::runtime::Interpreter interpreter(scope);

    expectFailure(
        [&]() {
            (void)interpreter.evaluate(*identifier);
        },
        {"Identifier 'body'", "expected numeric value", "geometry"});
}

void numericDoesNotBecomeGeometrySource() {
    expectFailure(
        [&]() {
            (void)instantiateGeometry(
                R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
bored_body: radius -bore(
radius- 0.5/n;
);
})qps");
        },
        {"GEOMETRY source stage 'radius'", "expected geometry value", "numeric"});
}

void duplicateActionOverrideRejected() {
    expectFailure(
        [&]() {
            (void)instantiateGeometry(
                R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder(
radius- 4/n;
radius- 5/n;
);
})qps");
        },
        {"Duplicate GEOMETRY action override", "radius"});
}

void unknownActionParameterRejected() {
    expectFailure(
        [&]() {
            (void)instantiateGeometry(
                R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder(
cheese- 9/n;
);
})qps");
        },
        {"Unknown GEOMETRY parameter", "cheese", "-cylinder"});
}

void boreRequiresSourceButSucceedsWithSource() {
    expectFailure(
        [&]() {
            (void)instantiateGeometry(
                R"qps({@pu1:
[>radius]- 3/n;
hole: -bore(
radius- 0.5/n;
);
})qps");
        },
        {"GEOMETRY action '-bore' requires a geometry source"});

    const auto instance = instantiateGeometry(
        R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
bored_body: body -bore(
radius- 0.5/n;
);
})qps");

    requireGeometryBinding(instance.scope, "bored_body");
}

void contextParameterTypeSafety() {
    auto program = parseSource(R"qps({@pu1:
body: -cylinder;
})qps");

    qps::runtime::GeometryHandle radius_handle;
    radius_handle.id = 7;
    radius_handle.action_name = "cylinder";
    radius_handle.active_target = "other";

    qps::runtime::ExecutionScope scope;
    scope.bind(
        "radius",
        qps::runtime::RuntimeValue::geometry(radius_handle),
        std::nullopt,
        qps::runtime::BindingOrigin::LOCAL);
    scope.bind(
        "width",
        1.0,
        std::nullopt,
        qps::runtime::BindingOrigin::LOCAL);

    qps::runtime::FakeGeometryActionDispatcher dispatcher;
    qps::runtime::InterpreterOptions options;
    options.domain = qps::ast::ExecutionDomain::GEOMETRY;
    options.active_target = "pu1";
    options.geometry_dispatcher = &dispatcher;

    qps::runtime::Interpreter interpreter(
        scope,
        qps::runtime::FunctionTable{},
        options);

    expectFailure(
        [&]() {
            (void)interpreter.executeForResult(
                *requireDefinition(*program).body_);
        },
        {"context parameter 'radius'", "expected numeric value", "geometry"});
}

void numericExecutionRegression() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]-
[>arm]- 2/n;

%[>T]: f * arm
}

{>Leverage_Equation:
f- 5/n;
}

{>Leverage_Equation:
f- 7/n;
})qps");

    require(instances.size() == 2, "Expected two numeric instances.");
    assertNear(
        requireBinding(instances[0].scope, "T").value.asNumber("T"),
        10.0,
        "first T");
    assertNear(
        requireBinding(instances[1].scope, "T").value.asNumber("T"),
        14.0,
        "second T");
    require(
        requireBinding(instances[0].scope, "T").value.isNumeric(),
        "Numeric result should remain numeric.");
    require(
        !instances[0].result.has_value() && !instances[1].result.has_value(),
        "Numeric execution definitions should not require result values.");
}

void functionBehaviorRegression() {
    qps::runtime::ExecutionScope scope;
    qps::runtime::Interpreter interpreter(scope);
    auto program = parseSource(R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}

{
%answer: leverage(10, 3)
}
)qps");

    interpreter.executeProgram(*program);
    assertNear(
        requireBinding(scope, "answer").value.asNumber("answer"),
        30.0,
        "function answer");
}

void semanticInputsAreCollectedAndDefaulted() {
    auto program = parseSource(R"qps({@pu1:
[>radius]- 3/n;
[>width]- 1/n;
body: -cylinder;
-return body;
})qps");

    const auto& definition = requireDefinition(*program);
    qps::runtime::ExecutionEngine engine;
    const auto info = engine.inspectDefinition(definition);

    require(info.inputs.size() == 2, "Expected only two semantic inputs.");
    require(info.inputs[0].name == "radius", "First input should be radius.");
    require(info.inputs[1].name == "width", "Second input should be width.");
    require(info.inputs[0].has_default, "Radius should have a default.");
    require(info.inputs[1].has_default, "Width should have a default.");

    engine.registerDefinition(definition);
    const auto instance = engine.instantiate("pu1", {});
    const auto& body = requireGeometryBinding(instance.scope, "body");
    assertParameter(body, "radius", 3.0, false);
    assertParameter(body, "width", 1.0, false);
}

void inputSideReferenceRemainsInvalidStructuralSyntax() {
    expectParseFailure(
        R"qps({@pu1:
[<radius]- 3/n;
})qps",
        {"Unrecognized statement"});
}

void independentGeometryInstances() {
    auto program = parseSource(R"qps({@pu1:
[>radius]-
[>width]-
body: -cylinder;
bored_body: body -bore(
radius- 0.5/n;
);
-return bored_body;
})qps");

    qps::runtime::ExecutionEngine engine;
    const auto& definition = requireDefinition(*program);
    engine.registerDefinition(definition);

    const auto first = engine.instantiateNumeric(
        "pu1",
        {{"radius", 3.0}, {"width", 1.0}});
    const auto second = engine.instantiateNumeric(
        "pu1",
        {{"radius", 6.0}, {"width", 2.0}});

    const auto& first_body = requireGeometryBinding(first.scope, "body");
    const auto& second_body = requireGeometryBinding(second.scope, "body");
    const auto& first_bored = requireGeometryBinding(first.scope, "bored_body");
    const auto& second_bored = requireGeometryBinding(second.scope, "bored_body");

    assertParameter(first_body, "radius", 3.0, false);
    assertParameter(second_body, "radius", 6.0, false);
    assertParameter(first_body, "width", 1.0, false);
    assertParameter(second_body, "width", 2.0, false);

    require(
        first_bored.source_handle_id.has_value() &&
            *first_bored.source_handle_id == first_body.id,
        "First instance should chain to its own body handle.");
    require(
        second_bored.source_handle_id.has_value() &&
            *second_bored.source_handle_id == second_body.id,
        "Second instance should chain to its own body handle.");
    require(
        first.result.has_value() && second.result.has_value(),
        "Both geometry instances should return a result.");
    require(
        first.result->asGeometry("first result").id == first_bored.id,
        "First return should match first bored body.");
    require(
        second.result->asGeometry("second result").id == second_bored.id,
        "Second return should match second bored body.");
}

class RecordingGeometryDispatcher
    : public qps::runtime::GeometryActionDispatcher {

public:
    qps::runtime::RuntimeValue invoke(
        const qps::runtime::ResolvedGeometryAction& action) override {

        ++invocation_count;
        last_action = action;

        qps::runtime::GeometryHandle handle;
        handle.id = 9001;
        handle.action_name = action.action_name;
        handle.active_target = action.active_target;
        handle.stage_name = action.result_stage_name;
        handle.source_stage_name = action.source_stage_name;

        if (action.source_geometry.has_value()) {
            handle.source_handle_id =
                action.source_geometry->id;
        }

        for (const auto& resolved :
             action.parameters) {

            qps::runtime::GeometryParameterValue parameter;
            parameter.name = resolved.name;
            parameter.value = resolved.value;
            parameter.explicit_override =
                resolved.explicit_override;

            handle.parameters.push_back(parameter);
        }

        return qps::runtime::RuntimeValue::geometry(
            std::move(handle));
    }

    int invocation_count = 0;

    std::optional<
        qps::runtime::ResolvedGeometryAction
    > last_action;
};

void resolverDispatchBoundary() {
    qps::runtime::ExecutionScope scope;

    scope.bind(
        "radius",
        3.0,
        std::nullopt,
        qps::runtime::BindingOrigin::SUPPLIED);

    scope.bind(
        "width",
        1.0,
        std::nullopt,
        qps::runtime::BindingOrigin::SUPPLIED);

    qps::runtime::GeometryActionInvocation good;
    good.action_name = "cylinder";
    good.active_target = "pu1";
    good.result_stage_name = "body";
    good.scope = &scope;

    good.explicit_parameters.emplace(
        "radius",
        qps::runtime::RuntimeValue::numeric(4.0));

    qps::runtime::GeometryActionResolver resolver;
    RecordingGeometryDispatcher dispatcher;

    const auto resolved =
        resolver.resolve(good);

    require(
        dispatcher.invocation_count == 0,
        "Resolution must not dispatch geometry.");

    require(
        resolved.parameters.size() == 2,
        "Cylinder should resolve exactly two parameters.");

    require(
        resolved.parameters[0].name == "radius",
        "Resolved cylinder parameter order should begin with radius.");

    require(
        resolved.parameters[1].name == "width",
        "Resolved cylinder parameter order should end with width.");

    assertNear(
        resolved.parameters[0].value,
        4.0,
        "resolved radius");

    require(
        resolved.parameters[0].explicit_override,
        "Resolved radius should preserve explicit override authority.");

    assertNear(
        resolved.parameters[1].value,
        1.0,
        "resolved width");

    require(
        !resolved.parameters[1].explicit_override,
        "Resolved width should preserve context authority.");

    const auto result =
        dispatcher.invoke(resolved);

    require(
        dispatcher.invocation_count == 1,
        "Valid resolved geometry should dispatch exactly once.");

    require(
        dispatcher.last_action.has_value(),
        "Dispatcher should receive resolved geometry action.");

    require(
        dispatcher.last_action->action_name == "cylinder",
        "Dispatcher should receive cylinder operation.");

    require(
        dispatcher.last_action->active_target == "pu1",
        "Dispatcher should receive active target.");

    require(
        result.isGeometry(),
        "Recording dispatcher should return geometry.");

    qps::runtime::GeometryActionInvocation bad;
    bad.action_name = "cylinder";
    bad.active_target = "broken";
    bad.scope = nullptr;

    expectFailure(
        [&]() {
            const auto invalid =
                resolver.resolve(bad);

            (void)dispatcher.invoke(invalid);
        },
        {
            "Missing required GEOMETRY parameter",
            "radius",
            "-cylinder"
        });

    require(
        dispatcher.invocation_count == 1,
        "Failed resolution must not cross dispatcher boundary.");
}

struct TestCase {
    const char* name;
    std::function<void()> run;
};

} // namespace


void itemUnitSuffixParsing() {
    auto program = parseSource(R"qps(
diameter- 1/in;

depth- 5/mm;

pressure- 120/psi;

angle- 90/degrees;

count- 8/n;
)qps");

    assert(program != nullptr);
    assert(program->statements.size() == 5);

    auto require_item =
        [&](std::size_t index)
            -> qps::ast::ItemDeclarationNode& {

        auto* item =
            dynamic_cast<
                qps::ast::ItemDeclarationNode*>(
                    program->statements.at(index).get());

        assert(item != nullptr);
        assert(item->value_node_ != nullptr);

        return *item;
    };

    {
        auto& item = require_item(0);
        auto* numeric =
            dynamic_cast<
                qps::ast::NumericLiteralNode*>(
                    item.value_node_.get());

        assert(numeric != nullptr);
        assert(numeric->value_ == 1.0);
        assert(item.unit_hint_.has_value());
        assert(*item.unit_hint_ == "in");
        assert(!item.type_hint_.has_value());
    }

    {
        auto& item = require_item(1);
        assert(item.unit_hint_.has_value());
        assert(*item.unit_hint_ == "mm");
    }

    {
        auto& item = require_item(2);
        assert(item.unit_hint_.has_value());
        assert(*item.unit_hint_ == "psi");
    }

    {
        auto& item = require_item(3);
        assert(item.unit_hint_.has_value());
        assert(*item.unit_hint_ == "degrees");
    }

    {
        auto& item = require_item(4);
        assert(!item.unit_hint_.has_value());
        assert(item.type_hint_.has_value());
        assert(
            *item.type_hint_ ==
            qps::tokens::TokenType::TYPE_NUMERIC);
    }
}

void calculationDivisionRemainsArithmetic() {
    auto program = parseSource(R"qps(
{1:
%ratio: 10 / 2
}
)qps");

    assert(program != nullptr);

    auto* definition =
        dynamic_cast<
            qps::ast::ExecutionDefinitionNode*>(
                program->statements.front().get());

    assert(definition != nullptr);
    assert(definition->body_ != nullptr);

    auto* calculation =
        dynamic_cast<
            qps::ast::CalculationNode*>(
                definition->body_->statements.front().get());

    assert(calculation != nullptr);

    auto* binary =
        dynamic_cast<
            qps::ast::BinaryExpressionNode*>(
                calculation->getExpression());

    assert(binary != nullptr);

    assert(
        binary->getOperator() ==
        qps::ast::BinaryExpressionNode::Operator::DIVIDE);
}

int main() {
    const std::vector<TestCase> tests = {
        {"GEOMETRY domain parsing", geometryDomainParsing},
        {"whitespace is non-semantic", whitespaceIsNonSemantic},
        {"semicolon remains statement delimiter", semicolonRemainsStatementDelimiter},
        {"named feature stage parses", namedFeatureStageParses},
        {"source feature stage parses", sourceFeatureStageParses},
        {"context parameter resolution", contextParameterResolution},
        {"explicit Item override wins", explicitItemOverrideWins},
        {"missing required parameter fails clearly", missingRequiredParameterFailsClearly},
        {"unknown action fails at runtime", unknownActionFailsAtRuntime},
        {"geometry primitive is not a host primitive", geometryPrimitiveIsNotAHostPrimitive},
        {"geometry result type is opaque geometry", geometryResultTypeIsOpaqueGeometry},
        {"feature stage stored in scope", featureStageStoredInScope},
        {"source chaining preserves feature history", sourceChainingPreservesFeatureHistory},
        {"geometry return yields returned stage", geometryReturnYieldsReturnedStage},
        {"geometry does not become numeric", geometryDoesNotBecomeNumeric},
        {"numeric does not become geometry source", numericDoesNotBecomeGeometrySource},
        {"duplicate action override rejected", duplicateActionOverrideRejected},
        {"unknown action parameter rejected", unknownActionParameterRejected},
        {"bore requires source but succeeds with source", boreRequiresSourceButSucceedsWithSource},
        {"context parameter type safety", contextParameterTypeSafety},
        {"numeric execution regression", numericExecutionRegression},
        {"function behavior regression", functionBehaviorRegression},
        {"semantic inputs are collected and defaulted", semanticInputsAreCollectedAndDefaulted},
        {"[<] remains invalid structural syntax", inputSideReferenceRemainsInvalidStructuralSyntax},
        {"independent geometry instances", independentGeometryInstances},
        {"resolver dispatch boundary", resolverDispatchBoundary},
        {"Item unit suffix parsing", itemUnitSuffixParsing},
        {"calculation division remains arithmetic", calculationDivisionRemainsArithmetic},
    };

    int failures = 0;

    for (const auto& test : tests) {
        try {
            test.run();
            std::cout << "PASS " << test.name << "\n";
        } catch (const std::exception& e) {
            ++failures;
            std::cerr << "FAIL " << test.name << ": " << e.what() << "\n";
        }
    }

    if (failures != 0) {
        std::cerr << failures << " geometry execution test(s) failed.\n";
        return 1;
    }

    return 0;
}
