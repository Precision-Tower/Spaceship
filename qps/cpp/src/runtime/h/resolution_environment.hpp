#ifndef QPS_RUNTIME_H_RESOLUTION_ENVIRONMENT_HPP
#define QPS_RUNTIME_H_RESOLUTION_ENVIRONMENT_HPP

#include "document_loader.hpp"
#include "document_store.hpp"
#include "path_resolver.hpp"
#include "symbol_resolver.hpp"

#include <filesystem>

namespace qps {
namespace runtime {

// Owns the native mechanisms whose lifetimes must remain connected
// while resolving structural QPS references.
//
// This object does not choose authored policy. The caller supplies the
// reference planner and semantic walker explicitly.
class ResolutionEnvironment {
public:
    ResolutionEnvironment(
        std::filesystem::path workspace_root,
        std::filesystem::path reference_planner,
        std::filesystem::path semantic_walker);

    PathResolver& paths();
    DocumentStore& documents();
    SymbolResolver& symbols();

private:
    PathResolver paths_;
    DocumentLoader loader_;
    DocumentStore documents_;
    SymbolResolver symbols_;
};

} // namespace runtime
} // namespace qps

#endif
