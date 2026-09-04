#ifndef QPS_RUNTIME_H_DOCUMENT_STORE_HPP
#define QPS_RUNTIME_H_DOCUMENT_STORE_HPP

#include <filesystem>
#include <memory>
#include <unordered_map>

namespace qps {

namespace ast {
class ProgramNode;
}

namespace runtime {

class DocumentLoader;

// Owns parsed QPS documents and keeps their ASTs alive.
// Each physical document is parsed once per store instance.
class DocumentStore {
public:
    explicit DocumentStore(DocumentLoader& loader);

    std::shared_ptr<ast::ProgramNode> get(
        const std::filesystem::path& file);

    std::size_t cachedDocumentCount() const;

private:
    DocumentLoader& loader_;

    std::unordered_map<
        std::string,
        std::shared_ptr<ast::ProgramNode>
    > cache_;
};

} // namespace runtime
} // namespace qps

#endif
