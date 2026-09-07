#include "../h/execution_environment.hpp"

#include "../h/document_store.hpp"
#include "../h/execution_engine.hpp"
#include "../h/path_resolver.hpp"

#include "../../ast/ast_node.hpp"
#include "../../ast/h/declarations.hpp"

namespace qps {
namespace runtime {

ExecutionEnvironment::ExecutionEnvironment(
    PathResolver& paths,
    DocumentStore& documents,
    ExecutionEngine& engine)
    : paths_(paths),
      documents_(documents),
      engine_(engine) {}

void ExecutionEnvironment::loadModule(
    const std::filesystem::path& module_relative) {

    const auto files =
        paths_.qpsFiles(module_relative);

    for (const auto& relative : files) {
        const auto absolute =
            paths_.resolveFile(relative);

        auto program =
            documents_.get(absolute);

        for (const auto& statement :
             program->statements) {

            if (const auto* definition =
                    dynamic_cast<
                        const ast::ExecutionDefinitionNode*>(
                            statement.get())) {

                engine_.registerDefinition(
                    *definition,
                    relative.generic_string());

                continue;
            }

            const auto* term =
                dynamic_cast<
                    const ast::TermDeclarationNode*>(
                        statement.get());

            if (!term) {
                continue;
            }

            std::size_t execution_bodies = 0;

            for (const auto& child : term->content_) {
                if (dynamic_cast<
                        const ast::ExecutionBlockNode*>(
                            child.get())) {

                    ++execution_bodies;
                }
            }

            if (execution_bodies == 0) {
                continue;
            }

            engine_.registerDefinition(
                *term,
                relative.generic_string());
        }
    }
}

} // namespace runtime
} // namespace qps
