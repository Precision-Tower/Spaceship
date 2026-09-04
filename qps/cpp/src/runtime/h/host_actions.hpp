#pragma once

#include "symbol_table.hpp"

#include <map>
#include <optional>
#include <string>
#include <vector>

namespace qps::runtime {

struct HostActionInvocation {
    std::string action_name;
    std::map<std::string, RuntimeValue> parameters;
};

struct ProcessRequest {
    std::string program;
    std::vector<std::string> arguments;
    std::optional<std::string> cwd;
};

struct ProcessResult {
    int exit_code = -1;
    std::string stdout_text;
    std::string stderr_text;
};

class HostActionDispatcher {
public:
    ProcessResult execute(
        const HostActionInvocation& invocation) const;

    ProcessResult execute(
        const std::string& action_name) const;
};

} // namespace qps::runtime
