#include "../h/test_suite.hpp"

#include "../h/interpreter.hpp"
#include "../h/symbol_table.hpp"
#include "../../ast/ast_node.hpp"

#include <stdexcept>
#include <unordered_set>
#include <utility>

namespace qps {
namespace runtime {

namespace {

struct DiscoveredTest {
    std::string identity;
    const ast::TestDeclarationNode* declaration = nullptr;
    int line = 0;
    int column = 0;
};

std::string joinIdentity(
    const std::vector<std::string>& segments) {

    std::string result;

    for (const auto& segment : segments) {
        if (!result.empty()) {
            result += ".";
        }

        result += segment;
    }

    return result;
}

std::size_t testDeclarationCount(
    const ast::TermDeclarationNode& term) {

    std::size_t count = 0;

    for (const auto& child : term.content_) {
        if (dynamic_cast<const ast::TestDeclarationNode*>(child.get())) {
            ++count;
        }
    }

    return count;
}

void discoverInNode(
    const ast::AstNode& node,
    std::vector<std::string>& path,
    std::vector<DiscoveredTest>& tests) {

    if (auto* key =
            dynamic_cast<const ast::KeyDeclarationNode*>(&node)) {

        path.push_back(key->identifier_);

        for (const auto& child : key->content_) {
            discoverInNode(*child, path, tests);
        }

        path.pop_back();
        return;
    }

    if (auto* term =
            dynamic_cast<const ast::TermDeclarationNode*>(&node)) {

        path.push_back(term->identifier_);
        const std::size_t declarations = testDeclarationCount(*term);

        if (declarations > 0) {
            if (declarations != 1 || term->content_.size() != 1) {
                throw std::runtime_error(
                    "QPS test Term '" +
                    joinIdentity(path) +
                    "' must contain exactly one -test declaration.");
            }

            auto* declaration =
                dynamic_cast<const ast::TestDeclarationNode*>(
                    term->content_.front().get());

            DiscoveredTest test;
            test.identity = joinIdentity(path);
            test.declaration = declaration;
            test.line = term->getLine();
            test.column = term->getColumn();

            tests.push_back(std::move(test));
            path.pop_back();
            return;
        }

        for (const auto& child : term->content_) {
            discoverInNode(*child, path, tests);
        }

        path.pop_back();
        return;
    }

    if (auto* container =
            dynamic_cast<const ast::ContainerNode*>(&node)) {

        for (const auto& child : container->elements) {
            discoverInNode(*child, path, tests);
        }
    }
}

std::vector<DiscoveredTest> discoverTests(
    const ast::ProgramNode& program) {

    std::vector<DiscoveredTest> tests;
    std::vector<std::string> path;

    for (const auto& statement : program.statements) {
        discoverInNode(*statement, path, tests);
    }

    std::unordered_set<std::string> identities;

    for (const auto& test : tests) {
        if (!identities.insert(test.identity).second) {
            throw std::runtime_error(
                "Duplicate QPS test identity '" +
                test.identity +
                "'.");
        }
    }

    return tests;
}

void registerTopLevelFunctions(
    const ast::ProgramNode& program,
    Interpreter& interpreter) {

    for (const auto& statement : program.statements) {
        if (auto* function =
                dynamic_cast<const ast::FunctionDeclarationNode*>(
                    statement.get())) {

            interpreter.registerFunction(*function);
        }
    }
}

TestResult runOne(
    const ast::ProgramNode& program,
    const DiscoveredTest& test) {

    TestResult result;
    result.identity = test.identity;
    result.line = test.line;
    result.column = test.column;

    if (test.declaration == nullptr ||
        test.declaration->body_ == nullptr) {

        result.outcome = TestOutcome::ERROR;
        result.message = "Test declaration has no execution body.";
        return result;
    }

    try {
        ExecutionScope scope;
        Interpreter interpreter(scope);

        registerTopLevelFunctions(program, interpreter);
        interpreter.execute(*test.declaration->body_);

        result.outcome = TestOutcome::PASSED;
    } catch (const AssertionFailure& e) {
        result.outcome = TestOutcome::FAILED;
        result.message = e.what();
        if (e.line() > 0) {
            result.line = e.line();
            result.column = e.column();
        }
    } catch (const RuntimeDiagnostic& e) {
        result.outcome = TestOutcome::ERROR;
        result.message = e.what();
        if (e.line() > 0) {
            result.line = e.line();
            result.column = e.column();
        }
    } catch (const std::exception& e) {
        result.outcome = TestOutcome::ERROR;
        result.message = e.what();
    }

    return result;
}

std::size_t countOutcome(
    const std::vector<TestResult>& results,
    TestOutcome outcome) {

    std::size_t count = 0;

    for (const auto& result : results) {
        if (result.outcome == outcome) {
            ++count;
        }
    }

    return count;
}

} // namespace

std::size_t TestSuiteSummary::total() const {
    return results.size();
}

std::size_t TestSuiteSummary::passed() const {
    return countOutcome(results, TestOutcome::PASSED);
}

std::size_t TestSuiteSummary::failed() const {
    return countOutcome(results, TestOutcome::FAILED);
}

std::size_t TestSuiteSummary::errors() const {
    return countOutcome(results, TestOutcome::ERROR);
}

bool TestSuiteSummary::successful() const {
    return !results.empty() && failed() == 0 && errors() == 0;
}

TestSuiteSummary TestSuiteRunner::run(
    const ast::ProgramNode& program) const {

    TestSuiteSummary summary;

    for (const auto& test : discoverTests(program)) {
        summary.results.push_back(
            runOne(program, test));
    }

    return summary;
}

const char* testOutcomeName(
    TestOutcome outcome) {

    switch (outcome) {
        case TestOutcome::PASSED:
            return "PASS";
        case TestOutcome::FAILED:
            return "FAIL";
        case TestOutcome::ERROR:
            return "ERROR";
    }

    return "UNKNOWN";
}

char testOutcomeGlyph(
    TestOutcome outcome) {

    switch (outcome) {
        case TestOutcome::PASSED:
            return '.';
        case TestOutcome::FAILED:
            return 'F';
        case TestOutcome::ERROR:
            return 'E';
    }

    return '?';
}

} // namespace runtime
} // namespace qps
