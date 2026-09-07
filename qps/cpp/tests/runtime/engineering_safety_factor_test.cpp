#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace ast = qps::ast;
namespace runtime = qps::runtime;
namespace fs = std::filesystem;

void expect(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string readFile(
    const fs::path& path) {

    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error(
            "Could not open authored safety factor floor: " +
            path.string());
    }

    return std::string(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

std::unique_ptr<ast::ProgramNode>
parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);

    return parser.parseProgram();
}

const ast::ExecutionBlockNode& authoredFloor(
    const ast::ProgramNode& program) {

    expect(
        program.statements.size() == 1,
        "Authored safety factor floor must contain one top-level statement.");

    const auto* floor =
        dynamic_cast<const ast::ExecutionBlockNode*>(
            program.statements.front().get());

    expect(
        floor != nullptr,
        "Authored safety factor floor must be an execution block.");

    return *floor;
}

const runtime::RuntimeValue& dictionaryEntry(
    const std::vector<runtime::RuntimeDictionaryEntry>& dictionary,
    int id,
    const std::string& context) {

    for (const auto& entry : dictionary) {
        if (entry.id == id) {
            return entry.value;
        }
    }

    throw std::runtime_error(
        context +
        " missing Dictionary entry " +
        std::to_string(id) +
        ".");
}

std::vector<runtime::RuntimeDictionaryEntry> executeFloor(
    const ast::ExecutionBlockNode& floor,
    double measured_safety_factor) {

    runtime::ExecutionScope scope;

    scope.bind(
        "measured_safety_factor",
        runtime::RuntimeValue::numeric(
            measured_safety_factor),
        std::nullopt,
        runtime::BindingOrigin::SUPPLIED);

    runtime::InterpreterOptions options;
    options.allow_return = true;
    options.symbol_resolver = nullptr;

    runtime::Interpreter interpreter(
        scope,
        runtime::FunctionTable{},
        options);

    const auto result =
        interpreter.executeForResult(floor);

    expect(
        result.has_value(),
        "Authored safety factor floor returned no value.");

    expect(
        result->isDictionary(),
        "Authored safety factor floor did not return a Dictionary.");

    return result->asDictionary(
        "authored safety factor floor");
}

double resultNumber(
    const std::vector<runtime::RuntimeDictionaryEntry>& result,
    int id,
    const std::string& context) {

    const auto& value =
        dictionaryEntry(
            result,
            id,
            context);

    expect(
        value.isNumeric(),
        context + " entry is not numeric.");

    return value.asNumber(context);
}

void expectNear(
    double actual,
    double expected,
    const std::string& context) {

    if (std::fabs(actual - expected) > 0.0000001) {
        throw std::runtime_error(
            context +
            " mismatch: expected " +
            std::to_string(expected) +
            ", got " +
            std::to_string(actual) +
            ".");
    }
}

void expectFloorResult(
    const ast::ExecutionBlockNode& floor,
    double measured_safety_factor,
    double expected_acceptable,
    double expected_shortfall,
    const std::string& witness) {

    const auto result =
        executeFloor(
            floor,
            measured_safety_factor);

    expectNear(
        resultNumber(result, 1, witness + " acceptable"),
        expected_acceptable,
        witness + " acceptable");

    expectNear(
        resultNumber(result, 2, witness + " shortfall"),
        expected_shortfall,
        witness + " shortfall");

    std::cout
        << witness
        << ": PASS\n";
}

} // namespace

int main(
    int argc,
    char** argv) {

    try {
        if (argc != 2) {
            std::cerr
                << "Usage: "
                << argv[0]
                << " <safety_factor_floor.qps>\n";
            return 2;
        }

        const auto program =
            parseSource(
                readFile(argv[1]));

        const auto& floor =
            authoredFloor(*program);

        expectFloorResult(floor, 2.8, 1.0, 0.0, "CASE_A");
        expectFloorResult(floor, 2.1, 0.0, 0.4, "CASE_B_NEGATIVE_WITNESS");
        expectFloorResult(floor, 2.5, 1.0, 0.0, "ON_FLOOR");

        std::cout
            << "QPS ENGINEERING SAFETY FACTOR FLOOR: PASS\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "ERROR: "
            << error.what()
            << "\n";
        return 1;
    }
}
