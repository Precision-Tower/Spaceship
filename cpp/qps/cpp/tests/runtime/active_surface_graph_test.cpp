#include "ast/ast_node.hpp"
#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/path_resolver.hpp"
#include "runtime/h/symbol_resolver.hpp"

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

struct SurfaceEntry {
    fs::path module;
    std::string symbol;
};

void collectModules(
    qps::runtime::PathResolver& paths,
    const fs::path& module,
    std::vector<fs::path>& modules) {

    modules.push_back(module);

    for (const auto& child : paths.childModules(module)) {
        collectModules(paths, child, modules);
    }
}

void requireInsideWorkspace(
    const fs::path& workspace,
    const fs::path& file) {

    const auto relative =
        fs::weakly_canonical(file)
            .lexically_relative(
                fs::weakly_canonical(workspace));

    for (const auto& part : relative) {
        if (part == "..") {
            throw std::runtime_error(
                "Resolved document escaped QPS workspace: " +
                file.string());
        }
    }
}

void requireAcyclic(
    const std::map<
        std::string,
        std::set<std::string>
    >& graph) {

    enum class State {
        UNSEEN,
        VISITING,
        DONE
    };

    std::map<std::string, State> states;
    std::vector<std::string> stack;

    const auto visit =
        [&](const auto& self,
            const std::string& node) -> void {

        const State state = states[node];

        if (state == State::DONE) {
            return;
        }

        if (state == State::VISITING) {
            std::string message =
                "QPS module-surface delegation cycle:";

            for (const auto& part : stack) {
                message +=
                    " " +
                    (
                        part.empty()
                            ? std::string("<root>")
                            : part
                    ) +
                    " ->";
            }

            message +=
                " " +
                (
                    node.empty()
                        ? std::string("<root>")
                        : node
                );

            throw std::runtime_error(message);
        }

        states[node] = State::VISITING;
        stack.push_back(node);

        const auto found = graph.find(node);

        if (found != graph.end()) {
            for (const auto& child :
                 found->second) {

                self(self, child);
            }
        }

        stack.pop_back();
        states[node] = State::DONE;
    };

    for (const auto& [node, children] : graph) {
        (void)children;
        visit(visit, node);
    }
}

} // namespace


int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " <qps-workspace-root>\n";

        return EXIT_FAILURE;
    }

    try {
        const fs::path workspace =
            fs::weakly_canonical(argv[1]);

        qps::runtime::PathResolver paths(workspace);
        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(loader);

        qps::runtime::SymbolResolver symbols(
            paths,
            documents);

        std::vector<fs::path> modules;

        collectModules(
            paths,
            fs::path{},
            modules);

        std::vector<SurfaceEntry> surfaces;

        std::map<
            std::string,
            std::set<std::string>
        > delegation_graph;

        for (const auto& module : modules) {
            const fs::path index_file =
                paths.indexFile(module);

            const auto index_ast =
                documents.get(index_file);

            for (const auto& statement :
                 index_ast->statements) {

                auto* item =
                    dynamic_cast<
                        qps::ast::ItemDeclarationNode*>(
                        statement.get());

                if (!item) {
                    continue;
                }

                auto* target =
                    dynamic_cast<
                        qps::ast::IdentifierNode*>(
                        item->target_.get());

                if (!target) {
                    throw std::runtime_error(
                        "Surface Item in " +
                        index_file.string() +
                        " does not use IdentifierNode target.");
                }

                auto* path_ref =
                    dynamic_cast<
                        qps::ast::PathReferenceNode*>(
                        item->value_node_.get());

                if (!path_ref) {
                    throw std::runtime_error(
                        "Surface symbol '" +
                        target->name_ +
                        "' in " +
                        index_file.string() +
                        " does not reference a QPS path.");
                }

                const auto& segments =
                    path_ref->getPathSegments();

                if (segments.empty()) {
                    throw std::runtime_error(
                        "Surface symbol '" +
                        target->name_ +
                        "' has empty reference path.");
                }

                surfaces.push_back(
                    SurfaceEntry{
                        module,
                        target->name_
                    });

                const fs::path child =
                    (module / segments.front())
                        .lexically_normal();

                if (paths.isModule(child)) {
                    if (segments.size() != 2) {
                        throw std::runtime_error(
                            "Module delegation for '" +
                            target->name_ +
                            "' in " +
                            index_file.string() +
                            " must use <module>.<symbol>.");
                    }

                    delegation_graph[
                        module.generic_string()
                    ].insert(
                        child.generic_string());
                }
            }
        }

        // Prove recursive module delegation terminates before
        // invoking SymbolResolver's recursive implementation.
        requireAcyclic(delegation_graph);

        std::size_t resolved = 0;

        for (const auto& surface : surfaces) {
            const auto result =
                symbols.resolve(
                    surface.symbol,
                    surface.module);

            if (result.document_file.empty()) {
                throw std::runtime_error(
                    "Surface symbol '" +
                    surface.symbol +
                    "' resolved without a document.");
            }

            requireInsideWorkspace(
                workspace,
                result.document_file);

            if (result.target_type !=
                "KEY_DECLARATION") {

                throw std::runtime_error(
                    "Surface symbol '" +
                    surface.symbol +
                    "' terminated as '" +
                    result.target_type +
                    "' instead of KEY_DECLARATION.");
            }

            if (result.target_identifier.empty()) {
                throw std::runtime_error(
                    "Surface symbol '" +
                    surface.symbol +
                    "' resolved without terminal identifier.");
            }

            if (!result.document_owner ||
                result.target_node == nullptr) {

                throw std::runtime_error(
                    "Surface symbol '" +
                    surface.symbol +
                    "' did not retain terminal AST ownership.");
            }

            ++resolved;

            std::cout
                << "PASS "
                << (
                    surface.module.empty()
                        ? std::string("<root>")
                        : surface.module.generic_string()
                )
                << "."
                << surface.symbol
                << " -> "
                << result.document_file
                       .lexically_relative(workspace)
                       .generic_string()
                << ":"
                << result.target_identifier
                << "\n";
        }

        std::size_t edges = 0;

        for (const auto& [module, children] :
             delegation_graph) {

            (void)module;
            edges += children.size();
        }

        std::cout << "\n";
        std::cout
            << "modules="
            << modules.size()
            << "\n";

        std::cout
            << "surface_items="
            << surfaces.size()
            << "\n";

        std::cout
            << "resolved="
            << resolved
            << "\n";

        std::cout
            << "failed="
            << (surfaces.size() - resolved)
            << "\n";

        std::cout
            << "delegation_edges="
            << edges
            << "\n";

        if (resolved != surfaces.size()) {
            throw std::runtime_error(
                "Not every active surface Item resolved.");
        }

        std::cout
            << "\nQPS ACTIVE MODULE SURFACE GRAPH OK\n";

        return EXIT_SUCCESS;
    }
    catch (const std::exception& e) {
        std::cerr
            << "ERROR: "
            << e.what()
            << "\n";

        return EXIT_FAILURE;
    }
}
