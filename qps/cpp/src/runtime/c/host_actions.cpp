#include "host_actions.hpp"

#include <stdexcept>

namespace qps::runtime {

void HostActionDispatcher::execute(
    const std::string& action_name) const {

    if (action_name == "process") {
        // Primitive exists. Process invocation semantics are
        // intentionally not implemented yet.
        return;
    }

    throw std::runtime_error(
        "Unknown host execution action '-" +
        action_name + "'.");
}

} // namespace qps::runtime
