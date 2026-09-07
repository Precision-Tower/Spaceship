#ifndef QPS_RUNTIME_H_PATH_RESOLVER_HPP
#define QPS_RUNTIME_H_PATH_RESOLVER_HPP

#include <filesystem>
#include <optional>
#include <vector>

namespace qps {
namespace runtime {

class PathResolver {
public:
    explicit PathResolver(std::filesystem::path workspace_root);

    const std::filesystem::path& workspaceRoot() const;

    // Return the connected module containing a physical source file.
    // The result is workspace-relative. Sources outside the workspace or
    // beneath a broken module chain are not connected.
    std::optional<std::filesystem::path> containingModule(
        const std::filesystem::path& source) const;

    // A QPS module is a directory containing _index.qps.
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

    // Immediate .qps documents in a module, excluding _index.qps.
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
