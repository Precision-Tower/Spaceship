#ifndef QPS_RUNTIME_H_PATH_RESOLVER_HPP
#define QPS_RUNTIME_H_PATH_RESOLVER_HPP

#include <filesystem>
#include <vector>

namespace qps {
namespace runtime {

class PathResolver {
public:
    explicit PathResolver(std::filesystem::path workspace_root);

    const std::filesystem::path& workspaceRoot() const;

    // A QPS module is a directory containing <index.qps.
    bool isModule(const std::filesystem::path& module_relative) const;

    // Resolve a connected QPS module from the workspace root.
    std::filesystem::path resolveModule(
        const std::filesystem::path& module_relative) const;

    // Resolve a .qps file whose parent chain consists entirely of QPS modules.
    std::filesystem::path resolveFile(
        const std::filesystem::path& file_relative) const;

    // Immediate child directories that participate in the QPS module web.
    std::vector<std::filesystem::path> childModules(
        const std::filesystem::path& module_relative = {}) const;

    // Immediate .qps documents in a module, excluding <index.qps.
    std::vector<std::filesystem::path> qpsFiles(
        const std::filesystem::path& module_relative = {}) const;

    std::filesystem::path indexFile(
        const std::filesystem::path& module_relative = {}) const;

private:
    std::filesystem::path root_;

    static void validateRelativePath(const std::filesystem::path& path);
    void requireConnectedChain(
        const std::filesystem::path& module_relative) const;
};

} // namespace runtime
} // namespace qps

#endif
