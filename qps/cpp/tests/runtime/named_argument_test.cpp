#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"
#include "parser/h/_index.hpp"
#include "runtime/h/interpreter.hpp"

#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

double executeAnswer(
    const std::string& source) {

    qps::tokens::CharStream stream(source);
    qps::tokens::Lexer lexer(stream);
    qps::parser::Parser parser(lexer);

    auto program =
        parser.parseProgram();

    qps::runtime::ExecutionScope scope;
    qps::runtime::Interpreter interpreter(scope);

    interpreter.executeProgram(*program);

    require(
        scope.contains("answer"),
        "Expected answer binding.");

    return scope.get("answer").value.asNumber(
        "answer");
}

void requireNear(
    double actual,
    double expected,
    const std::string& label) {

    require(
        std::abs(actual - expected) < 1e-9,
        label +
        ": expected " +
        std::to_string(expected) +
        ", got " +
        std::to_string(actual));
}

void requireThrowsContaining(
    const std::function<void()>& operation,
    const std::string& expected,
    const std::string& label) {

    try {
        operation();
    }
    catch (const std::exception& error) {
        const std::string message =
            error.what();

        require(
            message.find(expected) !=
                std::string::npos,
            label +
            ": wrong error: " +
            message);

        return;
    }

    throw std::runtime_error(
        label +
        ": expected failure.");
}

const char* prefix = R"qps(
-func subtract(
a-/n;
b-/n;
){
%T: a - b
-return T;
}

)qps";

std::string source(
    const std::string& call) {

    return
        std::string(prefix) +
        "{\n%answer: " +
        call +
        "\n}\n";
}

}

int main() {
    try {
        requireNear(
            executeAnswer(
                source(
                    "subtract(9, 4)")),
            5.0,
            "positional");

        requireNear(
            executeAnswer(
                source(
                    "subtract(a- 9, b- 4)")),
            5.0,
            "named declaration order");

        requireNear(
            executeAnswer(
                source(
                    "subtract(b- 4, a- 9)")),
            5.0,
            "named reordered");

        requireNear(
            executeAnswer(
                source(
                    "subtract(9, b- 4)")),
            5.0,
            "mixed positional then named");

        requireThrowsContaining(
            [] {
                executeAnswer(
                    source(
                        "subtract(c- 9, b- 4)"));
            },
            "Unknown named argument 'c'",
            "unknown named argument");

        requireThrowsContaining(
            [] {
                executeAnswer(
                    source(
                        "subtract(9, a- 4)"));
            },
            "assigned more than once",
            "duplicate positional and named");

        requireThrowsContaining(
            [] {
                executeAnswer(
                    source(
                        "subtract(a- 9, a- 4)"));
            },
            "assigned more than once",
            "duplicate named argument");

        std::cout
            << "QPS_NAMED_ARGUMENT_BINDING=PASS\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "QPS_NAMED_ARGUMENT_BINDING=FAIL: "
            << error.what()
            << "\n";

        return 1;
    }
}
