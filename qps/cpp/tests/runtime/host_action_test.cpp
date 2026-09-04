#include "runtime/h/host_actions.hpp"
#include "ast/structural_selection.hpp"
#include "parser/h/_index.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

void expectFailureContaining(
    const std::function<void()>& action,
    const std::string& expected,
    const std::string& context) {

    try {
        action();
    }
    catch (const std::runtime_error& e) {
        const std::string message = e.what();

        require(
            message.find(expected) !=
                std::string::npos,
            context +
            " produced unexpected failure: " +
            message);

        return;
    }

    throw std::runtime_error(
        context +
        " unexpectedly succeeded.");
}

qps::runtime::RuntimeValue makeDictionary(
    std::vector<qps::runtime::RuntimeDictionaryEntry> entries) {

    return qps::runtime::RuntimeValue::dictionary(
        std::move(entries));
}

qps::runtime::HostActionResult runDictionarySize(
    qps::runtime::RuntimeValue value) {

    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "dictionary_size";

    invocation.parameters.emplace(
        "value",
        std::move(value));

    qps::runtime::HostActionDispatcher host;
    return host.execute(invocation);
}

qps::runtime::HostActionResult runDictionaryAt(
    qps::runtime::RuntimeValue value,
    double index) {

    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "dictionary_at";

    invocation.parameters.emplace(
        "value",
        std::move(value));

    invocation.parameters.emplace(
        "index",
        qps::runtime::RuntimeValue::numeric(index));

    qps::runtime::HostActionDispatcher host;
    return host.execute(invocation);
}

std::shared_ptr<qps::ast::ProgramNode> parseStructureFixture() {
    const std::string source = R"qps(
root.
child: (
value- "opaque";
);
)qps";

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);

    auto parsed =
        parser.parseProgram();

    return std::shared_ptr<qps::ast::ProgramNode>(
        std::move(parsed));
}

qps::runtime::RuntimeValue makeStructureFixture() {
    auto owner =
        parseStructureFixture();

    qps::ast::AstNode* root =
        qps::ast::selectDocumentStructure(
            *owner,
            "root");

    require(
        root != nullptr,
        "Structure fixture root was not found.");

    qps::runtime::StructuralHandle handle;
    handle.document_owner = owner;
    handle.target_node = root;

    return qps::runtime::RuntimeValue::structure(
        std::move(handle));
}

qps::runtime::HostActionResult runStructureAction(
    const std::string& action,
    qps::runtime::RuntimeValue structure,
    const std::string& name) {

    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = action;

    invocation.parameters.emplace(
        "structure",
        std::move(structure));

    invocation.parameters.emplace(
        "name",
        qps::runtime::RuntimeValue::string(name));

    qps::runtime::HostActionDispatcher host;
    return host.execute(invocation);
}

void structureChildReturnsOpaqueStructure() {
    const auto result =
        runStructureAction(
            "structure_child",
            makeStructureFixture(),
            "child");

    require(
        result.value.has_value(),
        "structure_child returned no value.");

    const auto& handle =
        result.value->asStructure(
            "structure_child result");

    require(
        handle.document_owner != nullptr,
        "structure_child lost document ownership.");

    require(
        handle.target_node != nullptr,
        "structure_child returned no target node.");

    require(
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            handle.target_node) != nullptr,
        "structure_child did not select the child Term.");
}

void structureItemReturnsOpaqueStructure() {
    const auto child =
        runStructureAction(
            "structure_child",
            makeStructureFixture(),
            "child");

    require(
        child.value.has_value(),
        "structure_child returned no fixture child.");

    const auto item =
        runStructureAction(
            "structure_item",
            *child.value,
            "value");

    require(
        item.value.has_value(),
        "structure_item returned no value.");

    const auto& handle =
        item.value->asStructure(
            "structure_item result");

    require(
        handle.document_owner != nullptr,
        "structure_item lost document ownership.");

    require(
        handle.target_node != nullptr,
        "structure_item returned no target node.");

    require(
        dynamic_cast<qps::ast::ItemDeclarationNode*>(
            handle.target_node) != nullptr,
        "structure_item did not select the Item declaration.");
}

void structureActionsRejectMissingSelection() {
    expectFailureContaining(
        []() {
            (void)runStructureAction(
                "structure_child",
                makeStructureFixture(),
                "missing");
        },
        "Structural child 'missing' not found",
        "structure_child missing selection");

    const auto child =
        runStructureAction(
            "structure_child",
            makeStructureFixture(),
            "child");

    require(
        child.value.has_value(),
        "structure_child returned no fixture child.");

    expectFailureContaining(
        [&child]() {
            (void)runStructureAction(
                "structure_item",
                *child.value,
                "missing");
        },
        "Structural Item 'missing' not found",
        "structure_item missing selection");
}

void structureActionsRejectWrongTypes() {
    expectFailureContaining(
        []() {
            (void)runStructureAction(
                "structure_child",
                qps::runtime::RuntimeValue::string(
                    "not-structure"),
                "child");
        },
        "expected structure value",
        "structure_child non-structure input");

    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "structure_child";

    invocation.parameters.emplace(
        "structure",
        makeStructureFixture());

    invocation.parameters.emplace(
        "name",
        qps::runtime::RuntimeValue::numeric(1.0));

    qps::runtime::HostActionDispatcher host;

    expectFailureContaining(
        [&host, &invocation]() {
            (void)host.execute(invocation);
        },
        "expected string value",
        "structure_child non-string name");
}

void structureActionsRejectIncompleteHandles() {
    qps::runtime::StructuralHandle incomplete;

    expectFailureContaining(
        [&incomplete]() {
            (void)runStructureAction(
                "structure_child",
                qps::runtime::RuntimeValue::structure(
                    incomplete),
                "child");
        },
        "complete structural handle",
        "structure_child incomplete handle");
}

void structureActionsRejectUnknownParameters() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "structure_child";

    invocation.parameters.emplace(
        "structure",
        makeStructureFixture());

    invocation.parameters.emplace(
        "name",
        qps::runtime::RuntimeValue::string(
            "child"));

    invocation.parameters.emplace(
        "extra",
        qps::runtime::RuntimeValue::numeric(
            1.0));

    qps::runtime::HostActionDispatcher host;

    expectFailureContaining(
        [&host, &invocation]() {
            (void)host.execute(invocation);
        },
        "Unknown structure_child parameter 'extra'",
        "structure_child unknown parameter");
}

void processRequiresProgram() {
    qps::runtime::HostActionDispatcher host;

    try {
        (void)host.execute("process");
    }
    catch (const std::runtime_error& e) {
        require(
            std::string(e.what()).find(
                "requires parameter 'program'") !=
                std::string::npos,
            "Unexpected missing-program failure.");

        return;
    }

    throw std::runtime_error(
        "Process without program unexpectedly succeeded.");
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

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "printf process should exit successfully.");

    require(
        result.stdout_text ==
            "QPS_PROCESS_OK",
        "printf stdout mismatch.");

    require(
        result.stderr_text.empty(),
        "printf stderr should be empty.");
}

void processDrainsStdoutAndStderrTogether() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "process";

    invocation.parameters.emplace(
        "program",
        qps::runtime::RuntimeValue::string(
            "python3"));

    invocation.parameters.emplace(
        "arg_0",
        qps::runtime::RuntimeValue::string(
            "-c"));

    invocation.parameters.emplace(
        "arg_1",
        qps::runtime::RuntimeValue::string(
            "import sys;"
            "sys.stderr.write('E' * 262144);"
            "sys.stderr.flush();"
            "sys.stdout.write('O' * 262144);"
            "sys.stdout.flush()"));

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "dual-pipe process should exit successfully.");

    require(
        result.stdout_text.size() == 262144,
        "dual-pipe stdout size mismatch.");

    require(
        result.stderr_text.size() == 262144,
        "dual-pipe stderr size mismatch.");

    require(
        result.stdout_text.front() == 'O' &&
        result.stdout_text.back() == 'O',
        "dual-pipe stdout content mismatch.");

    require(
        result.stderr_text.front() == 'E' &&
        result.stderr_text.back() == 'E',
        "dual-pipe stderr content mismatch.");
}

void writeAcceptsRuntimeStringValue() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "write";

    invocation.parameters.emplace(
        "stream",
        qps::runtime::RuntimeValue::string(
            "stdout"));

    invocation.parameters.emplace(
        "value",
        qps::runtime::RuntimeValue::string(
            ""));

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "write primitive should succeed.");

    require(
        result.stdout_text.empty() &&
        result.stderr_text.empty(),
        "write primitive should not manufacture captured output.");
}

void invalidWriteStreamFails() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "write";

    invocation.parameters.emplace(
        "stream",
        qps::runtime::RuntimeValue::string(
            "sideways"));

    invocation.parameters.emplace(
        "value",
        qps::runtime::RuntimeValue::string(
            "ignored"));

    qps::runtime::HostActionDispatcher host;

    try {
        (void)host.execute(invocation);
    }
    catch (const std::runtime_error& e) {
        require(
            std::string(e.what()).find(
                "stdout") != std::string::npos,
            "Unexpected invalid-stream failure.");
        return;
    }

    throw std::runtime_error(
        "Invalid write stream unexpectedly succeeded.");
}

void qpsCheckAcceptsValidSource() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "qps_check";

    invocation.parameters.emplace(
        "source",
        qps::runtime::RuntimeValue::string(
            "Probe.\nvalue- 1;\n"));

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.exit_code == 0,
        "qps_check should accept valid QPS.");
}

void qpsCheckRejectsInvalidSource() {
    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "qps_check";

    invocation.parameters.emplace(
        "source",
        qps::runtime::RuntimeValue::string(
            "Probe.\nvalue- @@@;\n"));

    qps::runtime::HostActionDispatcher host;

    try {
        (void)host.execute(invocation);
    }
    catch (const std::exception&) {
        return;
    }

    throw std::runtime_error(
        "qps_check unexpectedly accepted invalid QPS.");
}

void pathKindReturnsFilesystemFact() {
    namespace fs = std::filesystem;

    const fs::path root =
        fs::temp_directory_path() /
        "qps_host_path_kind_test";

    fs::remove_all(root);
    fs::create_directories(root);

    const fs::path file =
        root / "probe.txt";

    {
        std::ofstream out(file);
        out << "probe";
    }

    qps::runtime::HostActionDispatcher host;

    const auto run =
        [&](const fs::path& path) {
            qps::runtime::HostActionInvocation invocation;
            invocation.action_name = "path_kind";

            invocation.parameters.emplace(
                "path",
                qps::runtime::RuntimeValue::string(
                    path.string()));

            return host.execute(invocation);
        };

    const auto directory = run(root);
    require(
        directory.value.has_value(),
        "path_kind directory returned no runtime value.");
    require(
        directory.value->asString("directory kind") ==
            "directory",
        "path_kind directory mismatch.");

    const auto regular = run(file);
    require(
        regular.value.has_value(),
        "path_kind file returned no runtime value.");
    require(
        regular.value->asString("file kind") ==
            "file",
        "path_kind file mismatch.");

    const auto missing =
        run(root / "missing");

    require(
        missing.value.has_value(),
        "path_kind missing returned no runtime value.");
    require(
        missing.value->asString("missing kind") ==
            "missing",
        "path_kind missing mismatch.");

    fs::remove_all(root);
}

void pathParentReturnsParentPath() {
    qps::runtime::HostActionDispatcher host;

    const auto run =
        [&](const std::string& path) {
            qps::runtime::HostActionInvocation invocation;
            invocation.action_name = "path_parent";

            invocation.parameters.emplace(
                "path",
                qps::runtime::RuntimeValue::string(path));

            return host.execute(invocation);
        };

    const auto nested = run("a/b/c");
    require(
        nested.value.has_value(),
        "path_parent nested path returned no runtime value.");
    require(
        nested.value->asString("nested parent") == "a/b",
        "path_parent nested path mismatch.");

    const auto child = run("a/b");
    require(
        child.value.has_value(),
        "path_parent child path returned no runtime value.");
    require(
        child.value->asString("child parent") == "a",
        "path_parent child path mismatch.");

    const auto root_child = run("a");
    require(
        root_child.value.has_value(),
        "path_parent root child returned no runtime value.");
    require(
        root_child.value->asString("root child parent").empty(),
        "path_parent root child should return empty parent.");

    const auto current = run(".");
    require(
        current.value.has_value(),
        "path_parent current path returned no runtime value.");
    require(
        current.value->asString("current parent").empty(),
        "path_parent current path should return empty parent.");
}

void pathCanonicalReturnsCanonicalPath() {
    namespace fs = std::filesystem;

    const fs::path root =
        fs::temp_directory_path() /
        "qps_host_path_canonical_test";

    fs::remove_all(root);
    fs::create_directories(
        root / "child");

    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "path_canonical";

    invocation.parameters.emplace(
        "path",
        qps::runtime::RuntimeValue::string(
            (root / "child" / ".." / "child").string()));

    qps::runtime::HostActionDispatcher host;

    const auto result =
        host.execute(invocation);

    require(
        result.value.has_value(),
        "path_canonical returned no runtime value.");

    require(
        result.value->asString("canonical path") ==
            fs::weakly_canonical(
                root / "child").string(),
        "path_canonical mismatch.");

    fs::remove_all(root);
}

void dictionarySizeReturnsCounts() {
    const auto empty =
        runDictionarySize(
            makeDictionary({}));

    require(
        empty.value.has_value(),
        "dictionary_size empty dictionary returned no value.");

    require(
        empty.value->asNumber(
            "empty dictionary size") == 0.0,
        "dictionary_size empty dictionary mismatch.");

    const auto multi_entry =
        runDictionarySize(
            makeDictionary({
                {
                    10,
                    qps::runtime::RuntimeValue::string(
                        "compact")
                },
                {
                    20,
                    qps::runtime::RuntimeValue::numeric(42.0)
                },
                {
                    30,
                    qps::runtime::RuntimeValue::string(
                        "dense")
                }
            }));

    require(
        multi_entry.value.has_value(),
        "dictionary_size multi-entry dictionary returned no value.");

    require(
        multi_entry.value->asNumber(
            "multi-entry dictionary size") == 3.0,
        "dictionary_size multi-entry dictionary mismatch.");
}

void dictionarySizeRejectsNonDictionaryInput() {
    expectFailureContaining(
        []() {
            (void)runDictionarySize(
                qps::runtime::RuntimeValue::numeric(1.0));
        },
        "expected dictionary",
        "dictionary_size non-dictionary input");
}

void dictionaryAtReturnsOrderedValues() {
    const auto dictionary =
        makeDictionary({
            {
                10,
                qps::runtime::RuntimeValue::string(
                    "first")
            },
            {
                20,
                qps::runtime::RuntimeValue::numeric(42.0)
            }
        });

    const auto first =
        runDictionaryAt(
            dictionary,
            0.0);

    require(
        first.value.has_value(),
        "dictionary_at first entry returned no value.");

    require(
        first.value->asString(
            "dictionary_at first entry") == "first",
        "dictionary_at first string entry mismatch.");

    const auto numeric =
        runDictionaryAt(
            dictionary,
            1.0);

    require(
        numeric.value.has_value(),
        "dictionary_at numeric entry returned no value.");

    require(
        numeric.value->asNumber(
            "dictionary_at numeric entry") == 42.0,
        "dictionary_at numeric entry mismatch.");

    auto nested =
        makeDictionary({
            {
                1,
                qps::runtime::RuntimeValue::string(
                    "nested")
            }
        });

    const auto nested_result =
        runDictionaryAt(
            makeDictionary({
                {
                    10,
                    qps::runtime::RuntimeValue::string(
                        "outer")
                },
                {
                    20,
                    std::move(nested)
                }
            }),
            1.0);

    require(
        nested_result.value.has_value(),
        "dictionary_at nested entry returned no value.");

    require(
        nested_result.value->isDictionary(),
        "dictionary_at nested entry was not a dictionary.");

    const auto& nested_dictionary =
        nested_result.value->asDictionary(
            "dictionary_at nested entry");

    require(
        nested_dictionary.size() == 1 &&
        nested_dictionary[0].id == 1 &&
        nested_dictionary[0].value.asString(
            "dictionary_at nested value") == "nested",
        "dictionary_at nested dictionary mismatch.");
}

void dictionaryAtRejectsInvalidInputs() {
    const auto single_entry = []() {
        return makeDictionary({
            {
                1,
                qps::runtime::RuntimeValue::string(
                    "first")
            }
        });
    };

    expectFailureContaining(
        [&single_entry]() {
            (void)runDictionaryAt(
                single_entry(),
                -1.0);
        },
        "non-negative",
        "dictionary_at negative index");

    expectFailureContaining(
        [&single_entry]() {
            (void)runDictionaryAt(
                single_entry(),
                1.0);
        },
        "out of range",
        "dictionary_at out-of-range index");

    expectFailureContaining(
        [&single_entry]() {
            (void)runDictionaryAt(
                single_entry(),
                0.5);
        },
        "integral",
        "dictionary_at fractional index");

    expectFailureContaining(
        []() {
            (void)runDictionaryAt(
                qps::runtime::RuntimeValue::numeric(1.0),
                0.0);
        },
        "expected dictionary",
        "dictionary_at non-dictionary input");

    qps::runtime::HostActionInvocation invocation;
    invocation.action_name = "dictionary_at";

    invocation.parameters.emplace(
        "value",
        single_entry());

    invocation.parameters.emplace(
        "index",
        qps::runtime::RuntimeValue::numeric(0.0));

    invocation.parameters.emplace(
        "extra",
        qps::runtime::RuntimeValue::numeric(1.0));

    qps::runtime::HostActionDispatcher host;

    expectFailureContaining(
        [&host, &invocation]() {
            (void)host.execute(invocation);
        },
        "Unknown dictionary_at parameter 'extra'",
        "dictionary_at unknown parameter");
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
        processRequiresProgram();
        std::cout
            << "PASS process requires program\n";

        processAcceptsRuntimeStringParameters();
        std::cout
            << "PASS process accepts runtime string parameters\n";

        processDrainsStdoutAndStderrTogether();
        std::cout
            << "PASS process drains stdout and stderr together\n";

        writeAcceptsRuntimeStringValue();
        std::cout
            << "PASS write accepts runtime string value\n";

        invalidWriteStreamFails();
        std::cout
            << "PASS invalid write stream fails\n";

        qpsCheckAcceptsValidSource();
        std::cout
            << "PASS qps_check accepts valid source\n";

        qpsCheckRejectsInvalidSource();
        std::cout
            << "PASS qps_check rejects invalid source\n";

        pathKindReturnsFilesystemFact();
        std::cout
            << "PASS path_kind returns filesystem fact\n";

        pathParentReturnsParentPath();
        std::cout
            << "PASS path_parent returns parent path\n";

        pathCanonicalReturnsCanonicalPath();
        std::cout
            << "PASS path_canonical returns canonical path\n";

        dictionarySizeReturnsCounts();
        std::cout
            << "PASS dictionary_size returns counts\n";

        dictionarySizeRejectsNonDictionaryInput();
        std::cout
            << "PASS dictionary_size rejects non-dictionary input\n";

        dictionaryAtReturnsOrderedValues();
        std::cout
            << "PASS dictionary_at returns ordered values\n";

        dictionaryAtRejectsInvalidInputs();
        std::cout
            << "PASS dictionary_at rejects invalid inputs\n";

        structureChildReturnsOpaqueStructure();
        std::cout
            << "PASS structure_child returns opaque structure\n";

        structureItemReturnsOpaqueStructure();
        std::cout
            << "PASS structure_item returns opaque structure\n";

        structureActionsRejectMissingSelection();
        std::cout
            << "PASS structure actions reject missing selection\n";

        structureActionsRejectWrongTypes();
        std::cout
            << "PASS structure actions reject wrong types\n";

        structureActionsRejectIncompleteHandles();
        std::cout
            << "PASS structure actions reject incomplete handles\n";

        structureActionsRejectUnknownParameters();
        std::cout
            << "PASS structure actions reject unknown parameters\n";

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
