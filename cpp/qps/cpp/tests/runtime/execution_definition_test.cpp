#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/execution_engine.hpp"
#include "runtime/h/path_resolver.hpp"
#include "runtime/h/symbol_resolver.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <functional>
#include <filesystem>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
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

std::unique_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);
    return parser.parseProgram();
}

const qps::runtime::RuntimeBinding& requireBinding(
    const qps::runtime::ExecutionScope& scope,
    const std::string& name) {

    require(
        scope.contains(name),
        "Expected execution binding named " + name + ".");

    return scope.get(name);
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

void assertBinding(
    const qps::runtime::ExecutionScope& scope,
    const std::string& name,
    double value,
    qps::runtime::BindingOrigin origin,
    const std::optional<std::string>& semantic_symbol) {

    const auto& binding = requireBinding(scope, name);
    assertNear(binding.value, value, name + " value");

    require(
        binding.origin == origin,
        name + " origin mismatch.");

    require(
        binding.semantic_symbol == semantic_symbol,
        name + " semantic symbol mismatch.");
}

void assertBindingOrder(
    const qps::runtime::ExecutionScope& scope,
    const std::vector<std::string>& expected_names) {

    const auto bindings = scope.bindings();

    require(
        bindings.size() == expected_names.size(),
        "Expected " + std::to_string(expected_names.size()) +
        " bindings, got " + std::to_string(bindings.size()) + ".");

    for (std::size_t i = 0; i < expected_names.size(); ++i) {
        require(
            bindings[i].name == expected_names[i],
            "Expected binding " + std::to_string(i) + " to be " +
            expected_names[i] + ", got " + bindings[i].name + ".");
    }
}

const qps::ast::ExecutionDefinitionNode& requireDefinition(
    const qps::ast::ProgramNode& program,
    std::size_t index = 0) {

    require(
        program.statements.size() > index,
        "Expected execution definition statement.");

    auto* definition =
        dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
            program.statements[index].get());

    require(
        definition != nullptr,
        "Expected ExecutionDefinitionNode.");

    return *definition;
}

const qps::ast::ItemDeclarationNode& requireInput(
    const qps::ast::ExecutionDefinitionNode& definition,
    std::size_t index) {

    require(definition.body_ != nullptr, "Definition body missing.");
    require(
        definition.body_->statements.size() > index,
        "Expected definition input statement.");

    auto* item =
        dynamic_cast<qps::ast::ItemDeclarationNode*>(
            definition.body_->statements[index].get());

    require(item != nullptr, "Expected ItemDeclarationNode input.");

    auto* target =
        dynamic_cast<qps::ast::SymbolReferenceNode*>(
            item->getTarget());

    require(target != nullptr, "Expected semantic input target.");

    return *item;
}

const qps::ast::NumericLiteralNode& requireNumericValue(
    const qps::ast::ItemDeclarationNode& item) {

    auto* numeric =
        dynamic_cast<qps::ast::NumericLiteralNode*>(
            item.value_node_.get());

    require(numeric != nullptr, "Expected numeric item value.");
    return *numeric;
}

std::vector<qps::runtime::ExecutionInstance> executeProgram(
    const std::string& source) {

    auto program = parseSource(source);
    qps::runtime::ExecutionEngine engine;
    return engine.execute(*program);
}

void expectRuntimeFailure(
    const std::string& source,
    const std::string& message_fragment) {

    try {
        (void)executeProgram(source);
    } catch (const std::exception& e) {
        const std::string message = e.what();

        require(
            message.find(message_fragment) != std::string::npos,
            "Expected failure containing " + message_fragment +
            ", got " + message + ".");
        return;
    }

    fail("Expected runtime failure containing " + message_fragment + ".");
}


void structuralSemanticReferencesPreserveNavigation() {
    auto program = parseSource(R"qps({Reference_Test:
%one: [>v]
%dotted: [>key.dimensions]
%mixed: [>folder/file.key.term]
%parent: [>//file.key.term]
%item: [>key.dimensions.body.radius-]
})qps");

    const auto& definition =
        requireDefinition(*program);

    require(
        definition.body_->statements.size() == 5,
        "Expected five structural reference witnesses.");

    const auto requireReference =
        [&](std::size_t index)
            -> const qps::ast::SymbolReferenceNode& {

        auto* calculation =
            dynamic_cast<qps::ast::CalculationNode*>(
                definition.body_->statements.at(index).get());

        require(
            calculation != nullptr,
            "Expected CalculationNode reference witness.");

        auto* reference =
            dynamic_cast<qps::ast::SymbolReferenceNode*>(
                calculation->getExpression());

        require(
            reference != nullptr,
            "Expected SymbolReferenceNode expression.");

        return *reference;
    };

    {
        const auto& reference =
            requireReference(0);

        require(
            reference.getSymbol() == "v",
            "Single reference spelling mismatch.");

        require(
            reference.getParentDepth() == 0,
            "Single reference parent depth mismatch.");

        require(
            reference.getSegments().size() == 1,
            "Single reference segment count mismatch.");

        require(
            !reference.selectsItemValue(),
            "Plain reference must remain structural.");
    }

    {
        const auto& reference =
            requireReference(1);

        require(
            reference.getSymbol() == "key.dimensions",
            "Dotted reference spelling mismatch.");

        require(
            reference.getSegments().size() == 2,
            "Dotted reference segment count mismatch.");

        require(
            reference.getSegments()[0].name == "key",
            "Dotted root mismatch.");

        require(
            reference.getSegments()[1].name == "dimensions",
            "Dotted child mismatch.");

        require(
            reference.getSegments()[1].separator ==
                qps::ast::SymbolReferenceSeparator::DOT,
            "Dotted separator mismatch.");

        require(
            !reference.selectsItemValue(),
            "Dotted structural reference must not select Item value.");
    }

    {
        const auto& reference =
            requireReference(2);

        require(
            reference.getSymbol() ==
                "folder/file.key.term",
            "Mixed reference spelling mismatch.");

        require(
            reference.getSegments().size() == 4,
            "Mixed reference segment count mismatch.");

        require(
            reference.getSegments()[1].separator ==
                qps::ast::SymbolReferenceSeparator::SLASH,
            "folder/file must preserve slash navigation.");

        require(
            reference.getSegments()[2].separator ==
                qps::ast::SymbolReferenceSeparator::DOT,
            "file.key must preserve semantic navigation.");

        require(
            reference.getSegments()[3].separator ==
                qps::ast::SymbolReferenceSeparator::DOT,
            "key.term must preserve semantic navigation.");

        require(
            !reference.selectsItemValue(),
            "Mixed structural reference must remain structural.");
    }

    {
        const auto& reference =
            requireReference(3);

        require(
            reference.getSymbol() ==
                "//file.key.term",
            "Parent reference spelling mismatch.");

        require(
            reference.getParentDepth() == 2,
            "Two-parent reference depth mismatch.");

        require(
            reference.getSegments().size() == 3,
            "Parent reference segment count mismatch.");

        require(
            !reference.selectsItemValue(),
            "Parent structural reference must remain structural.");
    }

    {
        const auto& reference =
            requireReference(4);

        require(
            reference.getSymbol() ==
                "key.dimensions.body.radius-",
            "Item reference spelling mismatch.");

        require(
            reference.getSegments().size() == 4,
            "Item reference segment count mismatch.");

        require(
            reference.getSegments()[3].name == "radius",
            "Item name mismatch.");

        require(
            reference.selectsItemValue(),
            "Trailing '-' inside [] must explicitly select Item value.");
    }
}

void namedReusableExecutionDefinitionParses() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
})qps");

    const auto& definition = requireDefinition(*program);

    require(definition.identifier_ == "Leverage_Equation", "Named definition id mismatch.");
    require(!definition.identifier_is_numeric_, "Named definition marked numeric.");
    require(
        definition.domain_ == qps::ast::ExecutionDomain::GENERIC,
        "Legacy execution definition should remain GENERIC.");
    require(definition.body_->statements.size() == 3, "Definition body statement count mismatch.");
    requireInput(definition, 0);
    requireInput(definition, 1);
    require(requireInput(definition, 0).value_node_ == nullptr, "f should be required.");
    require(requireInput(definition, 1).value_node_ == nullptr, "arm should be required.");
}

void geometryExecutionDomainParsesStructurally() {
    auto program = parseSource(R"qps({@geometry_case:
})qps");

    const auto& definition = requireDefinition(*program);

    require(
        definition.identifier_ == "geometry_case",
        "Geometry execution definition identifier mismatch.");

    require(
        definition.domain_ == qps::ast::ExecutionDomain::GEOMETRY,
        "Expected GEOMETRY execution domain.");

    require(
        definition.body_ != nullptr,
        "Geometry execution definition body missing.");
}

void structuralExecutionBindingsPreserveNavigationRoots() {
    auto program = parseSource(R"qps({@structural_binding_case:
v: [>shape.dimensions];
v1: [v.bore1];
})qps");

    const auto& definition = requireDefinition(*program);

    require(
        definition.domain_ == qps::ast::ExecutionDomain::GEOMETRY,
        "Structural binding witness should parse in GEOMETRY domain.");

    require(
        definition.body_ != nullptr,
        "Structural binding witness body missing.");

    require(
        definition.body_->statements.size() == 2,
        "Expected two structural binding Terms.");

    auto* v =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            definition.body_->statements[0].get());

    auto* v1 =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            definition.body_->statements[1].get());

    require(v != nullptr, "Expected v to be a TermDeclarationNode.");
    require(v1 != nullptr, "Expected v1 to be a TermDeclarationNode.");

    require(v->identifier_ == "v", "First structural binding should be v.");
    require(v1->identifier_ == "v1", "Second structural binding should be v1.");

    require(
        v->content_.size() == 1,
        "v should contain exactly one structural reference.");

    require(
        v1->content_.size() == 1,
        "v1 should contain exactly one structural reference.");

    auto* external =
        dynamic_cast<qps::ast::SymbolReferenceNode*>(
            v->content_[0].get());

    auto* local =
        dynamic_cast<qps::ast::SymbolReferenceNode*>(
            v1->content_[0].get());

    require(
        external != nullptr,
        "v content should be a SymbolReferenceNode.");

    require(
        local != nullptr,
        "v1 content should be a SymbolReferenceNode.");

    require(
        external->getOrigin() ==
            qps::ast::SymbolReferenceOrigin::CURRENT_FILE,
        "[>shape.dimensions] should begin from current document.");

    require(
        local->getOrigin() ==
            qps::ast::SymbolReferenceOrigin::LOCAL_BINDING,
        "[v.bore1] should begin from local execution scope.");

    require(
        external->getSegments().size() == 2,
        "External structural reference should preserve two segments.");

    require(
        external->getSegments()[0].name == "shape" &&
        external->getSegments()[1].name == "dimensions",
        "External structural reference path mismatch.");

    require(
        local->getSegments().size() == 2,
        "Local structural reference should preserve two segments.");

    require(
        local->getSegments()[0].name == "v" &&
        local->getSegments()[1].name == "bore1",
        "Local structural reference path mismatch.");
}

void calculationAtStartOfAnonymousBlockRemainsCalculation() {
    auto program = parseSource(R"qps({
%[>T]: 2 * 3
})qps");

    require(
        program->statements.size() == 1,
        "Expected one anonymous execution block.");

    auto* block =
        dynamic_cast<qps::ast::ExecutionBlockNode*>(
            program->statements[0].get());

    require(
        block != nullptr,
        "Leading calculation must not be mistaken for MATH definition.");

    require(
        block->statements.size() == 1,
        "Expected one calculation inside anonymous block.");

    require(
        dynamic_cast<qps::ast::CalculationNode*>(
            block->statements[0].get()) != nullptr,
        "Expected calculation statement inside anonymous block.");
}

void numericReusableExecutionDefinitionParses() {
    auto program = parseSource(R"qps({1:
[>f]-

%[>T]: f * 2
})qps");

    const auto& definition = requireDefinition(*program);

    require(definition.identifier_ == "1", "Numeric definition id mismatch.");
    require(definition.identifier_is_numeric_, "Numeric definition was not marked numeric.");
    require(definition.body_->statements.size() == 2, "Numeric definition body count mismatch.");
}

void namedCallInstantiatesDefinition() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>Leverage_Equation:
f- 10/n;
arm- 3/n;
})qps");

    require(instances.size() == 1, "Expected one named call instance.");
    assertBindingOrder(instances[0].scope, {"f", "arm", "T"});
    assertBinding(instances[0].scope, "T", 30.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void numericCallInstantiatesDefinition() {
    const auto instances = executeProgram(R"qps({1:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>1:
f- 4/n;
arm- 7/n;
})qps");

    require(instances.size() == 1, "Expected one numeric call instance.");
    require(instances[0].identifier_is_numeric, "Numeric instance was not marked numeric.");
    assertBinding(instances[0].scope, "T", 28.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void requiredInputSuppliedSuccessfully() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>Leverage_Equation:
f- 8/n;
arm- 6/n;
})qps");

    require(instances.size() == 1, "Expected one instance.");
    assertBinding(instances[0].scope, "f", 8.0, qps::runtime::BindingOrigin::SUPPLIED, "f");
    assertBinding(instances[0].scope, "arm", 6.0, qps::runtime::BindingOrigin::SUPPLIED, "arm");
    assertBinding(instances[0].scope, "T", 48.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void missingRequiredInputFailsClearly() {
    expectRuntimeFailure(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>Leverage_Equation:
f- 8/n;
})qps",
        "Missing required execution input 'arm'");
}

void defaultInputUsedWhenNotOverridden() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]- 10/n;
[>arm]- 3/n;

%[>T]: f * arm
}

{>Leverage_Equation:
})qps");

    require(instances.size() == 1, "Expected one default-backed instance.");
    assertBindingOrder(instances[0].scope, {"f", "arm", "T"});
    assertBinding(instances[0].scope, "f", 10.0, qps::runtime::BindingOrigin::SUPPLIED, "f");
    assertBinding(instances[0].scope, "arm", 3.0, qps::runtime::BindingOrigin::SUPPLIED, "arm");
    assertBinding(instances[0].scope, "T", 30.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void defaultInputCanBeOverriddenPerInstance() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]- 10/n;
[>arm]- 3/n;

%[>T]: f * arm
}

{>Leverage_Equation:
arm- 5/n;
})qps");

    require(instances.size() == 1, "Expected one override-backed instance.");
    assertBindingOrder(instances[0].scope, {"f", "arm", "T"});
    assertBinding(instances[0].scope, "f", 10.0, qps::runtime::BindingOrigin::SUPPLIED, "f");
    assertBinding(instances[0].scope, "arm", 5.0, qps::runtime::BindingOrigin::SUPPLIED, "arm");
    assertBinding(instances[0].scope, "T", 50.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void unknownOverrideNameFailsClearly() {
    expectRuntimeFailure(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>Leverage_Equation:
f- 8/n;
arm- 6/n;
length- 2/n;
})qps",
        "Unknown instance override 'length'");
}

void twoCallsWithDifferentInputsAreIndependent() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>Leverage_Equation:
f- 10/n;
arm- 3/n;
}

{>Leverage_Equation:
f- 2/n;
arm- 9/n;
})qps");

    require(instances.size() == 2, "Expected two independent instances.");
    assertBinding(instances[0].scope, "f", 10.0, qps::runtime::BindingOrigin::SUPPLIED, "f");
    assertBinding(instances[0].scope, "arm", 3.0, qps::runtime::BindingOrigin::SUPPLIED, "arm");
    assertBinding(instances[0].scope, "T", 30.0, qps::runtime::BindingOrigin::DERIVED, "T");
    assertBinding(instances[1].scope, "f", 2.0, qps::runtime::BindingOrigin::SUPPLIED, "f");
    assertBinding(instances[1].scope, "arm", 9.0, qps::runtime::BindingOrigin::SUPPLIED, "arm");
    assertBinding(instances[1].scope, "T", 18.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void callingDefinitionDoesNotMutateDefaults() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]- 10/n;
[>arm]- 3/n;

%[>T]: f * arm
}

{>Leverage_Equation:
arm- 5/n;
}

{>Leverage_Equation:
})qps");

    const auto& definition = requireDefinition(*program);
    const auto& f_default = requireNumericValue(requireInput(definition, 0));
    const auto& arm_default = requireNumericValue(requireInput(definition, 1));

    qps::runtime::ExecutionEngine engine;
    const auto instances = engine.execute(*program);

    require(instances.size() == 2, "Expected two instances from default immutability test.");
    assertNear(f_default.value_, 10.0, "definition f default after calls");
    assertNear(arm_default.value_, 3.0, "definition arm default after calls");
    assertBinding(instances[0].scope, "T", 50.0, qps::runtime::BindingOrigin::DERIVED, "T");
    assertBinding(instances[1].scope, "T", 30.0, qps::runtime::BindingOrigin::DERIVED, "T");
}

void derivedSemanticOutputsExecuteInsideInstance() {
    const auto instances = executeProgram(R"qps({Leverage_Equation:
[>f]-
[>arm]-

%[>T]: f * arm
}

{>Leverage_Equation:
f- 11/n;
arm- 4/n;
})qps");

    require(instances.size() == 1, "Expected one instance.");
    assertBinding(instances[0].scope, "T", 44.0, qps::runtime::BindingOrigin::DERIVED, "T");
}


void executionDefinitionInspectionExposesStructuralInputs() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-
[>arm]-/n;
[>ratio]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition = requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    const auto info = engine.inspectDefinition(definition);

    require(
        info.identifier == "Leverage_Equation",
        "Definition inspection identifier mismatch.");

    require(
        !info.identifier_is_numeric,
        "Named definition should not be marked numeric.");

    require(
        info.inputs.size() == 3,
        "Expected three inspected semantic inputs.");

    require(
        info.inputs[0].name == "f",
        "First inspected input name mismatch.");
    require(
        !info.inputs[0].type_hint.has_value(),
        "f should not expose an explicit type hint.");
    require(
        !info.inputs[0].has_default,
        "f should be required.");

    require(
        info.inputs[1].name == "arm",
        "Second inspected input name mismatch.");
    require(
        info.inputs[1].type_hint ==
            qps::tokens::TokenType::TYPE_NUMERIC,
        "arm should expose TYPE_NUMERIC.");
    require(
        !info.inputs[1].has_default,
        "arm should be required.");

    require(
        info.inputs[2].name == "ratio",
        "Third inspected input name mismatch.");
    require(
        info.inputs[2].type_hint ==
            qps::tokens::TokenType::TYPE_NUMERIC,
        "ratio should expose TYPE_NUMERIC.");
    require(
        info.inputs[2].has_default,
        "ratio should expose a default.");
}


void registeredDefinitionInspectionPreservesOptionalSourceIdentity() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition = requireDefinition(*program);

    {
        qps::runtime::ExecutionEngine engine;
        engine.registerDefinition(definition);

        const auto info =
            engine.inspectRegisteredDefinition(
                "Leverage_Equation");

        require(
            info.identifier == "Leverage_Equation",
            "Registered definition identifier mismatch.");

        require(
            !info.source.has_value(),
            "Source-less registration should not invent provenance.");
    }

    {
        qps::runtime::ExecutionEngine engine;
        engine.registerDefinition(
            definition,
            "designs/leverage.qps");

        const auto info =
            engine.inspectRegisteredDefinition(
                "Leverage_Equation");

        require(
            info.source.has_value(),
            "Source-aware registration should preserve provenance.");

        require(
            info.source->source_document ==
                "designs/leverage.qps",
            "Registered source document mismatch.");
    }
}

void executionInstancePreservesRegisteredSourceIdentity() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition = requireDefinition(*program);

    {
        qps::runtime::ExecutionEngine engine;
        engine.registerDefinition(definition);

        const auto execution =
            engine.instantiate(
                "Leverage_Equation",
                {{"f", 10.0}});

        require(
            !execution.source.has_value(),
            "Source-less execution should not invent provenance.");
    }

    {
        qps::runtime::ExecutionEngine engine;
        engine.registerDefinition(
            definition,
            "designs/leverage.qps");

        const auto execution =
            engine.instantiate(
                "Leverage_Equation",
                {{"f", 10.0}});

        require(
            execution.source.has_value(),
            "Execution should preserve registered source provenance.");

        require(
            execution.source->source_document ==
                "designs/leverage.qps",
            "Execution source document mismatch.");
    }
}

void registeredDefinitionRejectsEmptySourceIdentity() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;

%[>T]: f
})qps");

    const auto& definition = requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;

    bool rejected = false;

    try {
        engine.registerDefinition(definition, "");
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    require(
        rejected,
        "Empty execution definition source identity should be rejected.");
}


void externalStructuralBindingResolvesIntoExecutionScope() {
    auto program = parseSource(R"qps({@structural_binding_runtime:
v: [>shape.dimensions];
v1: [v.cylinder];
})qps");

    const auto& definition =
        requireDefinition(*program);

    const std::filesystem::path dashboard_root =
        std::filesystem::path(__FILE__)
            .parent_path()  // runtime
            .parent_path()  // tests
            .parent_path()  // cpp
            .parent_path()  // qps
            .parent_path()  // cpp
            .parent_path(); // ce-os

    const std::filesystem::path engineering_workspace =
        dashboard_root / "Engineering" / "qps";

    qps::runtime::PathResolver paths(
        engineering_workspace);

    qps::runtime::DocumentLoader loader;
    qps::runtime::DocumentStore documents(loader);

    qps::runtime::SymbolResolver symbols(
        paths,
        documents);

    qps::runtime::ExecutionEngine engine(symbols);

    engine.registerDefinition(
        definition,
        "defs/semantic_walk/shape.qps");

    const auto execution =
        engine.instantiate(
            "structural_binding_runtime",
            {});

    const auto& binding =
        requireBinding(
            execution.scope,
            "v");

    require(
        binding.value.kind() ==
            qps::runtime::RuntimeValue::Kind::STRUCTURE,
        "Structural execution binding should retain structure.");

    require(
        binding.origin ==
            qps::runtime::BindingOrigin::LOCAL,
        "Structural execution binding should be local.");

    const auto& structure =
        binding.value.asStructure(
            "structural binding v");

    require(
        structure.target_identifier ==
            "dimensions",
        "Structural execution binding should resolve dimensions.");

    require(
        structure.target_type ==
            "TERM_DECLARATION",
        "Structural execution binding should resolve a Term.");

    require(
        dynamic_cast<
            qps::ast::TermDeclarationNode*>(
                structure.target_node) != nullptr,
        "Structural execution binding target should retain Term AST node.");

    const auto& local_binding =
        requireBinding(
            execution.scope,
            "v1");

    require(
        local_binding.value.kind() ==
            qps::runtime::RuntimeValue::Kind::STRUCTURE,
        "Local structural descent should retain structure.");

    const auto& local_structure =
        local_binding.value.asStructure(
            "structural binding v1");

    require(
        local_structure.target_identifier ==
            "cylinder",
        "Local structural descent should resolve cylinder.");

    require(
        local_structure.target_type ==
            "TERM_DECLARATION",
        "Local structural descent should resolve a Term.");

    require(
        dynamic_cast<
            qps::ast::TermDeclarationNode*>(
                local_structure.target_node) != nullptr,
        "Local structural descent should retain cylinder Term AST node.");

    // Same definition without resolver injection must fail explicitly.
    qps::runtime::ExecutionEngine unresolved_engine;

    unresolved_engine.registerDefinition(
        definition,
        "defs/semantic_walk/shape.qps");

    bool rejected = false;

    try {
        (void)unresolved_engine.instantiate(
            "structural_binding_runtime",
            {});
    } catch (const std::runtime_error& e) {
        rejected =
            std::string(e.what()).find(
                "requires a SymbolResolver") !=
            std::string::npos;
    }

    require(
        rejected,
        "Structural execution without SymbolResolver should fail explicitly.");
}

struct TestCase {
    const char* name;
    std::function<void()> run;
};

} // namespace

int main() {
    const std::vector<TestCase> tests = {
        {"structural semantic references preserve navigation", structuralSemanticReferencesPreserveNavigation},
        {"named reusable execution definition parses", namedReusableExecutionDefinitionParses},
        {"geometry execution domain parses structurally", geometryExecutionDomainParsesStructurally},
        {"structural execution bindings preserve navigation roots", structuralExecutionBindingsPreserveNavigationRoots},
        {"calculation at start of anonymous block remains calculation", calculationAtStartOfAnonymousBlockRemainsCalculation},
        {"numeric reusable execution definition parses", numericReusableExecutionDefinitionParses},
        {"named call instantiates definition", namedCallInstantiatesDefinition},
        {"numeric call instantiates definition", numericCallInstantiatesDefinition},
        {"required input supplied successfully", requiredInputSuppliedSuccessfully},
        {"missing required input fails clearly", missingRequiredInputFailsClearly},
        {"default input is used when not overridden", defaultInputUsedWhenNotOverridden},
        {"default input can be overridden per instance", defaultInputCanBeOverriddenPerInstance},
        {"unknown override name fails clearly", unknownOverrideNameFailsClearly},
        {"two calls with different inputs are independent", twoCallsWithDifferentInputsAreIndependent},
        {"calling a definition does not mutate defaults", callingDefinitionDoesNotMutateDefaults},
        {"derived semantic outputs execute inside instance", derivedSemanticOutputsExecuteInsideInstance},
        {"execution definition inspection exposes structural inputs", executionDefinitionInspectionExposesStructuralInputs},
        {"registered definition inspection preserves optional source identity", registeredDefinitionInspectionPreservesOptionalSourceIdentity},
        {"execution instance preserves registered source identity", executionInstancePreservesRegisteredSourceIdentity},
        {"registered definition rejects empty source identity", registeredDefinitionRejectsEmptySourceIdentity},
        {"external structural binding resolves into execution scope", externalStructuralBindingResolvesIntoExecutionScope},
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
        std::cerr << failures << " execution definition test(s) failed.\n";
        return 1;
    }

    return 0;
}
