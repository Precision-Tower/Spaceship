#ifndef QPS_RUNTIME_H_DOCUMENT_LOADER_HPP
#define QPS_RUNTIME_H_DOCUMENT_LOADER_HPP

#include <filesystem>
#include <memory>

namespace qps {
namespace ast {
class ProgramNode;
}

namespace runtime {

// Converts a QPS source document into its parsed AST.
// Filesystem/module semantics belong to PathResolver;
// this class only knows how to load and parse a document.
class DocumentLoader {
public:
    std::unique_ptr<ast::ProgramNode> load(
        const std::filesystem::path& file) const;
};

} // namespace runtime
} // namespace qps

#endif
