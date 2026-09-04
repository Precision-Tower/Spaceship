#ifndef QPS_RUNTIME_H_SYMBOL_RESOLVER_HPP
#define QPS_RUNTIME_H_SYMBOL_RESOLVER_HPP

#include "symbol_table.hpp"

#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace qps {
namespace ast {
class ProgramNode;
class AstNode;
class SymbolReferenceNode;
}
namespace runtime {

class PathResolver;
class DocumentStore;

struct StructuralReferenceContext {
    // Workspace-relative .qps document containing the reference.
    //
    // Example:
    //   defs/semantic_walk/shape.qps
    std::filesystem::path current_document;
};

class StructuralResolver {
public:
    virtual ~StructuralResolver() = default;

    virtual StructuralHandle resolve(
        const ast::SymbolReferenceNode& reference,
        const StructuralReferenceContext& context) const = 0;

    virtual StructuralHandle resolveFrom(
        const StructuralHandle& root,
        const ast::SymbolReferenceNode& reference) const = 0;
};

struct ResolvedSymbol : public StructuralHandle {
    // Authored/surfaced symbol requested from the bootstrap resolver.
    std::string symbol;

    // Bootstrap resolver provenance retained by the legacy surfaced-symbol
    // namespace, not by runtime structural values.
    std::filesystem::path surface_module;
    std::filesystem::path index_file;
    std::filesystem::path document_file;
    std::vector<std::string> semantic_path;
};

class SymbolResolver : public StructuralResolver {
public:
    SymbolResolver(
        PathResolver& paths,
        DocumentStore& documents);

    // Resolve the legacy surfaced-symbol/index namespace.
    ResolvedSymbol resolve(
        const std::string& symbol,
        const std::filesystem::path& start_module) const;

    // Resolve an explicit structural QPS reference from document context.
    //
    //   [>name]              current document
    //   [>.file.name]        sibling file in current module
    //   [>folder/file.name]  child module/file
    //   [>/file.name]        one parent module
    //   [>//file.name]       two parent modules
    //   [>...item-]          explicit Item-value selection
    //
    // Structural names may resolve to Keys or Terms. Filesystem and
    // semantic traversal remain separate and are preserved by the AST.
    StructuralHandle resolve(
        const ast::SymbolReferenceNode& reference,
        const StructuralReferenceContext& context) const override;

    // Continue structural navigation from an already-resolved local root.
    //
    // Example:
    //
    //   root = [>shape.dimensions]
    //   reference = [v.cylinder]
    //
    // resolves the same document path as:
    //
    //   [>shape.dimensions.cylinder]
    StructuralHandle resolveFrom(
        const StructuralHandle& root,
        const ast::SymbolReferenceNode& reference) const override;

private:
    PathResolver& paths_;
    DocumentStore& documents_;
};

} // namespace runtime
} // namespace qps

#endif
