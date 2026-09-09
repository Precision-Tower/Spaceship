#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

#include <cassert>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::unique_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);
    return parser.parseProgram();
}

const qps::ast::ItemDeclarationNode& itemAt(
    const qps::ast::ProgramNode& program,
    std::size_t index) {

    require(
        index < program.statements.size(),
        "Missing expected Item declaration.");

    auto* item =
        dynamic_cast<
            const qps::ast::ItemDeclarationNode*>(
                program.statements[index].get());

    require(
        item != nullptr,
        "Expected Item declaration.");

    require(
        item->value_node_ != nullptr,
        "Expected Item value.");

    return *item;
}

qps::runtime::RuntimeValue evaluateItem(
    const std::string& source,
    std::size_t index) {

    auto program =
        parseSource(source);

    qps::runtime::ExecutionScope scope;
    qps::runtime::Interpreter interpreter(scope);

    return interpreter.evaluateValue(
        *itemAt(*program, index).value_node_);
}

bool throwsFor(
    const std::string& source) {

    try {
        (void)evaluateItem(
            source,
            0);
    }
    catch (const std::runtime_error&) {
        return true;
    }

    return false;
}

} // namespace

int main() {
    try {
        const std::string source =
            "empty- record();\n"
            "\n"
            "one- record(\"mass\", 2);\n"
            "\n"
            "mixed- record("
            "\"mass\", 2, "
            "\"unit\", \"kg\", "
            "\"nested\", record(\"x\", 1), "
            "\"values\", sequence(1, \"two\")"
            ");\n";

        const auto empty =
            evaluateItem(
                source,
                0);

        require(
            empty.isRecord(),
            "record() did not produce RECORD.");

        require(
            empty.kind() ==
                qps::runtime::RuntimeValue::Kind::RECORD,
            "record() runtime kind mismatch.");

        require(
            empty.asRecord("empty").empty(),
            "record() was not empty.");

        const auto one =
            evaluateItem(
                source,
                1);

        require(
            one.isRecord(),
            "single-field record did not produce RECORD.");

        const auto& one_fields =
            one.asRecord("one");

        require(
            one_fields.size() == 1,
            "single-field record size mismatch.");

        require(
            one_fields[0].name == "mass",
            "single-field record name mismatch.");

        require(
            one_fields[0].value.isNumeric() &&
            one_fields[0].value.asNumber(
                "one.mass") == 2.0,
            "single-field record value mismatch.");

        const auto mixed =
            evaluateItem(
                source,
                2);

        require(
            mixed.isRecord(),
            "mixed record did not produce RECORD.");

        const auto& fields =
            mixed.asRecord("mixed");

        require(
            fields.size() == 4,
            "mixed record field count mismatch.");

        require(
            fields[0].name == "mass" &&
            fields[0].value.asNumber(
                "mixed.mass") == 2.0,
            "mixed.mass mismatch.");

        require(
            fields[1].name == "unit" &&
            fields[1].value.asString(
                "mixed.unit") == "kg",
            "mixed.unit mismatch.");

        require(
            fields[2].name == "nested" &&
            fields[2].value.isRecord(),
            "mixed.nested mismatch.");

        const auto& nested =
            fields[2].value.asRecord(
                "mixed.nested");

        require(
            nested.size() == 1 &&
            nested[0].name == "x" &&
            nested[0].value.asNumber(
                "mixed.nested.x") == 1.0,
            "nested record mismatch.");

        require(
            fields[3].name == "values" &&
            fields[3].value.isSequence(),
            "mixed.values mismatch.");

        const auto& values =
            fields[3].value.asSequence(
                "mixed.values");

        require(
            values.size() == 2,
            "mixed.values size mismatch.");

        require(
            values[0].asNumber(
                "mixed.values[0]") == 1.0,
            "mixed.values[0] mismatch.");

        require(
            values[1].asString(
                "mixed.values[1]") == "two",
            "mixed.values[1] mismatch.");

        require(
            throwsFor(
                "bad- record(\"x\");\n"),
            "odd record argument count did not fail.");

        require(
            throwsFor(
                "bad- record(1, 2);\n"),
            "non-string record field name did not fail.");

        require(
            throwsFor(
                "bad- record(\"x\", 1, \"x\", 2);\n"),
            "duplicate record field did not fail.");

        std::cout
            << "QPS_RECORD_EXPRESSION=PASS\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "QPS_RECORD_EXPRESSION=FAIL: "
            << error.what()
            << '\n';

        return 1;
    }
}
