#include "../h/checklist_save_transition.hpp"

#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace qps::runtime {
namespace {

std::size_t requireFind(
    const std::string& source,
    const std::string& needle,
    std::size_t start,
    const std::string& error) {

    const std::size_t found =
        source.find(needle, start);

    if (found == std::string::npos) {
        throw std::runtime_error(error);
    }

    return found;
}


void replaceOnceInRange(
    std::string& source,
    const std::string& before,
    const std::string& after,
    std::size_t begin,
    std::size_t end,
    const std::string& error) {

    const std::size_t found =
        source.find(before, begin);

    if (
        found == std::string::npos ||
        found >= end) {

        throw std::runtime_error(error);
    }

    source.replace(
        found,
        before.size(),
        after);
}


std::pair<std::size_t, std::size_t>
historyCandidateRange(
    const std::string& source) {

    const std::size_t begin =
        requireFind(
            source,
            "history_candidate: (",
            0,
            "Checklist has no history_candidate.");

    const std::size_t tasks =
        requireFind(
            source,
            "\ntasks: (",
            begin,
            "Checklist has no current_work tasks surface after history_candidate.");

    const std::size_t end =
        source.rfind("\n);\n", tasks);

    if (
        end == std::string::npos ||
        end <= begin) {

        throw std::runtime_error(
            "Unable to determine history_candidate boundary.");
    }

    // The candidate closes immediately before current_work.tasks.
    const std::size_t candidate_end =
        source.rfind("\n);", tasks);

    if (
        candidate_end == std::string::npos ||
        candidate_end <= begin) {

        throw std::runtime_error(
            "Unable to determine history_candidate closing boundary.");
    }

    return {
        begin,
        candidate_end + 3
    };
}


std::pair<std::size_t, std::size_t>
taskRange(
    const std::string& source,
    const std::string& identity) {

    const std::string identity_line =
        "identity- \"" +
        identity +
        "\";";

    const auto candidate =
        historyCandidateRange(source);

    const std::size_t tasks_begin =
        requireFind(
            source,
            "\ntasks: (",
            candidate.second,
            "Checklist has no current_work tasks surface.");

    const std::size_t identity_pos =
        requireFind(
            source,
            identity_line,
            tasks_begin,
            "Referenced Checklist task identity not found: " +
            identity);

    const std::size_t task_begin =
        source.rfind(
            "task_",
            identity_pos);

    if (
        task_begin == std::string::npos ||
        task_begin < tasks_begin) {

        throw std::runtime_error(
            "Unable to locate task structure for identity: " +
            identity);
    }

    const std::size_t task_end =
        requireFind(
            source,
            "\n);",
            identity_pos,
            "Unable to locate task closing boundary for identity: " +
            identity);

    return {
        task_begin,
        task_end + 3
    };
}

} // namespace


std::string applyChecklistSaveTransition(
    const std::string& source,
    const std::string& history_identity,
    const std::string& history_timestamp,
    const std::vector<std::string>& task_identities) {

    if (history_identity.empty()) {
        throw std::runtime_error(
            "Save transition history identity is empty.");
    }

    if (history_timestamp.empty()) {
        throw std::runtime_error(
            "Save transition history timestamp is empty.");
    }

    if (task_identities.empty()) {
        throw std::runtime_error(
            "Save transition requires at least one task.");
    }

    std::set<std::string> unique;

    for (const auto& identity : task_identities) {
        if (!unique.insert(identity).second) {
            throw std::runtime_error(
                "Duplicate Save task identity: " +
                identity);
        }
    }

    std::string result = source;

    auto candidate =
        historyCandidateRange(result);

    replaceOnceInRange(
        result,
        "ready- true;",
        "ready- false;",
        candidate.first,
        candidate.second,
        "History candidate is not ready.");

    // Recalculate boundary after replacement.
    candidate =
        historyCandidateRange(result);

    replaceOnceInRange(
        result,
        "state- \"ready\";",
        "state- \"saved\";",
        candidate.first,
        candidate.second,
        "History candidate state is not ready.");

    candidate =
        historyCandidateRange(result);

    replaceOnceInRange(
        result,
        "history_identity- \"\";",
        "history_identity- \"" +
            history_identity +
            "\";",
        candidate.first,
        candidate.second,
        "History candidate history_identity is not empty.");

    candidate =
        historyCandidateRange(result);

    replaceOnceInRange(
        result,
        "history_timestamp- \"\";",
        "history_timestamp- \"" +
            history_timestamp +
            "\";",
        candidate.first,
        candidate.second,
        "History candidate history_timestamp is not empty.");

    for (const auto& identity : task_identities) {
        const auto task =
            taskRange(
                result,
                identity);

        replaceOnceInRange(
            result,
            "state- \"complete\";",
            "state- \"saved\";",
            task.first,
            task.second,
            "Referenced task is not complete: " +
            identity);
    }

    return result;
}

} // namespace qps::runtime
