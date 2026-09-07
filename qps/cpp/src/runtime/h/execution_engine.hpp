#ifndef QPS_RUNTIME_H_EXECUTION_ENGINE_HPP
#define QPS_RUNTIME_H_EXECUTION_ENGINE_HPP

#include "symbol_table.hpp"
#include "../../ast/h/statements.hpp"

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
class CausalRelationshipNode;
class ExecutionBlockNode;
class ExecutionCallNode;
class ExecutionDefinitionNode;
class TermDeclarationNode;
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

struct CausalRelationshipInfo {
    std::string causal_definition_id;
    std::size_t boundary_index = 0;

    std::string source_entity;
    std::string source_input_domain;
    std::string source_output_domain;

    std::string destination_entity;
    std::string destination_input_domain;
    std::string destination_output_domain;
};

struct CausalTransferTrace {
    CausalRelationshipInfo relationship;

    std::string source_definition_id;
    std::string destination_definition_id;
    std::string semantic_symbol;
    std::optional<std::string> source_semantic_symbol;

    double value = 0.0;
    BindingOrigin source_origin = BindingOrigin::LOCAL;
    BindingOrigin destination_origin = BindingOrigin::SUPPLIED;
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

    // Explicit causal runtime transfers received while constructing
    // this instance. Empty for ordinary non-causal execution calls.
    std::vector<CausalTransferTrace> causal_transfers;
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

    void registerDefinition(
        const ast::TermDeclarationNode& term);

    void registerDefinition(
        const ast::TermDeclarationNode& term,
        std::string source_document);

    ExecutionDefinitionInfo inspectDefinition(
        const ast::ExecutionDefinitionNode& definition) const;

    ExecutionDefinitionInfo inspectRegisteredDefinition(
        const std::string& definition_id) const;

    ExecutionInstance instantiate(
        const ast::ExecutionCallNode& call) const;

    // Expression-position execution calls evaluate their explicit
    // overrides against the calling execution scope.
    ExecutionInstance instantiate(
        const ast::ExecutionCallNode& call,
        ExecutionScope& caller_scope) const;

    // RuntimeValue is the canonical execution override representation.
    ExecutionInstance instantiate(
        const std::string& definition_id,
        const std::unordered_map<std::string, RuntimeValue>& overrides) const;

    // Explicit numeric convenience for native callers.
    ExecutionInstance instantiateNumeric(
        const std::string& definition_id,
        const std::unordered_map<std::string, double>& overrides) const;

    // Register top-level execution definitions without invoking
    // authored calls.
    void registerDefinitions(
        const ast::ProgramNode& program);

    // Execute top-level calls using definitions already registered.
    // Causal definitions are interpreted from this entry program.
    std::vector<ExecutionInstance> executeCalls(
        const ast::ProgramNode& program) const;

    // Compatibility composition for a self-contained program.
    std::vector<ExecutionInstance> execute(
        const ast::ProgramNode& program);

    std::size_t registeredDefinitionCount() const;

private:
    struct RegisteredDefinition {
        std::string identifier;
        bool identifier_is_numeric = false;
        ast::ExecutionDomain domain = ast::ExecutionDomain::GENERIC;
        const ast::ExecutionBlockNode* body = nullptr;
        std::optional<ExecutionDefinitionSourceInfo> source;
    };

    struct CausalInput {
        double value = 0.0;
        CausalTransferTrace trace;
    };

    ExecutionInstance instantiate(
        const ast::ExecutionCallNode& call,
        ExecutionScope& override_scope,
        const std::unordered_map<std::string, CausalInput>&
            causal_inputs) const;

    ExecutionInstance instantiate(
        const std::string& definition_id,
        const std::unordered_map<std::string, RuntimeValue>& overrides,
        const std::unordered_map<std::string, CausalInput>&
            causal_inputs) const;

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
