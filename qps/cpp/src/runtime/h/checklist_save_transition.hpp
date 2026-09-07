#pragma once

#include <string>
#include <vector>

namespace qps::runtime {

std::string applyChecklistSaveTransition(
    const std::string& source,
    const std::string& history_identity,
    const std::string& history_timestamp,
    const std::vector<std::string>& task_identities);

} // namespace qps::runtime
