#include "../../src/runtime/h/symbol_table.hpp"

#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

}

int main() {
    try {
        using qps::runtime::RuntimeValue;

        RuntimeValue sequence =
            RuntimeValue::sequence({
                RuntimeValue::numeric(1.0),
                RuntimeValue::string("two"),
                RuntimeValue::sequence({
                    RuntimeValue::numeric(3.0),
                    RuntimeValue::string("four")
                })
            });

        require(
            sequence.kind() ==
                RuntimeValue::Kind::SEQUENCE,
            "Sequence has wrong RuntimeValue kind.");

        require(
            sequence.isSequence(),
            "Sequence does not report isSequence().");

        const auto& values =
            sequence.asSequence("root");

        require(
            values.size() == 3,
            "Sequence size mismatch.");

        require(
            values[0].isNumeric() &&
            values[0].asNumber("first") == 1.0,
            "First Sequence value mismatch.");

        require(
            values[1].isString() &&
            values[1].asString("second") == "two",
            "Second Sequence value mismatch.");

        require(
            values[2].isSequence(),
            "Nested Sequence kind mismatch.");

        const auto& nested =
            values[2].asSequence("nested");

        require(
            nested.size() == 2 &&
            nested[0].asNumber("nested first") == 3.0 &&
            nested[1].asString("nested second") == "four",
            "Nested Sequence values mismatch.");

        bool rejected = false;

        try {
            RuntimeValue::numeric(1.0)
                .asSequence("numeric");
        } catch (const std::exception&) {
            rejected = true;
        }

        require(
            rejected,
            "asSequence accepted non-Sequence value.");

        std::cout << "QPS_RUNTIME_SEQUENCE=PASS\n";
        return 0;

    } catch (const std::exception& error) {
        std::cerr
            << "QPS_RUNTIME_SEQUENCE=FAIL\n"
            << "detail: " << error.what() << "\n";
        return 1;
    }
}
