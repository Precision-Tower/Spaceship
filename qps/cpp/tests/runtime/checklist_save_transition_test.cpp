#include "runtime/h/checklist_save_transition.hpp"

#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>


namespace {

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}


void expectFailure(
    const std::function<void()>& action,
    const std::string& expected) {

    try {
        action();
    }
    catch (const std::exception& e) {
        require(
            std::string(e.what()).find(expected) !=
                std::string::npos,
            std::string("Unexpected error: ") +
                e.what());

        return;
    }

    throw std::runtime_error(
        "Expected failure containing: " +
        expected);
}


const char* source = R"qps(
current_work: (

history_candidate: (
ready- true;
state- "ready";
history_identity- "";
history_timestamp- "";

identity- "test.accepted";
summary- "Summary";
meaning- "Meaning";

scope: (
path_1- "qps/qps";
);

proof: (
test- "PASS";
);

relevant: (
path_1- "qps/qps/checklist.qps";
);

remaining: (
item_1- "Future";
);

tasks: (
task_1- "task.alpha";
task_2- "task.beta";
);
);

tasks: (

task_1: (
identity- "task.alpha";
summary- "Alpha";
state- "complete";
);

task_2: (
identity- "task.beta";
summary- "Beta";
state- "complete";
);

task_3: (
identity- "task.gamma";
summary- "Gamma";
state- "waiting";
);

);

);
)qps";


void transitionSucceeds() {

    const std::string result =
        qps::runtime::applyChecklistSaveTransition(
            source,
            "test.accepted",
            "2026-09-06T09:00:00Z",
            {
                "task.alpha",
                "task.beta"
            });

    require(
        result.find("ready- false;") !=
            std::string::npos,
        "Candidate ready state was not cleared.");

    require(
        result.find("state- \"saved\";") !=
            std::string::npos,
        "Saved state missing.");

    require(
        result.find(
            "history_identity- \"test.accepted\";") !=
            std::string::npos,
        "History identity not recorded.");

    require(
        result.find(
            "history_timestamp- \"2026-09-06T09:00:00Z\";") !=
            std::string::npos,
        "History timestamp not recorded.");

    require(
        result.find(
            "identity- \"task.gamma\";\n"
            "summary- \"Gamma\";\n"
            "state- \"waiting\";") !=
            std::string::npos,
        "Unrelated task was modified.");
}


void candidateIdentityMayEqualTaskIdentity() {

    std::string colliding(source);

    const std::string before =
        "identity- \"test.accepted\";";

    const std::string after =
        "identity- \"task.alpha\";";

    const std::size_t pos =
        colliding.find(before);

    require(
        pos != std::string::npos,
        "Candidate identity fixture missing.");

    colliding.replace(
        pos,
        before.size(),
        after);

    const std::string result =
        qps::runtime::applyChecklistSaveTransition(
            colliding,
            "task.alpha",
            "2026-09-06T09:00:00Z",
            {
                "task.alpha"
            });

    require(
        result.find(
            "identity- \"task.alpha\";\n"
            "summary- \"Alpha\";\n"
            "state- \"saved\";") !=
                std::string::npos,
        "Task sharing candidate identity was not saved.");
}



void missingTaskFails() {

    expectFailure(
        [] {
            (void)
                qps::runtime::
                    applyChecklistSaveTransition(
                        source,
                        "test.accepted",
                        "2026-09-06T09:00:00Z",
                        {
                            "task.missing"
                        });
        },
        "not found");
}


void incompleteTaskFails() {

    expectFailure(
        [] {
            (void)
                qps::runtime::
                    applyChecklistSaveTransition(
                        source,
                        "test.accepted",
                        "2026-09-06T09:00:00Z",
                        {
                            "task.gamma"
                        });
        },
        "not complete");
}


void duplicateTaskFails() {

    expectFailure(
        [] {
            (void)
                qps::runtime::
                    applyChecklistSaveTransition(
                        source,
                        "test.accepted",
                        "2026-09-06T09:00:00Z",
                        {
                            "task.alpha",
                            "task.alpha"
                        });
        },
        "Duplicate Save task identity");
}


void alreadySavedFails() {

    std::string saved(source);

    const std::size_t pos =
        saved.find("ready- true;");

    require(
        pos != std::string::npos,
        "Fixture ready state missing.");

    saved.replace(
        pos,
        std::string("ready- true;").size(),
        "ready- false;");

    expectFailure(
        [&] {
            (void)
                qps::runtime::
                    applyChecklistSaveTransition(
                        saved,
                        "test.accepted",
                        "2026-09-06T09:00:00Z",
                        {
                            "task.alpha"
                        });
        },
        "not ready");
}

} // namespace


int main() {

    const std::vector<
        std::pair<
            const char*,
            std::function<void()>>> tests = {

        {
            "transition succeeds",
            transitionSucceeds
        },
        {
            "candidate identity may equal task identity",
            candidateIdentityMayEqualTaskIdentity
        },
        {
            "missing task fails",
            missingTaskFails
        },
        {
            "incomplete task fails",
            incompleteTaskFails
        },
        {
            "duplicate task fails",
            duplicateTaskFails
        },
        {
            "already saved fails",
            alreadySavedFails
        },
    };

    int failures = 0;

    for (const auto& test : tests) {
        try {
            test.second();
            std::cout
                << "PASS "
                << test.first
                << "\n";
        }
        catch (const std::exception& e) {
            ++failures;

            std::cerr
                << "FAIL "
                << test.first
                << ": "
                << e.what()
                << "\n";
        }
    }

    return failures == 0 ? 0 : 1;
}
