#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <functional>
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

qps::runtime::ExecutionScope executeSource(
    const std::string& source) {

    auto program = parseSource(source);
    qps::runtime::ExecutionScope scope;
    qps::runtime::Interpreter interpreter(scope);
    interpreter.executeProgram(*program);
    return scope;
}

const qps::runtime::RuntimeBinding& requireBinding(
    const qps::runtime::ExecutionScope& scope,
    const std::string& name) {

    require(scope.contains(name), "Expected execution binding named " + name + ".");
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
    double expected) {

    assertNear(requireBinding(scope, name).value, expected, name + " value");
}

const qps::ast::FunctionDeclarationNode& requireFunction(
    const qps::ast::ProgramNode& program,
    std::size_t index = 0) {

    require(program.statements.size() > index, "Expected function declaration.");

    auto* function =
        dynamic_cast<qps::ast::FunctionDeclarationNode*>(
            program.statements[index].get());

    require(function != nullptr, "Expected FunctionDeclarationNode.");
    return *function;
}

const qps::ast::ContainerNode& requireParameterContainer(
    const qps::ast::FunctionDeclarationNode& function) {

    auto* container =
        dynamic_cast<qps::ast::ContainerNode*>(
            function.params_node_.get());

    require(container != nullptr, "Expected function parameters to be a ContainerNode.");
    return *container;
}

const qps::ast::ItemDeclarationNode& requireParameter(
    const qps::ast::FunctionDeclarationNode& function,
    std::size_t index) {

    const auto& container = requireParameterContainer(function);

    require(
        container.elements.size() > index,
        "Expected parameter at index " + std::to_string(index) + ".");

    auto* item =
        dynamic_cast<qps::ast::ItemDeclarationNode*>(
            container.elements[index].get());

    require(item != nullptr, "Expected ItemDeclarationNode parameter.");
    return *item;
}

const qps::ast::IdentifierNode& requireIdentifierTarget(
    const qps::ast::ItemDeclarationNode& item) {

    auto* identifier =
        dynamic_cast<qps::ast::IdentifierNode*>(
            item.getTarget());

    require(identifier != nullptr, "Expected identifier item target.");
    return *identifier;
}

const qps::ast::CalculationNode& requireCalculation(
    const qps::ast::ExecutionBlockNode& block,
    std::size_t index = 0) {

    require(block.statements.size() > index, "Expected calculation statement.");

    auto* calculation =
        dynamic_cast<qps::ast::CalculationNode*>(
            block.statements[index].get());

    require(calculation != nullptr, "Expected CalculationNode.");
    return *calculation;
}

const qps::ast::FunctionCallNode& requireFunctionCallExpression(
    const qps::ast::CalculationNode& calculation) {

    auto* call =
        dynamic_cast<qps::ast::FunctionCallNode*>(
            calculation.getExpression());

    require(call != nullptr, "Expected FunctionCallNode expression.");
    return *call;
}

void expectRuntimeFailure(
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

    fail("Expected runtime failure containing " + message_fragment + ".");
}

const char* leverageSource = R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}
)qps";

const char* leverageProgramSource = R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}

{
%answer: leverage(10, 3)
}
)qps";

void functionDeclarationParses() {
    auto program = parseSource(leverageSource);
    const auto& function = requireFunction(*program);

    require(function.name_ == "leverage", "Function name mismatch.");
    require(function.body_ != nullptr, "Function body missing.");
    require(function.body_->statements.size() == 2, "Function body statement count mismatch.");
}

void typedRequiredParametersAreRetained() {
    auto program = parseSource(leverageSource);
    const auto& function = requireFunction(*program);
    const auto& params = requireParameterContainer(function);

    require(params.elements.size() == 2, "Parameter count mismatch.");

    const auto& f = requireParameter(function, 0);
    const auto& arm = requireParameter(function, 1);

    require(requireIdentifierTarget(f).name_ == "f", "First parameter name mismatch.");
    require(requireIdentifierTarget(arm).name_ == "arm", "Second parameter name mismatch.");
    require(!f.value_node_, "f should be required, not defaulted.");
    require(!arm.value_node_, "arm should be required, not defaulted.");
    require(f.type_hint_ == qps::tokens::TokenType::TYPE_NUMERIC, "f numeric type hint missing.");
    require(arm.type_hint_ == qps::tokens::TokenType::TYPE_NUMERIC, "arm numeric type hint missing.");
}

void zeroArgumentFunctionParses() {
    auto program = parseSource(R"qps(-func answer(){
%T: 30
-return T;
}
)qps");

    const auto& function = requireFunction(*program);
    const auto& params = requireParameterContainer(function);

    require(function.name_ == "answer", "Zero-argument function name mismatch.");
    require(params.elements.empty(), "Zero-argument function should have no parameters.");
}

void functionCallParsesAsExpression() {
    auto program = parseSource(R"qps({
%answer: leverage(10, 3)
})qps");

    require(program->statements.size() == 1, "Expected one top-level block.");

    auto* block =
        dynamic_cast<qps::ast::ExecutionBlockNode*>(
            program->statements[0].get());

    require(block != nullptr, "Expected ExecutionBlockNode.");

    const auto& call = requireFunctionCallExpression(requireCalculation(*block));

    require(call.name_ == "leverage", "Function call name mismatch.");
    require(call.arguments_.size() == 2, "Function call argument count mismatch.");
}

void positionalArgumentsBindInDeclarationOrder() {
    const auto scope = executeSource(R"qps(-func ordered(
f-/n;
arm-/n;
){
%T: f - arm
-return T;
}

{
%answer: ordered(10, 3)
}
)qps");

    assertBinding(scope, "answer", 7.0);
}

void leverageReturnsThirty() {
    const auto scope = executeSource(leverageProgramSource);
    assertBinding(scope, "answer", 30.0);
}

void callerCanStoreReturnValue() {
    const auto scope = executeSource(leverageProgramSource);

    require(scope.contains("answer"), "Caller should store function return value.");
    assertBinding(scope, "answer", 30.0);
}

void returnedLocalIdentifierResolvesFromFunctionScope() {
    const auto scope = executeSource(R"qps(-func local_value(
f-/n;
arm-/n;
){
%product: f * arm
%offset: product + 2
-return offset;
}

{
%answer: local_value(10, 3)
}
)qps");

    assertBinding(scope, "answer", 32.0);
}

void functionLocalBindingsDoNotLeakIntoCaller() {
    const auto scope = executeSource(leverageProgramSource);

    require(!scope.contains("f"), "Function parameter f leaked into caller.");
    require(!scope.contains("arm"), "Function parameter arm leaked into caller.");
    require(!scope.contains("T"), "Function local T leaked into caller.");
    assertBinding(scope, "answer", 30.0);
}

void twoInvocationsReceiveIndependentScopes() {
    const auto scope = executeSource(R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}

{
%first: leverage(10, 3)
%second: leverage(2, 9)
}
)qps");

    assertBinding(scope, "first", 30.0);
    assertBinding(scope, "second", 18.0);
}

void callerIdentifiersCanBeArguments() {
    const auto scope = executeSource(R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}

{
%f: 10
%arm: 3
%answer: leverage(f, arm)
}
)qps");

    assertBinding(scope, "answer", 30.0);
}

void literalDefaultParameterExecutes() {
    const auto scope = executeSource(R"qps(-func leverage(
f-/n;
arm- 3/n;
){
%T: f * arm
-return T;
}

{
%answer: leverage(10)
}
)qps");

    assertBinding(scope, "answer", 30.0);
}

void suppliedArgumentOverridesDefault() {
    const auto scope = executeSource(R"qps(-func leverage(
f-/n;
arm- 3/n;
){
%T: f * arm
-return T;
}

{
%answer: leverage(10, 4)
}
)qps");

    assertBinding(scope, "answer", 40.0);
}

void laterDefaultCanReferenceEarlierParameter() {
    const auto scope = executeSource(R"qps(-func scale(
value-/n;
factor- value/n;
){
%T: value * factor
-return T;
}

{
%answer: scale(4)
}
)qps");

    assertBinding(scope, "answer", 16.0);
}

void requiredParameterAfterDefaultFailsClearly() {
    expectRuntimeFailure(R"qps(-func broken(
first- 3/n;
second-/n;
){
-return second;
}
)qps",
        "Required function parameter 'second' follows a defaulted parameter");
}

void tooFewArgumentsFailClearly() {
    expectRuntimeFailure(R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}

{
%answer: leverage(10)
}
)qps", "Too few arguments for function 'leverage'");
}

void tooManyArgumentsFailClearly() {
    expectRuntimeFailure(R"qps(-func leverage(
f-/n;
arm-/n;
){
%T: f * arm
-return T;
}

{
%answer: leverage(10, 3, 2)
}
)qps", "Too many arguments for function 'leverage'");
}

void undefinedFunctionFailsClearly() {
    expectRuntimeFailure(R"qps({
%answer: missing(10, 3)
})qps", "Undefined function 'missing'");
}

void undefinedReturnIdentifierFailsClearly() {
    expectRuntimeFailure(R"qps(-func broken(){
%T: 30
-return missing;
}

{
%answer: broken()
}
)qps", "Undefined return identifier 'missing'");
}

struct TestCase {
    const char* name;
    std::function<void()> run;
};

} // namespace

int main() {
    const std::vector<TestCase> tests = {
        {"function declaration parses", functionDeclarationParses},
        {"typed required parameters are retained", typedRequiredParametersAreRetained},
        {"zero-argument function parses", zeroArgumentFunctionParses},
        {"function call parses as expression", functionCallParsesAsExpression},
        {"positional arguments bind in declaration order", positionalArgumentsBindInDeclarationOrder},
        {"leverage returns 30", leverageReturnsThirty},
        {"caller can store return value", callerCanStoreReturnValue},
        {"returned local identifier resolves from function scope", returnedLocalIdentifierResolvesFromFunctionScope},
        {"function-local bindings do not leak into caller", functionLocalBindingsDoNotLeakIntoCaller},
        {"two invocations receive independent scopes", twoInvocationsReceiveIndependentScopes},
        {"caller identifiers can be arguments", callerIdentifiersCanBeArguments},
        {"literal default parameter executes", literalDefaultParameterExecutes},
        {"supplied argument overrides default", suppliedArgumentOverridesDefault},
        {"later default can reference earlier parameter", laterDefaultCanReferenceEarlierParameter},
        {"required parameter after default fails clearly", requiredParameterAfterDefaultFailsClearly},
        {"too few arguments fail clearly", tooFewArgumentsFailClearly},
        {"too many arguments fail clearly", tooManyArgumentsFailClearly},
        {"undefined function fails clearly", undefinedFunctionFailsClearly},
        {"undefined return identifier fails clearly", undefinedReturnIdentifierFailsClearly},
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
        std::cerr << failures << " function semantic test(s) failed.\n";
        return 1;
    }

    return 0;
}
