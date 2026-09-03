#ifndef QPS_RUNTIME_H_SYMBOL_RESOLVER_HPP
#define QPS_RUNTIME_H_SYMBOL_RESOLVER_HPP

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

struct ResolvedSymbol {
    std::string symbol;

    // Module whose _index.qps surfaced the symbol.
    std::filesystem::path surface_module;

    // Actual index file where the symbol was found.
    std::filesystem::path index_file;

    // Physical .qps document containing the target.
    std::filesystem::path document_file;

    // Semantic path inside that document.
    // Example: uni.p -> document=uni.qps, semantic_path={"p"}
    std::vector<std::string> semantic_path;

    // Verified terminal semantic object.
    //
    // Structural resolution may terminate on a Key, Term, or explicit
    // Item-value selection while retaining the owning document AST.
    std::string target_type;
    std::string target_identifier;

    // Keeps the parsed document alive for target lifetime.
    std::shared_ptr<ast::ProgramNode> document_owner;

    // Non-owning pointer into document_owner.
    ast::AstNode* target_node = nullptr;
};

class SymbolResolver {
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
    ResolvedSymbol resolve(
        const ast::SymbolReferenceNode& reference,
        const StructuralReferenceContext& context) const;

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
    ResolvedSymbol resolveFrom(
        const ResolvedSymbol& root,
        const ast::SymbolReferenceNode& reference) const;

private:
    PathResolver& paths_;
    DocumentStore& documents_;
};

} // namespace runtime
} // namespace qps

#endif
