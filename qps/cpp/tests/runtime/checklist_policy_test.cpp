#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

namespace ast = qps::ast;
namespace runtime = qps::runtime;
namespace fs = std::filesystem;

void require(
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
            "Could not open authored checklist policy: " +
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

const runtime::RuntimeValue&
dictionaryEntry(
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

runtime::RuntimeValue evidenceEntry(
    const std::string& id,
    bool present) {

    std::vector<runtime::RuntimeDictionaryEntry> facts;

    facts.push_back({
        1,
        runtime::RuntimeValue::string(id)
    });

    facts.push_back({
        2,
        runtime::RuntimeValue::numeric(
            present ? 1.0 : 0.0)
    });

    return runtime::RuntimeValue::dictionary(
        std::move(facts));
}

runtime::RuntimeValue evidence(
    bool runtime_dictionary,
    bool reference_test,
    bool reference_parity,
    bool structural_handle) {

    std::vector<runtime::RuntimeDictionaryEntry> entries;

    entries.push_back({
        1,
        evidenceEntry(
            "ctest.runtime_dictionary",
            runtime_dictionary)
    });

    entries.push_back({
        2,
        evidenceEntry(
            "ctest.reference_document_plan",
            reference_test)
    });

    entries.push_back({
        3,
        evidenceEntry(
            "authored.reference_document_parity",
            reference_parity)
    });

    entries.push_back({
        4,
        evidenceEntry(
            "invariant.structural_handle_owner_node_only",
            structural_handle)
    });

    return runtime::RuntimeValue::dictionary(
        std::move(entries));
}

std::vector<runtime::RuntimeDictionaryEntry>
executePolicy(
    const ast::ExecutionBlockNode& policy,
    runtime::RuntimeValue supplied_evidence) {

    runtime::ExecutionScope scope;

    scope.bind(
        "evidence",
        std::move(supplied_evidence),
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
        interpreter.executeForResult(policy);

    require(
        result.has_value(),
        "Authored checklist policy returned no value.");

    require(
        result->isDictionary(),
        "Authored checklist policy did not return Dictionary.");

    return result->asDictionary(
        "authored checklist policy result");
}

double resultState(
    const std::vector<runtime::RuntimeDictionaryEntry>& result,
    int result_id) {

    const auto& state =
        dictionaryEntry(
            result,
            result_id,
            "checklist result");

    require(
        state.isNumeric(),
        "Checklist result state is not numeric.");

    return state.asNumber(
        "checklist result state");
}

void allEvidenceProvesPolicy(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            evidence(
                true,
                true,
                true,
                true));

    require(
        resultState(
            result,
            1) == 1.0,
        "runtime.dictionary was not proven.");

    require(
        resultState(
            result,
            2) == 1.0,
        "policy.reference_document was not proven.");

    require(
        resultState(
            result,
            3) == 1.0,
        "kernel.structural_handle_minimal was not proven.");

    require(
        resultState(
            result,
            4) == 1.0,
        "Required checklist did not prove.");

    std::cout
        << "ALL_EVIDENCE_PRESENT: PASS\n";
}

void missingRequiredEvidenceFailsOverall(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            evidence(
                true,
                true,
                false,
                true));

    require(
        resultState(
            result,
            1) == 1.0,
        "Unrelated runtime.dictionary proof changed.");

    require(
        resultState(
            result,
            2) == 0.0,
        "Reference policy incorrectly proved with missing parity evidence.");

    require(
        resultState(
            result,
            3) == 1.0,
        "Unrelated StructuralHandle proof changed.");

    require(
        resultState(
            result,
            4) == 0.0,
        "Required checklist incorrectly proved.");

    std::cout
        << "MISSING_REQUIRED_EVIDENCE: PASS\n";
}

void wrongEvidenceIdentityDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    std::vector<runtime::RuntimeDictionaryEntry> entries;

    entries.push_back({
        1,
        evidenceEntry(
            "ctest.not_runtime_dictionary",
            true)
    });

    entries.push_back({
        2,
        evidenceEntry(
            "ctest.reference_document_plan",
            true)
    });

    entries.push_back({
        3,
        evidenceEntry(
            "authored.reference_document_parity",
            true)
    });

    entries.push_back({
        4,
        evidenceEntry(
            "invariant.structural_handle_owner_node_only",
            true)
    });

    const auto result =
        executePolicy(
            policy,
            runtime::RuntimeValue::dictionary(
                std::move(entries)));

    require(
        resultState(
            result,
            1) == 0.0,
        "Wrong evidence identity incorrectly proved runtime.dictionary.");

    require(
        resultState(
            result,
            4) == 0.0,
        "Wrong evidence identity incorrectly proved required checklist.");

    std::cout
        << "WRONG_EVIDENCE_IDENTITY: PASS\n";
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
                << " <checklist-policy.qps>\n";
            return 2;
        }

        const auto program =
            parseSource(
                readFile(argv[1]));

        require(
            program->statements.size() == 1,
            "Authored checklist policy must contain exactly one top-level statement.");

        const auto* policy =
            dynamic_cast<const ast::ExecutionBlockNode*>(
                program->statements.front().get());

        require(
            policy != nullptr,
            "Authored checklist policy top-level statement must be execution block.");

        allEvidenceProvesPolicy(*policy);
        missingRequiredEvidenceFailsOverall(*policy);
        wrongEvidenceIdentityDoesNotProve(*policy);

        std::cout
            << "QPS AUTHORED IMPLEMENTATION PROOF POLICY: PASS\n";

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
