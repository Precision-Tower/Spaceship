#include "../h/path_resolver.hpp"

#include <algorithm>
#include <stdexcept>
#include <string>

namespace qps {
namespace runtime {

namespace fs = std::filesystem;

PathResolver::PathResolver(fs::path workspace_root)
    : root_(fs::weakly_canonical(std::move(workspace_root))) {

    if (!fs::is_directory(root_)) {
        throw std::runtime_error(
            "QPS workspace root is not a directory: " + root_.string());
    }

    if (!fs::is_regular_file(root_ / "_index.qps")) {
        throw std::runtime_error(
            "QPS workspace root does not contain _index.qps: " +
            root_.string());
    }
}

const fs::path& PathResolver::workspaceRoot() const {
    return root_;
}

void PathResolver::validateRelativePath(const fs::path& path) {
    if (path.is_absolute()) {
        throw std::runtime_error(
            "QPS module paths must be workspace-relative.");
    }

    for (const auto& part : path) {
        if (part == "..") {
            throw std::runtime_error(
                "QPS module path cannot escape the workspace root.");
        }
    }
}

void PathResolver::requireConnectedChain(
    const fs::path& module_relative) const {

    validateRelativePath(module_relative);

    fs::path current = root_;

    if (!fs::is_regular_file(current / "_index.qps")) {
        throw std::runtime_error(
            "Broken QPS module chain at workspace root.");
    }

    for (const auto& part : module_relative) {
        if (part == "." || part.empty()) {
            continue;
        }

        current /= part;

        if (!fs::is_directory(current) ||
            !fs::is_regular_file(current / "_index.qps")) {
            throw std::runtime_error(
                "Broken QPS module chain at: " + current.string());
        }
    }
}

bool PathResolver::isModule(const fs::path& module_relative) const {
    try {
        requireConnectedChain(module_relative);
        return true;
    } catch (...) {
        return false;
    }
}

fs::path PathResolver::resolveModule(
    const fs::path& module_relative) const {

    requireConnectedChain(module_relative);
    return (root_ / module_relative).lexically_normal();
}

fs::path PathResolver::resolveFile(
    const fs::path& file_relative) const {

    validateRelativePath(file_relative);

    if (file_relative.extension() != ".qps") {
        throw std::runtime_error(
            "QPS document must use .qps extension: " +
            file_relative.string());
    }

    requireConnectedChain(file_relative.parent_path());

    fs::path resolved = (root_ / file_relative).lexically_normal();

    if (!fs::is_regular_file(resolved)) {
        throw std::runtime_error(
            "QPS document not found: " + resolved.string());
    }

    return resolved;
}

std::vector<fs::path> PathResolver::childModules(
    const fs::path& module_relative) const {

    fs::path module = resolveModule(module_relative);
    std::vector<fs::path> result;

    for (const auto& entry : fs::directory_iterator(module)) {
        if (entry.is_directory() &&
            fs::is_regular_file(entry.path() / "_index.qps")) {
            result.push_back(
                fs::relative(entry.path(), root_));
        }
    }

    std::sort(result.begin(), result.end());
    return result;
}

std::vector<fs::path> PathResolver::qpsFiles(
    const fs::path& module_relative) const {

    fs::path module = resolveModule(module_relative);
    std::vector<fs::path> result;

    for (const auto& entry : fs::directory_iterator(module)) {
        if (!entry.is_regular_file()) {
            continue;
        }

        const fs::path file = entry.path();

        if (file.extension() == ".qps" &&
            file.filename() != "_index.qps") {
            result.push_back(fs::relative(file, root_));
        }
    }

    std::sort(result.begin(), result.end());
    return result;
}

fs::path PathResolver::indexFile(
    const fs::path& module_relative) const {

    return resolveModule(module_relative) / "_index.qps";
}

} // namespace runtime
} // namespace qps
