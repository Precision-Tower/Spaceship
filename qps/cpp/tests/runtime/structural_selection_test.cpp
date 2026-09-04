#include "../../src/ast/structural_selection.hpp"
#include "../../src/ast/h/declarations.hpp"

#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::unique_ptr<qps::ast::ItemDeclarationNode>
item(const std::string& name) {

    return std::make_unique<qps::ast::ItemDeclarationNode>(
        std::make_unique<qps::ast::IdentifierNode>(
            name,
            1,
            1),
        1,
        1);
}

} // namespace

int main() {
    try {
        using namespace qps::ast;

        ProgramNode document(1, 1);

        auto surface_container =
            std::make_unique<ContainerNode>(
                1,
                1);

        surface_container->elements.push_back(
            std::make_unique<KeyDeclarationNode>(
                "surface",
                1,
                1));

        document.statements.push_back(
            std::move(surface_container));

        require(
            selectDocumentStructure(
                document,
                "surface") != nullptr,
            "document surface selection failed");

        require(
            selectDocumentStructure(
                document,
                "missing") == nullptr,
            "missing document structure must return nullptr");

        KeyDeclarationNode root("root", 1, 1);

        auto direct =
            std::make_unique<TermDeclarationNode>(
                "direct",
                1,
                1);

        auto container =
            std::make_unique<ContainerNode>(
                1,
                1);

        auto nested =
            std::make_unique<KeyDeclarationNode>(
                "nested",
                1,
                1);

        nested->content_.push_back(
            item("value"));

        container->elements.push_back(
            std::move(nested));

        root.content_.push_back(
            std::move(direct));

        root.content_.push_back(
            std::move(container));

        require(
            selectStructuralChild(root, "direct") != nullptr,
            "direct Term selection failed");

        AstNode* nested_node =
            selectStructuralChild(root, "nested");

        require(
            nested_node != nullptr,
            "transparent Container selection failed");

        require(
            selectStructuralItem(
                *nested_node,
                "value") != nullptr,
            "direct Item selection failed");

        require(
            selectStructuralChild(root, "missing") == nullptr,
            "missing structural child must return nullptr");

        require(
            selectStructuralItem(
                *nested_node,
                "missing") == nullptr,
            "missing structural Item must return nullptr");

        auto duplicate_container =
            std::make_unique<ContainerNode>(
                1,
                1);

        duplicate_container->elements.push_back(
            std::make_unique<TermDeclarationNode>(
                "direct",
                1,
                1));

        root.content_.push_back(
            std::move(duplicate_container));

        bool duplicate_rejected = false;

        try {
            (void)selectStructuralChild(
                root,
                "direct");
        }
        catch (const std::runtime_error&) {
            duplicate_rejected = true;
        }

        require(
            duplicate_rejected,
            "duplicate structural identity must be rejected");

        std::cout
            << "qps/cpp/tests/runtime/structural_selection_test.cpp: PASS\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "qps/cpp/tests/runtime/structural_selection_test.cpp: "
            << "FAIL: "
            << error.what()
            << '\n';

        return 1;
    }
}
