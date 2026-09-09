#ifndef QPS_RUNTIME_H_INTERPRETER_HPP
#define QPS_RUNTIME_H_INTERPRETER_HPP

#include "geometry_actions.hpp"
#include "symbol_table.hpp"
#include "symbol_resolver.hpp"

#include "../../ast/h/statements.hpp"

#include <functional>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace qps {

namespace ast {
class AstNode;
class ExecutionActionNode;
class ExecutionCallNode;
class ExecutionBlockNode;
class FunctionCallNode;
class FunctionDeclarationNode;
class ItemDeclarationNode;
class CalculationNode;
class ProgramNode;
class AssertStatementNode;
class FailStatementNode;
class RaiseStatementNode;
class RaisesStatementNode;
class ReturnStatementNode;
class TermDeclarationNode;
}

namespace runtime {

class RuntimeDiagnostic : public std::runtime_error {
public:
    RuntimeDiagnostic(
        const std::string& message,
        int line,
        int column)
        : std::runtime_error(message),
          line_(line),
          column_(column) {}

    int line() const { return line_; }
    int column() const { return column_; }

private:
    int line_ = 0;
    int column_ = 0;
};

class AssertionFailure : public RuntimeDiagnostic {
public:
    AssertionFailure(
        const std::string& message,
        int line = 0,
        int column = 0)
        : RuntimeDiagnostic(message, line, column) {}
};

class ExecutionError : public RuntimeDiagnostic {
public:
    ExecutionError(
        const std::string& message,
        int line = 0,
        int column = 0)
        : RuntimeDiagnostic(message, line, column) {}
};

struct HostActionResult;

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
    StructuralResolver* symbol_resolver = nullptr;

    std::string current_document;

    // Optional owner for the parsed Program currently being executed.
    // Local authored structural Terms use this owner when they become
    // RuntimeValue::STRUCTURE so returned values cannot dangle.
    std::shared_ptr<ast::ProgramNode> program_owner;

    // Optional bridge for evaluating reusable execution calls
    // as ordinary RuntimeValue expressions.
    std::function<
        RuntimeValue(
            const ast::ExecutionCallNode&)>
        execution_call;
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

    // Runtime Item values may be non-numeric.
    RuntimeValue evaluateValue(
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

    void executeLocatedStatement(
        const ast::AstNode& statement);

    void executeItem(
        const ast::ItemDeclarationNode& item);

    void executeCalculation(
        const ast::CalculationNode& calculation);

    void executeIf(
        const ast::IfStatementNode& statement);

    void executeWhile(
        const ast::WhileStatementNode& statement);

    void executeAssert(
        const ast::AssertStatementNode& statement) const;

    void executeFail(
        const ast::FailStatementNode& statement) const;

    void executeRaise(
        const ast::RaiseStatementNode& statement) const;

    void executeRaises(
        const ast::RaisesStatementNode& statement);

    void executeGeometryFeature(
        const ast::TermDeclarationNode& term);

    void executeStructuralBinding(
        const ast::TermDeclarationNode& term);

    RuntimeValue executeGeometryAction(
        const ast::ExecutionActionNode& action,
        const std::optional<std::string>&
            result_stage_name);

    HostActionResult executeHostAction(
        const ast::ExecutionActionNode& action);

    RuntimeValue evaluateReturn(
        const ast::ReturnStatementNode&
            statement) const;

    RuntimeValue invokeFunction(
        const ast::FunctionCallNode& call) const;

    bool evaluateTruth(
        const ast::AstNode& node) const;

    bool runtimeTruth(
        const RuntimeValue& value) const;

    bool runtimeValueEqual(
        const RuntimeValue& left,
        const RuntimeValue& right) const;

    bool runtimeContains(
        const RuntimeValue& value,
        const RuntimeValue& container) const;

    std::string evaluateMessage(
        const ast::AstNode* node) const;

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
