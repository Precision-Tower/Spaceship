#pragma once

#include "symbol_table.hpp"

#include <map>
#include <string>

namespace qps::runtime {

struct HostActionInvocation {
    std::string action_name;
    std::map<std::string, RuntimeValue> parameters;
};

class HostActionDispatcher {
public:
    void execute(const HostActionInvocation& invocation) const;
    void execute(const std::string& action_name) const;
};

} // namespace qps::runtime
