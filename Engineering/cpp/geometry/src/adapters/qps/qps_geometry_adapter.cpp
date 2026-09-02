#include "engineering/geometry/qps_geometry_adapter.hpp"
#include "engineering/qps_quantity_adapter.hpp"

#include "runtime/h/geometry_action_resolver.hpp"
#include "ast/h/declarations.hpp"

#include <stdexcept>
#include <string>
#include <utility>

namespace engineering::geometry {

namespace {


const qps::ast::TermDeclarationNode*
findDirectTerm(
    const qps::ast::AstNode& node,
    const std::string& name) {

    if (const auto* term =
            dynamic_cast<
                const qps::ast::TermDeclarationNode*>(
                    &node)) {

        for (const auto& child : term->content_) {
            if (const auto* found =
                    findDirectTerm(
                        *child,
                        name)) {
                return found;
            }
        }

        return nullptr;
    }

    if (const auto* container =
            dynamic_cast<
                const qps::ast::ContainerNode*>(
                    &node)) {

        for (const auto& child :
             container->elements) {

            if (const auto* child_term =
                    dynamic_cast<
                        const qps::ast::TermDeclarationNode*>(
                            child.get())) {

                if (child_term->identifier_ == name) {
                    return child_term;
                }

                // A named Term is a semantic boundary.
                // Do not search through the wrong Term.
                continue;
            }

            if (const auto* found =
                    findDirectTerm(
                        *child,
                        name)) {
                return found;
            }
        }
    }

    return nullptr;
}


const qps::ast::ItemDeclarationNode*
findDirectItem(
    const qps::ast::AstNode& node,
    const std::string& name) {

    if (const auto* item =
            dynamic_cast<
                const qps::ast::ItemDeclarationNode*>(
                    &node)) {

        const auto* target =
            dynamic_cast<
                const qps::ast::IdentifierNode*>(
                    item->getTarget());

        if (target != nullptr &&
            target->name_ == name) {

            return item;
        }

        return nullptr;
    }

    if (const auto* term =
            dynamic_cast<
                const qps::ast::TermDeclarationNode*>(
                    &node)) {

        for (const auto& child :
             term->content_) {

            // Other named Terms are semantic boundaries.
            if (dynamic_cast<
                    const qps::ast::TermDeclarationNode*>(
                        child.get()) != nullptr) {
                continue;
            }

            if (const auto* found =
                    findDirectItem(
                        *child,
                        name)) {
                return found;
            }
        }

        return nullptr;
    }

    if (const auto* container =
            dynamic_cast<
                const qps::ast::ContainerNode*>(
                    &node)) {

        for (const auto& child :
             container->elements) {

            if (dynamic_cast<
                    const qps::ast::TermDeclarationNode*>(
                        child.get()) != nullptr) {
                continue;
            }

            if (const auto* found =
                    findDirectItem(
                        *child,
                        name)) {
                return found;
            }
        }
    }

    return nullptr;
}


void appendStructuralCylinderParameters(
    FeatureNode& feature,
    const qps::runtime::ResolvedGeometryAction& action) {

    if (action.structural_arguments.size() != 1) {
        throw std::runtime_error(
            "Structural QPS cylinder requires exactly one structural argument.");
    }

    const auto& structure =
        action.structural_arguments.front();

    if (structure.target_node == nullptr) {
        throw std::runtime_error(
            "Structural QPS cylinder argument has no resolved AST target.");
    }

    const auto* body =
        findDirectTerm(
            *structure.target_node,
            "body");

    if (body == nullptr) {
        throw std::runtime_error(
            "Structural QPS cylinder requires direct Term 'body'.");
    }

    const auto* radius =
        findDirectItem(
            *body,
            "radius");

    if (radius == nullptr) {
        throw std::runtime_error(
            "Structural QPS cylinder body requires Item 'radius'.");
    }

    const auto* depth =
        findDirectItem(
            *body,
            "depth");

    if (depth == nullptr) {
        throw std::runtime_error(
            "Structural QPS cylinder body requires Item 'depth'.");
    }

    const auto radius_quantity =
        engineering::makeQuantity(*radius);

    const auto depth_quantity =
        engineering::makeQuantity(*depth);

    feature.parameters.push_back({
        .name = "radius",
        .numeric_value =
            radius_quantity.canonicalValue(),
    });

    // "depth" is the authored primitive property.
    // Existing geometry backend calls axial cylinder extent "width".
    feature.parameters.push_back({
        .name = "width",
        .numeric_value =
            depth_quantity.canonicalValue(),
    });
}


FeatureKind featureKindForAction(
    const std::string& action_name) {

    if (action_name == "cylinder") {
        return FeatureKind::PRIMITIVE;
    }

    if (action_name == "bore") {
        return FeatureKind::BOOLEAN;
    }

    throw std::runtime_error(
        "Unsupported QPS geometry action '" +
        action_name +
        "' for Engineering geometry translation.");
}

} // namespace


FeatureNode makeFeatureNode(
    const qps::runtime::ResolvedGeometryAction& action) {

    if (!action.result_stage_name.has_value() ||
        action.result_stage_name->empty()) {

        throw std::runtime_error(
            "Resolved QPS geometry action '" +
            action.action_name +
            "' has no result stage name.");
    }

    FeatureNode feature;

    feature.id =
        *action.result_stage_name;

    feature.kind =
        featureKindForAction(
            action.action_name);

    feature.operation =
        action.action_name;

    if (!action.structural_arguments.empty()) {
        if (action.action_name == "cylinder") {
            appendStructuralCylinderParameters(
                feature,
                action);
        } else {
            throw std::runtime_error(
                "QPS geometry action '-" +
                action.action_name +
                "' does not accept structural arguments.");
        }
    } else {
        feature.parameters.reserve(
            action.parameters.size());

        for (const auto& parameter :
             action.parameters) {

            feature.parameters.push_back({
                .name = parameter.name,
                .numeric_value = parameter.value,
            });
        }
    }

    if (action.source_stage_name.has_value()) {
        if (action.source_stage_name->empty()) {
            throw std::runtime_error(
                "Resolved QPS geometry action '" +
                action.action_name +
                "' has an empty source stage name.");
        }

        feature.dependencies.push_back(
            *action.source_stage_name);
    }

    return feature;
}


qps::runtime::RuntimeValue
EngineeringGeometryDispatcher::invoke(
    const qps::runtime::ResolvedGeometryAction& action) {

    FeatureNode feature =
        makeFeatureNode(action);

    dag_.addFeature(
        std::move(feature));

    // QPS requires an opaque geometry result so later feature
    // stages can validate and chain geometry sources.
    //
    // This handle is runtime transport state only. Engineering's
    // FeatureDAG remains the structural authority.
    qps::runtime::GeometryHandle handle;

    handle.id =
        next_handle_id_++;

    handle.action_name =
        action.action_name;

    handle.active_target =
        action.active_target;

    handle.stage_name =
        action.result_stage_name;

    handle.source_stage_name =
        action.source_stage_name;

    if (action.source_geometry.has_value()) {
        handle.source_handle_id =
            action.source_geometry->id;
    }

    handle.parameters.reserve(
        action.parameters.size());

    for (const auto& parameter :
         action.parameters) {

        qps::runtime::GeometryParameterValue value;

        value.name =
            parameter.name;

        value.value =
            parameter.value;

        value.explicit_override =
            parameter.explicit_override;

        handle.parameters.push_back(
            std::move(value));
    }

    return qps::runtime::RuntimeValue::geometry(
        std::move(handle));
}


const FeatureDAG&
EngineeringGeometryDispatcher::featureDAG() const {
    return dag_;
}

} // namespace engineering::geometry
