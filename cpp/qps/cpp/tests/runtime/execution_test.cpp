#include "runtime/h/document_loader.hpp"
#include "runtime/h/interpreter.hpp"
#include "runtime/h/symbol_table.hpp"

#include "ast/ast_node.hpp"

#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {

    if (argc != 2) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " <qps-file>\n";

        return 2;
    }

    try {
        qps::runtime::DocumentLoader loader;

        auto program =
            loader.load(argv[1]);

        if (program->statements.size() != 1) {
            throw std::runtime_error(
                "Execution witness expects exactly one top-level node.");
        }

        auto* block =
            dynamic_cast<qps::ast::ExecutionBlockNode*>(
                program->statements.front().get());

        if (!block) {
            throw std::runtime_error(
                "Execution witness expects a top-level execution block.");
        }

        qps::runtime::ExecutionScope scope;
        qps::runtime::Interpreter interpreter(scope);

        interpreter.execute(*block);

        for (const auto& binding :
             scope.bindings()) {

            std::cout
                << binding.name
                << " = "
                << binding.value
                << " ["
                << qps::runtime::bindingOriginName(
                    binding.origin);

            if (binding.semantic_symbol) {
                std::cout
                    << ", semantic="
                    << *binding.semantic_symbol;
            }

            std::cout
                << "]\n";
        }

        return 0;

    } catch (const std::exception& e) {

        std::cerr
            << "ERROR: "
            << e.what()
            << "\n";

        return 1;
    }
}
