#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

std::unique_ptr<qps::ast::ProgramNode>
parseSource(const std::string& source) {
    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);
    return parser.parseProgram();
}

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

} // namespace

int main() {
    try {
        auto program = parseSource(R"qps(
[
1: "compact",
2: "comfortable",
3: 42,
4: [
1: "nested"
];
];
)qps");

        require(
            program->statements.size() == 1,
            "Expected one parsed Dictionary declaration.");

        const auto* dictionary_node =
            dynamic_cast<
                const qps::ast::DictionaryDeclarationNode*>(
                    program->statements.front().get());

        require(
            dictionary_node != nullptr,
            "Expected parsed source to be a Dictionary declaration.");

        qps::runtime::ExecutionScope scope;
        qps::runtime::Interpreter interpreter(scope);

        const auto value =
            interpreter.evaluateValue(*dictionary_node);

        require(
            value.isDictionary(),
            "Dictionary binding is not DICTIONARY runtime value.");

        const auto& dictionary =
            value.asDictionary("settings");

        require(
            dictionary.size() == 4,
            "Dictionary runtime size mismatch.");

        require(
            dictionary[0].id == 1 &&
            dictionary[0].value.isString() &&
            dictionary[0].value.asString("entry 1") == "compact",
            "Dictionary entry 1 mismatch.");

        require(
            dictionary[1].id == 2 &&
            dictionary[1].value.isString() &&
            dictionary[1].value.asString("entry 2") == "comfortable",
            "Dictionary entry 2 mismatch.");

        require(
            dictionary[2].id == 3 &&
            dictionary[2].value.isNumeric() &&
            dictionary[2].value.asNumber("entry 3") == 42.0,
            "Dictionary entry 3 mismatch.");

        require(
            dictionary[3].id == 4 &&
            dictionary[3].value.isDictionary(),
            "Dictionary entry 4 was not nested dictionary.");

        const auto& nested_dictionary =
            dictionary[3].value.asDictionary("entry 4");

        require(
            nested_dictionary.size() == 1 &&
            nested_dictionary[0].id == 1 &&
            nested_dictionary[0].value.isString() &&
            nested_dictionary[0].value.asString("nested entry 1") == "nested",
            "Nested dictionary entry mismatch.");

        std::cout << "RUNTIME DICTIONARY: PASS\n";

    {
        auto program = parseSource(R"qps({
-return [
1: "defs/shape.qps",
2: 2
];;
})qps");

        require(
            program->statements.size() == 1,
            "Expected one top-level execution block.");

        const auto* execution =
            dynamic_cast<const qps::ast::ExecutionBlockNode*>(
                program->statements.front().get());

        require(
            execution != nullptr,
            "Expected parsed source to be an execution block.");

        qps::runtime::ExecutionScope scope;

        qps::runtime::InterpreterOptions options;
        options.allow_return = true;

        qps::runtime::Interpreter interpreter(
            scope,
            {},
            options);

        const auto result =
            interpreter.executeForResult(*execution);

        require(
            result.has_value(),
            "Expected Dictionary return expression to produce a value.");

        require(
            result->isDictionary(),
            "Expected Dictionary return expression to produce a Dictionary.");

        const auto& dictionary =
            result->asDictionary("returned Dictionary");

        require(
            dictionary.size() == 2,
            "Returned Dictionary size mismatch.");

        require(
            dictionary[0].id == 1 &&
            dictionary[0].value.isString() &&
            dictionary[0].value.asString("entry 1") == "defs/shape.qps",
            "Returned Dictionary entry 1 mismatch.");

        require(
            dictionary[1].id == 2 &&
            dictionary[1].value.isNumeric() &&
            dictionary[1].value.asNumber("entry 2") == 2.0,
            "Returned Dictionary entry 2 mismatch.");
    }

    return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << "\n";
        return 1;
    }
}
