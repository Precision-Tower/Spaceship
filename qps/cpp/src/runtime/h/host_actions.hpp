#pragma once

#include "symbol_table.hpp"

#include <map>
#include <optional>
#include <string>
#include <vector>

#include <cstddef>
#include <filesystem>
#include <functional>

namespace qps::runtime {

struct FileReplacement {
    std::filesystem::path path;
    std::string text;
};

using PublishFilesCheckpoint =
    std::function<void(std::size_t published_count)>;

/*
 * Generic transactional file publication.
 *
 * Every replacement is staged before authority is touched. Existing
 * destinations are backed up, staged candidates are published, and any
 * exception restores the original authority set.
 *
 * checkpoint is a native observation hook for deterministic transaction
 * tests. The authored publish_files action does not expose fault injection.
 */
void publishFileReplacements(
    const std::vector<FileReplacement>& replacements,
    const PublishFilesCheckpoint& checkpoint = {});


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

struct HostActionResult {
    int exit_code = 0;
    std::string stdout_text;
    std::string stderr_text;
    std::optional<RuntimeValue> value;
};

class HostActionDispatcher {
public:
    HostActionResult execute(
        const HostActionInvocation& invocation) const;

    HostActionResult execute(
        const std::string& action_name) const;
};

} // namespace qps::runtime
