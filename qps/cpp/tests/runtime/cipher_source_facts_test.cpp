#include "../../src/parser/h/_index.hpp"
#include "../../src/runtime/h/execution_engine.hpp"
#include "../../src/runtime/h/symbol_table.hpp"
#include "../../src/tokens/h/char_stream.hpp"
#include "../../src/tokens/h/lexer.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace fs = std::filesystem;

namespace {

std::string readFile(const fs::path& path) {
    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error(
            "Unable to open " + path.string());
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

} // namespace


int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            throw std::runtime_error(
                "usage: qps_cipher_source_facts_test "
                "<cipher.qps> <repo-root> <source.py>");
        }

        const fs::path cipher = argv[1];
        const fs::path root = argv[2];
        const fs::path source = argv[3];

        auto program =
            parseSource(
                readFile(cipher));

        qps::runtime::ExecutionEngine engine;

        engine.registerDefinitions(
            *program);

        using qps::runtime::RuntimeValue;

        std::unordered_map<
            std::string,
            RuntimeValue
        > inputs;

        inputs.emplace(
            "source",
            RuntimeValue::string(
                source.string()));

        inputs.emplace(
            "root",
            RuntimeValue::string(
                root.string()));

        const auto instance =
            engine.instantiate(
                "Cipher_Source_Facts",
                inputs);

        require(
            instance.result.has_value(),
            "Cipher_Source_Facts returned no value.");

        require(
            instance.result->isStructure(),
            "Cipher_Source_Facts did not return STRUCTURE.");

        const auto& structure =
            instance.result->asStructure(
                "Cipher_Source_Facts result");

        require(
            structure.document_owner != nullptr,
            "Cipher facts own no parsed document.");

        require(
            structure.target_node != nullptr,
            "Cipher facts have no structural target.");

        require(
            structure.target_node ==
                structure.document_owner.get(),
            "Cipher facts did not return parsed root.");

        std::cout
            << "CIPHER_SOURCE_FACTS_RUNTIME=PASS\n";

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
