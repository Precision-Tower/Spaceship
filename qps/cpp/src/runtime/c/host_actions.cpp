#include "host_actions.hpp"
#include "document_loader.hpp"
#include "path_resolver.hpp"

#include "../../ast/structural_selection.hpp"

#include "../../parser/h/_index.hpp"
#include "../../tokens/h/char_stream.hpp"
#include "../../tokens/h/lexer.hpp"


#include <algorithm>
#include <array>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <poll.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
#include <ctime>
#include <iomanip>

namespace qps::runtime {

namespace {

const RuntimeValue& requireParameter(
    const HostActionInvocation& invocation,
    const std::string& name) {

    const auto found =
        invocation.parameters.find(name);

    if (found == invocation.parameters.end()) {
        throw std::runtime_error(
            "Host action '-" +
            invocation.action_name +
            "' requires parameter '" +
            name +
            "'.");
    }

    return found->second;
}

void rejectUnknownParameters(
    const HostActionInvocation& invocation,
    std::initializer_list<std::string> allowed_names) {

    for (const auto& [name, value] :
         invocation.parameters) {

        (void)value;

        if (std::find(
                allowed_names.begin(),
                allowed_names.end(),
                name) != allowed_names.end()) {
            continue;
        }

        throw std::runtime_error(
            "Unknown " +
            invocation.action_name +
            " parameter '" +
            name +
            "'.");
    }
}

ProcessRequest resolveProcessRequest(
    const HostActionInvocation& invocation) {

    ProcessRequest request;

    request.program =
        requireParameter(invocation, "program")
            .asString("process program");

    if (request.program.empty()) {
        throw std::runtime_error(
            "Process program cannot be empty.");
    }

    const auto cwd =
        invocation.parameters.find("cwd");

    if (cwd != invocation.parameters.end()) {
        request.cwd =
            cwd->second.asString("process cwd");
    }

    std::vector<std::pair<int, std::string>> indexed;

    for (const auto& [name, value] :
         invocation.parameters) {

        if (name.rfind("arg_", 0) != 0) {
            continue;
        }

        const std::string suffix =
            name.substr(4);

        if (suffix.empty() ||
            !std::all_of(
                suffix.begin(),
                suffix.end(),
                [](unsigned char c) {
                    return c >= '0' && c <= '9';
                })) {

            throw std::runtime_error(
                "Invalid process argument parameter '" +
                name +
                "'. Expected arg_N.");
        }

        indexed.emplace_back(
            std::stoi(suffix),
            value.asString(
                "process argument '" +
                name +
                "'"));
    }

    std::sort(
        indexed.begin(),
        indexed.end(),
        [](const auto& left, const auto& right) {
            return left.first < right.first;
        });

    for (const auto& [index, value] : indexed) {
        (void)index;
        request.arguments.push_back(value);
    }

    for (const auto& [name, value] :
         invocation.parameters) {

        (void)value;

        if (name == "program" ||
            name == "cwd" ||
            name.rfind("arg_", 0) == 0) {
            continue;
        }

        throw std::runtime_error(
            "Unknown process parameter '" +
            name +
            "'.");
    }

    return request;
}

void drainReadyPipe(
    int& fd,
    std::string& output) {

    std::array<char, 4096> buffer{};

    while (true) {
        const ssize_t count =
            ::read(
                fd,
                buffer.data(),
                buffer.size());

        if (count > 0) {
            output.append(
                buffer.data(),
                static_cast<std::size_t>(count));
            return;
        }

        if (count == 0) {
            ::close(fd);
            fd = -1;
            return;
        }

        if (errno == EINTR) {
            continue;
        }

        throw std::runtime_error(
            "Process pipe read failed: " +
            std::string(std::strerror(errno)));
    }
}

void captureProcessOutput(
    int stdout_fd,
    int stderr_fd,
    ProcessResult& result) {

    int stdout_open = stdout_fd;
    int stderr_open = stderr_fd;

    while (stdout_open >= 0 ||
           stderr_open >= 0) {

        pollfd descriptors[2]{};

        descriptors[0].fd = stdout_open;
        descriptors[0].events =
            stdout_open >= 0 ? POLLIN : 0;

        descriptors[1].fd = stderr_open;
        descriptors[1].events =
            stderr_open >= 0 ? POLLIN : 0;

        int ready = 0;

        do {
            ready =
                ::poll(
                    descriptors,
                    2,
                    -1);
        } while (ready < 0 &&
                 errno == EINTR);

        if (ready < 0) {
            if (stdout_open >= 0) {
                ::close(stdout_open);
            }

            if (stderr_open >= 0) {
                ::close(stderr_open);
            }

            throw std::runtime_error(
                "Process pipe poll failed: " +
                std::string(
                    std::strerror(errno)));
        }

        const short readable =
            POLLIN | POLLHUP | POLLERR;

        if (stdout_open >= 0 &&
            (descriptors[0].revents &
             readable)) {

            drainReadyPipe(
                stdout_open,
                result.stdout_text);
        }

        if (stderr_open >= 0 &&
            (descriptors[1].revents &
             readable)) {

            drainReadyPipe(
                stderr_open,
                result.stderr_text);
        }
    }
}

ProcessResult runProcess(
    const ProcessRequest& request) {

    int stdout_pipe[2];
    int stderr_pipe[2];

    if (::pipe(stdout_pipe) != 0 ||
        ::pipe(stderr_pipe) != 0) {

        throw std::runtime_error(
            "Unable to create process pipes.");
    }

    const pid_t pid = ::fork();

    if (pid < 0) {
        throw std::runtime_error(
            "Unable to fork process.");
    }

    if (pid == 0) {
        ::close(stdout_pipe[0]);
        ::close(stderr_pipe[0]);

        ::dup2(
            stdout_pipe[1],
            STDOUT_FILENO);

        ::dup2(
            stderr_pipe[1],
            STDERR_FILENO);

        ::close(stdout_pipe[1]);
        ::close(stderr_pipe[1]);

        if (request.cwd.has_value() &&
            ::chdir(request.cwd->c_str()) != 0) {

            const std::string message =
                "Unable to change process directory to '" +
                *request.cwd +
                "': " +
                std::strerror(errno) +
                "\n";

            ::write(
                STDERR_FILENO,
                message.data(),
                message.size());

            _exit(126);
        }

        std::vector<std::string> storage;
        storage.reserve(
            request.arguments.size() + 1);

        storage.push_back(request.program);

        for (const auto& argument :
             request.arguments) {
            storage.push_back(argument);
        }

        std::vector<char*> argv;
        argv.reserve(storage.size() + 1);

        for (auto& value : storage) {
            argv.push_back(value.data());
        }

        argv.push_back(nullptr);

        ::execvp(
            request.program.c_str(),
            argv.data());

        const std::string message =
            "Unable to execute process '" +
            request.program +
            "': " +
            std::strerror(errno) +
            "\n";

        ::write(
            STDERR_FILENO,
            message.data(),
            message.size());

        _exit(127);
    }

    ::close(stdout_pipe[1]);
    ::close(stderr_pipe[1]);

    ProcessResult result;

    captureProcessOutput(
        stdout_pipe[0],
        stderr_pipe[0],
        result);

    int status = 0;

    while (::waitpid(pid, &status, 0) < 0) {
        if (errno == EINTR) {
            continue;
        }

        throw std::runtime_error(
            "Unable to wait for process.");
    }

    if (WIFEXITED(status)) {
        result.exit_code =
            WEXITSTATUS(status);
    }
    else if (WIFSIGNALED(status)) {
        result.exit_code =
            128 + WTERMSIG(status);
    }

    return result;
}

} // namespace

HostActionResult HostActionDispatcher::execute(
    const HostActionInvocation& invocation) const {

    if (invocation.action_name == "process") {
        const ProcessResult process =
            runProcess(
                resolveProcessRequest(invocation));

        return HostActionResult{
            process.exit_code,
            process.stdout_text,
            process.stderr_text,
            std::nullopt
        };
    }

    if (invocation.action_name == "write") {
        const std::string stream =
            requireParameter(
                invocation,
                "stream")
                .asString("write stream");

        const RuntimeValue& value =
            requireParameter(
                invocation,
                "value");

        std::string rendered;

        if (value.isString()) {
            rendered =
                value.asString(
                    "write value");
        }
        else if (value.isNumeric()) {
            std::ostringstream out;
            out << value.asNumber(
                "write value");
            rendered = out.str();
        }
        else {
            throw std::runtime_error(
                "write value requires a scalar STRING or NUMERIC value.");
        }

        for (const auto& [name, parameter] :
             invocation.parameters) {

            (void)parameter;

            if (name != "stream" &&
                name != "value") {

                throw std::runtime_error(
                    "Unknown write parameter '" +
                    name +
                    "'.");
            }
        }

        if (stream == "stdout") {
            std::cout << rendered;
            std::cout.flush();
        }
        else if (stream == "stderr") {
            std::cerr << rendered;
            std::cerr.flush();
        }
        else {
            throw std::runtime_error(
                "Write stream must be 'stdout' or 'stderr'.");
        }

        return HostActionResult{};
    }

    if (invocation.action_name == "qps_load") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString("qps_load path");

        rejectUnknownParameters(
            invocation,
            {"path"});

        qps::runtime::DocumentLoader loader;

        std::unique_ptr<qps::ast::ProgramNode> parsed =
            loader.load(
                std::filesystem::path(path));

        if (!parsed) {
            throw std::runtime_error(
                "QPS load produced no program.");
        }

        std::shared_ptr<qps::ast::ProgramNode> program(
            std::move(parsed));

        qps::runtime::StructuralHandle handle;
        handle.document_owner = program;
        handle.target_node = program.get();

        HostActionResult result;
        result.value =
            qps::runtime::RuntimeValue::structure(
                std::move(handle));

        return result;
    }

    if (invocation.action_name == "qps_parse") {
        const std::string source =
            requireParameter(
                invocation,
                "source")
                .asString("qps_parse source");

        for (const auto& [name, value] :
             invocation.parameters) {

            (void)value;

            if (name != "source") {
                throw std::runtime_error(
                    "Unknown qps_parse parameter '" +
                    name +
                    "'.");
            }
        }

        qps::tokens::CharStream char_stream(source);
        qps::tokens::Lexer lexer(char_stream);
        qps::parser::Parser parser(lexer);

        std::unique_ptr<qps::ast::ProgramNode> parsed =
            parser.parseProgram();

        if (!parsed) {
            throw std::runtime_error(
                "QPS parse produced no program.");
        }

        std::shared_ptr<qps::ast::ProgramNode> program(
            std::move(parsed));

        qps::runtime::StructuralHandle handle;
        handle.document_owner = program;
        handle.target_node = program.get();

        HostActionResult result;
        result.value =
            qps::runtime::RuntimeValue::structure(
                std::move(handle));

        return result;
    }

    if (invocation.action_name == "qps_check") {
        const std::string source =
            requireParameter(
                invocation,
                "source")
                .asString("qps_check source");

        for (const auto& [name, value] :
             invocation.parameters) {

            (void)value;

            if (name != "source") {
                throw std::runtime_error(
                    "Unknown qps_check parameter '" +
                    name +
                    "'.");
            }
        }

        qps::tokens::CharStream char_stream(source);
        qps::tokens::Lexer lexer(char_stream);
        qps::parser::Parser parser(lexer);

        std::unique_ptr<qps::ast::ProgramNode> program =
            parser.parseProgram();

        if (!program) {
            throw std::runtime_error(
                "QPS validation produced no program.");
        }

        return HostActionResult{};
    }

    if (invocation.action_name == "path_kind") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString("path_kind path");

        for (const auto& [name, value] :
             invocation.parameters) {

            (void)value;

            if (name != "path") {
                throw std::runtime_error(
                    "Unknown path_kind parameter '" +
                    name +
                    "'.");
            }
        }

        namespace fs = std::filesystem;

        std::string kind = "missing";

        std::error_code error;
        const fs::file_status status =
            fs::status(
                fs::path(path),
                error);

        if (!error) {
            if (fs::is_regular_file(status)) {
                kind = "file";
            }
            else if (fs::is_directory(status)) {
                kind = "directory";
            }
        }

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                std::move(kind));

        return result;
    }

    if (invocation.action_name == "path_parent") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString("path_parent path");

        for (const auto& [name, value] :
             invocation.parameters) {

            (void)value;

            if (name != "path") {
                throw std::runtime_error(
                    "Unknown path_parent parameter '" +
                    name +
                    "'.");
            }
        }

        namespace fs = std::filesystem;

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                fs::path(path)
                    .parent_path()
                    .string());

        return result;
    }

    if (invocation.action_name == "path_canonical") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString("path_canonical path");

        for (const auto& [name, value] :
             invocation.parameters) {

            (void)value;

            if (name != "path") {
                throw std::runtime_error(
                    "Unknown path_canonical parameter '" +
                    name +
                    "'.");
            }
        }

        namespace fs = std::filesystem;

        const fs::path canonical =
            fs::weakly_canonical(
                fs::path(path));

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                canonical.string());

        return result;
    }

    if (invocation.action_name == "structure_child") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "structure");

        const std::string name =
            requireParameter(
                invocation,
                "name")
                .asString("structure_child name");

        rejectUnknownParameters(
            invocation,
            {"structure", "name"});

        const StructuralHandle& source =
            value.asStructure(
                "structure_child structure");

        if (!source.document_owner ||
            source.target_node == nullptr) {

            throw std::runtime_error(
                "structure_child requires a complete structural handle.");
        }

        ast::AstNode* selected = nullptr;

        if (auto* program =
                dynamic_cast<ast::ProgramNode*>(
                    source.target_node)) {

            selected =
                const_cast<ast::AstNode*>(
                    ast::selectDocumentStructure(
                        *program,
                        name));
        }
        else {
            selected =
                ast::selectStructuralChild(
                    *source.target_node,
                    name);
        }

        if (!selected) {
            throw std::runtime_error(
                "Structural child '" +
                name +
                "' not found.");
        }

        StructuralHandle result_handle;
        result_handle.document_owner =
            source.document_owner;
        result_handle.target_node =
            selected;

        HostActionResult result;
        result.value =
            RuntimeValue::structure(
                std::move(result_handle));

        return result;
    }

    if (invocation.action_name == "structure_item") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "structure");

        const std::string name =
            requireParameter(
                invocation,
                "name")
                .asString("structure_item name");

        rejectUnknownParameters(
            invocation,
            {"structure", "name"});

        const StructuralHandle& source =
            value.asStructure(
                "structure_item structure");

        if (!source.document_owner ||
            source.target_node == nullptr) {

            throw std::runtime_error(
                "structure_item requires a complete structural handle.");
        }

        ast::ItemDeclarationNode* selected =
            ast::selectStructuralItem(
                *source.target_node,
                name);

        if (!selected) {
            throw std::runtime_error(
                "Structural Item '" +
                name +
                "' not found.");
        }

        StructuralHandle result_handle;
        result_handle.document_owner =
            source.document_owner;
        result_handle.target_node =
            selected;

        HostActionResult result;
        result.value =
            RuntimeValue::structure(
                std::move(result_handle));

        return result;
    }

    if (invocation.action_name == "structure_children") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "structure");

        rejectUnknownParameters(
            invocation,
            {"structure"});

        const StructuralHandle& source =
            value.asStructure(
                "structure_children structure");

        if (!source.document_owner ||
            source.target_node == nullptr) {

            throw std::runtime_error(
                "structure_children requires a complete structural handle.");
        }

        std::vector<RuntimeValue> values;

        for (const auto* child :
             ast::structuralScope(
                 *source.target_node)) {

            StructuralHandle handle;
            handle.document_owner =
                source.document_owner;
            handle.target_node =
                const_cast<ast::AstNode*>(child);

            values.push_back(
                RuntimeValue::structure(
                    std::move(handle)));
        }

        HostActionResult result;
        result.value =
            RuntimeValue::sequence(
                std::move(values));

        return result;
    }

    if (invocation.action_name == "structure_name") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "structure");

        rejectUnknownParameters(
            invocation,
            {"structure"});

        const StructuralHandle& source =
            value.asStructure(
                "structure_name structure");

        if (!source.document_owner ||
            source.target_node == nullptr) {

            throw std::runtime_error(
                "structure_name requires a complete structural handle.");
        }

        std::string name;

        if (const auto* key =
                dynamic_cast<
                    const ast::KeyDeclarationNode*>(
                        source.target_node)) {

            name = key->identifier_;
        }
        else if (const auto* term =
                     dynamic_cast<
                         const ast::TermDeclarationNode*>(
                             source.target_node)) {

            name = term->identifier_;
        }
        else if (const auto* item =
                     dynamic_cast<
                         const ast::ItemDeclarationNode*>(
                             source.target_node)) {

            if (const auto* identifier =
                    dynamic_cast<
                        const ast::IdentifierNode*>(
                            item->getTarget())) {

                name = identifier->name_;
            }
            else if (const auto* semantic =
                         dynamic_cast<
                             const ast::SymbolReferenceNode*>(
                                 item->getTarget())) {

                name =
                    semantic->getFinalSegmentName();
            }
            else {
                throw std::runtime_error(
                    "structure_name cannot identify Item target.");
            }
        }
        else {
            throw std::runtime_error(
                "structure_name requires a Key, Term, or Item.");
        }

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                std::move(name));

        return result;
    }

    if (invocation.action_name == "publish_files") {
        const RuntimeValue& replacements_value =
            requireParameter(
                invocation,
                "replacements");

        rejectUnknownParameters(
            invocation,
            {"replacements"});

        const auto& replacements =
            replacements_value.asDictionary(
                "publish_files replacements");

        if (replacements.empty()) {
            throw std::runtime_error(
                "publish_files requires at least one replacement.");
        }

        struct Publication {
            std::filesystem::path destination;
            std::filesystem::path staged;
            std::filesystem::path backup;
            std::string text;
            bool had_original = false;
            bool backup_created = false;
            bool published = false;
        };

        std::vector<Publication> publications;
        publications.reserve(replacements.size());

        const std::string nonce =
            std::to_string(
                std::chrono::steady_clock::now()
                    .time_since_epoch()
                    .count());

        for (std::size_t i = 0;
             i < replacements.size();
             ++i) {

            const auto& pair =
                replacements[i].value.asDictionary(
                    "publish_files replacement");

            if (pair.size() != 2) {
                throw std::runtime_error(
                    "publish_files replacement must contain "
                    "exactly path and text values.");
            }

            const std::string path =
                pair[0].value.asString(
                    "publish_files replacement path");

            const std::string text =
                pair[1].value.asString(
                    "publish_files replacement text");

            if (path.empty()) {
                throw std::runtime_error(
                    "publish_files replacement path is empty.");
            }

            Publication publication;
            publication.destination =
                std::filesystem::absolute(std::filesystem::path(path))
                    .lexically_normal();

            publication.text = text;

            for (const auto& existing : publications) {
                if (existing.destination ==
                    publication.destination) {

                    throw std::runtime_error(
                        "publish_files contains duplicate destination: " +
                        publication.destination.generic_string());
                }
            }

            const std::filesystem::path parent =
                publication.destination.parent_path();

            if (parent.empty() ||
                !std::filesystem::exists(parent) ||
                !std::filesystem::is_directory(parent)) {

                throw std::runtime_error(
                    "publish_files destination parent does not exist: " +
                    publication.destination.generic_string());
            }

            publication.staged =
                parent /
                (
                    "." +
                    publication.destination.filename().string() +
                    ".publish." +
                    nonce +
                    "." +
                    std::to_string(i)
                );

            publication.backup =
                parent /
                (
                    "." +
                    publication.destination.filename().string() +
                    ".backup." +
                    nonce +
                    "." +
                    std::to_string(i)
                );

            publication.had_original =
                std::filesystem::exists(publication.destination);

            publications.push_back(
                std::move(publication));
        }

        try {
            // Stage every complete replacement before touching authority.
            for (auto& publication : publications) {
                std::ofstream output(
                    publication.staged,
                    std::ios::binary |
                    std::ios::trunc);

                if (!output) {
                    throw std::runtime_error(
                        "publish_files unable to create staged file: " +
                        publication.staged.generic_string());
                }

                output.write(
                    publication.text.data(),
                    static_cast<std::streamsize>(
                        publication.text.size()));

                if (!output) {
                    throw std::runtime_error(
                        "publish_files unable to write staged file: " +
                        publication.staged.generic_string());
                }
            }

            // Move every existing authority aside.
            for (auto& publication : publications) {
                if (!publication.had_original) {
                    continue;
                }

                std::filesystem::rename(
                    publication.destination,
                    publication.backup);

                publication.backup_created = true;
            }

            // Publish every staged replacement.
            for (auto& publication : publications) {
                std::filesystem::rename(
                    publication.staged,
                    publication.destination);

                publication.staged.clear();
                publication.published = true;
            }
        }
        catch (...) {
            std::error_code ec;

            // Remove any newly published replacements.
            for (auto& publication : publications) {
                if (publication.published &&
                    std::filesystem::exists(publication.destination)) {

                    std::filesystem::remove(
                        publication.destination,
                        ec);
                    ec.clear();
                }
            }

            // Restore every original authority.
            for (auto& publication : publications) {
                if (publication.backup_created &&
                    std::filesystem::exists(publication.backup)) {

                    std::filesystem::rename(
                        publication.backup,
                        publication.destination,
                        ec);
                    ec.clear();
                }
            }

            // Remove any unconsumed staged files.
            for (auto& publication : publications) {
                if (!publication.staged.empty() &&
                    std::filesystem::exists(publication.staged)) {

                    std::filesystem::remove(
                        publication.staged,
                        ec);
                    ec.clear();
                }
            }

            throw;
        }

        // Successful publication: backups are no longer needed.
        {
            std::error_code ec;

            for (auto& publication : publications) {
                if (publication.backup_created &&
                    std::filesystem::exists(publication.backup)) {

                    std::filesystem::remove(
                        publication.backup,
                        ec);
                    ec.clear();
                }
            }
        }

        return HostActionResult{};
    }

    if (invocation.action_name == "time_utc_compact") {
        rejectUnknownParameters(
            invocation,
            {});

        const auto now =
            std::chrono::system_clock::now();

        const auto milliseconds =
            std::chrono::duration_cast<
                std::chrono::milliseconds>(
                    now.time_since_epoch())
                .count() % 1000;

        const std::time_t wall_time =
            std::chrono::system_clock::to_time_t(
                now);

        std::tm utc{};

#if defined(_WIN32)
        gmtime_s(
            &utc,
            &wall_time);
#else
        gmtime_r(
            &wall_time,
            &utc);
#endif

        std::ostringstream out;

        out
            << std::put_time(
                &utc,
                "%Y%m%d_%H%M%S")
            << "_"
            << std::setw(3)
            << std::setfill('0')
            << milliseconds;

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                out.str());

        return result;
    }

    if (invocation.action_name == "time_utc") {
        rejectUnknownParameters(
            invocation,
            {});

        const auto now =
            std::chrono::system_clock::now();

        const std::time_t wall_time =
            std::chrono::system_clock::to_time_t(
                now);

        std::tm utc{};

#if defined(_WIN32)
        gmtime_s(
            &utc,
            &wall_time);
#else
        gmtime_r(
            &wall_time,
            &utc);
#endif

        std::ostringstream out;
        out
            << std::put_time(
                &utc,
                "%Y-%m-%dT%H:%M:%SZ");

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                out.str());

        return result;
    }

    if (invocation.action_name == "file_read") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString("file_read path");

        rejectUnknownParameters(
            invocation,
            {"path"});

        std::ifstream input(
            path,
            std::ios::binary);

        if (!input) {
            throw std::runtime_error(
                "Unable to read file: " +
                path);
        }

        std::ostringstream out;
        out << input.rdbuf();

        if (!input.eof() && input.fail()) {
            throw std::runtime_error(
                "Unable to read complete file: " +
                path);
        }

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                out.str());

        return result;
    }

    if (invocation.action_name == "file_insert_before_line") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString(
                    "file_insert_before_line path");

        const double line_value =
            requireParameter(
                invocation,
                "line")
                .asNumber(
                    "file_insert_before_line line");

        const std::string text =
            requireParameter(
                invocation,
                "text")
                .asString(
                    "file_insert_before_line text");

        rejectUnknownParameters(
            invocation,
            {"path", "line", "text"});

        const int target_line =
            static_cast<int>(
                line_value);

        if (line_value !=
                static_cast<double>(
                    target_line) ||
            target_line <= 0) {

            throw std::runtime_error(
                "file_insert_before_line requires "
                "a positive integral line.");
        }

        std::ifstream input(
            path,
            std::ios::binary);

        if (!input) {
            throw std::runtime_error(
                "Unable to read file_insert_before_line source: " +
                path);
        }

        std::ostringstream out;
        std::string line;
        int line_number = 0;
        bool inserted = false;

        while (std::getline(input, line)) {
            ++line_number;

            if (line_number == target_line) {
                out << text;
                inserted = true;
            }

            out << line;

            if (!input.eof()) {
                out << '\n';
            }
        }

        if (!input.eof() &&
            input.fail()) {

            throw std::runtime_error(
                "Unable to read file_insert_before_line source: " +
                path);
        }

        if (!inserted) {
            throw std::runtime_error(
                "file_insert_before_line target line "
                "is beyond end of file.");
        }

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                out.str());

        return result;
    }

    if (invocation.action_name == "file_without_span") {
        const std::string path =
            requireParameter(invocation, "path")
                .asString("file_without_span path");

        const double start_value =
            requireParameter(invocation, "start")
                .asNumber("file_without_span start");

        const double end_value =
            requireParameter(invocation, "end")
                .asNumber("file_without_span end");

        rejectUnknownParameters(
            invocation,
            {"path", "start", "end"});

        const int start_line =
            static_cast<int>(start_value);

        const int end_line =
            static_cast<int>(end_value);

        if (start_value !=
                static_cast<double>(start_line) ||
            end_value !=
                static_cast<double>(end_line) ||
            start_line <= 0 ||
            end_line < start_line) {

            throw std::runtime_error(
                "file_without_span requires positive integral "
                "start/end lines with end >= start.");
        }

        std::ifstream input(
            path,
            std::ios::binary);

        if (!input) {
            throw std::runtime_error(
                "Unable to read file_without_span source: " +
                path);
        }

        std::ostringstream out;
        std::string line;
        int line_number = 0;

        while (std::getline(input, line)) {
            ++line_number;

            const bool had_newline =
                !input.eof();

            if (line_number < start_line ||
                line_number > end_line) {

                out << line;

                if (had_newline) {
                    out << '\n';
                }
            }
        }

        if (!input.eof() && input.fail()) {
            throw std::runtime_error(
                "Unable to read file_without_span source: " +
                path);
        }

        if (line_number < start_line) {
            throw std::runtime_error(
                "file_without_span start line is beyond end of file.");
        }

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                out.str());

        return result;
    }

    if (invocation.action_name == "file_span") {
        const std::string path =
            requireParameter(
                invocation,
                "path")
                .asString("file_span path");

        const double start_value =
            requireParameter(
                invocation,
                "start")
                .asNumber("file_span start");

        const double end_value =
            requireParameter(
                invocation,
                "end")
                .asNumber("file_span end");

        rejectUnknownParameters(
            invocation,
            {"path", "start", "end"});

        if (start_value < 1.0 ||
            end_value < start_value ||
            std::floor(start_value) != start_value ||
            std::floor(end_value) != end_value) {

            throw std::runtime_error(
                "file_span requires positive integral "
                "start/end lines with end >= start.");
        }

        const std::size_t start_line =
            static_cast<std::size_t>(
                start_value);

        const std::size_t end_line =
            static_cast<std::size_t>(
                end_value);

        std::ifstream input(path);

        if (!input) {
            throw std::runtime_error(
                "Unable to read file_span source: " +
                path);
        }

        std::ostringstream out;
        std::string line;
        std::size_t line_number = 0;

        while (std::getline(input, line)) {
            ++line_number;

            if (line_number < start_line) {
                continue;
            }

            if (line_number > end_line) {
                break;
            }

            out << line;

            if (line_number < end_line) {
                out << "\n";
            }
        }

        if (line_number < start_line) {
            throw std::runtime_error(
                "file_span start line is beyond end of file.");
        }

        HostActionResult result;
        result.value =
            RuntimeValue::string(
                out.str());

        return result;
    }

    if (invocation.action_name == "structure_start") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "structure");

        rejectUnknownParameters(
            invocation,
            {"structure"});

        const StructuralHandle& source =
            value.asStructure(
                "structure_start structure");

        if (!source.document_owner ||
            source.target_node == nullptr) {

            throw std::runtime_error(
                "structure_start requires a complete structural handle.");
        }

        HostActionResult result;
        result.value =
            RuntimeValue::numeric(
                static_cast<double>(
                    source.target_node->getLine()));

        return result;
    }

    if (invocation.action_name == "structure_end") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "structure");

        rejectUnknownParameters(
            invocation,
            {"structure"});

        const StructuralHandle& source =
            value.asStructure(
                "structure_end structure");

        if (!source.document_owner ||
            source.target_node == nullptr) {

            throw std::runtime_error(
                "structure_end requires a complete structural handle.");
        }

        int end_line =
            source.target_node->getLine();

        if (const auto* key =
                dynamic_cast<
                    const ast::KeyDeclarationNode*>(
                        source.target_node)) {

            end_line = key->getEndLine();
        }
        else if (const auto* term =
                     dynamic_cast<
                         const ast::TermDeclarationNode*>(
                             source.target_node)) {

            end_line = term->getEndLine();
        }
        else if (const auto* item =
                     dynamic_cast<
                         const ast::ItemDeclarationNode*>(
                             source.target_node)) {

            end_line = item->getEndLine();
        }

        HostActionResult result;
        result.value =
            RuntimeValue::numeric(
                static_cast<double>(
                    end_line));

        return result;
    }

    if (invocation.action_name == "sequence_size") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "value");

        rejectUnknownParameters(
            invocation,
            {"value"});

        const auto& sequence =
            value.asSequence(
                "sequence_size value");

        HostActionResult result;
        result.value =
            RuntimeValue::numeric(
                static_cast<double>(
                    sequence.size()));

        return result;
    }

    if (invocation.action_name == "sequence_at") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "value");

        const RuntimeValue& index =
            requireParameter(
                invocation,
                "index");

        rejectUnknownParameters(
            invocation,
            {"value", "index"});

        const auto& sequence =
            value.asSequence(
                "sequence_at value");

        const double index_value =
            index.asNumber(
                "sequence_at index");

        if (index_value < 0.0) {
            throw std::runtime_error(
                "sequence_at index must be non-negative.");
        }

        if (std::floor(index_value) != index_value) {
            throw std::runtime_error(
                "sequence_at index must be integral.");
        }

        if (index_value >=
            static_cast<double>(
                sequence.size())) {

            throw std::runtime_error(
                "sequence_at index out of range.");
        }

        HostActionResult result;
        result.value =
            sequence[
                static_cast<std::size_t>(
                    index_value)];

        return result;
    }

    if (invocation.action_name == "module_children") {
        const std::string root =
            requireParameter(
                invocation,
                "root")
                .asString(
                    "module_children root");

        const std::string module =
            requireParameter(
                invocation,
                "module")
                .asString(
                    "module_children module");

        rejectUnknownParameters(
            invocation,
            {"root", "module"});

        PathResolver paths(root);

        std::vector<RuntimeValue> values;

        for (const auto& child :
             paths.childModules(module)) {

            values.push_back(
                RuntimeValue::string(
                    child.generic_string()));
        }

        HostActionResult result;
        result.value =
            RuntimeValue::sequence(
                std::move(values));

        return result;
    }

    if (invocation.action_name == "module_files") {
        const std::string root =
            requireParameter(
                invocation,
                "root")
                .asString(
                    "module_files root");

        const std::string module =
            requireParameter(
                invocation,
                "module")
                .asString(
                    "module_files module");

        rejectUnknownParameters(
            invocation,
            {"root", "module"});

        PathResolver paths(root);

        std::vector<RuntimeValue> values;

        for (const auto& file :
             paths.qpsFiles(module)) {

            values.push_back(
                RuntimeValue::string(
                    file.generic_string()));
        }

        HostActionResult result;
        result.value =
            RuntimeValue::sequence(
                std::move(values));

        return result;
    }

    if (invocation.action_name == "dictionary_size") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "value");

        rejectUnknownParameters(
            invocation,
            {"value"});

        const auto& dictionary =
            value.asDictionary(
                "dictionary_size value");

        HostActionResult result;
        result.value =
            RuntimeValue::numeric(
                static_cast<double>(
                    dictionary.size()));

        return result;
    }

    if (invocation.action_name == "dictionary_at") {
        const RuntimeValue& value =
            requireParameter(
                invocation,
                "value");

        const RuntimeValue& index =
            requireParameter(
                invocation,
                "index");

        rejectUnknownParameters(
            invocation,
            {"value", "index"});

        const auto& dictionary =
            value.asDictionary(
                "dictionary_at value");

        const double index_value =
            index.asNumber(
                "dictionary_at index");

        if (index_value < 0.0) {
            throw std::runtime_error(
                "dictionary_at index must be non-negative.");
        }

        if (std::floor(index_value) != index_value) {
            throw std::runtime_error(
                "dictionary_at index must be integral.");
        }

        if (index_value >=
            static_cast<double>(dictionary.size())) {
            throw std::runtime_error(
                "dictionary_at index out of range.");
        }

        HostActionResult result;
        result.value =
            dictionary[static_cast<std::size_t>(index_value)].value;

        return result;
    }

    throw std::runtime_error(
        "Unknown host execution action '-" +
        invocation.action_name + "'.");
}

HostActionResult HostActionDispatcher::execute(
    const std::string& action_name) const {

    return execute(HostActionInvocation{
        action_name,
        {}
    });
}

} // namespace qps::runtime
