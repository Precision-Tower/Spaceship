#include "host_actions.hpp"

#include <stdexcept>

namespace qps::runtime {

void HostActionDispatcher::execute(
    const HostActionInvocation& invocation) const {

    if (invocation.action_name == "process") {
        // Primitive exists. Process invocation semantics are
        // intentionally not implemented yet.
        //
        // Parameters have crossed the AST/runtime boundary and are
        // represented only as RuntimeValue objects here.
        return;
    }

    throw std::runtime_error(
        "Unknown host execution action '-" +
        invocation.action_name + "'.");
}

void HostActionDispatcher::execute(
    const std::string& action_name) const {

    execute(HostActionInvocation{
        action_name,
        {}
    });
}

} // namespace qps::runtime
