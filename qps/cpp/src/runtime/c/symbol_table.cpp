#include "../h/symbol_table.hpp"

#include <stdexcept>
#include <utility>

namespace qps {
namespace runtime {

RuntimeValue::RuntimeValue()
    : value_(0.0) {}

RuntimeValue::RuntimeValue(
    std::variant<
        double,
        bool,
        std::monostate,
        std::string,
        std::vector<RuntimeDictionaryEntry>,
        RuntimeSequence,
        RuntimeRecord,
        GeometryHandle,
        StructuralHandle> value)
    : value_(std::move(value)) {}

RuntimeValue RuntimeValue::numeric(
    double value) {

    return RuntimeValue(value);
}

RuntimeValue RuntimeValue::boolean(
    bool value) {

    return RuntimeValue(value);
}

RuntimeValue RuntimeValue::null() {
    return RuntimeValue(std::monostate{});
}

RuntimeValue RuntimeValue::string(
    std::string value) {

    return RuntimeValue(std::move(value));
}

RuntimeValue RuntimeValue::dictionary(
    std::vector<RuntimeDictionaryEntry> entries) {

    return RuntimeValue(std::move(entries));
}

RuntimeValue RuntimeValue::sequence(
    std::vector<RuntimeValue> values) {

    return RuntimeValue(
        std::make_shared<std::vector<RuntimeValue>>(
            std::move(values)));
}

RuntimeValue RuntimeValue::record(
    std::vector<RuntimeRecordEntry> entries) {

    return RuntimeValue(
        std::make_shared<std::vector<RuntimeRecordEntry>>(
            std::move(entries)));
}

RuntimeValue RuntimeValue::geometry(
    GeometryHandle handle) {

    return RuntimeValue(std::move(handle));
}

RuntimeValue RuntimeValue::structure(
    StructuralHandle structure) {

    return RuntimeValue(std::move(structure));
}

RuntimeValue::Kind RuntimeValue::kind() const {
    if (isNumeric()) {
        return Kind::NUMERIC;
    }

    if (isBoolean()) {
        return Kind::BOOLEAN;
    }

    if (isNull()) {
        return Kind::NULL_VALUE;
    }

    if (isString()) {
        return Kind::STRING;
    }

    if (isDictionary()) {
        return Kind::DICTIONARY;
    }

    if (isSequence()) {
        return Kind::SEQUENCE;
    }

    if (isRecord()) {
        return Kind::RECORD;
    }

    if (isGeometry()) {
        return Kind::GEOMETRY;
    }

    return Kind::STRUCTURE;
}

bool RuntimeValue::isNumeric() const {
    return std::holds_alternative<double>(value_);
}

bool RuntimeValue::isBoolean() const {
    return std::holds_alternative<bool>(value_);
}

bool RuntimeValue::isNull() const {
    return std::holds_alternative<std::monostate>(value_);
}

bool RuntimeValue::isString() const {
    return std::holds_alternative<std::string>(value_);
}

bool RuntimeValue::isDictionary() const {
    return std::holds_alternative<
        std::vector<RuntimeDictionaryEntry>>(value_);
}

bool RuntimeValue::isSequence() const {
    return std::holds_alternative<
        RuntimeSequence>(value_);
}

bool RuntimeValue::isRecord() const {
    return std::holds_alternative<
        RuntimeRecord>(value_);
}

bool RuntimeValue::isGeometry() const {
    return std::holds_alternative<GeometryHandle>(value_);
}

bool RuntimeValue::isStructure() const {
    return std::holds_alternative<StructuralHandle>(value_);
}

double RuntimeValue::asNumber(
    const std::string& context) const {

    if (const auto* number =
            std::get_if<double>(&value_)) {

        return *number;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected numeric value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

bool RuntimeValue::asBoolean(
    const std::string& context) const {

    if (const auto* boolean =
            std::get_if<bool>(&value_)) {

        return *boolean;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected boolean value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

const std::string& RuntimeValue::asString(
    const std::string& context) const {

    if (const auto* text =
            std::get_if<std::string>(&value_)) {

        return *text;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected string value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

const std::vector<RuntimeDictionaryEntry>&
RuntimeValue::asDictionary(
    const std::string& context) const {

    if (const auto* dictionary =
            std::get_if<
                std::vector<RuntimeDictionaryEntry>>(
                    &value_)) {

        return *dictionary;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected dictionary value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

const std::vector<RuntimeValue>&
RuntimeValue::asSequence(
    const std::string& context) const {

    if (const auto* sequence =
            std::get_if<RuntimeSequence>(
                &value_)) {

        if (*sequence) {
            return **sequence;
        }
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected sequence value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

std::vector<RuntimeValue>&
RuntimeValue::asMutableSequence(
    const std::string& context) {

    if (auto* sequence =
            std::get_if<RuntimeSequence>(
                &value_)) {

        if (*sequence) {
            return **sequence;
        }
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected sequence value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

const std::vector<RuntimeRecordEntry>&
RuntimeValue::asRecord(
    const std::string& context) const {

    if (const auto* record =
            std::get_if<RuntimeRecord>(
                &value_)) {

        if (*record) {
            return **record;
        }
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected record value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

const GeometryHandle& RuntimeValue::asGeometry(
    const std::string& context) const {

    if (const auto* geometry =
            std::get_if<GeometryHandle>(&value_)) {

        return *geometry;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected geometry value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

const StructuralHandle& RuntimeValue::asStructure(
    const std::string& context) const {

    if (const auto* structure =
            std::get_if<StructuralHandle>(&value_)) {

        return *structure;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected structure value but found " +
        std::string(runtimeValueKindName(kind())) +
        ".");
}

void ExecutionScope::bind(
    const std::string& name,
    double value,
    std::optional<std::string> semantic_symbol,
    BindingOrigin origin) {

    bind(
        name,
        RuntimeValue::numeric(value),
        std::move(semantic_symbol),
        origin);
}

void ExecutionScope::bind(
    const std::string& name,
    RuntimeValue value,
    std::optional<std::string> semantic_symbol,
    BindingOrigin origin) {

    if (!contains(name)) {
        insertion_order_.push_back(name);
    }

    RuntimeBinding binding;
    binding.name = name;
    binding.value = std::move(value);
    binding.semantic_symbol = std::move(semantic_symbol);
    binding.origin = origin;

    bindings_[name] = std::move(binding);
}

bool ExecutionScope::contains(
    const std::string& name) const {

    return bindings_.find(name) !=
           bindings_.end();
}

const RuntimeBinding& ExecutionScope::get(
    const std::string& name) const {

    auto it = bindings_.find(name);

    if (it == bindings_.end()) {
        throw std::runtime_error(
            "Undefined execution value: " + name);
    }

    return it->second;
}

std::vector<RuntimeBinding>
ExecutionScope::bindings() const {

    std::vector<RuntimeBinding> result;
    result.reserve(insertion_order_.size());

    for (const auto& name : insertion_order_) {
        result.push_back(bindings_.at(name));
    }

    return result;
}

const char* bindingOriginName(
    BindingOrigin origin) {

    switch (origin) {
        case BindingOrigin::SUPPLIED:
            return "supplied";

        case BindingOrigin::DERIVED:
            return "derived";

        case BindingOrigin::LOCAL:
            return "local";
    }

    return "unknown";
}

const char* runtimeValueKindName(
    RuntimeValue::Kind kind) {

    switch (kind) {
        case RuntimeValue::Kind::NUMERIC:
            return "numeric";

        case RuntimeValue::Kind::STRING:
            return "string";

        case RuntimeValue::Kind::DICTIONARY:
            return "dictionary";

        case RuntimeValue::Kind::SEQUENCE:
            return "sequence";

        case RuntimeValue::Kind::RECORD:
            return "record";

        case RuntimeValue::Kind::GEOMETRY:
            return "geometry";

        case RuntimeValue::Kind::STRUCTURE:
            return "structure";
    }

    return "unknown";
}

} // namespace runtime
} // namespace qps
