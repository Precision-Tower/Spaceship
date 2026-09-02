#include "../h/document_store.hpp"

#include "../h/document_loader.hpp"
#include "../../ast/ast_node.hpp"

namespace qps {
namespace runtime {

DocumentStore::DocumentStore(
    DocumentLoader& loader)
    : loader_(loader) {}

std::shared_ptr<ast::ProgramNode>
DocumentStore::get(
    const std::filesystem::path& file) {

    const std::filesystem::path canonical =
        std::filesystem::weakly_canonical(file);

    const std::string key =
        canonical.string();

    auto existing =
        cache_.find(key);

    if (existing != cache_.end()) {
        return existing->second;
    }

    auto loaded =
        loader_.load(canonical);

    std::shared_ptr<ast::ProgramNode> stored =
        std::move(loaded);

    cache_.emplace(key, stored);

    return stored;
}

std::size_t
DocumentStore::cachedDocumentCount() const {
    return cache_.size();
}

} // namespace runtime
} // namespace qps
