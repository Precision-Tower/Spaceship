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
        GeometryHandle,
        ResolvedSymbol> value)
    : value_(std::move(value)) {}

RuntimeValue RuntimeValue::numeric(
    double value) {

    return RuntimeValue(value);
}

RuntimeValue RuntimeValue::geometry(
    GeometryHandle handle) {

    return RuntimeValue(std::move(handle));
}

RuntimeValue RuntimeValue::structure(
    ResolvedSymbol structure) {

    return RuntimeValue(std::move(structure));
}

RuntimeValue::Kind RuntimeValue::kind() const {
    if (isNumeric()) {
        return Kind::NUMERIC;
    }

    if (isGeometry()) {
        return Kind::GEOMETRY;
    }

    return Kind::STRUCTURE;
}

bool RuntimeValue::isNumeric() const {
    return std::holds_alternative<double>(value_);
}

bool RuntimeValue::isGeometry() const {
    return std::holds_alternative<GeometryHandle>(value_);
}

bool RuntimeValue::isStructure() const {
    return std::holds_alternative<ResolvedSymbol>(value_);
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
        std::string(
            isGeometry()
                ? "geometry"
                : "structure") +
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
        std::string(
            isNumeric()
                ? "numeric"
                : "structure") +
        ".");
}

const ResolvedSymbol& RuntimeValue::asStructure(
    const std::string& context) const {

    if (const auto* structure =
            std::get_if<ResolvedSymbol>(&value_)) {

        return *structure;
    }

    const std::string prefix =
        context.empty()
            ? "Runtime value"
            : context;

    throw std::runtime_error(
        prefix +
        " expected structure value but found " +
        std::string(
            isNumeric()
                ? "numeric"
                : "geometry") +
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

        case RuntimeValue::Kind::GEOMETRY:
            return "geometry";

        case RuntimeValue::Kind::STRUCTURE:
            return "structure";
    }

    return "unknown";
}

} // namespace runtime
} // namespace qps
