#ifndef QPS_RUNTIME_H_EXECUTION_ENVIRONMENT_HPP
#define QPS_RUNTIME_H_EXECUTION_ENVIRONMENT_HPP

#include <filesystem>

namespace qps {
namespace runtime {

class PathResolver;
class DocumentStore;
class ExecutionEngine;

// Assembles executable definitions from an already-selected
// connected QPS module.
//
// This is mechanism, not visibility policy:
// - PathResolver defines connected module topology.
// - the caller selects the module.
// - this class loads its immediate QPS documents and registers
//   their execution definitions with source provenance.
// - it does not recurse, interpret _index.qps, or execute calls.
class ExecutionEnvironment {
public:
    ExecutionEnvironment(
        PathResolver& paths,
        DocumentStore& documents,
        ExecutionEngine& engine);

    void loadModule(
        const std::filesystem::path& module_relative);

private:
    PathResolver& paths_;
    DocumentStore& documents_;
    ExecutionEngine& engine_;
};

} // namespace runtime
} // namespace qps

#endif
