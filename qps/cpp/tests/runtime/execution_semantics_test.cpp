#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
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
[>v-] 30/n;
[>er-] 10/n;

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
[>v-] 30/n;
[>er-] 10/n;

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
[>left-] 18/n;
[>right-] 6/n;

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
[>left-] 18/n;
[>right-] 6/n;

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
[>x-] 4/n;

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
[>v-] 30/n;

%[>v]: v + 1
})qps");

    assertBindingOrder(scope, {"v"});
    assertBinding(scope, "v", 31.0, qps::runtime::BindingOrigin::DERIVED, "v");
}


void semanticRebindingPreservesSemanticIdentityAndCurrentLocal() {
    const auto scope = executeSource(R"qps({
[>v-] 30/n;
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
[>v-] 30/n;
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
[>v-] 30/n;
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
[>v-] 5/n;
%a: 5
%[>v]: v + 1
%a: a + 1
})qps");

    assertBindingOrder(scope, {"v", "a"});
    assertBinding(scope, "v", 6.0, qps::runtime::BindingOrigin::DERIVED, "v");
    assertBinding(scope, "a", 6.0, qps::runtime::BindingOrigin::LOCAL, std::nullopt);
    assertNoBindingWithValue(scope, 5.0, "prior semantic and local values");
}

void stringItemsBecomeRuntimeValues() {
    const auto scope = executeSource(R"qps({
[>program-] "cmake";
[>cwd-] "qps/cpp";
})qps");

    const auto& program =
        requireBinding(scope, "program");

    require(
        program.value.kind() ==
            qps::runtime::RuntimeValue::Kind::STRING,
        "program should have STRING runtime kind.");

    require(
        program.value.asString("program") == "cmake",
        "program should preserve authored string value.");

    assertOrigin(
        program,
        qps::runtime::BindingOrigin::SUPPLIED,
        "program");

    assertSemanticSymbol(
        program,
        std::optional<std::string>("program"),
        "program");

    const auto& cwd =
        requireBinding(scope, "cwd");

    require(
        cwd.value.isString(),
        "cwd should be a string runtime value.");

    require(
        cwd.value.asString("cwd") == "qps/cpp",
        "cwd should preserve authored string value.");

    assertOrigin(
        cwd,
        qps::runtime::BindingOrigin::SUPPLIED,
        "cwd");

    assertSemanticSymbol(
        cwd,
        std::optional<std::string>("cwd"),
        "cwd");
}

void namedHostActionBindsProcessResult() {
    const auto scope = executeSource(R"qps({
[>fixture-] 0/n;

probe: -process(
program- "python3";
arg_0- "-c";
arg_1- "import sys;sys.stdout.write('OUT');sys.stderr.write('ERR');sys.exit(7)";
);
})qps");

    const auto& exit_code =
        requireBinding(
            scope,
            "probe_exit_code");

    require(
        exit_code.value.isNumeric(),
        "process exit code should be numeric");

    require(
        exit_code.value.asNumber(
            "probe_exit_code") == 7.0,
        "process exit code mismatch");

    const auto& stdout_value =
        requireBinding(
            scope,
            "probe_stdout");

    require(
        stdout_value.value.isString(),
        "process stdout should be string");

    require(
        stdout_value.value.asString(
            "probe_stdout") == "OUT",
        "process stdout mismatch");

    const auto& stderr_value =
        requireBinding(
            scope,
            "probe_stderr");

    require(
        stderr_value.value.isString(),
        "process stderr should be string");

    require(
        stderr_value.value.asString(
            "probe_stderr") == "ERR",
        "process stderr mismatch");
}


void itemValuesComposeStringsAndNumbers() {
    const auto scope = executeSource(R"qps({
[>path-] "qps";
[>index-] path + "/_index.qps";

[>prefix-] "root/";
[>nested-] prefix + path + "/_index.qps";

[>left-] 2/n;
[>right-] 3/n;
[>sum-] left + right;
})qps");

    const auto& index =
        requireBinding(scope, "index");

    require(
        index.value.isString(),
        "composed index path should be STRING.");

    require(
        index.value.asString("index") ==
            "qps/_index.qps",
        "string Item composition mismatch.");

    const auto& nested =
        requireBinding(scope, "nested");

    require(
        nested.value.isString(),
        "nested composed path should be STRING.");

    require(
        nested.value.asString("nested") ==
            "root/qps/_index.qps",
        "chained string Item composition mismatch.");

    const auto& sum =
        requireBinding(scope, "sum");

    require(
        sum.value.isNumeric(),
        "numeric Item addition should remain NUMERIC.");

    require(
        sum.value.asNumber("sum") == 5.0,
        "numeric RuntimeValue addition mismatch.");
}

void qpsDerivesConnectedModuleAncestryFromFilesystemFacts() {
    namespace fs = std::filesystem;

    const fs::path fixture =
        fs::absolute("__qps_connected_ancestry_fixture__")
            .lexically_normal();

    fs::remove_all(fixture);

    fs::create_directories(fixture / "connected/child");
    fs::create_directories(fixture / "broken/child");

    {
        std::ofstream root_index(fixture / "_index.qps");
        require(
            static_cast<bool>(root_index),
            "Expected root fixture index to be writable.");
        root_index << "fixture.\\n\\n";

        std::ofstream connected_index(
            fixture / "connected/_index.qps");
        require(
            static_cast<bool>(connected_index),
            "Expected connected fixture index to be writable.");
        connected_index << "connected.\\n\\n";

        std::ofstream child_index(
            fixture / "connected/child/_index.qps");
        require(
            static_cast<bool>(child_index),
            "Expected connected child index to be writable.");
        child_index << "child.\\n\\n";

        std::ofstream broken_child_index(
            fixture / "broken/child/_index.qps");
        require(
            static_cast<bool>(broken_child_index),
            "Expected broken child index to be writable.");
        broken_child_index << "child.\\n\\n";
    }

    const auto run_policy =
        [&](const fs::path& target) {

            const std::string root =
                fixture.generic_string();

            const std::string path =
                target.generic_string();

            const std::string source =
                "{\n"
                "[>root-] \"" + root + "\";\n"
                "[>path-] \"" + path + "\";\n"
                "\n"
                "[>current-] path;\n"
                "[>active-] 1;\n"
                "[>connected-] 1;\n"
                "\n"
                "-while active == 1 {\n"
                "[>index_path-] current + \"/_index.qps\";\n"
                "\n"
                "directory_kind: -path_kind(\n"
                "path- current;\n"
                ");\n"
                "\n"
                "index_kind: -path_kind(\n"
                "path- index_path;\n"
                ");\n"
                "\n"
                "-if directory_kind == \"directory\" {\n"
                "-if index_kind == \"file\" {\n"
                "[>active-] active;\n"
                "}\n"
                "-else {\n"
                "[>connected-] 0;\n"
                "[>active-] 0;\n"
                "}\n"
                "}\n"
                "-else {\n"
                "[>connected-] 0;\n"
                "[>active-] 0;\n"
                "}\n"
                "\n"
                "-if active == 1 {\n"
                "-if current == root {\n"
                "[>active-] 0;\n"
                "}\n"
                "-else {\n"
                "parent: -path_parent(\n"
                "path- current;\n"
                ");\n"
                "[>current-] parent;\n"
                "}\n"
                "}\n"
                "}\n"
                "}\n";

            return executeSource(source);
        };

    try {
        const auto connected =
            run_policy(fixture / "connected/child");

        require(
            requireBinding(
                connected,
                "connected").value.asNumber(
                    "connected ancestry result") == 1.0,
            "Fully indexed ancestry should be connected.");

        const auto broken =
            run_policy(fixture / "broken/child");

        require(
            requireBinding(
                broken,
                "connected").value.asNumber(
                    "broken ancestry result") == 0.0,
            "Missing ancestor _index.qps should break connectivity.");

        const auto root =
            run_policy(fixture);

        require(
            requireBinding(
                root,
                "connected").value.asNumber(
                    "root ancestry result") == 1.0,
            "Workspace root should satisfy its own module boundary.");
    }
    catch (...) {
        fs::remove_all(fixture);
        throw;
    }

    fs::remove_all(fixture);
}


struct TestCase {
    const char* name;
    std::function<void()> run;
};

} // namespace


void whileRebindsLocalItemUntilConditionIsFalse() {
    const std::string source = R"qps(
{
[>count-] 0;

-while count < 3 {
[>count-] count + 1;
}
}
)qps";

    const qps::runtime::ExecutionScope scope =
        executeSource(source);

    require(
        scope.contains("count"),
        "while loop should preserve count binding.");

    require(
        scope.get("count").value.isNumeric(),
        "while loop count should remain NUMERIC.");

    require(
        scope.get("count").value.asNumber(
            "count") == 3.0,
        "while loop should stop when count reaches 3.");
}


void calculationBindsDictionaryRuntimeValue() {
    const std::string source = R"qps(
{
%record: [
1: "evidence.id",
2: 1
];
}
)qps";

    const qps::runtime::ExecutionScope scope =
        executeSource(source);

    require(
        scope.contains("record"),
        "Dictionary calculation should bind record.");

    const auto& value =
        scope.get("record").value;

    require(
        value.isDictionary(),
        "Dictionary calculation should produce DICTIONARY runtime value.");

    const auto& dictionary =
        value.asDictionary(
            "calculation record");

    require(
        dictionary.size() == 2,
        "Dictionary calculation size mismatch.");

    require(
        dictionary[0].id == 1 &&
        dictionary[0].value.isString() &&
        dictionary[0].value.asString(
            "calculation entry 1") == "evidence.id",
        "Dictionary calculation entry 1 mismatch.");

    require(
        dictionary[1].id == 2 &&
        dictionary[1].value.isNumeric() &&
        dictionary[1].value.asNumber(
            "calculation entry 2") == 1.0,
        "Dictionary calculation entry 2 mismatch.");
}


void ifSelectsNumericLessThanBranch() {
    const std::string source = R"qps(
{
[>count-] 2;

-if count < 3 {
[>selected-] "if";
}
-else {
[>selected-] "else";
}
}
)qps";

    const qps::runtime::ExecutionScope scope =
        executeSource(source);

    require(
        scope.contains("selected"),
        "numeric less-than if should bind selected.");

    require(
        scope.get("selected").value.asString(
            "selected") == "if",
        "2 < 3 should select if branch.");
}


void ifSelectsStringEqualityBranch() {
    const std::string source = R"qps(
{
[>kind-] "directory";

-if kind == "directory" {
[>selected-] "if";
}
-else {
[>selected-] "else";
}
}
)qps";

    const qps::runtime::ExecutionScope scope =
        executeSource(source);

    require(
        scope.contains("selected"),
        "if should bind selected.");

    require(
        scope.get("selected").value.asString(
            "selected") == "if",
        "true string equality should select if branch.");
}

void ifSelectsElseBranch() {
    const std::string source = R"qps(
{
[>kind-] "file";

-if kind == "directory" {
[>selected-] "if";
}
-else {
[>selected-] "else";
}
}
)qps";

    const qps::runtime::ExecutionScope scope =
        executeSource(source);

    require(
        scope.contains("selected"),
        "else should bind selected.");

    require(
        scope.get("selected").value.asString(
            "selected") == "else",
        "false string equality should select else branch.");
}

int main() {
    const std::vector<TestCase> tests = {
        {"QPS derives connected module ancestry from filesystem facts", qpsDerivesConnectedModuleAncestryFromFilesystemFacts},
        {"while rebinds local Item until condition is false", whileRebindsLocalItemUntilConditionIsFalse},
        {"calculation binds Dictionary runtime value", calculationBindsDictionaryRuntimeValue},
        {"if selects numeric less-than branch", ifSelectsNumericLessThanBranch},
        {"if selects string equality branch", ifSelectsStringEqualityBranch},
        {"if selects else branch", ifSelectsElseBranch},
        {"semantic supplied and derived bindings", semanticSuppliedAndDerivedBindings},
        {"string Items become runtime values", stringItemsBecomeRuntimeValues},
        {"Item values compose strings and numbers", itemValuesComposeStringsAndNumbers},
        {"named host action binds process result", namedHostActionBindsProcessResult},
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
