#include "structural_selection.hpp"

#include "h/declarations.hpp"

#include <stdexcept>
#include <vector>

namespace qps::ast {
namespace {

const std::vector<std::unique_ptr<AstNode>>&
structuralChildren(AstNode& parent) {

    if (auto* key =
            dynamic_cast<KeyDeclarationNode*>(&parent)) {
        return key->content_;
    }

    if (auto* term =
            dynamic_cast<TermDeclarationNode*>(&parent)) {
        return term->content_;
    }

    throw std::runtime_error(
        "AST structural selection requires a Key or Term parent.");
}

AstNode* findStructuralChild(
    const std::vector<std::unique_ptr<AstNode>>& nodes,
    const std::string& name) {

    AstNode* match = nullptr;

    for (const auto& child : nodes) {
        AstNode* candidate = nullptr;

        if (auto* key =
                dynamic_cast<KeyDeclarationNode*>(child.get())) {

            if (key->identifier_ == name) {
                candidate = key;
            }
        }
        else if (auto* term =
                     dynamic_cast<TermDeclarationNode*>(child.get())) {

            if (term->identifier_ == name) {
                candidate = term;
            }
        }
        else if (auto* container =
                     dynamic_cast<ContainerNode*>(child.get())) {

            candidate =
                findStructuralChild(
                    container->elements,
                    name);
        }

        if (!candidate) {
            continue;
        }

        if (match != nullptr) {
            throw std::runtime_error(
                "Duplicate AST structural child '" +
                name +
                "'.");
        }

        match = candidate;
    }

    return match;
}

void findStructuralItem(
    const std::vector<std::unique_ptr<AstNode>>& nodes,
    const std::string& name,
    ItemDeclarationNode*& match) {

    for (const auto& child : nodes) {
        if (auto* item =
                dynamic_cast<ItemDeclarationNode*>(child.get())) {

            auto* identifier =
                dynamic_cast<IdentifierNode*>(
                    item->getTarget());

            if (!identifier ||
                identifier->name_ != name) {
                continue;
            }

            if (match != nullptr) {
                throw std::runtime_error(
                    "Duplicate AST structural Item '" +
                    name +
                    "'.");
            }

            match = item;
            continue;
        }

        if (auto* container =
                dynamic_cast<ContainerNode*>(child.get())) {

            findStructuralItem(
                container->elements,
                name,
                match);
        }
    }
}

} // namespace

AstNode* selectStructuralChild(
    AstNode& parent,
    const std::string& name) {

    return findStructuralChild(
        structuralChildren(parent),
        name);
}

ItemDeclarationNode* selectStructuralItem(
    AstNode& parent,
    const std::string& name) {

    ItemDeclarationNode* match = nullptr;

    findStructuralItem(
        structuralChildren(parent),
        name,
        match);

    return match;
}

} // namespace qps::ast
