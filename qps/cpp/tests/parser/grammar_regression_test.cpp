#include "ast/ast_node.hpp"
#include "parser/h/_index.hpp"
#include "tokens/h/char_stream.hpp"
#include "tokens/h/lexer.hpp"

#include <cmath>
#include <functional>
#include <cassert>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string& message) {
    if (!condition) {
        fail(message);
    }
}

std::unique_ptr<qps::ast::ProgramNode> parseSource(
    const std::string& source) {

    qps::tokens::CharStream char_stream(source);
    qps::tokens::Lexer lexer(char_stream);
    qps::parser::Parser parser(lexer);
    return parser.parseProgram();
}

void expectParseFailure(
    const std::string& source,
    const std::string& message_fragment) {

    try {
        (void)parseSource(source);
    } catch (const std::exception& e) {
        const std::string message = e.what();
        require(
            message.find(message_fragment) != std::string::npos,
            "Expected parse failure containing " + message_fragment +
            ", got " + message + ".");
        return;
    }

    fail("Expected parse failure containing " + message_fragment + ".");
}

const qps::ast::KeyDeclarationNode& requireProgramKey(
    const qps::ast::ProgramNode& program,
    std::size_t index,
    const std::string& name) {

    require(program.statements.size() > index, "Expected top-level statement at index.");

    auto* key =
        dynamic_cast<qps::ast::KeyDeclarationNode*>(
            program.statements[index].get());

    require(key != nullptr, "Expected KeyDeclarationNode.");
    require(key->identifier_ == name, "Expected Key named " + name + ".");
    return *key;
}

const qps::ast::TermDeclarationNode& requireKeyTerm(
    const qps::ast::KeyDeclarationNode& key,
    std::size_t index,
    const std::string& name) {

    require(key.content_.size() > index, "Expected Key content at index.");

    auto* term =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            key.content_[index].get());

    require(term != nullptr, "Expected TermDeclarationNode in Key content.");
    require(term->identifier_ == name, "Expected Term named " + name + ".");
    return *term;
}

const qps::ast::TermDeclarationNode& requireContainerTerm(
    const qps::ast::ContainerNode& container,
    std::size_t index,
    const std::string& name) {

    require(container.elements.size() > index, "Expected Container element at index.");

    auto* term =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            container.elements[index].get());

    require(term != nullptr, "Expected TermDeclarationNode in Container.");
    require(term->identifier_ == name, "Expected Container Term named " + name + ".");
    return *term;
}

const qps::ast::ContainerNode& requireOnlyTermContainer(
    const qps::ast::TermDeclarationNode& term) {

    require(term.content_.size() == 1, "Expected Term to contain one node.");

    auto* container =
        dynamic_cast<qps::ast::ContainerNode*>(
            term.content_[0].get());

    require(container != nullptr, "Expected Term content to be a ContainerNode.");
    return *container;
}

const qps::ast::ItemDeclarationNode& requireContainerItem(
    const qps::ast::ContainerNode& container,
    std::size_t index,
    const std::string& name) {

    require(container.elements.size() > index, "Expected Container item at index.");

    auto* item =
        dynamic_cast<qps::ast::ItemDeclarationNode*>(
            container.elements[index].get());

    require(item != nullptr, "Expected ItemDeclarationNode in Container.");

    auto* target =
        dynamic_cast<qps::ast::IdentifierNode*>(
            item->getTarget());

    require(target != nullptr, "Expected Item target identifier.");
    require(target->name_ == name, "Expected Item named " + name + ".");
    return *item;
}

const qps::ast::ContainerNode& parseExampleContainer(
    const std::string& source) {

    auto program = parseSource(source);
    const auto& key = requireProgramKey(*program, 0, "test");
    const auto& term = requireKeyTerm(key, 0, "Example");
    const auto& container = requireOnlyTermContainer(term);

    static std::unique_ptr<qps::ast::ProgramNode> owner;
    owner = std::move(program);
    return container;
}

void requireTypeHint(
    const qps::ast::ItemDeclarationNode& item,
    std::optional<qps::tokens::TokenType> expected,
    const std::string& context) {

    require(item.type_hint_ == expected, context + " type hint mismatch.");
}

void requireNoValue(
    const qps::ast::ItemDeclarationNode& item,
    const std::string& context) {

    require(!item.value_node_, context + " should not have a value node.");
}

const qps::ast::NumericLiteralNode& requireNumericValue(
    const qps::ast::ItemDeclarationNode& item,
    double expected,
    const std::string& context) {

    auto* numeric =
        dynamic_cast<qps::ast::NumericLiteralNode*>(
            item.value_node_.get());

    require(numeric != nullptr, context + " should have a numeric value.");
    require(std::fabs(numeric->value_ - expected) < 0.0000001, context + " numeric value mismatch.");
    return *numeric;
}

void requireStringValue(
    const qps::ast::ItemDeclarationNode& item,
    const std::string& expected,
    const std::string& context) {

    auto* string =
        dynamic_cast<qps::ast::StringLiteralNode*>(
            item.value_node_.get());

    require(string != nullptr, context + " should have a string value.");
    require(string->value_ == expected, context + " string value mismatch.");
}

void requireBooleanValue(
    const qps::ast::ItemDeclarationNode& item,
    bool expected,
    const std::string& context) {

    auto* boolean =
        dynamic_cast<qps::ast::BooleanLiteralNode*>(
            item.value_node_.get());

    require(boolean != nullptr, context + " should have a boolean value.");
    require(boolean->value_ == expected, context + " boolean value mismatch.");
}

void requireNullValue(
    const qps::ast::ItemDeclarationNode& item,
    const std::string& context) {

    require(
        dynamic_cast<qps::ast::NullLiteralNode*>(item.value_node_.get()) != nullptr,
        context + " should have an explicit null value.");
}

void requireDefinitionText(
    const qps::ast::TermDeclarationNode& term,
    const std::string& expected) {

    require(term.content_.size() == 1, "Expected definition Term to contain one literal.");

    auto* literal =
        dynamic_cast<qps::ast::StringLiteralNode*>(
            term.content_[0].get());

    require(literal != nullptr, "Expected definition text literal.");
    require(literal->value_ == expected, "Definition text mismatch.");
}

void requireDimensionItems(
    const qps::ast::ContainerNode& container) {

    require(container.elements.size() == 4, "Expected four dimension items.");
    requireTypeHint(requireContainerItem(container, 0, "radius"), qps::tokens::TokenType::TYPE_NUMERIC, "radius");
    requireTypeHint(requireContainerItem(container, 1, "width"), qps::tokens::TokenType::TYPE_NUMERIC, "width");
    requireTypeHint(requireContainerItem(container, 2, "depth"), qps::tokens::TokenType::TYPE_NUMERIC, "depth");
    requireTypeHint(requireContainerItem(container, 3, "material"), qps::tokens::TokenType::TYPE_ALPHANUM, "material");
}

void paragraphKeysParseAsPeerKeys() {
    auto program = parseSource(R"qps(p. Potential: def"example";

r. Resistance: def"example";
)qps");

    require(program->statements.size() == 2, "Expected two peer Keys.");
    requireDefinitionText(requireKeyTerm(requireProgramKey(*program, 0, "p"), 0, "Potential"), "example");
    requireDefinitionText(requireKeyTerm(requireProgramKey(*program, 1, "r"), 0, "Resistance"), "example");
}

void eofClosesFinalKey() {
    auto program = parseSource(R"qps(p. Potential: def"example";)qps");

    require(program->statements.size() == 1, "Expected EOF to close final Key.");
    requireDefinitionText(requireKeyTerm(requireProgramKey(*program, 0, "p"), 0, "Potential"), "example");
}

void legacyKeyClosingBackslashRejected() {
    expectParseFailure(
        R"qps(p. Potential: def"example"; \)qps",
        "Unexpected token");
}

void singleMemberContainerDoesNotNeedDelimiter() {
    const auto& container = parseExampleContainer(R"qps(test. Example: (
a- 1;
);
)qps");

    require(container.elements.size() == 1, "Expected one container member.");
    requireNumericValue(requireContainerItem(container, 0, "a"), 1.0, "a");
}

void commaRequiresAnotherPeer() {
    const auto& container = parseExampleContainer(R"qps(test. Example: (
a- 1;
b- 2;
);)qps");

    require(
        container.elements.size() == 2,
        "Expected consecutive self-terminated Container peers.");

    requireNumericValue(
        requireContainerItem(container, 0, "a"),
        1.0,
        "a");

    requireNumericValue(
        requireContainerItem(container, 1, "b"),
        2.0,
        "b");
}

void backslashWithoutCollectionIsRejected() {
    expectParseFailure(
        R"qps(test. Example: (
a- 1;\
);)qps",
        "Unexpected token");
}

void commaSeparatedPeersEndingInBackslashParse() {
    expectParseFailure(
        R"qps(test. Example: (
a- 1;,
b- 2;,
c- 3;\
);
)qps",
        "Unexpected token");
}

void activeCollectionMustCloseBeforeContainer() {
    const auto& container = parseExampleContainer(R"qps(test. Example: (
a- 1;
b- 2;
);)qps");

    require(
        container.elements.size() == 2,
        "Expected ')' to own Container closure.");

    requireNumericValue(
        requireContainerItem(container, 0, "a"),
        1.0,
        "a");

    requireNumericValue(
        requireContainerItem(container, 1, "b"),
        2.0,
        "b");
}

void itemStatesRetainValuesAndTypeHints() {
    auto program = parseSource(R"qps(items. Example: (
empty-;
number-/n;
text-/a;
flag-/b;
null_hint-/null;
inferred_number- 10;
explicit_number- 10/n;
explicit_text- "steel"/a;
explicit_bool- true/b;
explicit_null- null;
);
)qps");

    const auto& key = requireProgramKey(*program, 0, "items");
    const auto& container = requireOnlyTermContainer(requireKeyTerm(key, 0, "Example"));

    require(container.elements.size() == 10, "Expected ten item-state examples.");

    const auto& empty = requireContainerItem(container, 0, "empty");
    requireNoValue(empty, "empty");
    requireTypeHint(empty, std::nullopt, "empty");

    const auto& number = requireContainerItem(container, 1, "number");
    requireNoValue(number, "number");
    requireTypeHint(number, qps::tokens::TokenType::TYPE_NUMERIC, "number");

    const auto& text = requireContainerItem(container, 2, "text");
    requireNoValue(text, "text");
    requireTypeHint(text, qps::tokens::TokenType::TYPE_ALPHANUM, "text");

    const auto& flag = requireContainerItem(container, 3, "flag");
    requireNoValue(flag, "flag");
    requireTypeHint(flag, qps::tokens::TokenType::TYPE_BOOLEAN, "flag");

    const auto& null_hint = requireContainerItem(container, 4, "null_hint");
    requireNoValue(null_hint, "null_hint");
    requireTypeHint(null_hint, qps::tokens::TokenType::TYPE_NULL, "null_hint");

    const auto& inferred_number = requireContainerItem(container, 5, "inferred_number");
    requireNumericValue(inferred_number, 10.0, "inferred_number");
    requireTypeHint(inferred_number, std::nullopt, "inferred_number");

    const auto& explicit_number = requireContainerItem(container, 6, "explicit_number");
    requireNumericValue(explicit_number, 10.0, "explicit_number");
    requireTypeHint(explicit_number, qps::tokens::TokenType::TYPE_NUMERIC, "explicit_number");

    const auto& explicit_text = requireContainerItem(container, 7, "explicit_text");
    requireStringValue(explicit_text, "steel", "explicit_text");
    requireTypeHint(explicit_text, qps::tokens::TokenType::TYPE_ALPHANUM, "explicit_text");

    const auto& explicit_bool = requireContainerItem(container, 8, "explicit_bool");
    requireBooleanValue(explicit_bool, true, "explicit_bool");
    requireTypeHint(explicit_bool, qps::tokens::TokenType::TYPE_BOOLEAN, "explicit_bool");

    const auto& explicit_null = requireContainerItem(container, 9, "explicit_null");
    requireNullValue(explicit_null, "explicit_null");
    requireTypeHint(explicit_null, std::nullopt, "explicit_null");
}

void pulleySchemaAstHierarchyParses() {
    auto program = parseSource(R"qps(pu. Pulley: def"A pulley.";
dimensions: (
radius-/n;
width-/n;
depth-/n;
material-/a;
);
)qps");

    require(program->statements.size() == 1, "Expected one pulley Key.");
    const auto& key = requireProgramKey(*program, 0, "pu");
    require(key.content_.size() == 2, "Pulley Key content count mismatch.");
    requireDefinitionText(requireKeyTerm(key, 0, "Pulley"), "A pulley.");
    requireDimensionItems(requireOnlyTermContainer(requireKeyTerm(key, 1, "dimensions")));
}

void combinePulleySchemaAstHierarchyParses() {
    auto program = parseSource(R"qps(cbp. Combine_Pulley: def"A combined pulley.";
input: (
mv-/n;
rpm-/n;
);
output: (
mv-/n;
rpm-/n;
);
dimensions: (
master: (
radius-/n;
width-/n;
depth-/n;
material-/a;
);
slave: (
radius-/n;
width-/n;
depth-/n;
material-/a;
);
);
)qps");

    require(program->statements.size() == 1, "Expected one combine pulley Key.");
    const auto& key = requireProgramKey(*program, 0, "cbp");
    require(key.content_.size() == 4, "Combine pulley Key content count mismatch.");

    requireDefinitionText(requireKeyTerm(key, 0, "Combine_Pulley"), "A combined pulley.");

    const auto& input = requireOnlyTermContainer(requireKeyTerm(key, 1, "input"));
    require(input.elements.size() == 2, "Input item count mismatch.");
    requireTypeHint(requireContainerItem(input, 0, "mv"), qps::tokens::TokenType::TYPE_NUMERIC, "input mv");
    requireTypeHint(requireContainerItem(input, 1, "rpm"), qps::tokens::TokenType::TYPE_NUMERIC, "input rpm");

    const auto& output = requireOnlyTermContainer(requireKeyTerm(key, 2, "output"));
    require(output.elements.size() == 2, "Output item count mismatch.");
    requireTypeHint(requireContainerItem(output, 0, "mv"), qps::tokens::TokenType::TYPE_NUMERIC, "output mv");
    requireTypeHint(requireContainerItem(output, 1, "rpm"), qps::tokens::TokenType::TYPE_NUMERIC, "output rpm");

    const auto& dimensions = requireOnlyTermContainer(requireKeyTerm(key, 3, "dimensions"));
    require(dimensions.elements.size() == 2, "Expected master/slave dimension terms.");
    requireDimensionItems(requireOnlyTermContainer(requireContainerTerm(dimensions, 0, "master")));
    requireDimensionItems(requireOnlyTermContainer(requireContainerTerm(dimensions, 1, "slave")));
}


void leadingDecimalNumericLiteralParses() {
    auto program = parseSource(R"qps(test. Example: (
offset- .5;
);
)qps");

    const auto& key = requireProgramKey(*program, 0, "test");
    const auto& container =
        requireOnlyTermContainer(requireKeyTerm(key, 0, "Example"));

    requireNumericValue(
        requireContainerItem(container, 0, "offset"),
        0.5,
        "leading decimal offset");
}

void pulleySystemAuthoringFrontier() {
    // '$' is lexed as MODEL_MARKER but its execution semantics are
    // intentionally not canonical yet. Preserve the intended authoring
    // frontier without pretending the parser currently implements it.
    expectParseFailure(
        R"qps(pus.
Pulley_System: def"2 inline pulleys";
pu_master: dimensions:
(body: radius- 5/in; depth- 1/in;;)
(groove: x_center- .5/in;;);;
pu_slave: dimensions:
(body: radius- 2/in; depth- 1/in;;)
(groove: x_center- .5/in;;);;
{pus_model:
master: [>pus.pu_master.dimensions];
slave: [>pus.pu_slave.dimensions];
groove: [master.groove];
@masterpulley: -cylinder(master), -wrap(groove);
@slavepulley: -cylinder(slave), -wrap(groove);
$masterplacement:;
$slaveplacement:;
%ratio:;
!drive:;
;}
)qps",
        "Unrecognized statement in execution definition");
}



void genericExecutionActionParsesStructurally() {
    auto program = parseSource(R"qps({host_probe:
-process;
})qps");

    assert(program != nullptr);
    assert(program->statements.size() == 1);

    auto* definition =
        dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
            program->statements.front().get());

    assert(definition != nullptr);
    assert(
        definition->domain_ ==
        qps::ast::ExecutionDomain::GENERIC);

    assert(definition->body_ != nullptr);
    assert(definition->body_->statements.size() == 1);

    auto* action =
        dynamic_cast<qps::ast::ExecutionActionNode*>(
            definition->body_->statements.front().get());

    assert(action != nullptr);
    assert(action->action_name_ == "process");
}


void statementGeometryQualificationSurvivesParsing() {
    auto program = parseSource(R"qps({model:
master: [>shape.dimensions];
@masterpulley: -cylinder(master);
}
)qps");

    assert(program != nullptr);
    assert(program->statements.size() == 1);

    auto* definition =
        dynamic_cast<qps::ast::ExecutionDefinitionNode*>(
            program->statements.front().get());

    assert(definition != nullptr);
    assert(
        definition->domain_ ==
        qps::ast::ExecutionDomain::GENERIC);

    assert(definition->body_ != nullptr);
    assert(definition->body_->statements.size() == 2);

    auto* binding =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            definition->body_->statements[0].get());

    auto* geometry =
        dynamic_cast<qps::ast::TermDeclarationNode*>(
            definition->body_->statements[1].get());

    assert(binding != nullptr);
    assert(geometry != nullptr);

    assert(binding->identifier_ == "master");
    assert(!binding->geometry_qualified_);

    assert(geometry->identifier_ == "masterpulley");
    assert(geometry->geometry_qualified_);
}

struct TestCase {
    const char* name;
    std::function<void()> run;
};

} // namespace

int main() {
    const std::vector<TestCase> tests = {
        {"paragraph Keys parse as peers", paragraphKeysParseAsPeerKeys},
        {"EOF closes final Key", eofClosesFinalKey},
        {"legacy Key-closing backslash is rejected", legacyKeyClosingBackslashRejected},
        {"single-member container needs no delimiter", singleMemberContainerDoesNotNeedDelimiter},
        {"consecutive Container peers need no separator", commaRequiresAnotherPeer},
        {"legacy Container backslash is rejected", backslashWithoutCollectionIsRejected},
        {"legacy Container collection punctuation is rejected", commaSeparatedPeersEndingInBackslashParse},
        {"right parenthesis owns Container closure", activeCollectionMustCloseBeforeContainer},
        {"Item states retain values and type hints", itemStatesRetainValuesAndTypeHints},
        {"pulley schema AST hierarchy parses", pulleySchemaAstHierarchyParses},
        {"combine pulley schema AST hierarchy parses", combinePulleySchemaAstHierarchyParses},
        {"leading decimal numeric literal parses", leadingDecimalNumericLiteralParses},
        {"generic execution action parses structurally", genericExecutionActionParsesStructurally},

        {"statement @ qualification survives parsing", statementGeometryQualificationSurvivesParsing},
        {"pulley system $ authoring frontier remains unimplemented", pulleySystemAuthoringFrontier},
    };

    int failures = 0;

    for (const auto& test : tests) {
        try {
            test.run();
            std::cout << "PASS " << test.name << "\n";
        } catch (const std::exception& e) {
            ++failures;
            std::cerr << "FAIL " << test.name << ": " << e.what() << "\n";
        }
    }

    if (failures != 0) {
        std::cerr << failures << " grammar regression test(s) failed.\n";
        return 1;
    }

    return 0;
}
