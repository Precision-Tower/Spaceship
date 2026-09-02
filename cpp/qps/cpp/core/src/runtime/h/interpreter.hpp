#ifndef QPS_RUNTIME_H_INTERPRETER_HPP
#define QPS_RUNTIME_H_INTERPRETER_HPP

#include "geometry_actions.hpp"
#include "symbol_table.hpp"

#include "../../ast/h/statements.hpp"

#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qps {

namespace ast {
class AstNode;
class ExecutionActionNode;
class ExecutionBlockNode;
class FunctionCallNode;
class FunctionDeclarationNode;
class ItemDeclarationNode;
class CalculationNode;
class ProgramNode;
class ReturnStatementNode;
class TermDeclarationNode;
}

namespace runtime {

class SymbolResolver;

using FunctionTable =
    std::unordered_map<
        std::string,
        const ast::FunctionDeclarationNode*>;

struct InterpreterOptions {
    ast::ExecutionDomain domain =
        ast::ExecutionDomain::GENERIC;

    std::string active_target;

    bool allow_return = false;

    GeometryActionDispatcher*
        geometry_dispatcher = nullptr;

    // Optional structural-reference runtime context.
    //
    // Required when execution contains:
    //   v: [>shape.dimensions]
    SymbolResolver* symbol_resolver = nullptr;

    std::string current_document;
};

class Interpreter {
public:
    explicit Interpreter(
        ExecutionScope& scope);

    Interpreter(
        ExecutionScope& scope,
        FunctionTable functions);

    Interpreter(
        ExecutionScope& scope,
        FunctionTable functions,
        InterpreterOptions options);

    void registerFunction(
        const ast::FunctionDeclarationNode& function);

    void executeProgram(
        const ast::ProgramNode& program);

    void execute(
        const ast::ExecutionBlockNode& block);

    std::optional<RuntimeValue>
    executeForResult(
        const ast::ExecutionBlockNode& block,
        bool skip_item_declarations = false);

    void executeStatement(
        const ast::AstNode& statement);

    // Numeric QPS evaluator remains numeric.
    double evaluate(
        const ast::AstNode& node) const;

private:
    Interpreter(
        ExecutionScope& scope,
        FunctionTable functions,
        std::vector<std::string> active_functions,
        std::string current_function);

    ExecutionScope& scope_;

    FunctionTable functions_;

    std::vector<std::string>
        active_functions_;

    std::string current_function_;

    InterpreterOptions options_;

    void executeItem(
        const ast::ItemDeclarationNode& item);

    void executeCalculation(
        const ast::CalculationNode& calculation);

    void executeGeometryFeature(
        const ast::TermDeclarationNode& term);

    void executeStructuralBinding(
        const ast::TermDeclarationNode& term);

    RuntimeValue executeGeometryAction(
        const ast::ExecutionActionNode& action,
        const std::optional<std::string>&
            result_stage_name);

    RuntimeValue evaluateReturn(
        const ast::ReturnStatementNode&
            statement) const;

    double invokeFunction(
        const ast::FunctionCallNode& call) const;

    void bindTarget(
        const ast::AstNode& target,
        double value,
        bool derived);

    void bindTarget(
        const ast::AstNode& target,
        RuntimeValue value,
        bool derived);
};

} // namespace runtime
} // namespace qps

#endif
