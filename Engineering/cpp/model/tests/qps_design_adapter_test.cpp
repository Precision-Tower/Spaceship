#include "engineering/qps_design_adapter.hpp"
#include "engineering/qps_quantity_adapter.hpp"

#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cassert>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

std::unique_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);

    return parser.parseProgram();
}

const qps::ast::ExecutionDefinitionNode&
requireDefinition(
    const qps::ast::ProgramNode& program) {

    for (const auto& statement : program.statements) {
        auto* definition =
            dynamic_cast<
                qps::ast::ExecutionDefinitionNode*>(
                    statement.get());

        if (definition) {
            return *definition;
        }
    }

    throw std::runtime_error(
        "Expected execution definition.");
}

engineering::EngineeringBinding explicitNumeric(
    const engineering::EngineeringBinding& existing,
    double value) {

    auto binding = existing;

    binding.explicit_numeric_value = value;
    binding.resolved = true;
    binding.numeric_value = value;
    binding.provenance =
        engineering::BindingProvenance::SUPPLIED;

    return binding;
}

engineering::EngineeringBinding explicitNumeric(
    const std::string& name,
    double value,
    bool has_default = false) {

    return {
        .name = name,
        .declared_type =
            engineering::BindingDeclaredType::NUMERIC,
        .has_default = has_default,
        .explicit_numeric_value = value,
        .resolved = true,
        .numeric_value = value,
        .provenance =
            engineering::BindingProvenance::SUPPLIED,
    };
}


const qps::ast::ItemDeclarationNode&
requireItem(
    const qps::ast::ProgramNode& program,
    std::size_t index) {

    const auto* item =
        dynamic_cast<
            const qps::ast::ItemDeclarationNode*>(
                program.statements.at(index).get());

    if (item == nullptr) {
        throw std::runtime_error(
            "Expected QPS Item declaration.");
    }

    return *item;
}

void qpsItemUnitsTranslateToEngineeringQuantities() {
    auto program = parseSource(R"qps(
inch- 1/in;

millimeter- 25.4/mm;

pressure- 120/psi;

angle- 90/degrees;

plain- 5;
)qps");

    assert(program != nullptr);
    assert(program->statements.size() == 5);

    {
        const auto quantity =
            engineering::makeQuantity(
                requireItem(*program, 0));

        assert(quantity.value == 1.0);
        assert(quantity.dimension == "length");
        assert(quantity.unit == "in");
        assert(quantity.canonicalValue() == 25.4);
        assert(quantity.canonicalUnit() == "mm");
    }

    {
        const auto quantity =
            engineering::makeQuantity(
                requireItem(*program, 1));

        assert(quantity.value == 25.4);
        assert(quantity.dimension == "length");
        assert(quantity.unit == "mm");
        assert(quantity.canonicalValue() == 25.4);
    }

    {
        const auto quantity =
            engineering::makeQuantity(
                requireItem(*program, 2));

        assert(quantity.value == 120.0);
        assert(quantity.dimension == "pressure");
        assert(quantity.unit == "psi");
        assert(quantity.canonicalUnit() == "Pa");
    }

    {
        const auto quantity =
            engineering::makeQuantity(
                requireItem(*program, 3));

        assert(quantity.value == 90.0);
        assert(quantity.dimension == "angle");
        assert(quantity.unit == "degrees");
        assert(quantity.canonicalUnit() == "rad");
    }

    bool plain_rejected = false;

    try {
        (void)engineering::makeQuantity(
            requireItem(*program, 4));
    } catch (const std::runtime_error&) {
        plain_rejected = true;
    }

    assert(plain_rejected);
}

void unknownQpsUnitFailsAtEngineeringBoundary() {
    auto program = parseSource(R"qps(
distance- 1/furlong_of_doom;
)qps");

    assert(program != nullptr);

    // QPS preserves the authored unit without deciding whether it is
    // physically meaningful.
    const auto& item =
        requireItem(*program, 0);

    assert(item.unit_hint_.has_value());
    assert(*item.unit_hint_ == "furlong_of_doom");

    bool rejected = false;

    try {
        (void)engineering::makeQuantity(item);
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

void constructionExecutionAndApplication() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition =
        requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    engine.registerDefinition(definition);

    const auto info =
        engine.inspectDefinition(definition);

    auto design =
        engineering::makeDesignInstance(
            "lever_A",
            info);

    assert(design.hasBinding("f"));
    assert(design.hasBinding("arm"));
    assert(!design.hasBinding("T"));

    const auto& f = design.binding("f");
    assert(!f.resolved);
    assert(!f.has_default);
    assert(!f.explicit_numeric_value.has_value());
    assert(
        f.declared_type ==
        engineering::BindingDeclaredType::NUMERIC);

    const auto& arm = design.binding("arm");
    assert(!arm.resolved);
    assert(arm.has_default);
    assert(!arm.explicit_numeric_value.has_value());
    assert(
        arm.declared_type ==
        engineering::BindingDeclaredType::NUMERIC);

    design.setBinding(
        explicitNumeric(
            design.binding("f"),
            10.0));

    const auto execution =
        engineering::executeDesignInstance(
            design,
            engine);

    assert(execution.scope.get("f").value == 10.0);
    assert(execution.scope.get("arm").value == 3.0);
    assert(execution.scope.get("T").value == 30.0);

    engineering::applyExecutionResult(
        design,
        execution);

    assert(design.binding("f").resolved);
    assert(design.binding("f").numeric_value == 10.0);
    assert(
        design.binding("f").explicit_numeric_value ==
        10.0);

    assert(design.binding("arm").resolved);
    assert(design.binding("arm").numeric_value == 3.0);

    // Critical authority assertion:
    // evaluating a QPS default does not create an Engineering
    // instance override.
    assert(
        !design.binding("arm")
             .explicit_numeric_value
             .has_value());

    assert(design.hasBinding("T"));
    assert(design.binding("T").resolved);
    assert(design.binding("T").numeric_value == 30.0);
    assert(
        !design.binding("T")
             .explicit_numeric_value
             .has_value());
    assert(
        design.binding("T").provenance ==
        engineering::BindingProvenance::DERIVED);
}

void executionLocalsDoNotEnterEngineeringState() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%tmp: f + arm
%[>T]: tmp * arm
})qps");

    const auto& definition =
        requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    engine.registerDefinition(definition);

    auto design =
        engineering::makeDesignInstance(
            "lever_local_filter",
            engine.inspectDefinition(definition));

    design.setBinding(
        explicitNumeric(
            design.binding("f"),
            10.0));

    const auto execution =
        engineering::executeDesignInstance(
            design,
            engine);

    assert(execution.scope.contains("tmp"));

    engineering::applyExecutionResult(
        design,
        execution);

    assert(design.hasBinding("f"));
    assert(design.hasBinding("arm"));
    assert(design.hasBinding("T"));
    assert(!design.hasBinding("tmp"));
}

void independentDesignInstancesRemainIndependent() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition =
        requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    engine.registerDefinition(definition);

    const auto info =
        engine.inspectDefinition(definition);

    auto a =
        engineering::makeDesignInstance(
            "lever_A",
            info);

    auto b =
        engineering::makeDesignInstance(
            "lever_B",
            info);

    a.setBinding(
        explicitNumeric(
            a.binding("f"),
            10.0));

    b.setBinding(
        explicitNumeric(
            b.binding("f"),
            20.0));

    auto execution_a =
        engineering::executeDesignInstance(
            a,
            engine);

    auto execution_b =
        engineering::executeDesignInstance(
            b,
            engine);

    engineering::applyExecutionResult(
        a,
        execution_a);

    engineering::applyExecutionResult(
        b,
        execution_b);

    assert(a.instanceId() != b.instanceId());

    assert(a.binding("f").numeric_value == 10.0);
    assert(b.binding("f").numeric_value == 20.0);

    assert(a.binding("T").numeric_value == 30.0);
    assert(b.binding("T").numeric_value == 60.0);
}

void sourceDerivedDefaultTracksDefinitionChange() {
    auto original_program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& original_definition =
        requireDefinition(*original_program);

    qps::runtime::ExecutionEngine original_engine;
    original_engine.registerDefinition(
        original_definition);

    auto design =
        engineering::makeDesignInstance(
            "lever_inherited_default",
            original_engine.inspectDefinition(
                original_definition));

    design.setBinding(
        explicitNumeric(
            design.binding("f"),
            10.0));

    auto first_execution =
        engineering::executeDesignInstance(
            design,
            original_engine);

    engineering::applyExecutionResult(
        design,
        first_execution);

    assert(design.binding("arm").numeric_value == 3.0);
    assert(design.binding("T").numeric_value == 30.0);

    // The evaluated default must still not be instance authority.
    assert(
        !design.binding("arm")
             .explicit_numeric_value
             .has_value());

    auto revised_program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 4/n;

%[>T]: f * arm
})qps");

    const auto& revised_definition =
        requireDefinition(*revised_program);

    qps::runtime::ExecutionEngine revised_engine;
    revised_engine.registerDefinition(
        revised_definition);

    auto second_execution =
        engineering::executeDesignInstance(
            design,
            revised_engine);

    engineering::applyExecutionResult(
        design,
        second_execution);

    // Same Engineering instance, same explicit f=10,
    // revised QPS inherited default arm=4.
    assert(design.binding("arm").numeric_value == 4.0);
    assert(design.binding("T").numeric_value == 40.0);

    assert(
        !design.binding("arm")
             .explicit_numeric_value
             .has_value());
}

void explicitOverrideSurvivesDefinitionChange() {
    auto original_program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& original_definition =
        requireDefinition(*original_program);

    qps::runtime::ExecutionEngine original_engine;
    original_engine.registerDefinition(
        original_definition);

    auto design =
        engineering::makeDesignInstance(
            "lever_explicit_override",
            original_engine.inspectDefinition(
                original_definition));

    design.setBinding(
        explicitNumeric(
            design.binding("f"),
            10.0));

    design.setBinding(
        explicitNumeric(
            design.binding("arm"),
            5.0));

    auto first_execution =
        engineering::executeDesignInstance(
            design,
            original_engine);

    engineering::applyExecutionResult(
        design,
        first_execution);

    assert(design.binding("arm").numeric_value == 5.0);
    assert(design.binding("T").numeric_value == 50.0);

    auto revised_program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 4/n;

%[>T]: f * arm
})qps");

    const auto& revised_definition =
        requireDefinition(*revised_program);

    qps::runtime::ExecutionEngine revised_engine;
    revised_engine.registerDefinition(
        revised_definition);

    auto second_execution =
        engineering::executeDesignInstance(
            design,
            revised_engine);

    engineering::applyExecutionResult(
        design,
        second_execution);

    // Explicit Engineering authority wins over revised source default.
    assert(
        design.binding("arm")
            .explicit_numeric_value ==
        5.0);

    assert(design.binding("arm").numeric_value == 5.0);
    assert(design.binding("T").numeric_value == 50.0);
}

void sourceProvenanceFlowsIntoEngineeringState() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition =
        requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    engine.registerDefinition(
        definition,
        "designs/leverage.qps");

    auto design =
        engineering::makeDesignInstance(
            "lever_provenance",
            engine.inspectRegisteredDefinition(
                "Leverage_Equation"));

    assert(design.definitionSource().has_value());
    assert(
        design.definitionSource()->source_document ==
        "designs/leverage.qps");

    assert(!design.evaluatedFrom().has_value());

    design.setBinding(
        explicitNumeric(
            design.binding("f"),
            10.0));

    const auto execution =
        engineering::executeDesignInstance(
            design,
            engine);

    assert(execution.source.has_value());

    engineering::applyExecutionResult(
        design,
        execution);

    assert(design.evaluatedFrom().has_value());
    assert(
        design.evaluatedFrom()->source_document ==
        "designs/leverage.qps");
}

void sourceLessEvaluationDoesNotInventEngineeringProvenance() {
    auto program = parseSource(R"qps({Leverage_Equation:
[>f]-/n;
[>arm]- 3/n;

%[>T]: f * arm
})qps");

    const auto& definition =
        requireDefinition(*program);

    qps::runtime::ExecutionEngine engine;
    engine.registerDefinition(definition);

    auto design =
        engineering::makeDesignInstance(
            "lever_no_source",
            engine.inspectRegisteredDefinition(
                "Leverage_Equation"));

    assert(!design.definitionSource().has_value());

    design.setBinding(
        explicitNumeric(
            design.binding("f"),
            10.0));

    const auto execution =
        engineering::executeDesignInstance(
            design,
            engine);

    engineering::applyExecutionResult(
        design,
        execution);

    assert(!design.evaluatedFrom().has_value());
}

void mismatchedDefinitionResultIsRejected() {
    engineering::DesignInstance design(
        "x",
        "expected_definition");

    qps::runtime::ExecutionInstance execution;
    execution.definition_id =
        "wrong_definition";

    bool rejected = false;

    try {
        engineering::applyExecutionResult(
            design,
            execution);
    } catch (const std::runtime_error&) {
        rejected = true;
    }

    assert(rejected);
}

} // namespace

int main() {
    qpsItemUnitsTranslateToEngineeringQuantities();
    unknownQpsUnitFailsAtEngineeringBoundary();
    constructionExecutionAndApplication();
    executionLocalsDoNotEnterEngineeringState();
    independentDesignInstancesRemainIndependent();

    sourceDerivedDefaultTracksDefinitionChange();
    explicitOverrideSurvivesDefinitionChange();

    sourceProvenanceFlowsIntoEngineeringState();
    sourceLessEvaluationDoesNotInventEngineeringProvenance();

    mismatchedDefinitionResultIsRejected();

    return 0;
}
