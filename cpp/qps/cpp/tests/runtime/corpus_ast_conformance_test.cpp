#include "../../core/src/ast/ast_node.hpp"
#include "../../core/src/visitors/ast_interface.hpp"
#include "../../core/src/parser/h/_index.hpp"
#include "../../core/src/tokens/h/char_stream.hpp"
#include "../../core/src/tokens/h/lexer.hpp"
#include "../../core/src/utils.hpp"

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <map>
#include <string>

namespace fs = std::filesystem;

namespace {

struct Profile {
    std::size_t programs = 0;
    std::size_t items = 0;
    std::size_t terms = 0;
    std::size_t keys = 0;
    std::size_t dictionaries = 0;
    std::size_t dictionary_entries = 0;
    std::size_t containers = 0;
    std::size_t causal_relationships = 0;
    std::size_t functions = 0;
    std::size_t classes = 0;

    std::size_t strings = 0;
    std::size_t numerics = 0;
    std::size_t booleans = 0;
    std::size_t nulls = 0;
    std::size_t path_references = 0;
    std::size_t symbol_references = 0;
    std::size_t index_path_references = 0;
    std::size_t non_index_path_references = 0;
    std::size_t identifiers = 0;
    std::size_t binary_expressions = 0;
    std::size_t function_calls = 0;
    std::size_t calculations = 0;

    std::size_t execution_blocks = 0;
    std::size_t execution_definitions = 0;
    std::size_t execution_calls = 0;
    std::size_t execution_actions = 0;

    std::size_t lets = 0;
    std::size_t sets = 0;
    std::size_t asserts = 0;
    std::size_t breaks = 0;
    std::size_t continues = 0;
    std::size_t elifs = 0;
    std::size_t elses = 0;
    std::size_t fors = 0;
    std::size_t ifs = 0;
    std::size_t loops = 0;
    std::size_t prints = 0;
    std::size_t returns = 0;
    std::size_t raises = 0;
    std::size_t tries = 0;
    std::size_t whiles = 0;
    std::size_t passes = 0;

    std::size_t items_without_target = 0;
    std::size_t empty_unit_hints = 0;

    std::map<std::string, std::size_t> units;
};

class ProfileVisitor final : public qps::visitors::AstVisitor {
public:
    Profile profile;

    void visit(qps::ast::ProgramNode* n) override {
        ++profile.programs;
        for (const auto& x : n->statements) x->accept(*this);
    }

    void visit(qps::ast::ItemDeclarationNode* n) override {
        ++profile.items;

        if (!n->target_) {
            ++profile.items_without_target;
        } else {
            n->target_->accept(*this);
        }

        if (n->unit_hint_) {
            if (n->unit_hint_->empty()) {
                ++profile.empty_unit_hints;
            } else {
                ++profile.units[*n->unit_hint_];
            }
        }

        if (n->value_node_) n->value_node_->accept(*this);
    }

    void visit(qps::ast::TermDeclarationNode* n) override {
        ++profile.terms;
        for (const auto& x : n->content_) x->accept(*this);
    }

    void visit(qps::ast::KeyDeclarationNode* n) override {
        ++profile.keys;
        for (const auto& x : n->content_) x->accept(*this);
    }

    void visit(qps::ast::DictionaryDeclarationNode* n) override {
        ++profile.dictionaries;
        for (const auto& x : n->entries) x->accept(*this);
    }

    void visit(qps::ast::DictionaryEntryNode* n) override {
        ++profile.dictionary_entries;
        if (n->value_node_) n->value_node_->accept(*this);
    }

    void visit(qps::ast::ContainerNode* n) override {
        ++profile.containers;
        for (const auto& x : n->elements) x->accept(*this);
    }

    void visit(qps::ast::CausalRelationshipNode* n) override {
        ++profile.causal_relationships;
        if (n->left_side_) {
            if (n->left_side_->entity) n->left_side_->entity->accept(*this);
            if (n->left_side_->input) n->left_side_->input->accept(*this);
            if (n->left_side_->output) n->left_side_->output->accept(*this);
        }
        if (n->right_side_) {
            if (n->right_side_->entity) n->right_side_->entity->accept(*this);
            if (n->right_side_->input) n->right_side_->input->accept(*this);
            if (n->right_side_->output) n->right_side_->output->accept(*this);
        }
    }

    void visit(qps::ast::FunctionDeclarationNode* n) override {
        ++profile.functions;
        if (n->params_node_) n->params_node_->accept(*this);
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::ClassDeclarationNode* n) override {
        ++profile.classes;
        for (const auto& x : n->members) x->accept(*this);
    }

    void visit(qps::ast::StringLiteralNode*) override { ++profile.strings; }
    void visit(qps::ast::NumericLiteralNode*) override { ++profile.numerics; }
    void visit(qps::ast::BooleanLiteralNode*) override { ++profile.booleans; }
    void visit(qps::ast::NullLiteralNode*) override { ++profile.nulls; }
    void visit(qps::ast::PathReferenceNode*) override { ++profile.path_references; }
    void visit(qps::ast::SymbolReferenceNode*) override { ++profile.symbol_references; }
    void visit(qps::ast::IdentifierNode*) override { ++profile.identifiers; }

    void visit(qps::ast::BinaryExpressionNode* n) override {
        ++profile.binary_expressions;
        if (n->getLeft()) n->getLeft()->accept(*this);
        if (n->getRight()) n->getRight()->accept(*this);
    }

    void visit(qps::ast::FunctionCallNode* n) override {
        ++profile.function_calls;
        for (const auto& x : n->arguments_) x->accept(*this);
    }

    void visit(qps::ast::CalculationNode* n) override {
        ++profile.calculations;
        if (n->hasTarget()) n->getTarget()->accept(*this);
        if (n->getExpression()) n->getExpression()->accept(*this);
    }

    void visit(qps::ast::ExecutionBlockNode* n) override {
        ++profile.execution_blocks;
        for (const auto& x : n->statements) x->accept(*this);
    }

    void visit(qps::ast::ExecutionDefinitionNode* n) override {
        ++profile.execution_definitions;
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::ExecutionCallNode* n) override {
        ++profile.execution_calls;
        for (const auto& x : n->arguments_) x->accept(*this);
    }

    void visit(qps::ast::ExecutionActionNode* n) override {
        ++profile.execution_actions;
        if (n->getSource()) n->getSource()->accept(*this);
        if (n->getParameters()) n->getParameters()->accept(*this);
    }

    void visit(qps::ast::LetStatementNode* n) override {
        ++profile.lets;
        if (n->initial_value_) n->initial_value_->accept(*this);
    }

    void visit(qps::ast::SetStatementNode* n) override {
        ++profile.sets;
        if (n->target_) n->target_->accept(*this);
        if (n->value_) n->value_->accept(*this);
    }

    void visit(qps::ast::AssertStatementNode* n) override {
        ++profile.asserts;
        if (n->condition_) n->condition_->accept(*this);
    }

    void visit(qps::ast::BreakStatementNode*) override { ++profile.breaks; }
    void visit(qps::ast::ContinueStatementNode*) override { ++profile.continues; }

    void visit(qps::ast::ElifStatementNode* n) override {
        ++profile.elifs;
        if (n->condition_) n->condition_->accept(*this);
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::ElseStatementNode* n) override {
        ++profile.elses;
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::ForStatementNode* n) override {
        ++profile.fors;
        if (n->loop_control_) n->loop_control_->accept(*this);
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::IfStatementNode* n) override {
        ++profile.ifs;
        if (n->condition_) n->condition_->accept(*this);
        if (n->body_) n->body_->accept(*this);
        for (const auto& x : n->elif_blocks_) x->accept(*this);
        if (n->else_block_) n->else_block_->accept(*this);
    }

    void visit(qps::ast::LoopStatementNode* n) override {
        ++profile.loops;
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::PrintStatementNode* n) override {
        ++profile.prints;
        if (n->expression_) n->expression_->accept(*this);
    }

    void visit(qps::ast::ReturnStatementNode* n) override {
        ++profile.returns;
        if (n->expression_) n->expression_->accept(*this);
    }

    void visit(qps::ast::RaiseStatementNode* n) override {
        ++profile.raises;
        if (n->message_) n->message_->accept(*this);
    }

    void visit(qps::ast::TryStatementNode* n) override {
        ++profile.tries;
        if (n->try_body_) n->try_body_->accept(*this);
    }

    void visit(qps::ast::WhileStatementNode* n) override {
        ++profile.whiles;
        if (n->condition_) n->condition_->accept(*this);
        if (n->body_) n->body_->accept(*this);
    }

    void visit(qps::ast::PassStatementNode*) override { ++profile.passes; }
};

} // namespace

int main(int argc, char** argv) {
    try {
        fs::path root;

        if (argc == 2) {
            root = fs::path(argv[1]);
        } else if (const char* env = std::getenv("CEOS_ROOT")) {
            root = fs::path(env);
        } else {
            root = fs::current_path();
        }

        root = fs::weakly_canonical(root);

        const fs::path corpus =
            root / "Engineering" / "qps";

        if (!fs::is_directory(corpus)) {
            std::cerr
                << "ERROR: Engineering QPS corpus not found: "
                << corpus
                << "\n";
            return EXIT_FAILURE;
        }

        ProfileVisitor visitor;
        std::size_t documents = 0;

        for (const auto& entry :
             fs::recursive_directory_iterator(corpus)) {

            if (!entry.is_regular_file()) {
                continue;
            }

            const auto& path = entry.path();

            if (path.extension() != ".qps") {
                continue;
            }

            bool archived = false;

            for (const auto& part : path) {
                if (part == "Archive") {
                    archived = true;
                    break;
                }
            }

            if (archived) {
                continue;
            }

            const std::string source =
                qps::utils::readFileContents(path.string());

            qps::tokens::CharStream stream(source);
            qps::tokens::Lexer lexer(stream);
            qps::parser::Parser parser(lexer);

            auto program = parser.parseProgram();

            if (!program) {
                throw std::runtime_error(
                    "Parser returned null ProgramNode for " +
                    path.string());
            }

            const std::size_t before_paths =
                visitor.profile.path_references;

            program->accept(visitor);

            const std::size_t document_paths =
                visitor.profile.path_references -
                before_paths;

            if (path.filename() == "_index.qps") {
                visitor.profile.index_path_references +=
                    document_paths;
            } else {
                visitor.profile.non_index_path_references +=
                    document_paths;
            }

            ++documents;
        }

        const auto& p = visitor.profile;

        if (documents == 0) {
            throw std::runtime_error(
                "No active Engineering QPS documents found.");
        }

        if (p.programs != documents) {
            throw std::runtime_error(
                "Program count does not match document count.");
        }

        if (p.items_without_target != 0) {
            throw std::runtime_error(
                "Active corpus contains Items without targets: " +
                std::to_string(p.items_without_target));
        }

        if (p.empty_unit_hints != 0) {
            throw std::runtime_error(
                "Active corpus contains empty authored unit hints: " +
                std::to_string(p.empty_unit_hints));
        }

        std::cout << "QPS ACTIVE CORPUS AST PROFILE\n\n";

        std::cout << "documents=" << documents << "\n";
        std::cout << "programs=" << p.programs << "\n";
        std::cout << "keys=" << p.keys << "\n";
        std::cout << "terms=" << p.terms << "\n";
        std::cout << "items=" << p.items << "\n";
        std::cout << "containers=" << p.containers << "\n";
        std::cout << "dictionaries=" << p.dictionaries << "\n";
        std::cout << "dictionary_entries="
                  << p.dictionary_entries << "\n";

        std::cout << "strings=" << p.strings << "\n";
        std::cout << "numerics=" << p.numerics << "\n";
        std::cout << "booleans=" << p.booleans << "\n";
        std::cout << "nulls=" << p.nulls << "\n";

        std::cout << "identifiers=" << p.identifiers << "\n";
        std::cout << "path_references="
                  << p.path_references << "\n";
        std::cout << "symbol_references="
                  << p.symbol_references << "\n";
        std::cout << "index_path_references="
                  << p.index_path_references << "\n";
        std::cout << "non_index_path_references="
                  << p.non_index_path_references << "\n";

        std::cout << "execution_definitions="
                  << p.execution_definitions << "\n";
        std::cout << "execution_calls="
                  << p.execution_calls << "\n";
        std::cout << "execution_actions="
                  << p.execution_actions << "\n";
        std::cout << "execution_blocks="
                  << p.execution_blocks << "\n";
        std::cout << "calculations="
                  << p.calculations << "\n";

        std::cout << "functions=" << p.functions << "\n";
        std::cout << "classes=" << p.classes << "\n";
        std::cout << "causal_relationships="
                  << p.causal_relationships << "\n";

        std::cout << "\nunits:\n";

        if (p.units.empty()) {
            std::cout << "  <none>\n";
        } else {
            for (const auto& [unit, count] : p.units) {
                std::cout
                    << "  "
                    << unit
                    << "="
                    << count
                    << "\n";
            }
        }

        std::cout
            << "\nQPS ACTIVE CORPUS AST CONFORMANCE OK\n";

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