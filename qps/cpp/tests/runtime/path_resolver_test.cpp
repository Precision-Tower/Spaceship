#include "../../src/runtime/h/path_resolver.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

[[noreturn]]
void fail(const std::string& message) {
    throw std::runtime_error(message);
}

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        fail(message);
    }
}

void writeFile(
    const std::filesystem::path& path,
    const std::string& contents) {

    std::filesystem::create_directories(
        path.parent_path());

    std::ofstream out(path);

    if (!out) {
        fail(
            "Failed to create fixture: " +
            path.string());
    }

    out << contents;
}

} // namespace


int main() {
    using qps::runtime::PathResolver;

    const auto fixture_root =
        std::filesystem::temp_directory_path() /
        "qps_index_surface_test";

    try {
        std::filesystem::remove_all(fixture_root);

        // ----------------------------------------------------
        // Canonical QPS workspace surface.
        //
        // workspace/
        // ├── _index.qps
        // └── child/
        //     └── _index.qps
        // ----------------------------------------------------

        writeFile(
            fixture_root / "_index.qps",
            "root. name- \"root\";\n");

        writeFile(
            fixture_root / "child" / "_index.qps",
            "child. name- \"child\";\n");

        PathResolver resolver(fixture_root);

        require(
            resolver.workspaceRoot() ==
                std::filesystem::weakly_canonical(
                    fixture_root),
            "Workspace root mismatch.");

        require(
            resolver.isModule("."),
            "Workspace root with _index.qps must be a module.");

        require(
            resolver.isModule("child"),
            "Child directory with _index.qps must be a module.");

        const auto child_index =
            resolver.resolveFile(
                "child/_index.qps");

        require(
            child_index ==
                std::filesystem::weakly_canonical(
                    fixture_root /
                    "child" /
                    "_index.qps"),
            "Child _index.qps resolution mismatch.");

        const auto children =
            resolver.childModules(".");

        bool found_child = false;

        for (const auto& child : children) {
            if (child.filename() == "child") {
                found_child = true;
                break;
            }
        }

        require(
            found_child,
            "childModules(.) did not expose child module.");

        // ----------------------------------------------------
        // Workspace without canonical surface must fail.
        // ----------------------------------------------------

        const auto invalid_root =
            std::filesystem::temp_directory_path() /
            "qps_missing_index_surface_test";

        std::filesystem::remove_all(invalid_root);
        std::filesystem::create_directories(
            invalid_root);

        bool rejected = false;

        try {
            PathResolver invalid(invalid_root);
            (void)invalid;
        }
        catch (const std::runtime_error& e) {
            const std::string message = e.what();

            rejected =
                message.find("_index.qps") !=
                std::string::npos;
        }

        require(
            rejected,
            "Workspace without _index.qps was not rejected.");

        // Historical module-surface filenames are intentionally not accepted.
        // _index.qps is the portable contract across Linux, Android, and Windows.
        const auto historical_root =
            std::filesystem::temp_directory_path() /
            "qps_historical_index_surface_test";

        std::filesystem::remove_all(historical_root);
        std::filesystem::create_directories(historical_root);

        writeFile(
            historical_root / "{index}.qps",
            "historical. name- \"brace\";\n");

        bool historical_rejected = false;

        try {
            PathResolver historical(historical_root);
            (void)historical;
        }
        catch (const std::runtime_error& e) {
            historical_rejected =
                std::string(e.what()).find("_index.qps") !=
                std::string::npos;
        }

        require(
            historical_rejected,
            "Historical {index}.qps unexpectedly defined a QPS module.");

        std::filesystem::remove_all(fixture_root);
        std::filesystem::remove_all(invalid_root);
        std::filesystem::remove_all(historical_root);

        std::cout
            << "PASS canonical _index.qps module surface\n";

        return 0;
    }
    catch (const std::exception& e) {
        std::filesystem::remove_all(fixture_root);

        std::cerr
            << "FAIL canonical _index.qps module surface: "
            << e.what()
            << "\n";

        return 1;
    }
}
