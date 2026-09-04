// qps/core/main.cpp

#include <iostream>
#include <string>
#include <type_traits>
#include <vector>
#include <memory>
#include <stdexcept>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <cstdio>
#include <array>

#include "tokens/h/lexer.hpp"
#include "parser/h/_index.hpp"
#include "ast/ast_node.hpp"
#include "runtime/h/test_suite.hpp"
#include "runtime/h/path_resolver.hpp"
#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/symbol_resolver.hpp"
#include "runtime/h/execution_engine.hpp"
#include "visitors/ast_interface.hpp"
#include "visitors/h/print.hpp"
#include "utils.hpp"

namespace {

namespace fs = std::filesystem;

bool programHasExecutionCall(
    const qps::ast::ProgramNode& program) {

    for (const auto& statement : program.statements) {
        if (dynamic_cast<
                const qps::ast::ExecutionCallNode*>(
                    statement.get())) {
            return true;
        }
    }

    return false;
}

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

std::unique_ptr<qps::ast::ProgramNode> parseFileQuiet(
    const std::string& filepath) {

    const std::string source_code =
        qps::utils::readFileContents(filepath);

    qps::tokens::CharStream char_stream(source_code);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);
    return parser.parseProgram();
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

std::string displayPath(const fs::path& path) {
    return path.generic_string();
}

bool isQpsFile(const fs::path& path) {
    return path.extension() == ".qps";
}

int lineOrOne(int line) {
    return line > 0 ? line : 1;
}

int extractLineFromMessage(const std::string& message) {
    const std::string marker = " at L";
    const std::size_t marker_pos = message.find(marker);

    if (marker_pos == std::string::npos) {
        return 1;
    }

    std::size_t pos = marker_pos + marker.size();
    int line = 0;

    while (pos < message.size() &&
           std::isdigit(static_cast<unsigned char>(message[pos]))) {
        line = (line * 10) + (message[pos] - '0');
        ++pos;
    }

    return lineOrOne(line);
}

std::string compactErrorMessage(const std::string& message) {
    if (message.empty()) {
        return "runtime error";
    }

    const std::string parse_prefix = "Parsing Error at L";
    if (message.rfind(parse_prefix, 0) == 0) {
        const std::size_t detail_pos = message.find(": ");
        if (detail_pos != std::string::npos) {
            return "parse error: " + message.substr(detail_pos + 2);
        }

        return "parse error";
    }

    return message;
}

std::string resultReason(const qps::runtime::TestResult& result) {
    if (!result.message.empty()) {
        return result.message;
    }

    switch (result.outcome) {
        case qps::runtime::TestOutcome::FAILED:
            return "test failed";
        case qps::runtime::TestOutcome::ERROR:
            return "runtime error";
        case qps::runtime::TestOutcome::PASSED:
            return "passed";
    }

    return "unknown test outcome";
}

std::vector<fs::path> collectQpsFiles(const fs::path& target) {
    if (!fs::exists(target)) {
        throw std::runtime_error(
            "QPS test target does not exist: " + displayPath(target));
    }

    if (fs::is_regular_file(target)) {
        if (!isQpsFile(target)) {
            throw std::runtime_error(
                "QPS test target is not a .qps file: " + displayPath(target));
        }

        return {target};
    }

    if (!fs::is_directory(target)) {
        throw std::runtime_error(
            "QPS test target is not a file or folder: " + displayPath(target));
    }

    std::vector<fs::path> files;

    for (const auto& entry : fs::recursive_directory_iterator(
             target,
             fs::directory_options::skip_permission_denied)) {
        if (!entry.is_regular_file()) {
            continue;
        }

        if (isQpsFile(entry.path())) {
            files.push_back(entry.path());
        }
    }

    std::sort(
        files.begin(),
        files.end(),
        [](const fs::path& left, const fs::path& right) {
            return left.generic_string() < right.generic_string();
        });

    return files;
}


enum class QuerySelectorKind {
    ITEM,
    TERM,
    KEY,
    FUNCTION,
    IDENTIFIER
};

struct QuerySelector {
    QuerySelectorKind kind;
    std::string identifier;
};

QuerySelector parseQuerySelector(const std::string& selector) {
    if (selector == "item-") {
        return {QuerySelectorKind::ITEM, ""};
    }
    if (selector == "term:") {
        return {QuerySelectorKind::TERM, ""};
    }
    if (selector == "key.") {
        return {QuerySelectorKind::KEY, ""};
    }
    if (selector == "-func") {
        return {QuerySelectorKind::FUNCTION, ""};
    }

    return {QuerySelectorKind::IDENTIFIER, selector};
}

std::string queryTargetIdentifier(const qps::ast::AstNode* target) {
    if (const auto* identifier =
            dynamic_cast<const qps::ast::IdentifierNode*>(target)) {
        return identifier->name_;
    }

    if (const auto* reference =
            dynamic_cast<const qps::ast::SymbolReferenceNode*>(target)) {
        return reference->getSymbol();
    }

    return "";
}

std::string itemIdentifier(const qps::ast::ItemDeclarationNode& item) {
    return queryTargetIdentifier(item.getTarget());
}

bool queryMatches(
    const qps::ast::AstNode& node,
    const QuerySelector& selector,
    std::string& identifier,
    std::string& suffix) {

    if (const auto* item =
            dynamic_cast<const qps::ast::ItemDeclarationNode*>(&node)) {
        identifier = itemIdentifier(*item);
        suffix = "-";

        if (identifier.empty()) {
            return false;
        }

        return selector.kind == QuerySelectorKind::ITEM ||
               (selector.kind == QuerySelectorKind::IDENTIFIER &&
                selector.identifier == identifier);
    }

    if (const auto* calculation =
            dynamic_cast<const qps::ast::CalculationNode*>(&node)) {
        identifier =
            queryTargetIdentifier(calculation->getTarget());
        suffix = ":";

        if (identifier.empty()) {
            return false;
        }

        return selector.kind == QuerySelectorKind::IDENTIFIER &&
               selector.identifier == identifier;
    }

    if (const auto* term =
            dynamic_cast<const qps::ast::TermDeclarationNode*>(&node)) {
        identifier = term->identifier_;
        suffix = ":";

        return selector.kind == QuerySelectorKind::TERM ||
               (selector.kind == QuerySelectorKind::IDENTIFIER &&
                selector.identifier == identifier);
    }

    if (const auto* key =
            dynamic_cast<const qps::ast::KeyDeclarationNode*>(&node)) {
        identifier = key->identifier_;
        suffix = ".";

        return selector.kind == QuerySelectorKind::KEY ||
               (selector.kind == QuerySelectorKind::IDENTIFIER &&
                selector.identifier == identifier);
    }

    if (const auto* function =
            dynamic_cast<const qps::ast::FunctionDeclarationNode*>(&node)) {
        identifier = function->name_;
        suffix = "";

        return selector.kind == QuerySelectorKind::FUNCTION ||
               (selector.kind == QuerySelectorKind::IDENTIFIER &&
                selector.identifier == identifier);
    }

    return false;
}

std::string joinSemanticPath(
    const std::vector<std::string>& ancestors,
    const std::string& leaf,
    const std::string& suffix) {

    std::ostringstream out;

    for (const auto& segment : ancestors) {
        if (!segment.empty()) {
            out << "." << segment;
        }
    }

    if (!leaf.empty()) {
        out << "." << leaf << suffix;
    }

    return out.str();
}

void queryWalkNode(
    const qps::ast::AstNode& node,
    const QuerySelector& selector,
    const fs::path& file,
    std::vector<std::string>& ancestors,
    std::vector<std::string>& results);

template <typename T, typename = void>
struct HasCausalSides : std::false_type {};

template <typename T>
struct HasCausalSides<
    T,
    std::void_t<
        decltype(std::declval<const T&>().sides_)
    >
> : std::true_type {};

template <typename T>
void queryWalkCausalRelationship(
    const T& relationship,
    const QuerySelector& selector,
    const fs::path& file,
    std::vector<std::string>& ancestors,
    std::vector<std::string>& results) {

    if constexpr (HasCausalSides<T>::value) {
        for (const auto& side : relationship.sides_) {
            if (!side) {
                continue;
            }

            if (side->entity) {
                queryWalkNode(
                    *side->entity,
                    selector,
                    file,
                    ancestors,
                    results);
            }

            for (const auto& domain : side->domain_chain) {
                if (domain) {
                    queryWalkNode(
                        *domain,
                        selector,
                        file,
                        ancestors,
                        results);
                }
            }
        }

        return;
    }
    else {
        const auto walk_legacy_side =
            [&](const auto* side) {

                if (!side) {
                    return;
                }

                if (side->entity) {
                    queryWalkNode(
                        *side->entity,
                        selector,
                        file,
                        ancestors,
                        results);
                }

                if (side->input) {
                    queryWalkNode(
                        *side->input,
                        selector,
                        file,
                        ancestors,
                        results);
                }

                if (side->output) {
                    queryWalkNode(
                        *side->output,
                        selector,
                        file,
                        ancestors,
                        results);
                }
            };

        walk_legacy_side(
            relationship.left_side_.get());

        walk_legacy_side(
            relationship.right_side_.get());
    }
}

void queryWalkNode(
    const qps::ast::AstNode& node,
    const QuerySelector& selector,
    const fs::path& file,
    std::vector<std::string>& ancestors,
    std::vector<std::string>& results) {

    std::string identifier;
    std::string suffix;

    if (queryMatches(node, selector, identifier, suffix)) {
        std::ostringstream result;
        result
            << displayPath(file)
            << joinSemanticPath(ancestors, identifier, suffix)
            << ":"
            << lineOrOne(node.getLine());

        results.push_back(result.str());
    }

    if (const auto* key =
            dynamic_cast<const qps::ast::KeyDeclarationNode*>(&node)) {
        ancestors.push_back(key->identifier_);
        for (const auto& child : key->content_) {
            queryWalkNode(
                *child, selector, file, ancestors, results);
        }
        ancestors.pop_back();
        return;
    }

    if (const auto* term =
            dynamic_cast<const qps::ast::TermDeclarationNode*>(&node)) {
        ancestors.push_back(term->identifier_);
        for (const auto& child : term->content_) {
            queryWalkNode(
                *child, selector, file, ancestors, results);
        }
        ancestors.pop_back();
        return;
    }

    if (const auto* container =
            dynamic_cast<const qps::ast::ContainerNode*>(&node)) {
        for (const auto& child : container->elements) {
            queryWalkNode(
                *child, selector, file, ancestors, results);
        }
        return;
    }

    if (const auto* dictionary =
            dynamic_cast<const qps::ast::DictionaryDeclarationNode*>(&node)) {
        for (const auto& entry : dictionary->entries) {
            if (entry && entry->value_node_) {
                queryWalkNode(
                    *entry->value_node_,
                    selector,
                    file,
                    ancestors,
                    results);
            }
        }
        return;
    }

    if (const auto* klass =
            dynamic_cast<const qps::ast::ClassDeclarationNode*>(&node)) {
        ancestors.push_back(klass->name_);
        for (const auto& member : klass->members) {
            queryWalkNode(
                *member, selector, file, ancestors, results);
        }
        ancestors.pop_back();
        return;
    }

    if (const auto* function =
            dynamic_cast<const qps::ast::FunctionDeclarationNode*>(&node)) {
        ancestors.push_back(function->name_);

        if (function->params_node_) {
            queryWalkNode(
                *function->params_node_,
                selector,
                file,
                ancestors,
                results);
        }

        if (function->body_) {
            queryWalkNode(
                *function->body_,
                selector,
                file,
                ancestors,
                results);
        }

        ancestors.pop_back();
        return;
    }

    if (const auto* execution =
            dynamic_cast<const qps::ast::ExecutionDefinitionNode*>(&node)) {
        ancestors.push_back(execution->identifier_);

        if (execution->body_) {
            queryWalkNode(
                *execution->body_,
                selector,
                file,
                ancestors,
                results);
        }

        ancestors.pop_back();
        return;
    }

    if (const auto* block =
            dynamic_cast<const qps::ast::ExecutionBlockNode*>(&node)) {
        for (const auto& statement : block->statements) {
            queryWalkNode(
                *statement,
                selector,
                file,
                ancestors,
                results);
        }
        return;
    }

    if (const auto* causal =
            dynamic_cast<const qps::ast::CausalDefinitionNode*>(&node)) {
        ancestors.push_back(causal->identifier_);

        for (const auto& relationship : causal->relationships) {
            queryWalkNode(
                *relationship,
                selector,
                file,
                ancestors,
                results);
        }

        ancestors.pop_back();
        return;
    }

    if (const auto* relationship =
            dynamic_cast<const qps::ast::CausalRelationshipNode*>(&node)) {

        queryWalkCausalRelationship(
            *relationship,
            selector,
            file,
            ancestors,
            results);

        return;
    }
}

void queryWalkProgram(
    const qps::ast::ProgramNode& program,
    const QuerySelector& selector,
    const fs::path& file,
    std::vector<std::string>& results) {

    std::vector<std::string> ancestors;

    for (const auto& statement : program.statements) {
        queryWalkNode(
            *statement,
            selector,
            file,
            ancestors,
            results);
    }
}



fs::path findCeOsRoot(fs::path start) {
    start = fs::absolute(start);

    while (true) {
        if (
            fs::exists(start / "_index.qps") &&
            fs::exists(
                start /
                "Engineering/py/cipher/cipher.py")) {
            return start;
        }

        const fs::path parent = start.parent_path();

        if (parent == start || parent.empty()) {
            break;
        }

        start = parent;
    }

    throw std::runtime_error(
        "Unable to locate CE-OS root for Cipher backend.");
}

int runCipherCommand(int argc, char* argv[]) {
    if (argc != 3 && argc != 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " cipher <source> [--report]"
            << std::endl;
        return 1;
    }

    if (
        argc == 4 &&
        std::string(argv[3]) != "--report") {

        std::cerr
            << "Usage: "
            << argv[0]
            << " cipher <source> [--report]"
            << std::endl;
        return 1;
    }

    try {
        const fs::path root =
            findCeOsRoot(fs::current_path());

        const fs::path source =
            fs::absolute(
                fs::path(argv[2]));

        const fs::path cipher_source =
            root / "qps/qps/cipher.qps";

        std::unique_ptr<qps::ast::ProgramNode>
            program =
                parseFileQuiet(
                    cipher_source.string());

        if (!program) {
            throw std::runtime_error(
                "QPS Cipher source produced no program.");
        }

        qps::runtime::ExecutionEngine engine;

        // Register authored Cipher definitions.
        (void)engine.execute(*program);

        std::unordered_map<
            std::string,
            qps::runtime::RuntimeValue
        > inputs;

        inputs.emplace(
            "source",
            qps::runtime::RuntimeValue::string(
                source.string()));

        inputs.emplace(
            "root",
            qps::runtime::RuntimeValue::string(
                root.string()));

        const std::string definition =
            argc == 4
                ? "Cipher_Report"
                : "Cipher_Run";

        (void)engine.instantiate(
            definition,
            inputs);

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr
            << "Error: "
            << e.what()
            << std::endl;
        return 1;
    }
}



int runBuildCommand(
    int argc,
    char* argv[]) {

    if (argc != 2) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " build"
            << std::endl;
        return 1;
    }

    try {
        const fs::path root =
            findCeOsRoot(
                fs::current_path());

        const fs::path build_source =
            root /
            "qps/qps/build.qps";

        std::unique_ptr<
            qps::ast::ProgramNode>
            program =
                parseFileQuiet(
                    build_source.string());

        if (!program) {
            throw std::runtime_error(
                "QPS build source produced no program.");
        }

        qps::runtime::ExecutionEngine engine;
        (void)engine.execute(*program);

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr
            << "Error: "
            << e.what()
            << std::endl;
        return 1;
    }
}


void printDirectoryTree(
    const fs::path& path,
    std::size_t current_depth,
    const std::optional<std::size_t>& max_depth) {

    if (
        max_depth.has_value() &&
        current_depth > *max_depth) {

        return;
    }

    std::vector<fs::directory_entry> entries;

    for (const auto& entry :
         fs::directory_iterator(path)) {

        entries.push_back(entry);
    }

    std::sort(
        entries.begin(),
        entries.end(),
        [](const auto& lhs, const auto& rhs) {
            return lhs.path().filename().string() <
                   rhs.path().filename().string();
        });

    for (const auto& entry : entries) {
        const std::string name =
            entry.path().filename().string();

        if (entry.is_directory()) {
            std::cout
                << name
                << ":(";

            const bool may_descend =
                !max_depth.has_value() ||
                current_depth < *max_depth;

            if (may_descend) {
                printDirectoryTree(
                    entry.path(),
                    current_depth + 1,
                    max_depth);
            }

            std::cout << ")";
        }
        else {
            std::cout
                << name
                << "-;";
        }
    }
}

int runDirectoryCommand(
    int argc,
    char* argv[]) {

    if (argc != 3 && argc != 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " dir <path> [depth]"
            << std::endl;
        return 1;
    }

    try {
        const fs::path target =
            fs::absolute(
                fs::path(argv[2]));

        if (!fs::exists(target)) {
            throw std::runtime_error(
                "Directory target does not exist: " +
                target.string());
        }

        if (!fs::is_directory(target)) {
            throw std::runtime_error(
                "Directory target is not a directory: " +
                target.string());
        }

        std::optional<std::size_t> max_depth;

        if (argc == 4) {
            const std::string depth_text =
                argv[3];

            std::size_t consumed = 0;

            const unsigned long parsed =
                std::stoul(
                    depth_text,
                    &consumed);

            if (consumed != depth_text.size()) {
                throw std::runtime_error(
                    "Directory depth must be a non-negative integer.");
            }

            max_depth =
                static_cast<std::size_t>(
                    parsed);
        }

        std::string root_name =
            target.filename().string();

        if (root_name.empty()) {
            root_name =
                target.root_name().string();

            if (root_name.empty()) {
                root_name = "root";
            }
        }

        std::cout
            << root_name
            << ".\n";

        if (
            !max_depth.has_value() ||
            *max_depth > 0) {

            printDirectoryTree(
                target,
                1,
                max_depth);

            std::cout << "\n\n";
        }
        else {
            // The Key already emitted its first newline.
            // One additional newline owns Key closure.
            std::cout << "\n";
        }

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr
            << "Error: "
            << e.what()
            << std::endl;
        return 1;
    }
}

int runQueryCommand(int argc, char* argv[]) {
    if (argc != 3 && argc != 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " qry <selector> [path/file.qps|path/folder]"
            << std::endl;
        return 1;
    }

    try {
        const QuerySelector selector =
            parseQuerySelector(argv[2]);

        const fs::path target =
            argc == 4
                ? fs::path(argv[3])
                : fs::current_path();

        const std::vector<fs::path> files =
            collectQpsFiles(target);

        std::vector<std::string> results;

        for (const auto& file : files) {
            std::unique_ptr<qps::ast::ProgramNode> ast_root =
                parseFileQuiet(file.string());

            queryWalkProgram(
                *ast_root,
                selector,
                file,
                results);
        }

        std::sort(results.begin(), results.end());

        for (const auto& result : results) {
            std::cout << result << "\n";
        }

        return 0;
    }
    catch (const std::exception& e) {
        std::cerr
            << "Error: "
            << e.what()
            << std::endl;
        return 1;
    }
}

bool runTestFile(
    const fs::path& file,
    bool& tested_any) {

    const std::string rendered_path = displayPath(file);

    try {
        std::unique_ptr<qps::ast::ProgramNode> ast_root =
            parseFileQuiet(file.string());

        qps::runtime::PathResolver paths(fs::current_path());
        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(loader);
        qps::runtime::SymbolResolver symbols(paths, documents);

        qps::runtime::TestSuiteRunner runner;
        qps::runtime::TestSuiteSummary summary =
            runner.run(*ast_root, &symbols, file);

        if (summary.total() == 0) {
            tested_any = true;
            std::cout << rendered_path << ": PASS\n";
            return true;
        }

        tested_any = true;

        if (summary.successful()) {
            std::cout << rendered_path << ": PASS\n";
            return true;
        }

        std::cout << rendered_path << ": FAIL\n";

        for (const auto& result : summary.results) {
            if (result.outcome == qps::runtime::TestOutcome::PASSED) {
                continue;
            }

            std::cout
                << rendered_path
                << ":"
                << lineOrOne(result.line)
                << " "
                << resultReason(result)
                << "\n";
        }

        return false;
    } catch (const std::exception& e) {
        tested_any = true;
        const std::string message = e.what();
        std::cout << rendered_path << ": FAIL\n";
        std::cout
            << rendered_path
            << ":"
            << extractLineFromMessage(message)
            << " "
            << compactErrorMessage(message)
            << "\n";
        return false;
    }
}

int runTestCommand(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " test <path/file.qps|path/folder>"
            << std::endl;
        return 1;
    }

    try {
        const fs::path target(argv[2]);
        const std::vector<fs::path> files = collectQpsFiles(target);

        bool successful = true;
        bool tested_any = false;
        const bool folder_target = fs::is_directory(target);

        if (folder_target) {
            for (const auto& file : files) {
                const std::string rendered_path = displayPath(file);

                try {
                    std::unique_ptr<qps::ast::ProgramNode> ast_root =
                        parseFileQuiet(file.string());

                    qps::runtime::PathResolver paths(fs::current_path());
                    qps::runtime::DocumentLoader loader;
                    qps::runtime::DocumentStore documents(loader);
                    qps::runtime::SymbolResolver symbols(paths, documents);

                    qps::runtime::TestSuiteRunner runner;
                    qps::runtime::TestSuiteSummary summary =
                        runner.run(*ast_root, &symbols, file);

                    tested_any = true;

                    if (!summary.successful() && summary.total() > 0) {
                        successful = false;

                        for (const auto& result : summary.results) {
                            if (result.outcome ==
                                qps::runtime::TestOutcome::PASSED) {
                                continue;
                            }

                            std::cout
                                << rendered_path
                                << ":"
                                << lineOrOne(result.line)
                                << " "
                                << resultReason(result)
                                << "\n";
                        }
                    }
                } catch (const std::exception& e) {
                    tested_any = true;
                    successful = false;

                    const std::string message = e.what();

                    std::cout
                        << rendered_path
                        << ":"
                        << extractLineFromMessage(message)
                        << " "
                        << compactErrorMessage(message)
                        << "\n";
                }
            }

            if (!tested_any) {
                std::cout << displayPath(target) << ": FAIL\n";
                std::cout << displayPath(target)
                          << ":1 no qps files discovered\n";
                return 1;
            }

            if (successful) {
                std::cout
                    << displayPath(target)
                    << ": PASS ("
                    << files.size()
                    << " files)\n";
                return 0;
            }

            std::cout << displayPath(target) << ": FAIL\n";
            return 1;
        }

        for (const auto& file : files) {
            if (!runTestFile(file, tested_any)) {
                successful = false;
            }
        }

        if (!tested_any) {
            std::cout << displayPath(target) << ": FAIL\n";
            std::cout << displayPath(target) << ":1 no qps files discovered\n";
            return 1;
        }

        return successful ? 0 : 1;
    } catch (const std::exception& e) {
        std::cerr
            << "Error: "
            << e.what()
            << std::endl;
        return 1;
    }
}

} // namespace


int main(int argc, char* argv[]) {
    if (argc >= 2 && std::string(argv[1]) == "build") {
        return runBuildCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "test") {
        return runTestCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "qry") {
        return runQueryCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "dir") {
        return runDirectoryCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "cipher") {
        return runCipherCommand(argc, argv);
    }

    if (argc < 2) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " <source_file.qps> [--check | --get path]\n"
            << "       "
            << argv[0]
            << " test <path/file.qps|path/folder>"
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
            << " <source_file.qps> [--check | --get path]\n"
            << "       "
            << argv[0]
            << " test <path/file.qps|path/folder>"
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

        if (programHasExecutionCall(*ast_root)) {
            qps::runtime::ExecutionEngine engine;
            (void)engine.execute(*ast_root);
            return 0;
        }

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
