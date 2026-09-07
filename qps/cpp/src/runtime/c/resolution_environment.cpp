#include "../h/resolution_environment.hpp"

#include <utility>

namespace qps {
namespace runtime {

ResolutionEnvironment::ResolutionEnvironment(
    std::filesystem::path workspace_root,
    std::filesystem::path reference_planner,
    std::filesystem::path semantic_walker)
    : paths_(std::move(workspace_root)),
      loader_(),
      documents_(loader_),
      symbols_(
          paths_,
          documents_,
          std::move(reference_planner),
          std::move(semantic_walker)) {}

PathResolver& ResolutionEnvironment::paths() {
    return paths_;
}

DocumentStore& ResolutionEnvironment::documents() {
    return documents_;
}

SymbolResolver& ResolutionEnvironment::symbols() {
    return symbols_;
}

} // namespace runtime
} // namespace qps
