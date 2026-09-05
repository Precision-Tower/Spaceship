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
    bool structural_handle,
    bool semantic_walk_test,
    bool semantic_walk_parity,
    bool semantic_walk_cutover,
    bool compatibility_absent,
    bool native_reference_absent,
    bool native_walk_absent,
    bool grammar_regression = true,
    bool parser_goldens = true,
    bool corpus_ast_conformance = true,
    bool active_corpus_conformance = true,
    bool runtime_semantics = true,
    bool function_semantics = true,
    bool execution_definition = true,
    bool structural_selection = true,
    bool symbol_resolver = true,
    bool path_resolver = true,
    bool host_action = true,
    bool cli_test = true,
    bool cli_probe = true,
    bool cli_dir = true,
    bool cli_query = true,
    bool cli_cipher = true,
    bool cli_source_execution = true,
    bool engineering_qps = true,
    bool authored_authorities = true) {

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

    entries.push_back({
        5,
        evidenceEntry(
            "ctest.semantic_walk",
            semantic_walk_test)
    });

    entries.push_back({
        6,
        evidenceEntry(
            "authored.semantic_walk.parity",
            semantic_walk_parity)
    });

    entries.push_back({
        7,
        evidenceEntry(
            "production.semantic_walk.cutover",
            semantic_walk_cutover)
    });

    entries.push_back({
        8,
        evidenceEntry(
            "absence.structural_handle.compatibility_metadata",
            compatibility_absent)
    });

    entries.push_back({
        9,
        evidenceEntry(
            "absence.native.reference_policy",
            native_reference_absent)
    });

    entries.push_back({
        10,
        evidenceEntry(
            "absence.native.semantic_walk",
            native_walk_absent)
    });

    entries.push_back({
        11,
        evidenceEntry(
            "ctest.grammar_regression",
            grammar_regression)
    });

    entries.push_back({
        12,
        evidenceEntry(
            "ctest.parser_goldens",
            parser_goldens)
    });

    entries.push_back({
        13,
        evidenceEntry(
            "ctest.corpus_ast_conformance",
            corpus_ast_conformance)
    });

    entries.push_back({
        14,
        evidenceEntry(
            "ctest.active_corpus_conformance",
            active_corpus_conformance)
    });

    entries.push_back({
        15,
        evidenceEntry(
            "ctest.runtime_semantics",
            runtime_semantics)
    });

    entries.push_back({
        16,
        evidenceEntry(
            "ctest.function_semantics",
            function_semantics)
    });

    entries.push_back({
        17,
        evidenceEntry(
            "ctest.execution_definition",
            execution_definition)
    });

    entries.push_back({
        18,
        evidenceEntry(
            "ctest.structural_selection",
            structural_selection)
    });

    entries.push_back({
        19,
        evidenceEntry(
            "ctest.symbol_resolver",
            symbol_resolver)
    });

    entries.push_back({
        20,
        evidenceEntry(
            "ctest.path_resolver_index_surface",
            path_resolver)
    });

    entries.push_back({
        21,
        evidenceEntry(
            "ctest.host_action",
            host_action)
    });

    entries.push_back({
        22,
        evidenceEntry(
            "ctest.cli.test",
            cli_test)
    });

    entries.push_back({
        23,
        evidenceEntry(
            "ctest.cli.probe",
            cli_probe)
    });

    entries.push_back({
        24,
        evidenceEntry(
            "ctest.cli.dir",
            cli_dir)
    });

    entries.push_back({
        25,
        evidenceEntry(
            "ctest.cli.query",
            cli_query)
    });

    entries.push_back({
        26,
        evidenceEntry(
            "ctest.cli.cipher",
            cli_cipher)
    });

    entries.push_back({
        27,
        evidenceEntry(
            "ctest.cli.source_execution",
            cli_source_execution)
    });

    entries.push_back({
        28,
        evidenceEntry(
            "qps_test.engineering",
            engineering_qps)
    });

    entries.push_back({
        29,
        evidenceEntry(
            "invariant.authored_authorities_present",
            authored_authorities)
    });

    entries.push_back({
        30,
        evidenceEntry(
            "transaction.git.clean_before",
            true)
    });

    entries.push_back({
        31,
        evidenceEntry(
            "transaction.git.changed_files_scoped",
            true)
    });

    entries.push_back({
        32,
        evidenceEntry(
            "transaction.git.diff_check_clean",
            true)
    });

    entries.push_back({
        33,
        evidenceEntry(
            "transaction.test.focused",
            true)
    });

    entries.push_back({
        34,
        evidenceEntry(
            "transaction.test.full",
            true)
    });

    entries.push_back({
        35,
        evidenceEntry(
            "transaction.qps_test.engineering",
            true)
    });

    entries.push_back({
        36,
        evidenceEntry(
            "transaction.git.staged_set_exact",
            true)
    });

    entries.push_back({
        37,
        evidenceEntry(
            "transaction.git.commit_identity_recorded",
            true)
    });

    entries.push_back({
        38,
        evidenceEntry(
            "transaction.git.clean_after",
            true)
    });

    return runtime::RuntimeValue::dictionary(
        std::move(entries));
}

runtime::RuntimeValue completePhaseAEvidence(
    int missing_entry = 0) {

    std::vector<runtime::RuntimeDictionaryEntry> entries;

    const std::vector<std::string> ids{
        "ctest.runtime_dictionary",
        "ctest.reference_document_plan",
        "authored.reference_document_parity",
        "invariant.structural_handle_owner_node_only",
        "ctest.semantic_walk",
        "authored.semantic_walk.parity",
        "production.semantic_walk.cutover",
        "absence.structural_handle.compatibility_metadata",
        "absence.native.reference_policy",
        "absence.native.semantic_walk",
        "ctest.grammar_regression",
        "ctest.parser_goldens",
        "ctest.corpus_ast_conformance",
        "ctest.active_corpus_conformance",
        "ctest.runtime_semantics",
        "ctest.function_semantics",
        "ctest.execution_definition",
        "ctest.structural_selection",
        "ctest.symbol_resolver",
        "ctest.path_resolver_index_surface",
        "ctest.host_action",
        "ctest.cli.test",
        "ctest.cli.probe",
        "ctest.cli.dir",
        "ctest.cli.query",
        "ctest.cli.cipher",
        "ctest.cli.source_execution",
        "qps_test.engineering",
        "invariant.authored_authorities_present",
        "transaction.git.clean_before",
        "transaction.git.changed_files_scoped",
        "transaction.git.diff_check_clean",
        "transaction.test.focused",
        "transaction.test.full",
        "transaction.qps_test.engineering",
        "transaction.git.staged_set_exact",
        "transaction.git.commit_identity_recorded",
        "transaction.git.clean_after"
    };

    int entry_id = 1;

    for (const auto& id : ids) {
        entries.push_back({
            entry_id,
            evidenceEntry(
                id,
                entry_id != missing_entry)
        });

        ++entry_id;
    }

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
                true,
                true,
                true,
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
        "policy.semantic_walk was not proven.");

    require(
        resultState(
            result,
            5) == 1.0,
        "kernel.native_policy_minimal was not proven.");

    require(
        resultState(
            result,
            6) == 1.0,
        "Required checklist did not prove.");

    require(
        resultState(
            result,
            7) == 1.0,
        "language.conformance was not proven.");

    require(
        resultState(
            result,
            8) == 1.0,
        "runtime.execution was not proven.");

    require(
        resultState(
            result,
            9) == 1.0,
        "implementation.required was not proven.");

    require(
        resultState(
            result,
            10) == 1.0,
        "reference.resolution was not proven.");

    require(
        resultState(
            result,
            11) == 1.0,
        "structural.runtime was not proven.");

    require(
        resultState(
            result,
            12) == 1.0,
        "host.boundary was not proven.");

    require(
        resultState(
            result,
            13) == 1.0,
        "cli.contract was not proven.");

    require(
        resultState(
            result,
            14) == 1.0,
        "engineering.surface was not proven.");

    require(
        resultState(
            result,
            15) == 1.0,
        "kernel.reduction was not proven.");

    require(
        resultState(
            result,
            16) == 1.0,
        "transaction.ready was not proven.");

    require(
        resultState(
            result,
            17) == 1.0,
        "transaction.committed was not proven.");

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
                true,
                true,
                true,
                true,
                true,
                true,
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
            6) == 0.0,
        "Required checklist incorrectly proved.");

    std::cout
        << "MISSING_REQUIRED_EVIDENCE: PASS\n";
}

void missingSemanticWalkCutoverDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            evidence(
                true,
                true,
                true,
                true,
                true,
                true,
                false,
                true,
                true,
                true));

    require(
        resultState(
            result,
            4) == 0.0,
        "Semantic walk incorrectly proved without production cutover.");

    require(
        resultState(
            result,
            5) == 1.0,
        "Unrelated native policy minimal proof changed.");

    require(
        resultState(
            result,
            6) == 0.0,
        "Required checklist incorrectly proved without semantic walk cutover.");

    std::cout
        << "MISSING_SEMANTIC_WALK_CUTOVER: PASS\n";
}

void missingNativePolicyAbsenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            evidence(
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                false));

    require(
        resultState(
            result,
            4) == 1.0,
        "Unrelated semantic walk proof changed.");

    require(
        resultState(
            result,
            5) == 0.0,
        "Native policy minimal incorrectly proved with native semantic walk present.");

    require(
        resultState(
            result,
            6) == 0.0,
        "Required checklist incorrectly proved with native policy residue.");

    std::cout
        << "MISSING_NATIVE_POLICY_ABSENCE: PASS\n";
}

void missingLanguageEvidenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            evidence(
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                false));

    require(
        resultState(
            result,
            6) == 1.0,
        "Legacy proof aggregate changed with language evidence.");

    require(
        resultState(
            result,
            7) == 0.0,
        "Language conformance incorrectly proved without parser goldens.");

    require(
        resultState(
            result,
            8) == 1.0,
        "Unrelated runtime execution proof changed.");

    require(
        resultState(
            result,
            9) == 0.0,
        "Implementation incorrectly proved without language conformance.");

    std::cout
        << "MISSING_LANGUAGE_EVIDENCE: PASS\n";
}


void missingRuntimeEvidenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            evidence(
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                true,
                false));

    require(
        resultState(
            result,
            6) == 1.0,
        "Legacy proof aggregate changed with runtime evidence.");

    require(
        resultState(
            result,
            7) == 1.0,
        "Unrelated language conformance proof changed.");

    require(
        resultState(
            result,
            8) == 0.0,
        "Runtime execution incorrectly proved without function semantics.");

    require(
        resultState(
            result,
            9) == 0.0,
        "Implementation incorrectly proved without runtime execution.");

    std::cout
        << "MISSING_RUNTIME_EVIDENCE: PASS\n";
}


void missingStructuralSelectionDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(18));

    require(
        resultState(result, 10) == 1.0,
        "Unrelated reference resolution proof changed.");

    require(
        resultState(result, 11) == 0.0,
        "Structural runtime incorrectly proved without structural selection.");

    require(
        resultState(result, 9) == 0.0,
        "Implementation incorrectly proved without structural runtime.");

    std::cout
        << "MISSING_STRUCTURAL_SELECTION: PASS\n";
}


void missingHostEvidenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(21));

    require(
        resultState(result, 12) == 0.0,
        "Host boundary incorrectly proved without host action evidence.");

    require(
        resultState(result, 13) == 1.0,
        "Unrelated CLI contract proof changed.");

    require(
        resultState(result, 9) == 0.0,
        "Implementation incorrectly proved without host boundary.");

    std::cout
        << "MISSING_HOST_EVIDENCE: PASS\n";
}


void missingCliEvidenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(25));

    require(
        resultState(result, 13) == 0.0,
        "CLI contract incorrectly proved without query evidence.");

    require(
        resultState(result, 12) == 1.0,
        "Unrelated host boundary proof changed.");

    require(
        resultState(result, 9) == 0.0,
        "Implementation incorrectly proved without CLI contract.");

    std::cout
        << "MISSING_CLI_EVIDENCE: PASS\n";
}


void missingEngineeringEvidenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(28));

    require(
        resultState(result, 14) == 0.0,
        "Engineering surface incorrectly proved without corpus evidence.");

    require(
        resultState(result, 15) == 1.0,
        "Unrelated kernel reduction proof changed.");

    require(
        resultState(result, 9) == 0.0,
        "Implementation incorrectly proved without Engineering surface.");

    std::cout
        << "MISSING_ENGINEERING_EVIDENCE: PASS\n";
}


void missingAuthoredAuthorityEvidenceDoesNotProve(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(29));

    require(
        resultState(result, 15) == 0.0,
        "Kernel reduction incorrectly proved without authored authorities.");

    require(
        resultState(result, 14) == 1.0,
        "Unrelated Engineering surface proof changed.");

    require(
        resultState(result, 9) == 0.0,
        "Implementation incorrectly proved without kernel reduction.");

    std::cout
        << "MISSING_AUTHORED_AUTHORITY_EVIDENCE: PASS\n";
}


void transactionCanBeReadyBeforeCommit(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(37));

    require(
        resultState(result, 9) == 1.0,
        "Implementation proof changed before transaction commit.");

    require(
        resultState(result, 16) == 1.0,
        "Transaction was not ready before commit identity existed.");

    require(
        resultState(result, 17) == 0.0,
        "Transaction incorrectly became committed without commit identity.");

    std::cout
        << "TRANSACTION_READY_BEFORE_COMMIT: PASS\n";
}


void transactionScopeFailureDoesNotUnproveImplementation(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(31));

    require(
        resultState(result, 9) == 1.0,
        "Transaction scope failure incorrectly unproved implementation.");

    require(
        resultState(result, 16) == 0.0,
        "Transaction incorrectly became ready with unscoped changes.");

    require(
        resultState(result, 17) == 0.0,
        "Unready transaction incorrectly became committed.");

    std::cout
        << "TRANSACTION_SCOPE_INDEPENDENT: PASS\n";
}


void transactionTestFailureDoesNotUnproveImplementation(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(34));

    require(
        resultState(result, 9) == 1.0,
        "Transaction test failure incorrectly unproved implementation.");

    require(
        resultState(result, 16) == 0.0,
        "Transaction incorrectly became ready without full tests.");

    require(
        resultState(result, 17) == 0.0,
        "Failed transaction incorrectly became committed.");

    std::cout
        << "TRANSACTION_TEST_INDEPENDENT: PASS\n";
}


void committedTransactionRequiresCleanAfter(
    const ast::ExecutionBlockNode& policy) {

    const auto result =
        executePolicy(
            policy,
            completePhaseAEvidence(38));

    require(
        resultState(result, 9) == 1.0,
        "Post-commit cleanliness incorrectly changed implementation proof.");

    require(
        resultState(result, 16) == 1.0,
        "Post-commit cleanliness incorrectly changed ready state.");

    require(
        resultState(result, 17) == 0.0,
        "Transaction incorrectly committed without clean-after evidence.");

    std::cout
        << "TRANSACTION_CLEAN_AFTER_REQUIRED: PASS\n";
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

    entries.push_back({
        5,
        evidenceEntry(
            "ctest.semantic_walk",
            true)
    });

    entries.push_back({
        6,
        evidenceEntry(
            "authored.semantic_walk.parity",
            true)
    });

    entries.push_back({
        7,
        evidenceEntry(
            "production.semantic_walk.cutover",
            true)
    });

    entries.push_back({
        8,
        evidenceEntry(
            "absence.structural_handle.compatibility_metadata",
            true)
    });

    entries.push_back({
        9,
        evidenceEntry(
            "absence.native.reference_policy",
            true)
    });

    entries.push_back({
        10,
        evidenceEntry(
            "absence.native.semantic_walk",
            true)
    });

    entries.push_back({
        11,
        evidenceEntry(
            "ctest.grammar_regression",
            true)
    });

    entries.push_back({
        12,
        evidenceEntry(
            "ctest.parser_goldens",
            true)
    });

    entries.push_back({
        13,
        evidenceEntry(
            "ctest.corpus_ast_conformance",
            true)
    });

    entries.push_back({
        14,
        evidenceEntry(
            "ctest.active_corpus_conformance",
            true)
    });

    entries.push_back({
        15,
        evidenceEntry(
            "ctest.runtime_semantics",
            true)
    });

    entries.push_back({
        16,
        evidenceEntry(
            "ctest.function_semantics",
            true)
    });

    entries.push_back({
        17,
        evidenceEntry(
            "ctest.execution_definition",
            true)
    });

    entries.push_back({
        18,
        evidenceEntry(
            "ctest.structural_selection",
            true)
    });

    entries.push_back({
        19,
        evidenceEntry(
            "ctest.symbol_resolver",
            true)
    });

    entries.push_back({
        20,
        evidenceEntry(
            "ctest.path_resolver_index_surface",
            true)
    });

    entries.push_back({
        21,
        evidenceEntry(
            "ctest.host_action",
            true)
    });

    entries.push_back({
        22,
        evidenceEntry(
            "ctest.cli.test",
            true)
    });

    entries.push_back({
        23,
        evidenceEntry(
            "ctest.cli.probe",
            true)
    });

    entries.push_back({
        24,
        evidenceEntry(
            "ctest.cli.dir",
            true)
    });

    entries.push_back({
        25,
        evidenceEntry(
            "ctest.cli.query",
            true)
    });

    entries.push_back({
        26,
        evidenceEntry(
            "ctest.cli.cipher",
            true)
    });

    entries.push_back({
        27,
        evidenceEntry(
            "ctest.cli.source_execution",
            true)
    });

    entries.push_back({
        28,
        evidenceEntry(
            "qps_test.engineering",
            true)
    });

    entries.push_back({
        29,
        evidenceEntry(
            "invariant.authored_authorities_present",
            true)
    });

    entries.push_back({
        30,
        evidenceEntry(
            "transaction.git.clean_before",
            true)
    });

    entries.push_back({
        31,
        evidenceEntry(
            "transaction.git.changed_files_scoped",
            true)
    });

    entries.push_back({
        32,
        evidenceEntry(
            "transaction.git.diff_check_clean",
            true)
    });

    entries.push_back({
        33,
        evidenceEntry(
            "transaction.test.focused",
            true)
    });

    entries.push_back({
        34,
        evidenceEntry(
            "transaction.test.full",
            true)
    });

    entries.push_back({
        35,
        evidenceEntry(
            "transaction.qps_test.engineering",
            true)
    });

    entries.push_back({
        36,
        evidenceEntry(
            "transaction.git.staged_set_exact",
            true)
    });

    entries.push_back({
        37,
        evidenceEntry(
            "transaction.git.commit_identity_recorded",
            true)
    });

    entries.push_back({
        38,
        evidenceEntry(
            "transaction.git.clean_after",
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
            6) == 0.0,
        "Wrong evidence identity incorrectly proved required checklist.");

    require(
        resultState(
            result,
            9) == 0.0,
        "Wrong evidence identity incorrectly proved implementation.required.");

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
        missingSemanticWalkCutoverDoesNotProve(*policy);
        missingNativePolicyAbsenceDoesNotProve(*policy);
        missingLanguageEvidenceDoesNotProve(*policy);
        missingRuntimeEvidenceDoesNotProve(*policy);
        missingStructuralSelectionDoesNotProve(*policy);
        missingHostEvidenceDoesNotProve(*policy);
        missingCliEvidenceDoesNotProve(*policy);
        missingEngineeringEvidenceDoesNotProve(*policy);
        missingAuthoredAuthorityEvidenceDoesNotProve(*policy);
        transactionCanBeReadyBeforeCommit(*policy);
        transactionScopeFailureDoesNotUnproveImplementation(*policy);
        transactionTestFailureDoesNotUnproveImplementation(*policy);
        committedTransactionRequiresCleanAfter(*policy);
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
