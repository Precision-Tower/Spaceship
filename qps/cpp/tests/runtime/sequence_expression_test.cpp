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

namespace {

void require(bool condition, const std::string& message) {
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
        dynamic_cast<const qps::ast::ItemDeclarationNode*>(
            program.statements[index].get());

    require(
        item != nullptr,
        "Expected Item declaration.");

    require(
        item->value_node_ != nullptr,
        "Expected Item value.");

    return *item;
}

} // namespace

int main() {
    try {
        auto program = parseSource(
            "empty- sequence();\n"
            "\n"
            "one- sequence(1);\n"
            "\n"
            "mixed- sequence(1, \"two\", sequence(3, \"four\"));\n");

        require(
            program->statements.size() == 3,
            "Expected three sequence-valued Items.");

        qps::runtime::ExecutionScope scope;
        qps::runtime::Interpreter interpreter(scope);

        const auto empty =
            interpreter.evaluateValue(
                *itemAt(*program, 0).value_node_);

        require(
            empty.isSequence(),
            "sequence() did not produce SEQUENCE.");

        require(
            empty.asSequence("empty").empty(),
            "sequence() was not empty.");

        const auto one =
            interpreter.evaluateValue(
                *itemAt(*program, 1).value_node_);

        require(
            one.isSequence(),
            "sequence(1) did not produce SEQUENCE.");

        const auto& one_values =
            one.asSequence("one");

        require(
            one_values.size() == 1,
            "sequence(1) size mismatch.");

        require(
            one_values[0].isNumeric() &&
            std::fabs(
                one_values[0].asNumber("one[0]") - 1.0) <
                1e-9,
            "sequence(1) numeric value mismatch.");

        const auto mixed =
            interpreter.evaluateValue(
                *itemAt(*program, 2).value_node_);

        require(
            mixed.isSequence(),
            "heterogeneous sequence did not produce SEQUENCE.");

        const auto& values =
            mixed.asSequence("mixed");

        require(
            values.size() == 3,
            "heterogeneous sequence size mismatch.");

        require(
            values[0].isNumeric() &&
            std::fabs(
                values[0].asNumber("mixed[0]") - 1.0) <
                1e-9,
            "mixed[0] mismatch.");

        require(
            values[1].isString() &&
            values[1].asString("mixed[1]") == "two",
            "mixed[1] mismatch.");

        require(
            values[2].isSequence(),
            "mixed[2] is not nested SEQUENCE.");

        const auto& nested =
            values[2].asSequence("mixed[2]");

        require(
            nested.size() == 2,
            "nested sequence size mismatch.");

        require(
            nested[0].isNumeric() &&
            std::fabs(
                nested[0].asNumber("nested[0]") - 3.0) <
                1e-9,
            "nested[0] mismatch.");

        require(
            nested[1].isString() &&
            nested[1].asString("nested[1]") == "four",
            "nested[1] mismatch.");

        std::cout << "SEQUENCE_EXPRESSION=PASS\n";
        return 0;

    } catch (const std::exception& error) {
        std::cerr
            << "SEQUENCE_EXPRESSION=FAIL: "
            << error.what()
            << '\n';
        return 1;
    }
}
