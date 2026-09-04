#ifndef QPS_RUNTIME_H_TEST_SUITE_HPP
#define QPS_RUNTIME_H_TEST_SUITE_HPP

#include <filesystem>
#include <cstddef>
#include <string>
#include <vector>

namespace qps {
namespace ast {
class ProgramNode;
}

namespace runtime {

class SymbolResolver;

enum class TestOutcome {
    PASSED,
    FAILED,
    ERROR
};

struct TestResult {
    std::string identity;
    TestOutcome outcome = TestOutcome::PASSED;
    std::string message;
    int line = 0;
    int column = 0;
};

struct TestSuiteSummary {
    std::vector<TestResult> results;

    std::size_t total() const;
    std::size_t passed() const;
    std::size_t failed() const;
    std::size_t errors() const;
    bool successful() const;
};

class TestSuiteRunner {
public:
    TestSuiteSummary run(
        const ast::ProgramNode& program,
        SymbolResolver* symbol_resolver = nullptr,
        const std::filesystem::path& current_document = {}) const;
};

const char* testOutcomeName(
    TestOutcome outcome);

char testOutcomeGlyph(
    TestOutcome outcome);

} // namespace runtime
} // namespace qps

#endif // QPS_RUNTIME_H_TEST_SUITE_HPP
