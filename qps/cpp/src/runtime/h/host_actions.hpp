#pragma once

#include <string>

namespace qps::runtime {

class HostActionDispatcher {
public:
    void execute(const std::string& action_name) const;
};

} // namespace qps::runtime
