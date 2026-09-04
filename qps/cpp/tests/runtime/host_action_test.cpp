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

void processPrimitiveExists() {
    qps::runtime::HostActionDispatcher host;
    host.execute("process");
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
    host.execute(invocation);
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
        processPrimitiveExists();
        std::cout
            << "PASS process host primitive exists\n";

        processAcceptsRuntimeStringParameters();
        std::cout
            << "PASS process accepts runtime string parameters\n";

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
