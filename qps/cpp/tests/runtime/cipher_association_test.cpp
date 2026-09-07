#include "../../src/parser/h/_index.hpp"
#include "../../src/runtime/h/execution_engine.hpp"
#include "../../src/tokens/h/char_stream.hpp"
#include "../../src/tokens/h/lexer.hpp"

#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

std::string readFile(const std::string& path) {
    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error(
            "Unable to open Cipher authority: " + path);
    }

    std::ostringstream buffer;
    buffer << input.rdbuf();
    return buffer.str();
}

std::shared_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream stream(source);
    qps::tokens::Lexer lexer(stream);
    qps::parser::Parser parser(lexer);

    return std::shared_ptr<qps::ast::ProgramNode>(
        parser.parseProgram().release());
}

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string association(
    qps::runtime::ExecutionEngine& engine,
    const std::string& local_name,
    const std::string& target_address,
    const std::string& source_kind) {

    using qps::runtime::RuntimeValue;

    std::unordered_map<std::string, RuntimeValue> overrides;

    overrides.emplace(
        "local_name",
        RuntimeValue::string(local_name));

    overrides.emplace(
        "target_address",
        RuntimeValue::string(target_address));

    overrides.emplace(
        "source_kind",
        RuntimeValue::string(source_kind));

    const auto instance =
        engine.instantiate(
            "Cipher_Association",
            overrides);

    require(
        instance.result.has_value(),
        "Cipher_Association returned no value.");

    return instance.result->asString(
        "Cipher_Association result");
}

} // namespace


int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error(
                "usage: qps_cipher_association_test "
                "<cipher.qps>");
        }

        auto program =
            parseSource(
                readFile(argv[1]));

        qps::runtime::ExecutionEngine engine;

        engine.registerDefinitions(
            *program);

        require(
            association(
                engine,
                "EquationResult",
                "/equations.EquationResult",
                "definition")
            ==
            "EquationResult: "
            "[>/equations.EquationResult];",
            "definition did not render Term association");

        require(
            association(
                engine,
                "weight_force_n",
                ".motion.weight_force_n",
                "function")
            ==
            "weight_force_n: "
            "[>.motion.weight_force_n];",
            "function did not render Term association");

        require(
            association(
                engine,
                "GRAVITY_EARTH_M_S2",
                "/constants.GRAVITY_EARTH_M_S2",
                "item")
            ==
            "GRAVITY_EARTH_M_S2- "
            "[>/constants.GRAVITY_EARTH_M_S2-];",
            "item did not render Item association");

        require(
            association(
                engine,
                "value",
                ".source.value",
                "assignment")
            ==
            "",
            "unsupported primitive unexpectedly rendered");

        std::cout
            << "CIPHER_ASSOCIATION_POLICY=PASS\n";

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
