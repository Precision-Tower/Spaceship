#pragma once

#include "engineering/design_instance.hpp"

#include "runtime/h/execution_engine.hpp"

#include <string>

namespace engineering {

DesignInstance makeDesignInstance(
    const std::string& instance_id,
    const qps::runtime::ExecutionDefinitionInfo& definition);

qps::runtime::ExecutionInstance executeDesignInstance(
    const DesignInstance& design,
    const qps::runtime::ExecutionEngine& engine);

void applyExecutionResult(
    DesignInstance& design,
    const qps::runtime::ExecutionInstance& execution);

} // namespace engineering
