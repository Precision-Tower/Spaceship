#include "structural_selection.hpp"

#include "h/declarations.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace qps::ast {
namespace {


struct StructuralPath {
    std::vector<std::string> segments;
    bool selects_item = false;
};

StructuralPath parseStructuralPath(
    const std::string& path) {

    StructuralPath result;
    std::string current;

    if (path.empty()) {
        throw std::runtime_error(
            "QPS structural address is empty.");
    }

    for (std::size_t i = 0; i < path.size(); ++i) {
        const char c = path[i];

        if (c == '.') {
            if (current.empty()) {
                throw std::runtime_error(
                    "QPS structural address contains an empty segment.");
            }

            result.segments.push_back(current);
            current.clear();
            continue;
        }

        if (c == '-') {
            if (i + 1 != path.size()) {
                throw std::runtime_error(
                    "QPS Item selector '-' must terminate the structural address.");
            }

            if (current.empty()) {
                throw std::runtime_error(
                    "QPS Item selector '-' has no target.");
            }

            result.selects_item = true;
            continue;
        }

        if (c == ':') {
            throw std::runtime_error(
                "QPS navigation does not use declaration ':' syntax.");
        }

        current.push_back(c);
    }

    if (current.empty()) {
        throw std::runtime_error(
            "QPS structural address contains an empty final segment.");
    }

    result.segments.push_back(current);
    return result;
}

const std::vector<std::unique_ptr<AstNode>>&
structuralChildren(const AstNode& parent) {

    if (const auto* program =
            dynamic_cast<const ProgramNode*>(&parent)) {
        return program->statements;
    }

    if (const auto* key =
            dynamic_cast<const KeyDeclarationNode*>(&parent)) {
        return key->content_;
    }

    if (const auto* term =
            dynamic_cast<const TermDeclarationNode*>(&parent)) {
        return term->content_;
    }

    throw std::runtime_error(
        "AST structural selection requires a Program, Key, or Term parent.");
}

const AstNode* findStructuralChild(
    const std::vector<std::unique_ptr<AstNode>>& nodes,
    const std::string& name) {

    const AstNode* match = nullptr;

    for (const auto& child : nodes) {
        const AstNode* candidate = nullptr;

        if (const auto* key =
                dynamic_cast<const KeyDeclarationNode*>(child.get())) {

            if (key->identifier_ == name) {
                candidate = key;
            }
        }
        else if (const auto* term =
                     dynamic_cast<const TermDeclarationNode*>(child.get())) {

            if (term->identifier_ == name) {
                candidate = term;
            }
        }
        else if (const auto* container =
                     dynamic_cast<const ContainerNode*>(child.get())) {

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

const ItemDeclarationNode* findStructuralItem(
    const std::vector<std::unique_ptr<AstNode>>& nodes,
    const std::string& name) {

    const ItemDeclarationNode* match = nullptr;

    for (const auto& child : nodes) {
        if (const auto* item =
                dynamic_cast<const ItemDeclarationNode*>(child.get())) {

            const auto* identifier =
                dynamic_cast<const IdentifierNode*>(
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

        if (const auto* container =
                dynamic_cast<const ContainerNode*>(child.get())) {

            const auto* nested =
                findStructuralItem(
                    container->elements,
                    name);

            if (!nested) {
                continue;
            }

            if (match != nullptr) {
                throw std::runtime_error(
                    "Duplicate AST structural Item '" +
                    name +
                    "'.");
            }

            match = nested;
        }
    }

    return match;
}

} // namespace


const AstNode* selectStructuralPath(
    const ProgramNode& document,
    const std::string& path) {

    const auto parsed =
        parseStructuralPath(path);

    if (parsed.segments.empty()) {
        return nullptr;
    }

    const AstNode* current =
        selectDocumentStructure(
            document,
            parsed.segments.front());

    if (!current) {
        return nullptr;
    }

    for (std::size_t i = 1;
         i < parsed.segments.size();
         ++i) {

        const bool final =
            i + 1 ==
            parsed.segments.size();

        /*
         * Final '-' means the caller explicitly expects an Item.
         * Without '-', normal structural navigation selects Key/Term
         * children by hierarchy.
         */
        if (final &&
            parsed.selects_item) {

            return selectStructuralItem(
                *current,
                parsed.segments[i]);
        }

        const AstNode* child =
            selectStructuralChild(
                *current,
                parsed.segments[i]);

        if (!child) {
            return nullptr;
        }

        current = child;
    }

    /*
     * A one-segment Item-selecting address is not currently valid
     * because document surface Items are not part of structural
     * document selection.
     */
    if (parsed.selects_item) {
        return nullptr;
    }

    return current;
}

std::vector<const AstNode*> structuralScope(
    const AstNode& parent) {

    std::vector<const AstNode*> result;

    /*
     * Items are structural leaves.
     *
     * Scope on an Item is valid and simply contains no members.
     * The caller may still render the selected Item itself.
     */
    if (dynamic_cast<const ItemDeclarationNode*>(&parent)) {
        return result;
    }

    const auto append =
        [&](const auto& self,
            const std::vector<std::unique_ptr<AstNode>>& nodes)
            -> void {

            for (const auto& child : nodes) {
                if (const auto* container =
                        dynamic_cast<const ContainerNode*>(
                            child.get())) {

                    self(self, container->elements);
                    continue;
                }

                if (
                    dynamic_cast<const KeyDeclarationNode*>(
                        child.get()) ||
                    dynamic_cast<const TermDeclarationNode*>(
                        child.get()) ||
                    dynamic_cast<const ItemDeclarationNode*>(
                        child.get())) {

                    result.push_back(child.get());
                }
            }
        };

    append(append, structuralChildren(parent));
    return result;
}


std::vector<const AstNode*> scoutStructuralName(
    const ProgramNode& document,
    const std::string& name) {

    std::vector<const AstNode*> result;

    const auto visit =
        [&](const auto& self,
            const std::vector<std::unique_ptr<AstNode>>& nodes)
            -> void {

            for (const auto& child : nodes) {
                if (const auto* definition =
                        dynamic_cast<const ExecutionDefinitionNode*>(
                            child.get())) {

                    if (!definition->identifier_is_numeric_ &&
                        definition->identifier_ == name) {

                        result.push_back(definition);
                    }

                    continue;
                }

                if (const auto* key =
                        dynamic_cast<const KeyDeclarationNode*>(
                            child.get())) {

                    if (key->identifier_ == name) {
                        result.push_back(key);
                    }

                    self(self, key->content_);
                    continue;
                }

                if (const auto* term =
                        dynamic_cast<const TermDeclarationNode*>(
                            child.get())) {

                    if (term->identifier_ == name) {
                        result.push_back(term);
                    }

                    self(self, term->content_);
                    continue;
                }

                if (const auto* item =
                        dynamic_cast<const ItemDeclarationNode*>(
                            child.get())) {

                    const auto* identifier =
                        dynamic_cast<const IdentifierNode*>(
                            item->getTarget());

                    if (identifier &&
                        identifier->name_ == name) {

                        result.push_back(item);
                    }

                    continue;
                }

                if (const auto* container =
                        dynamic_cast<const ContainerNode*>(
                            child.get())) {

                    self(self, container->elements);
                }
            }
        };

    visit(visit, document.statements);

    return result;
}


const AstNode* selectDocumentStructure(
    const ProgramNode& document,
    const std::string& name) {

    return findStructuralChild(
        document.statements,
        name);
}

AstNode* selectDocumentStructure(
    ProgramNode& document,
    const std::string& name) {

    return const_cast<AstNode*>(
        selectDocumentStructure(
            static_cast<const ProgramNode&>(document),
            name));
}

const AstNode* selectStructuralChild(
    const AstNode& parent,
    const std::string& name) {

    return findStructuralChild(
        structuralChildren(parent),
        name);
}

AstNode* selectStructuralChild(
    AstNode& parent,
    const std::string& name) {

    return const_cast<AstNode*>(
        selectStructuralChild(
            static_cast<const AstNode&>(parent),
            name));
}

const ItemDeclarationNode* selectStructuralItem(
    const AstNode& parent,
    const std::string& name) {

    return findStructuralItem(
        structuralChildren(parent),
        name);
}

ItemDeclarationNode* selectStructuralItem(
    AstNode& parent,
    const std::string& name) {

    return const_cast<ItemDeclarationNode*>(
        selectStructuralItem(
            static_cast<const AstNode&>(parent),
            name));
}

} // namespace qps::ast
