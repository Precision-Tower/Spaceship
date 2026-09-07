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
#include <optional>
#include <fstream>
#include <cstdio>
#include <array>
#include <chrono>
#include <ctime>
#include <iomanip>

#include "ast/structural_selection.hpp"
#include "ast/scalar_query.hpp"
#include "ast/ast_node.hpp"
#include "runtime/h/test_suite.hpp"
#include "runtime/h/path_resolver.hpp"
#include "runtime/h/document_loader.hpp"
#include "runtime/h/document_store.hpp"
#include "runtime/h/symbol_resolver.hpp"
#include "runtime/h/execution_engine.hpp"
#include "runtime/h/execution_environment.hpp"
#include "runtime/h/resolution_environment.hpp"
#include "runtime/h/source_span.hpp"
#include "runtime/h/checklist_save_transition.hpp"
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

std::unique_ptr<qps::ast::ProgramNode> parseFileQuiet(
    const std::string& filepath) {

    qps::runtime::DocumentLoader loader;
    return loader.load(filepath);
}

fs::path authoredAuthority(
    const fs::path& index_file,
    const std::string& selector) {

    qps::runtime::DocumentLoader loader;

    std::unique_ptr<qps::ast::ProgramNode> program =
        loader.load(index_file);

    if (!program) {
        throw std::runtime_error(
            "QPS authority index produced no program: " +
            index_file.generic_string());
    }

    const std::string authored =
        qps::ast::queryScalar(
            *program,
            selector);

    if (authored.empty()) {
        throw std::runtime_error(
            "QPS authority is empty: " +
            selector);
    }

    return fs::path(authored);
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



std::optional<fs::path> findOutermostIndexedRoot(
    fs::path start) {

    start = fs::absolute(start).lexically_normal();

    std::optional<fs::path> outermost_indexed_ancestor;

    while (true) {
        if (fs::is_regular_file(start / "_index.qps")) {
            outermost_indexed_ancestor = start;
        }

        const fs::path parent = start.parent_path();

        if (parent == start || parent.empty()) {
            break;
        }

        start = parent;
    }

    return outermost_indexed_ancestor;
}

fs::path findCeOsRoot(fs::path start) {
    const auto root =
        findOutermostIndexedRoot(std::move(start));

    if (root.has_value()) {
        return *root;
    }

    throw std::runtime_error(
        "Unable to locate indexed CE-OS repository root.");
}

int runCipherCommand(int argc, char* argv[]) {
    const auto usage = [&]() {
        std::cerr
            << "Usage: "
            << argv[0]
            << " cipher <source> [destination] [--report]\n"
            << "       "
            << argv[0]
            << " cipher test <source> [destination]"
            << std::endl;
    };

    const bool preflight =
        argc >= 3 &&
        std::string(argv[2]) == "test";

    if (preflight) {
        if (argc != 4 && argc != 5) {
            usage();
            return 1;
        }

        try {
            const fs::path root =
                findCeOsRoot(fs::current_path());

            const fs::path source =
                fs::absolute(
                    fs::path(argv[3]));

            std::optional<fs::path>
                preflight_destination;

            if (argc == 5) {
                preflight_destination =
                    fs::absolute(
                        fs::path(argv[4]));
            }

            const fs::path cipher_source =
                root / authoredAuthority(
                    root / "_index.qps",
                    "qps.cipher_authority-");

            std::unique_ptr<qps::ast::ProgramNode>
                program =
                    parseFileQuiet(
                        cipher_source.string());

            if (!program) {
                throw std::runtime_error(
                    "QPS Cipher source produced no program.");
            }

            qps::runtime::ExecutionEngine engine;
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
                preflight_destination.has_value()
                    ? "Cipher_Test_To"
                    : "Cipher_Test";

            if (preflight_destination.has_value()) {
                inputs.emplace(
                    "destination",
                    qps::runtime::RuntimeValue::string(
                        preflight_destination->string()));
            }

            const auto result =
                engine.instantiate(
                    definition,
                    inputs);

            if (
                result.result.has_value() &&
                result.result->isNumeric()) {

                return static_cast<int>(
                    result.result->asNumber(
                        "Cipher test exit code"));
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

    if (argc < 3 || argc > 5) {
        usage();
        return 1;
    }

    bool report = false;
    bool closure = false;
    std::optional<fs::path> destination;

    for (int i = 3; i < argc; ++i) {
        const std::string argument(argv[i]);

        if (argument == "--report") {
            if (report || closure) {
                usage();
                return 1;
            }

            report = true;
            continue;
        }

        if (argument == "--closure") {
            if (closure || report || destination.has_value()) {
                usage();
                return 1;
            }

            closure = true;
            continue;
        }

        if (destination.has_value()) {
            usage();
            return 1;
        }

        destination =
            fs::absolute(
                fs::path(argument));
    }

    try {
        const fs::path root =
            findCeOsRoot(fs::current_path());

        const fs::path source =
            fs::absolute(
                fs::path(argv[2]));

        const fs::path cipher_source =
            root / authoredAuthority(
                root / "_index.qps",
                "qps.cipher_authority-");

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

        if (destination.has_value()) {
            inputs.emplace(
                "destination",
                qps::runtime::RuntimeValue::string(
                    destination->string()));
        }

        std::string definition;

        if (closure) {
            definition = "Cipher_Closure";
        }
        else if (destination.has_value() && report) {
            definition = "Cipher_Report_To";
        }
        else if (destination.has_value()) {
            definition = "Cipher_Run_To";
        }
        else if (report) {
            definition = "Cipher_Report";
        }
        else {
            definition = "Cipher_Run";
        }

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
            root / authoredAuthority(
                root / "_index.qps",
                "qps.build_authority");

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





std::string qpsQuoted(
    const std::string& value) {

    std::string result;
    result.reserve(value.size() + 2);
    result.push_back('"');

    for (const char c : value) {
        switch (c) {
            case '\\':
                result += "\\\\";
                break;

            case '"':
                result += "\\\"";
                break;

            case '\n':
                result += "\\n";
                break;

            case '\r':
                result += "\\r";
                break;

            case '\t':
                result += "\\t";
                break;

            default:
                result.push_back(c);
                break;
        }
    }

    result.push_back('"');
    return result;
}


std::vector<std::pair<std::string, std::string>>
collectScalarSurface(
    const qps::ast::ProgramNode& program,
    const std::string& base) {

    const qps::ast::AstNode* surface =
        qps::ast::selectStructuralPath(
            program,
            base);

    if (!surface) {
        throw std::runtime_error(
            "Required QPS structural surface not found: " +
            base);
    }

    std::vector<std::pair<std::string, std::string>>
        result;

    for (const auto* member :
         qps::ast::structuralScope(*surface)) {

        const auto* item =
            dynamic_cast<
                const qps::ast::ItemDeclarationNode*>(
                    member);

        if (!item) {
            throw std::runtime_error(
                "Save surface '" +
                base +
                "' must contain scalar Items only.");
        }

        const auto* target =
            dynamic_cast<
                const qps::ast::IdentifierNode*>(
                    item->getTarget());

        if (!target) {
            throw std::runtime_error(
                "Save surface '" +
                base +
                "' contains a non-identifier Item.");
        }

        result.emplace_back(
            target->name_,
            qps::ast::queryScalar(
                program,
                base + "." + target->name_ + "-"));
    }

    return result;
}


std::string utcSaveTimestamp() {

    const auto now =
        std::chrono::system_clock::now();

    const std::time_t raw =
        std::chrono::system_clock::to_time_t(now);

    std::tm utc{};

#if defined(_WIN32)
    gmtime_s(&utc, &raw);
#else
    gmtime_r(&raw, &utc);
#endif

    std::ostringstream out;
    out << std::put_time(
        &utc,
        "%Y-%m-%dT%H:%M:%SZ");

    return out.str();
}


std::string historyStructuralKey() {

    const auto now =
        std::chrono::system_clock::now();

    const auto milliseconds =
        std::chrono::duration_cast<
            std::chrono::milliseconds>(
                now.time_since_epoch())
            .count() % 1000;

    const std::time_t raw =
        std::chrono::system_clock::to_time_t(now);

    std::tm utc{};

#if defined(_WIN32)
    gmtime_s(&utc, &raw);
#else
    gmtime_r(&raw, &utc);
#endif

    std::ostringstream out;

    out
        << "h_"
        << std::put_time(
               &utc,
               "%Y%m%d_%H%M%S")
        << "_"
        << std::setw(3)
        << std::setfill('0')
        << milliseconds;

    return out.str();
}


std::string renderHistorySurface(
    const std::string& name,
    const std::vector<
        std::pair<std::string, std::string>>& items) {

    std::ostringstream out;

    out
        << name
        << ": (\n";

    for (const auto& item : items) {
        out
            << item.first
            << "- "
            << qpsQuoted(item.second)
            << ";\n";
    }

    out << ");\n";

    return out.str();
}


bool historyContainsIdentity(
    const qps::ast::ProgramNode& history,
    const std::string& identity) {

    const qps::ast::AstNode* entries =
        qps::ast::selectStructuralPath(
            history,
            "entries");

    if (!entries) {
        throw std::runtime_error(
            "History ledger has no entries surface.");
    }

    for (const auto* member :
         qps::ast::structuralScope(*entries)) {

        const auto* entry =
            dynamic_cast<
                const qps::ast::TermDeclarationNode*>(
                    member);

        if (!entry) {
            continue;
        }

        const std::string base =
            "entries." +
            entry->identifier_;

        const std::string existing =
            qps::ast::queryScalar(
                history,
                base + ".identity-");

        if (existing == identity) {
            return true;
        }
    }

    return false;
}


int runSaveCommand(
    int argc,
    char* argv[]) {

    if (argc != 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " save <checklist-index> <task-number>"
            << std::endl;
        return 1;
    }

    try {
        const fs::path workspace =
            findCeOsRoot(
                fs::current_path());

        std::size_t checklist_consumed = 0;
        const std::string checklist_text(
            argv[2]);

        const unsigned long checklist_index =
            std::stoul(
                checklist_text,
                &checklist_consumed);

        if (
            checklist_consumed !=
                checklist_text.size() ||
            checklist_index == 0) {

            throw std::runtime_error(
                "Checklist index must be a positive integer.");
        }

        std::size_t task_consumed = 0;
        const std::string task_text(
            argv[3]);

        const unsigned long task_number =
            std::stoul(
                task_text,
                &task_consumed);

        if (
            task_consumed !=
                task_text.size() ||
            task_number == 0) {

            throw std::runtime_error(
                "Task number must be a positive integer.");
        }

        /*
         * Duplicate semantic identity is a public Save precondition.
         *
         * Resolve the indexed Checklist through the authored Checklist
         * authority rather than duplicating its filesystem/index policy in
         * native code. Checklist_Path is the authored public path-resolution query;
         * native code only consumes its returned path and checks the existing
         * root History ledger before entering the mutation transaction.
         */
        const fs::path checklist_source =
            workspace / authoredAuthority(
                workspace / "_index.qps",
                "qps.checklist_authority-");

        qps::runtime::PathResolver checklist_paths(
            workspace);

        const auto checklist_module =
            checklist_paths.containingModule(
                checklist_source);

        if (!checklist_module.has_value()) {
            throw std::runtime_error(
                "Checklist authority is not inside a connected QPS module.");
        }

        qps::runtime::DocumentLoader validation_loader;
        qps::runtime::DocumentStore validation_documents(
            validation_loader);
        qps::runtime::ExecutionEngine validation_engine;
        qps::runtime::ExecutionEnvironment validation_environment(
            checklist_paths,
            validation_documents,
            validation_engine);

        validation_environment.loadModule(
            *checklist_module);

        std::unordered_map<
            std::string,
            qps::runtime::RuntimeValue
        > checklist_inputs;

        checklist_inputs.emplace(
            "root",
            qps::runtime::RuntimeValue::string(
                workspace.string()));

        checklist_inputs.emplace(
            "checklist_index",
            qps::runtime::RuntimeValue::numeric(
                static_cast<double>(
                    checklist_index)));

        const auto checklist_result =
            validation_engine.instantiate(
                "Checklist_Path",
                checklist_inputs);

        if (!checklist_result.result.has_value()) {
            throw std::runtime_error(
                "Checklist authority returned no selected path.");
        }

        const fs::path selected_checklist =
            workspace /
            checklist_result.result->asString(
                "Checklist_Path result");

        const auto checklist_program =
            validation_loader.load(
                selected_checklist);

        if (!checklist_program) {
            throw std::runtime_error(
                "Selected Checklist produced no program.");
        }

        const std::string selected_task_name =
            "task_" + std::to_string(task_number);

        const std::string task_base =
            "current_work.tasks." +
            selected_task_name;

        const qps::ast::AstNode* selected_task =
            qps::ast::selectStructuralPath(
                *checklist_program,
                task_base);

        if (!selected_task) {
            throw std::runtime_error(
                "Selected Checklist task was not found.");
        }

        const std::string task_identity =
            qps::ast::queryScalar(
                *checklist_program,
                task_base + ".identity-");

        if (task_identity.empty()) {
            throw std::runtime_error(
                "Selected Checklist task has no semantic identity.");
        }

        const auto history_program =
            validation_loader.load(
                workspace / "history.qps");

        if (!history_program) {
            throw std::runtime_error(
                "History ledger produced no program.");
        }

        if (historyContainsIdentity(
                *history_program,
                task_identity)) {

            throw std::runtime_error(
                "Save rejected duplicate accepted identity: " +
                task_identity);
        }

        const fs::path save_source =
            workspace / authoredAuthority(
                workspace / "_index.qps",
                "qps.save_authority-");

        qps::runtime::PathResolver paths(
            workspace);

        const auto module =
            paths.containingModule(
                save_source);

        if (!module.has_value()) {
            throw std::runtime_error(
                "Save authority is not inside a connected QPS module.");
        }

        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(
            loader);

        qps::runtime::ExecutionEngine engine;

        qps::runtime::ExecutionEnvironment environment(
            paths,
            documents,
            engine);

        environment.loadModule(
            *module);

        std::unordered_map<
            std::string,
            qps::runtime::RuntimeValue
        > inputs;

        inputs.emplace(
            "root",
            qps::runtime::RuntimeValue::string(
                workspace.string()));

        inputs.emplace(
            "checklist_index",
            qps::runtime::RuntimeValue::numeric(
                static_cast<double>(
                    checklist_index)));

        inputs.emplace(
            "task_name",
            qps::runtime::RuntimeValue::string(
                "task_" +
                std::to_string(
                    task_number)));

        (void)engine.instantiate(
            "Save_Accept",
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


bool historyScopeMatches(
    const std::string& requested,
    const std::string& scope) {

    if (requested.empty()) {
        return true;
    }

    if (scope == requested) {
        return true;
    }

    if (scope.size() <= requested.size()) {
        return false;
    }

    if (scope.compare(
            0,
            requested.size(),
            requested) != 0) {

        return false;
    }

    return scope[requested.size()] == '/';
}


int runHistoryCommand(
    int argc,
    char* argv[]) {

    if (argc < 2 || argc > 3) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " history [path]"
            << std::endl;
        return 1;
    }

    try {
        const fs::path workspace =
            findCeOsRoot(
                fs::current_path());

        const fs::path history_path =
            workspace / "history.qps";

        qps::runtime::DocumentLoader loader;

        const auto history =
            loader.load(
                history_path);

        if (!history) {
            throw std::runtime_error(
                "History ledger produced no program.");
        }

        const qps::ast::AstNode* entries =
            qps::ast::selectStructuralPath(
                *history,
                "entries");

        if (!entries) {
            throw std::runtime_error(
                "History ledger has no entries surface.");
        }

        std::string requested;

        if (argc == 3) {
            requested =
                fs::path(argv[2])
                    .lexically_normal()
                    .generic_string();

            while (
                requested.size() > 1 &&
                requested.back() == '/') {

                requested.pop_back();
            }

            if (requested == ".") {
                requested.clear();
            }
        }

        for (const auto* member :
             qps::ast::structuralScope(*entries)) {

            const auto* entry =
                dynamic_cast<
                    const qps::ast::TermDeclarationNode*>(
                    member);

            if (!entry) {
                continue;
            }

            const std::string base =
                "entries." +
                entry->identifier_;

            bool associated =
                requested.empty();

            const qps::ast::AstNode* scope =
                qps::ast::selectStructuralPath(
                    *history,
                    base + ".scope");

            if (!associated && scope) {
                for (const auto* scope_member :
                     qps::ast::structuralScope(*scope)) {

                    const auto* item =
                        dynamic_cast<
                            const qps::ast::ItemDeclarationNode*>(
                            scope_member);

                    if (!item) {
                        continue;
                    }

                    const auto* target =
                        dynamic_cast<
                            const qps::ast::IdentifierNode*>(
                            item->getTarget());

                    if (!target) {
                        continue;
                    }

                    const std::string scope_path =
                        qps::ast::queryScalar(
                            *history,
                            base +
                                ".scope." +
                                target->name_ +
                                "-");

                    if (historyScopeMatches(
                            requested,
                            scope_path)) {

                        associated = true;
                        break;
                    }
                }
            }

            if (!associated) {
                continue;
            }

            const std::string timestamp =
                qps::ast::queryScalar(
                    *history,
                    base + ".timestamp-");

            const std::string identity =
                qps::ast::queryScalar(
                    *history,
                    base + ".identity-");

            const std::string summary =
                qps::ast::queryScalar(
                    *history,
                    base + ".summary-");

            std::cout
                << timestamp
                << "  "
                << identity
                << "  "
                << summary
                << "\n";
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


int runChecklistCommand(
    int argc,
    char* argv[]) {

    if (argc < 2 || argc > 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " checklist [checklist-index] [task-number]"
            << std::endl;
        return 1;
    }

    try {
        const fs::path workspace =
            findCeOsRoot(
                fs::current_path());

        const fs::path checklist_source =
            workspace / authoredAuthority(
                workspace / "_index.qps",
                "qps.checklist_authority-");

        qps::runtime::PathResolver paths(
            workspace);

        const auto module =
            paths.containingModule(
                checklist_source);

        if (!module.has_value()) {
            throw std::runtime_error(
                "Checklist authority is not inside a connected QPS module.");
        }

        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(
            loader);

        qps::runtime::ExecutionEngine engine;

        qps::runtime::ExecutionEnvironment environment(
            paths,
            documents,
            engine);

        environment.loadModule(
            *module);

        std::unordered_map<
            std::string,
            qps::runtime::RuntimeValue
        > inputs;

        inputs.emplace(
            "root",
            qps::runtime::RuntimeValue::string(
                workspace.string()));

        std::string definition =
            "Checklist_List";

        if (argc >= 3) {
            std::size_t consumed = 0;

            const std::string checklist_text(
                argv[2]);

            const unsigned long checklist_index =
                std::stoul(
                    checklist_text,
                    &consumed);

            if (consumed != checklist_text.size() ||
                checklist_index == 0) {

                throw std::runtime_error(
                    "Checklist index must be a positive integer.");
            }

            inputs.emplace(
                "checklist_index",
                qps::runtime::RuntimeValue::numeric(
                    static_cast<double>(
                        checklist_index)));

            definition =
                "Checklist_Show";
        }

        if (argc == 4) {
            std::size_t consumed = 0;

            const std::string task_text(
                argv[3]);

            const unsigned long task_number =
                std::stoul(
                    task_text,
                    &consumed);

            if (consumed != task_text.size() ||
                task_number == 0) {

                throw std::runtime_error(
                    "Task number must be a positive integer.");
            }

            inputs.emplace(
                "task_name",
                qps::runtime::RuntimeValue::string(
                    "task_" +
                    std::to_string(
                        task_number)));

            definition =
                "Checklist_Show_Task";
        }

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


int runScoutCommand(
    int argc,
    char* argv[]) {

    if (argc != 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " scout <indexed-module> <structural-name>"
            << std::endl;
        return 1;
    }

    try {
        const fs::path requested =
            fs::absolute(fs::path(argv[2]));

        fs::path module;

        if (fs::is_regular_file(requested) &&
            requested.filename() == "_index.qps") {

            module = requested.parent_path();
        }
        else if (fs::is_directory(requested)) {
            module = requested;
        }
        else {
            throw std::runtime_error(
                "Scout target must be a QPS module directory "
                "or its _index.qps.");
        }

        if (!fs::is_regular_file(module / "_index.qps")) {
            throw std::runtime_error(
                "Scout requires an indexed QPS module: " +
                module.string());
        }

        /*
         * The selected module is the scout boundary.
         *
         * PathResolver sees it as its workspace root, so qpsFiles(".")
         * can enumerate only immediate authored documents. Scout does
         * not descend child modules or recursively search the filesystem.
         */
        qps::runtime::PathResolver paths(module);
        qps::runtime::DocumentLoader loader;
        qps::runtime::DocumentStore documents(loader);

        std::vector<qps::runtime::SourceSpan> spans;
        std::size_t unreadable_documents = 0;

        for (const auto& relative : paths.qpsFiles(".")) {
            const fs::path absolute =
                paths.resolveFile(relative);

            try {
                const auto document =
                    documents.get(absolute);

                const auto matches =
                    qps::ast::scoutStructuralName(
                        *document,
                        argv[3]);

                for (const auto* selected : matches) {
                    const std::size_t line =
                        static_cast<std::size_t>(
                            lineOrOne(
                                selected->getLine()));

                    spans.push_back(
                        {absolute, line, line});
                }
            }
            catch (const std::exception&) {
                /*
                 * Scout is document-bounded reconnaissance.
                 *
                 * One document that the current parser cannot consume must
                 * not erase valid evidence from other immediate documents.
                 *
                 * We intentionally keep stdout evidence-only. If no match
                 * exists anywhere, unreadable document count is surfaced in
                 * the terminal error so a negative result is not overstated.
                 */
                ++unreadable_documents;
            }
        }

        if (spans.empty()) {
            std::string message =
                "QPS scout found no authored identity '" +
                std::string(argv[3]) +
                "' in the immediate indexed module.";

            if (unreadable_documents > 0) {
                message +=
                    " Unreadable documents: " +
                    std::to_string(unreadable_documents) +
                    ".";
            }

            throw std::runtime_error(message);
        }

        std::cout
            << qps::runtime::renderSourceSpans(
                module,
                spans);

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


std::size_t ownedStructuralEndLine(
    const qps::ast::AstNode& node) {

    if (const auto* key =
            dynamic_cast<
                const qps::ast::KeyDeclarationNode*>(
                    &node)) {

        return static_cast<std::size_t>(
            lineOrOne(
                key->getEndLine()));
    }

    if (const auto* term =
            dynamic_cast<
                const qps::ast::TermDeclarationNode*>(
                    &node)) {

        return static_cast<std::size_t>(
            lineOrOne(
                term->getEndLine()));
    }

    if (const auto* item =
            dynamic_cast<
                const qps::ast::ItemDeclarationNode*>(
                    &node)) {

        return static_cast<std::size_t>(
            lineOrOne(
                item->getEndLine()));
    }

    return static_cast<std::size_t>(
        lineOrOne(
            node.getLine()));
}


int runScopeCommand(
    int argc,
    char* argv[]) {

    if (argc != 4) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " scope <file.qps> <structural.path>"
            << std::endl;
        return 1;
    }

    try {
        const fs::path target =
            fs::absolute(fs::path(argv[2]));

        if (!fs::exists(target) ||
            !fs::is_regular_file(target)) {

            throw std::runtime_error(
                "Scope target is not a file: " +
                target.string());
        }

        if (target.extension() != ".qps") {
            throw std::runtime_error(
                "Scope requires a .qps document.");
        }

        qps::runtime::DocumentLoader loader;
        const auto document = loader.load(target);

        const qps::ast::AstNode* selected =
            qps::ast::selectStructuralPath(
                *document,
                argv[3]);

        if (!selected) {
            throw std::runtime_error(
                "QPS scope path not found: " +
                std::string(argv[3]));
        }

        std::vector<qps::runtime::SourceSpan> spans;

        const auto add =
            [&](const qps::ast::AstNode& node) {
                const std::size_t first =
                    static_cast<std::size_t>(
                        lineOrOne(node.getLine()));

                const std::size_t last =
                    ownedStructuralEndLine(node);

                spans.push_back(
                    {target, first, last});
            };

        add(*selected);

        for (const auto* member :
             qps::ast::structuralScope(*selected)) {
            add(*member);
        }

        std::cout
            << qps::runtime::renderSourceSpans(
                fs::current_path(),
                spans);

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


int runProbeCommand(
    int argc,
    char* argv[]) {

    if (argc != 4 && argc != 5) {
        std::cerr
            << "Usage: "
            << argv[0]
            << " probe <file> <line> [radius]"
            << std::endl;
        return 1;
    }

    try {
        const fs::path target =
            fs::absolute(
                fs::path(argv[2]));

        if (!fs::exists(target)) {
            throw std::runtime_error(
                "Probe target does not exist: " +
                target.string());
        }

        if (!fs::is_regular_file(target)) {
            throw std::runtime_error(
                "Probe target is not a file: " +
                target.string());
        }

        const std::string probe_target = argv[3];

        const bool qps_semantic_probe =
            target.extension() == ".qps" &&
            probe_target.find_first_not_of("0123456789") !=
                std::string::npos;

        if (qps_semantic_probe) {
            if (argc != 4) {
                throw std::runtime_error(
                    "Semantic QPS probe does not accept a radius.");
            }

            qps::runtime::DocumentLoader loader;
            const auto document =
                loader.load(target);

            const qps::ast::AstNode* selected =
                qps::ast::selectStructuralPath(
                    *document,
                    probe_target);

            if (!selected) {
                throw std::runtime_error(
                    "QPS probe path not found: " +
                    probe_target);
            }

            const std::size_t first =
                static_cast<std::size_t>(
                    lineOrOne(
                        selected->getLine()));

            const std::size_t last =
                ownedStructuralEndLine(
                    *selected);

            const std::vector<qps::runtime::SourceSpan> spans{
                {target, first, last}
            };

            std::cout
                << qps::runtime::renderSourceSpans(
                    fs::current_path(),
                    spans);

            return 0;
        }

        const auto parse_non_negative =
            [](const std::string& text,
               const std::string& label)
                -> std::size_t {

                std::size_t consumed = 0;

                const unsigned long value =
                    std::stoul(
                        text,
                        &consumed);

                if (consumed != text.size()) {
                    throw std::runtime_error(
                        label +
                        " must be a non-negative integer.");
                }

                return
                    static_cast<std::size_t>(
                        value);
            };

        const std::size_t center =
            parse_non_negative(
                argv[3],
                "Probe line");

        if (center == 0) {
            throw std::runtime_error(
                "Probe line must be greater than zero.");
        }

        const std::size_t radius =
            argc == 5
                ? parse_non_negative(
                    argv[4],
                    "Probe radius")
                : 10;

        std::ifstream input(target);

        if (!input) {
            throw std::runtime_error(
                "Unable to open probe target: " +
                target.string());
        }

        std::size_t line_count = 0;
        std::string line;

        while (std::getline(input, line)) {
            ++line_count;
        }

        if (center > line_count) {
            throw std::runtime_error(
                "Probe line exceeds file length.");
        }

        const std::size_t first =
            center > radius
                ? center - radius
                : 1;

        const std::size_t last =
            std::min(
                line_count,
                center + radius);

        const std::vector<qps::runtime::SourceSpan> spans{
            {target, first, last}
        };

        std::cout
            << qps::runtime::renderSourceSpans(
                fs::current_path(),
                spans);

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

        const fs::path root =
            findCeOsRoot(fs::current_path());

        qps::runtime::ResolutionEnvironment resolution(
            fs::current_path(),
            root / authoredAuthority(
                root / "_index.qps",
                "qps.reference_document_authority"),
            root / authoredAuthority(
                root / "_index.qps",
                "qps.semantic_walk_authority"));

        qps::runtime::TestSuiteRunner runner;
        qps::runtime::TestSuiteSummary summary =
            runner.run(
                *ast_root,
                &resolution.symbols(),
                file);

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

                    const fs::path root =
                        findCeOsRoot(fs::current_path());

                    qps::runtime::ResolutionEnvironment resolution(
                        fs::current_path(),
                        root / authoredAuthority(
                            root / "_index.qps",
                            "qps.reference_document_authority"),
                        root / authoredAuthority(
                            root / "_index.qps",
                            "qps.semantic_walk_authority"));

                    qps::runtime::TestSuiteRunner runner;
                    qps::runtime::TestSuiteSummary summary =
                        runner.run(
                            *ast_root,
                            &resolution.symbols(),
                            file);

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

    if (argc >= 2 && std::string(argv[1]) == "probe") {
        return runProbeCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "scope") {
        return runScopeCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "scout") {
        return runScoutCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "cipher") {
        return runCipherCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "checklist") {
        return runChecklistCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "history") {
        return runHistoryCommand(argc, argv);
    }

    if (argc >= 2 && std::string(argv[1]) == "save") {
        return runSaveCommand(argc, argv);
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
        if (!query_mode && !check_mode) {
            qps::utils::logMessage(
                "Loading QPS document: " + filepath);
        }

        qps::runtime::DocumentLoader loader;
        std::unique_ptr<qps::ast::ProgramNode> ast_root =
            loader.load(filepath);

        if (!query_mode && !check_mode) {
            qps::utils::logMessage(
                "Parsing complete. AST generated.");
        }

        if (query_mode) {
            std::cout
                << qps::ast::queryScalar(
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

            const fs::path source =
                fs::absolute(filepath).lexically_normal();

            const auto indexed_root =
                findOutermostIndexedRoot(
                    source.parent_path());

            if (indexed_root.has_value()) {
                qps::runtime::PathResolver paths(
                    *indexed_root);

                const auto module =
                    paths.containingModule(source);

                if (module.has_value()) {
                    qps::runtime::DocumentLoader loader;
                    qps::runtime::DocumentStore documents(loader);

                    qps::runtime::ExecutionEnvironment environment(
                        paths,
                        documents,
                        engine);

                    environment.loadModule(*module);
                    (void)engine.executeCalls(*ast_root);
                } else {
                    (void)engine.execute(*ast_root);
                }
            } else {
                (void)engine.execute(*ast_root);
            }

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
