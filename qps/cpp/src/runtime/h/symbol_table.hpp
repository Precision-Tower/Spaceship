#ifndef QPS_RUNTIME_H_SYMBOL_TABLE_HPP
#define QPS_RUNTIME_H_SYMBOL_TABLE_HPP

#include <cstddef>
#include <optional>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

#include "symbol_resolver.hpp"

namespace qps {
namespace runtime {

struct GeometryParameterValue {
    std::string name;
    double value = 0.0;
    bool explicit_override = false;
};

struct GeometryHandle {
    std::size_t id = 0;

    std::string action_name;
    std::string active_target;

    std::optional<std::string> stage_name;
    std::optional<std::string> source_stage_name;
    std::optional<std::size_t> source_handle_id;

    std::vector<GeometryParameterValue> parameters;
};

class RuntimeValue {
public:
    enum class Kind {
        NUMERIC,
        STRING,
        GEOMETRY,
        STRUCTURE
    };

    RuntimeValue();

    static RuntimeValue numeric(double value);
    static RuntimeValue string(std::string value);
    static RuntimeValue geometry(GeometryHandle handle);
    static RuntimeValue structure(ResolvedSymbol structure);

    Kind kind() const;

    bool isNumeric() const;
    bool isString() const;
    bool isGeometry() const;
    bool isStructure() const;

    double asNumber(
        const std::string& context = "") const;

    const std::string& asString(
        const std::string& context = "") const;

    const GeometryHandle& asGeometry(
        const std::string& context = "") const;

    const ResolvedSymbol& asStructure(
        const std::string& context = "") const;

    // Compatibility with existing numeric QPS runtime code.
    // This remains checked: geometry cannot silently become numeric.
    operator double() const {
        return asNumber();
    }

private:
    explicit RuntimeValue(
        std::variant<
            double,
            std::string,
            GeometryHandle,
            ResolvedSymbol> value);

    std::variant<
        double,
        std::string,
        GeometryHandle,
        ResolvedSymbol> value_;
};

enum class BindingOrigin {
    SUPPLIED,
    DERIVED,
    LOCAL
};

struct RuntimeBinding {
    std::string name;
    RuntimeValue value;
    std::optional<std::string> semantic_symbol;
    BindingOrigin origin = BindingOrigin::LOCAL;
};

class ExecutionScope {
public:
    void bind(
        const std::string& name,
        double value,
        std::optional<std::string> semantic_symbol,
        BindingOrigin origin);

    void bind(
        const std::string& name,
        RuntimeValue value,
        std::optional<std::string> semantic_symbol,
        BindingOrigin origin);

    bool contains(
        const std::string& name) const;

    const RuntimeBinding& get(
        const std::string& name) const;

    std::vector<RuntimeBinding> bindings() const;

private:
    std::unordered_map<std::string, RuntimeBinding> bindings_;
    std::vector<std::string> insertion_order_;
};

const char* bindingOriginName(
    BindingOrigin origin);

const char* runtimeValueKindName(
    RuntimeValue::Kind kind);

} // namespace runtime
} // namespace qps

#endif
