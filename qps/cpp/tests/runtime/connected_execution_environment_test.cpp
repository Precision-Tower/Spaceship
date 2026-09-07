#include "../../src/runtime/h/document_loader.hpp"
#include "../../src/runtime/h/document_store.hpp"
#include "../../src/runtime/h/execution_engine.hpp"
#include "../../src/runtime/h/execution_environment.hpp"
#include "../../src/runtime/h/path_resolver.hpp"

#include "../../src/ast/ast_node.hpp"
#include "../../src/ast/h/declarations.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void writeFile(
    const fs::path& path,
    const std::string& contents) {

    fs::create_directories(path.parent_path());

    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error(
            "Failed to write fixture: " + path.string());
    }

    out << contents;
}

} // namespace

int main() {
    const fs::path root =
        fs::temp_directory_path() /
        "qps_connected_execution_environment_test";

    try {
        fs::remove_all(root);
        fs::create_directories(root / "module");

        writeFile(
            root / "_index.qps",
            "Root.\n");

        writeFile(
            root / "module" / "_index.qps",
            "Module.\n");

        writeFile(
            root / "module" / "evidence.qps",
            R"qps(
{Evidence:
-return 7;
}
)qps");

        writeFile(
            root / "module" / "policy.qps",
            R"qps(
{Policy:
[>value-]/n;
-return value;
}
)qps");

        writeFile(
            root / "module" / "run.qps",
            R"qps(
{Run:
%observation: {>Evidence:
}

%result: {>Policy:
value- observation;
}

-return result;
}
)qps");

        qps::runtime::PathResolver paths(root);
        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(loader);
        qps::runtime::ExecutionEngine engine;

        qps::runtime::ExecutionEnvironment environment(
            paths,
            documents,
            engine);

        environment.loadModule("module");

        require(
            documents.cachedDocumentCount() == 3,
            "Expected all three module documents to remain owned.");

        const auto evidence =
            engine.inspectRegisteredDefinition("Evidence");

        const auto policy =
            engine.inspectRegisteredDefinition("Policy");

        const auto run =
            engine.inspectRegisteredDefinition("Run");

        require(
            evidence.source.has_value() &&
            evidence.source->source_document ==
                "module/evidence.qps",
            "Evidence provenance mismatch.");

        require(
            policy.source.has_value() &&
            policy.source->source_document ==
                "module/policy.qps",
            "Policy provenance mismatch.");

        require(
            run.source.has_value() &&
            run.source->source_document ==
                "module/run.qps",
            "Run provenance mismatch.");

        const auto result =
            engine.instantiate("Run", {});

        require(
            result.result.has_value(),
            "Run returned no value.");

        require(
            result.result->kind() ==
                qps::runtime::RuntimeValue::Kind::NUMERIC,
            "Run result was not numeric.");

        require(
            result.result->asNumber("Run result") == 7.0,
            "Connected execution returned wrong result.");

        std::cout
            << "QPS connected execution environment: PASS\n";

        fs::remove_all(root);
        return 0;
    }
    catch (const std::exception& e) {
        fs::remove_all(root);

        std::cerr
            << "QPS connected execution environment: FAIL: "
            << e.what()
            << "\n";

        return 1;
    }
}
