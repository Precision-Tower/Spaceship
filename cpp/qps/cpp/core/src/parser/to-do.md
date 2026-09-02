Parser Module To-Do List
This list summarizes the areas requiring further implementation, refinement, or clarification within the gravitus_principia/core/src/parser/ directory.

# I. Core Parser (_index.hpp & _index.cpp)

parseDeclaration() Refinement:
Action: Review and potentially expand parseDeclaration() to ensure it correctly dispatches to all possible top-level statement types, including control flow statements (e.g., -let, -if, -loop) if they can appear at the top level. Currently, it throws an error for unhandled types.
Status: Needs expansion for control flow and other executable statements.
parseExecutionBlock() Full Implementation:
Action: Implement full parsing logic for statements within an execution block ({...}). This is a major task. Each control flow keyword (-let, -if, -else, -elif, -try, -raise, -loop, -while, -for, -return-, -print, -assert, -set, -break, -continue, -pass) needs its own parsing function.
Status: Placeholder; currently throws errors for complex statements.
Function Call Parsing:
Action: Expression-level parseFunctionCall() supports IDENTIFIER followed by OPEN_PAREN, positional arguments, and CLOSE_PAREN. Standalone function-call statements remain out of scope.
Status: Implemented for primary expressions; standalone call statements still intentionally unsupported.
parseModuleManifest() Implementation (from library.cpp):
Action: Define explicit syntax for module manifests (e.g., expose: ...;) and implement parseModuleManifest() in library.cpp to correctly parse these.
Status: Placeholder; currently errors.

# II. Modular Parsing Components (Specific Files)

item.cpp (parseItemDeclaration()):
Consideration: The current logic for value_node relies on parseLiteral() or parsePathReference(). Ensure that item- path/to.ref; (implicit reference without /p;) is correctly handled if /p; is truly optional. The current code consumes a suffix if present, otherwise proceeds, which aligns with "If a value ... does not have a /type; suffix, it is assumed to be a reference". This seems mostly okay.
Status: Fairly stable, but edge case of implicit references vs. literals needs careful testing.

term.cpp (parseTermDeclaration()):
Refinement: The content loop for term: can be highly flexible. Review the grammar rules carefully for "content is a collection of other Gravitus Principia constructs" and "comma-separated lists". Ensure it correctly handles:
Lists of diverse declarations within a term (term: item- val;, other_term: def";, (container_content)\;).
The behavior of the semicolon and comma within lists and how they terminate the term block.
Status: Needs robust testing for complex nested content and list handling.

key.cpp (parseKeyDeclaration()):
Refinement: Similar to term.cpp, the content parsing for key. needs to be robust for varied nested declarations and comma-separated lists.
Status: Needs robust testing for complex nested content and list handling.

dictionary.cpp (parseDictionaryEntry()):
Refinement: The parsing of DICT_INPUT_REF (<.ID:) currently assumes the ID is numeric. Clarify if the ID can be an identifier (e.g., <.my_id:) and adjust parsing if needed.
Refinement: The handling of DICT_OUTPUT_REF (>.ID:) in parsePrimaryExpression (in math.cpp) currently creates a NumericLiteralNode. This is a simplification; a dedicated DictOutputReferenceNode might be better for semantic clarity.
Status: Good for basic cases, but dictionary ID and reference parsing could be more specialized.

container.cpp (parseContainer()):
Refinement: The handling of commas and backslashes for list termination (element1, element2\) needs careful testing to ensure correct parsing and error reporting for malformed lists.
Status: Fairly stable, but list termination via \ needs thorough testing.

causal.cpp (parseCausalRelationship() & parseCausalSide()):
Major Task: Chaining (A = B = C):
Action: Decide definitively how chained causal relationships should be represented in the AST (e.g., as multiple CausalRelationshipNodes in sequence at a higher level, or a single node with a list of relations). Then implement the parsing logic to handle A = B = C; syntax without throwing an error for subsequent =.
Status: Currently parses only one A = B link and explicitly errors on chaining, marking this as a significant area for future implementation.

math.cpp (Expression Parsing):
Refinement: The parsePrimaryExpression() logic for dictionary output references (>.ID) creates a NumericLiteralNode. A dedicated DictOutputReferenceNode might be more semantically appropriate.
Future Feature: Support for unary expressions (e.g., -A).
Status: Handles basic infix arithmetic and precedence, but references within expressions could be more specialized.

# III. Missing/Placeholder AST Nodes & Utilities
Statement-Specific AST Nodes:
Action: As we implement parseExecutionBlock() and its sub-parsers, we'll need specific AST nodes for:
LetStatementNode, SetStatementNode
IfStatementNode, ElseStatementNode, ElifStatementNode
LoopStatementNode, WhileStatementNode, ForStatementNode
ReturnStatementNode, PrintStatementNode, AssertStatementNode, TryStatementNode, RaiseStatementNode, BreakStatementNode, ContinueStatementNode, PassStatementNode
FunctionCallNode
Status: AstNodeType entries exist, but concrete classes and create helpers are pending full statement parsing implementation.