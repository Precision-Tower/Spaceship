#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <functional>
#include <iostream>
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

qps::runtime::ExecutionScope executeSource(const std::string& source) {
    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);

    auto program = parser.parseProgram();

    require(
        program->statements.size() == 1,
        "Expected one top-level execution block.");

    auto* block =
        dynamic_cast<qps::ast::ExecutionBlockNode*>(
            program->statements.front().get());

    require(
        block != nullptr,
        "Expected parsed source to be an execution block.");

    qps::runtime::ExecutionScope scope;
    qps::runtime::Interpreter interpreter(scope);
    interpreter.execute(*block);

    return scope;
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

void assertOrigin(
    const qps::runtime::RuntimeBinding& binding,
    qps::runtime::BindingOrigin expected,
    const std::string& context) {

    if (binding.origin != expected) {
        fail(
            context + ": expected origin " +
            qps::runtime::bindingOriginName(expected) +
            ", got " +
            qps::runtime::bindingOriginName(binding.origin) +
            ".");
    }
}

void assertSemanticSymbol(
    const qps::runtime::RuntimeBinding& binding,
    const std::optional<std::string>& expected,
    const std::string& context) {

    if (binding.semantic_symbol != expected) {
        std::string actual = binding.semantic_symbol.value_or("<none>");
        std::string wanted = expected.value_or("<none>");
        fail(
            context + ": expected semantic symbol " + wanted +
            ", got " + actual + ".");
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
    assertOrigin(binding, origin, name + " origin");
    assertSemanticSymbol(binding, semantic_symbol, name + " semantic symbol");
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


std::size_t countBindingsWithValue(
    const qps::runtime::ExecutionScope& scope,
    double expected_value) {

    std::size_t count = 0;

    for (const auto& binding : scope.bindings()) {
        if (std::fabs(binding.value - expected_value) <= 0.0000001) {
            ++count;
        }
    }

    return count;
}

void assertNoBindingWithValue(
    const qps::runtime::ExecutionScope& scope,
    double value,
    const std::string& context) {

    require(
        countBindingsWithValue(scope, value) == 0,
        context + ": did not expect any current binding with value " +
        numberToString(value) + ".");
}

void expectExecutionFailure(
    const std::string& source,
    const std::string& message_fragment) {

    try {
        (void)executeSource(source);
    } catch (const std::exception& e) {
        const std::string message = e.what();
        require(
            message.find(message_fragment) != std::string::npos,
            "Expected failure containing " + message_fragment +
            ", got " + message + ".");
        return;
    }

    fail("Expected execution to fail containing " + message_fragment + ".");
}

void semanticSuppliedAndDerivedBindings() {
    const auto scope = executeSource(R"qps({
[>v]- 30/n;
[>er]- 10/n;

%[>a]: v / er
%[>ew]: a * v
})qps");

    assertBindingOrder(scope, {"v", "er", "a", "ew"});
    assertBinding(scope, "v", 30.0, qps::runtime::BindingOrigin::SUPPLIED, "v");
    assertBinding(scope, "er", 10.0, qps::runtime::BindingOrigin::SUPPLIED, "er");
    assertBinding(scope, "a", 3.0, qps::runtime::BindingOrigin::DERIVED, "a");
    assertBinding(scope, "ew", 90.0, qps::runtime::BindingOrigin::DERIVED, "ew");
}

void localDerivedBindingsAndChainsUseEarlierBindings() {
    const auto scope = executeSource(R"qps({
[>v]- 30/n;
[>er]- 10/n;

%[>a]: v / er
%b: a * 2
%c: b + a
})qps");

    assertBindingOrder(scope, {"v", "er", "a", "b", "c"});
    assertBinding(scope, "a", 3.0, qps::runtime::BindingOrigin::DERIVED, "a");
    assertBinding(scope, "b", 6.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertBinding(scope, "c", 9.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
}

void arithmeticOperatorsEvaluate() {
    const auto scope = executeSource(R"qps({
[>left]- 18/n;
[>right]- 6/n;

%add: left + right
%subtract: left - right
%multiply: left * right
%divide: left / right
%precedence: left + right * 2
})qps");

    assertBinding(scope, "add", 24.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertBinding(scope, "subtract", 12.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertBinding(scope, "multiply", 108.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertBinding(scope, "divide", 3.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertBinding(scope, "precedence", 30.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
}

void parenthesizedArithmeticEvaluates() {
    const auto scope = executeSource(R"qps({
[>left]- 18/n;
[>right]- 6/n;

%grouped: (left + right) * (right - 2)
})qps");

    assertBinding(scope, "grouped", 96.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
}

void undefinedLocalIdentifierFailsClearly() {
    expectExecutionFailure(
        R"qps({
%bad: missing + 1
})qps",
        "Undefined execution value: missing");
}

void divisionByZeroFailsClearly() {
    expectExecutionFailure(
        R"qps({
[>x]- 4/n;

%bad: x / 0
})qps",
        "Division by zero");
}

void rebindingExistingLocalTargetOverwritesInPlace() {
    const auto scope = executeSource(R"qps({
%a: 1
%b: a + 1
%a: b + 3
})qps");

    assertBindingOrder(scope, {"a", "b"});
    assertBinding(scope, "a", 5.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertBinding(scope, "b", 2.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
}

void rebindingSemanticTargetOverwritesOriginAndValue() {
    const auto scope = executeSource(R"qps({
[>v]- 30/n;

%[>v]: v + 1
})qps");

    assertBindingOrder(scope, {"v"});
    assertBinding(scope, "v", 31.0, qps::runtime::BindingOrigin::DERIVED, "v");
}


void semanticRebindingPreservesSemanticIdentityAndCurrentLocal() {
    const auto scope = executeSource(R"qps({
[>v]- 30/n;
%a: v / 2
%[>v]: a * 3
})qps");

    assertBindingOrder(scope, {"v", "a"});
    assertBinding(scope, "v", 45.0, qps::runtime::BindingOrigin::DERIVED, "v");
    assertBinding(scope, "a", 15.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertNoBindingWithValue(scope, 30.0, "overwritten supplied v value");
}

void overwrittenSemanticBindingDoesNotExposePriorCausalHistory() {
    const auto scope = executeSource(R"qps({
[>v]- 30/n;
%a: v / 2
%[>v]: a * 3
})qps");

    const auto bindings = scope.bindings();

    require(
        bindings.size() == 2,
        "Expected current-scope snapshot to expose only final v and current a bindings.");

    assertNoBindingWithValue(scope, 30.0, "prior supplied event");
    assertBinding(scope, "v", 45.0, qps::runtime::BindingOrigin::DERIVED, "v");
    assertBinding(scope, "a", 15.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
}

void repeatedSemanticRebindingUsesCurrentValueDeterministically() {
    const std::string source = R"qps({
[>v]- 30/n;
%[>v]: v + 10
%[>v]: v * 2
})qps";

    for (int run = 0; run < 3; ++run) {
        const auto scope = executeSource(source);

        assertBindingOrder(scope, {"v"});
        assertBinding(scope, "v", 80.0, qps::runtime::BindingOrigin::DERIVED, "v");
        assertNoBindingWithValue(scope, 30.0, "prior supplied semantic value");
        assertNoBindingWithValue(scope, 40.0, "prior derived semantic value");
    }
}

void repeatedLocalRebindingUsesCurrentValueDeterministically() {
    const auto scope = executeSource(R"qps({
%a: 5
%a: a + 1
%a: a * 2
})qps");

    assertBindingOrder(scope, {"a"});
    assertBinding(scope, "a", 12.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertNoBindingWithValue(scope, 5.0, "prior initial local value");
    assertNoBindingWithValue(scope, 6.0, "prior intermediate local value");
}

void semanticAndLocalRebindingShareOverwriteBehaviorButKeepDifferentMetadata() {
    const auto scope = executeSource(R"qps({
[>v]- 5/n;
%a: 5
%[>v]: v + 1
%a: a + 1
})qps");

    assertBindingOrder(scope, {"v", "a"});
    assertBinding(scope, "v", 6.0, qps::runtime::BindingOrigin::DERIVED, "v");
    assertBinding(scope, "a", 6.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertNoBindingWithValue(scope, 5.0, "prior semantic and local values");
}

struct TestCase {
    const char* name;
    std::function<void()> run;
};

} // namespace

int main() {
    const std::vector<TestCase> tests = {
        {"semantic supplied and derived bindings", semanticSuppliedAndDerivedBindings},
        {"local derived bindings and chained calculations", localDerivedBindingsAndChainsUseEarlierBindings},
        {"arithmetic operators", arithmeticOperatorsEvaluate},
        {"parenthesized arithmetic", parenthesizedArithmeticEvaluates},
        {"undefined local identifier failure", undefinedLocalIdentifierFailsClearly},
        {"division by zero failure", divisionByZeroFailsClearly},
        {"local rebinding behavior", rebindingExistingLocalTargetOverwritesInPlace},
        {"semantic rebinding behavior", rebindingSemanticTargetOverwritesOriginAndValue},
        {"semantic rebinding preserves semantic identity and current local", semanticRebindingPreservesSemanticIdentityAndCurrentLocal},
        {"overwritten semantic binding lacks prior causal history", overwrittenSemanticBindingDoesNotExposePriorCausalHistory},
        {"repeated semantic rebinding determinism", repeatedSemanticRebindingUsesCurrentValueDeterministically},
        {"repeated local rebinding determinism", repeatedLocalRebindingUsesCurrentValueDeterministically},
        {"semantic and local rebinding metadata", semanticAndLocalRebindingShareOverwriteBehaviorButKeepDifferentMetadata},
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
        std::cerr << failures << " runtime semantics test(s) failed.\n";
        return 1;
    }

    return 0;
}
