#include "host_actions.hpp"

#include "../../parser/h/_index.hpp"
#include "../../tokens/h/char_stream.hpp"
#include "../../tokens/h/lexer.hpp"


#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <iostream>
#include <poll.h>
#include <stdexcept>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

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

        const std::string value =
            requireParameter(
                invocation,
                "value")
                .asString("write value");

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
            std::cout << value;
            std::cout.flush();
        }
        else if (stream == "stderr") {
            std::cerr << value;
            std::cerr.flush();
        }
        else {
            throw std::runtime_error(
                "Write stream must be 'stdout' or 'stderr'.");
        }

        return HostActionResult{};
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
