// qps/core/main.cpp

#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <stdexcept>
#include <sstream>

#include "tokens/h/lexer.hpp"
#include "parser/h/_index.hpp"
#include "ast/ast_node.hpp"
#include "visitors/ast_interface.hpp"
#include "visitors/h/print.hpp"
#include "utils.hpp"

namespace {

std::vector<std::string> splitPath(const std::string& path) {
    std::vector<std::string> segments;
    std::string current;

    for (char c : path) {
        if (c == '.') {
            if (current.empty()) {
                throw std::runtime_error(
                    "QPS query path contains an empty segment.");
            }
            segments.push_back(current);
            current.clear();
        } else {
            current.push_back(c);
        }
    }

    if (current.empty()) {
        throw std::runtime_error(
            "QPS query path contains an empty final segment.");
    }

    segments.push_back(current);
    return segments;
}

std::string scalarValue(
    const qps::ast::AstNode& node) {

    if (const auto* value =
            dynamic_cast<const qps::ast::StringLiteralNode*>(&node)) {
        return value->value_;
    }

    if (const auto* value =
            dynamic_cast<const qps::ast::NumericLiteralNode*>(&node)) {
        std::ostringstream out;
        out << value->value_;
        return out.str();
    }

    if (const auto* value =
            dynamic_cast<const qps::ast::BooleanLiteralNode*>(&node)) {
        return value->value_ ? "true" : "false";
    }

    if (dynamic_cast<const qps::ast::NullLiteralNode*>(&node)) {
        return "null";
    }

    throw std::runtime_error(
        "QPS query target is not a scalar value.");
}

const qps::ast::AstNode* findNamedChild(
    const std::vector<std::unique_ptr<qps::ast::AstNode>>& children,
    const std::string& name) {

    for (const auto& child : children) {
        if (const auto* key =
                dynamic_cast<const qps::ast::KeyDeclarationNode*>(
                    child.get())) {

            if (key->identifier_ == name) {
                return key;
            }
        }

        if (const auto* term =
                dynamic_cast<const qps::ast::TermDeclarationNode*>(
                    child.get())) {

            if (term->identifier_ == name) {
                return term;
            }
        }

        if (const auto* item =
                dynamic_cast<const qps::ast::ItemDeclarationNode*>(
                    child.get())) {

            const auto* identifier =
                dynamic_cast<const qps::ast::IdentifierNode*>(
                    item->getTarget());

            if (identifier && identifier->name_ == name) {
                return item;
            }
        }

        // Containers are structural grouping syntax, so descend
        // transparently when resolving a query path.
        if (const auto* container =
                dynamic_cast<const qps::ast::ContainerNode*>(
                    child.get())) {

            if (const auto* nested =
                    findNamedChild(container->elements, name)) {
                return nested;
            }
        }
    }

    return nullptr;
}

std::string queryProgram(
    const qps::ast::ProgramNode& program,
    const std::string& query_path) {

    const auto segments = splitPath(query_path);

    const qps::ast::AstNode* current =
        findNamedChild(
            program.statements,
            segments.front());

    if (!current) {
        throw std::runtime_error(
            "QPS query path not found: " + query_path);
    }

    for (std::size_t i = 1; i < segments.size(); ++i) {
        const auto& segment = segments[i];

        if (const auto* key =
                dynamic_cast<const qps::ast::KeyDeclarationNode*>(
                    current)) {

            current =
                findNamedChild(
                    key->content_,
                    segment);
        }
        else if (const auto* term =
                     dynamic_cast<const qps::ast::TermDeclarationNode*>(
                         current)) {

            current =
                findNamedChild(
                    term->content_,
                    segment);
        }
        else if (const auto* container =
                     dynamic_cast<const qps::ast::ContainerNode*>(
                         current)) {

            current =
                findNamedChild(
                    container->elements,
                    segment);
        }
        else {
            throw std::runtime_error(
                "QPS query cannot descend through path segment '" +
                segments[i - 1] + "'.");
        }

        if (!current) {
            throw std::runtime_error(
                "QPS query path not found: " + query_path);
        }
    }

    if (const auto* item =
            dynamic_cast<const qps::ast::ItemDeclarationNode*>(
                current)) {

        if (!item->value_node_) {
            throw std::runtime_error(
                "QPS query target Item has no value: " +
                query_path);
        }

        return scalarValue(*item->value_node_);
    }

    throw std::runtime_error(
        "QPS query target is structural, not a scalar Item: " +
        query_path);
}

} // namespace


int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " <source_file.qps> [--get path]"
            << std::endl;
        return 1;
    }

    const bool query_mode =
        argc == 4 &&
        std::string(argv[2]) == "--get";

    const bool check_mode =
        argc == 3 &&
        std::string(argv[2]) == "--check";

    if (argc != 2 && !query_mode && !check_mode) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " <source_file.qps> [--check | --get path]"
            << std::endl;
        return 1;
    }

    const std::string filepath = argv[1];

    try {
        const std::string source_code =
            qps::utils::readFileContents(filepath);

        if (!query_mode && !check_mode) {
            qps::utils::logMessage(
                "Successfully read file: " + filepath);
        }

        qps::tokens::CharStream char_stream(source_code);
        qps::tokens::Lexer lexer(char_stream);

        if (!query_mode && !check_mode) {
            qps::utils::logMessage(
                "Lexical analysis started.");
        }

        qps::parser::Parser parser(lexer);

        if (!query_mode && !check_mode) {
            qps::utils::logMessage(
                "Syntactic analysis (parsing) started.");
        }

        std::unique_ptr<qps::ast::ProgramNode> ast_root =
            parser.parseProgram();

        if (query_mode) {
            std::cout
                << queryProgram(
                       *ast_root,
                       argv[3])
                << std::endl;
            return 0;
        }

        if (check_mode) {
            return 0;
        }

        qps::utils::logMessage(
            "Parsing complete. AST generated.");

        qps::visitors::PrintVisitor printer;

        qps::utils::logMessage(
            "\n--- AST Representation ---");

        ast_root->accept(printer);

        qps::utils::logMessage(
            "--- AST Representation End ---");

        return 0;
    }
    catch (const std::runtime_error& e) {
        std::cerr
            << "Error: "
            << e.what()
            << std::endl;
        return 1;
    }
    catch (const std::exception& e) {
        std::cerr
            << "An unexpected error occurred: "
            << e.what()
            << std::endl;
        return 1;
    }
    catch (...) {
        std::cerr
            << "An unknown error occurred."
            << std::endl;
        return 1;
    }
}
