#ifndef QPS_RUNTIME_H_EXECUTION_ENGINE_HPP
#define QPS_RUNTIME_H_EXECUTION_ENGINE_HPP

#include "symbol_table.hpp"

#include <cstddef>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qps {
namespace tokens {
enum class TokenType;
}
namespace ast {
class ExecutionCallNode;
class ExecutionDefinitionNode;
class ProgramNode;
}
namespace runtime {

class GeometryActionDispatcher;

class SymbolResolver;

struct ExecutionInputInfo {
    std::string name;
    std::optional<tokens::TokenType> type_hint;
    bool has_default = false;
};

struct ExecutionDefinitionSourceInfo {
    // Workspace-relative QPS source document identity.
    //
    // This is source provenance, not revision identity.
    std::string source_document;
};

struct ExecutionDefinitionInfo {
    std::string identifier;
    bool identifier_is_numeric = false;
    std::vector<ExecutionInputInfo> inputs;
    std::optional<ExecutionDefinitionSourceInfo> source;
};

struct ExecutionInstance {
    std::string definition_id;
    bool identifier_is_numeric = false;

    // Source identity of the registered definition used to produce
    // this execution result.
    //
    // This is evaluation provenance, not revision identity.
    std::optional<ExecutionDefinitionSourceInfo> source;

    ExecutionScope scope;

    // Optional returned execution value.
    //
    // Numeric reusable definitions historically communicate through
    // semantic bindings. GEOMETRY definitions may additionally return
    // the final opaque geometry state.
    std::optional<RuntimeValue> result;
};

class ExecutionEngine {
public:
    ExecutionEngine() = default;

    explicit ExecutionEngine(
        SymbolResolver& symbol_resolver)
        : symbol_resolver_(&symbol_resolver) {}

    ExecutionEngine(
        SymbolResolver& symbol_resolver,
        GeometryActionDispatcher& geometry_dispatcher)
        : symbol_resolver_(&symbol_resolver),
          geometry_dispatcher_(&geometry_dispatcher) {}

    void registerDefinition(
        const ast::ExecutionDefinitionNode& definition);

    void registerDefinition(
        const ast::ExecutionDefinitionNode& definition,
        std::string source_document);

    ExecutionDefinitionInfo inspectDefinition(
        const ast::ExecutionDefinitionNode& definition) const;

    ExecutionDefinitionInfo inspectRegisteredDefinition(
        const std::string& definition_id) const;

    ExecutionInstance instantiate(
        const ast::ExecutionCallNode& call) const;

    ExecutionInstance instantiate(
        const std::string& definition_id,
        const std::unordered_map<std::string, double>& overrides) const;

    std::vector<ExecutionInstance> execute(
        const ast::ProgramNode& program);

    std::size_t registeredDefinitionCount() const;

private:
    struct RegisteredDefinition {
        const ast::ExecutionDefinitionNode* definition = nullptr;
        std::optional<ExecutionDefinitionSourceInfo> source;
    };

    std::unordered_map<
        std::string,
        RegisteredDefinition
    > definitions_;

    SymbolResolver* symbol_resolver_ = nullptr;
    GeometryActionDispatcher* geometry_dispatcher_ = nullptr;
};

} // namespace runtime
} // namespace qps

#endif
