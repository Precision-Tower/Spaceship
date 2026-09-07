// qps/core/src/ast/c/declarations.cpp

#include "../h/declarations.hpp" // Declarations specific header
#include "../h/statements.hpp" // For ExecutionBlockNode (used by Function/Class)
#include "../../visitors/ast_interface.hpp" // For AstVisitor acceptance
#include <utility> // For std::move

namespace qps {
namespace ast {

// --- Declarations Node Implementations ---

// ItemDeclarationNode
ItemDeclarationNode::ItemDeclarationNode(
    std::unique_ptr<AstNode> target,
    int line,
    int column)
    : AstNode(AstNodeType::ITEM_DECLARATION, line, column),
      target_(std::move(target)),
      value_node_(nullptr) {}

AstNode* ItemDeclarationNode::getTarget() const {
    return target_.get();
}

void ItemDeclarationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// TermDeclarationNode
TermDeclarationNode::TermDeclarationNode(const std::string& identifier, int line, int column)
    : AstNode(AstNodeType::TERM_DECLARATION, line, column), identifier_(identifier) {}

void TermDeclarationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// KeyDeclarationNode
KeyDeclarationNode::KeyDeclarationNode(const std::string& identifier, int line, int column)
    : AstNode(AstNodeType::KEY_DECLARATION, line, column), identifier_(identifier) {}

void KeyDeclarationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ContainerNode
ContainerNode::ContainerNode(int line, int column)
    : AstNode(AstNodeType::CONTAINER, line, column) {}

void ContainerNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// DictionaryEntryNode
DictionaryEntryNode::DictionaryEntryNode(int id, int line, int column)
    : AstNode(AstNodeType::DICTIONARY_DECLARATION, line, column), id_(id), value_node_(nullptr) {}

void DictionaryEntryNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// DictionaryDeclarationNode
DictionaryDeclarationNode::DictionaryDeclarationNode(int line, int column)
    : AstNode(AstNodeType::DICTIONARY_DECLARATION, line, column) {}

void DictionaryDeclarationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// CausalDefinitionNode
CausalDefinitionNode::CausalDefinitionNode(
    const std::string& identifier,
    int line,
    int column)
    : AstNode(AstNodeType::CAUSAL_DEFINITION, line, column),
      identifier_(identifier) {}

void CausalDefinitionNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// CausalRelationshipNode
const AstNode* CausalRelationshipNode::CausalSide::inputDomain() const {
    return domain_chain.empty()
        ? nullptr
        : domain_chain.front().get();
}

const AstNode* CausalRelationshipNode::CausalSide::outputDomain() const {
    return domain_chain.empty()
        ? nullptr
        : domain_chain.back().get();
}

CausalRelationshipNode::CausalRelationshipNode(
    std::vector<std::unique_ptr<CausalSide>> sides,
    int line,
    int column)
    : AstNode(AstNodeType::CAUSAL_RELATIONSHIP, line, column),
      sides_(std::move(sides)) {}

void CausalRelationshipNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// ClassDeclarationNode
ClassDeclarationNode::ClassDeclarationNode(const std::string& name, int line, int column)
    : AstNode(AstNodeType::CLASS_DECLARATION, line, column), name_(name) {}

void ClassDeclarationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

// FunctionDeclarationNode
FunctionDeclarationNode::FunctionDeclarationNode(const std::string& name, std::unique_ptr<AstNode> params_node,
                                               std::unique_ptr<ExecutionBlockNode> body, int line, int column)
    : AstNode(AstNodeType::FUNCTION_DECLARATION, line, column), name_(name),
      params_node_(std::move(params_node)), body_(std::move(body)) {}

void FunctionDeclarationNode::accept(visitors::AstVisitor& visitor) {
    visitor.visit(this);
}

} // namespace ast
} // namespace qps
