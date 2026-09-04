#include "runtime/h/host_actions.hpp"

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

void processRequiresProgram() {
    qps::runtime::HostActionDispatcher host;

    try {
        (void)host.execute("process");
    }
    catch (const std::runtime_error& e) {
        require(
            std::string(e.what()).find(
                "requires parameter 'program'") !=
                std::string::npos,
            "Unexpected missing-program failure.");

        return;
    }

    throw std::runtime_error(
        "Process without program unexpectedly succeeded.");
}

void processAcceptsRuntimeStringParameters() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "process";

    invocation.parameters.emplace(
        "program",
        qps::runtime::RuntimeValue::string("printf"));

    invocation.parameters.emplace(
        "arg_0",
        qps::runtime::RuntimeValue::string(
            "QPS_PROCESS_OK"));

    require(
        invocation.parameters.at("program")
                .asString("program") ==
            "printf",
        "Process program runtime value was not preserved.");

    require(
        invocation.parameters.at("arg_0")
                .asString("arg_0") ==
            "QPS_PROCESS_OK",
        "Process argument runtime value was not preserved.");

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "printf process should exit successfully.");

    require(
        result.stdout_text ==
            "QPS_PROCESS_OK",
        "printf stdout mismatch.");

    require(
        result.stderr_text.empty(),
        "printf stderr should be empty.");
}

void processDrainsStdoutAndStderrTogether() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "process";

    invocation.parameters.emplace(
        "program",
        qps::runtime::RuntimeValue::string(
            "python3"));

    invocation.parameters.emplace(
        "arg_0",
        qps::runtime::RuntimeValue::string(
            "-c"));

    invocation.parameters.emplace(
        "arg_1",
        qps::runtime::RuntimeValue::string(
            "import sys;"
            "sys.stderr.write('E' * 262144);"
            "sys.stderr.flush();"
            "sys.stdout.write('O' * 262144);"
            "sys.stdout.flush()"));

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "dual-pipe process should exit successfully.");

    require(
        result.stdout_text.size() == 262144,
        "dual-pipe stdout size mismatch.");

    require(
        result.stderr_text.size() == 262144,
        "dual-pipe stderr size mismatch.");

    require(
        result.stdout_text.front() == 'O' &&
        result.stdout_text.back() == 'O',
        "dual-pipe stdout content mismatch.");

    require(
        result.stderr_text.front() == 'E' &&
        result.stderr_text.back() == 'E',
        "dual-pipe stderr content mismatch.");
}

void writeAcceptsRuntimeStringValue() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "write";

    invocation.parameters.emplace(
        "stream",
        qps::runtime::RuntimeValue::string(
            "stdout"));

    invocation.parameters.emplace(
        "value",
        qps::runtime::RuntimeValue::string(
            ""));

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "write primitive should succeed.");

    require(
        result.stdout_text.empty() &&
        result.stderr_text.empty(),
        "write primitive should not manufacture captured output.");
}

void invalidWriteStreamFails() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "write";

    invocation.parameters.emplace(
        "stream",
        qps::runtime::RuntimeValue::string(
            "sideways"));

    invocation.parameters.emplace(
        "value",
        qps::runtime::RuntimeValue::string(
            "ignored"));

    qps::runtime::HostActionDispatcher host;

    try {
        (void)host.execute(invocation);
    }
    catch (const std::runtime_error& e) {
        require(
            std::string(e.what()).find(
                "stdout") != std::string::npos,
            "Unexpected invalid-stream failure.");
        return;
    }

    throw std::runtime_error(
        "Invalid write stream unexpectedly succeeded.");
}

void unknownPrimitiveFails() {
    qps::runtime::HostActionDispatcher host;

    try {
        host.execute("not_a_host_primitive");
    } catch (const std::runtime_error& e) {
        const std::string message = e.what();

        require(
            message.find(
                "Unknown host execution action") !=
                std::string::npos,
            "Unexpected failure: " + message);

        return;
    }

    throw std::runtime_error(
        "Unknown host primitive unexpectedly succeeded.");
}

} // namespace

int main() {
    try {
        processRequiresProgram();
        std::cout
            << "PASS process requires program\n";

        processAcceptsRuntimeStringParameters();
        std::cout
            << "PASS process accepts runtime string parameters\n";

        processDrainsStdoutAndStderrTogether();
        std::cout
            << "PASS process drains stdout and stderr together\n";

        writeAcceptsRuntimeStringValue();
        std::cout
            << "PASS write accepts runtime string value\n";

        invalidWriteStreamFails();
        std::cout
            << "PASS invalid write stream fails\n";

        unknownPrimitiveFails();
        std::cout
            << "PASS unknown host primitive fails\n";

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr
            << "FAIL "
            << e.what()
            << "\n";

        return 1;
    }
}
