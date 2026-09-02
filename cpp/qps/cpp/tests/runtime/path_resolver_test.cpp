#include "../../core/src/runtime/h/path_resolver.hpp"

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
        // ├── <index.qps
        // └── child/
        //     └── <index.qps
        // ----------------------------------------------------

        writeFile(
            fixture_root / "<index.qps",
            "root. name- \"root\";\n");

        writeFile(
            fixture_root / "child" / "<index.qps",
            "child. name- \"child\";\n");

        PathResolver resolver(fixture_root);

        require(
            resolver.workspaceRoot() ==
                std::filesystem::weakly_canonical(
                    fixture_root),
            "Workspace root mismatch.");

        require(
            resolver.isModule("."),
            "Workspace root with <index.qps must be a module.");

        require(
            resolver.isModule("child"),
            "Child directory with <index.qps must be a module.");

        const auto child_index =
            resolver.resolveFile(
                "child/<index.qps");

        require(
            child_index ==
                std::filesystem::weakly_canonical(
                    fixture_root /
                    "child" /
                    "<index.qps"),
            "Child <index.qps resolution mismatch.");

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
                message.find("<index.qps") !=
                std::string::npos;
        }

        require(
            rejected,
            "Workspace without <index.qps was not rejected.");

        std::filesystem::remove_all(fixture_root);
        std::filesystem::remove_all(invalid_root);

        std::cout
            << "PASS canonical <index.qps module surface\n";

        return 0;
    }
    catch (const std::exception& e) {
        std::filesystem::remove_all(fixture_root);

        std::cerr
            << "FAIL canonical <index.qps module surface: "
            << e.what()
            << "\n";

        return 1;
    }
}
