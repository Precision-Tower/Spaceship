## QPS Syntax Rules
Here are the fundamental rules governing the QPS language, designed for human conciseness and machine precision.

# Core Principles
Human-First Conciseness: Prioritizes readability and natural expression without relying on indentation. Structure is defined explicitly through delimiters and hierarchical naming.
Machine-Optimized Precision: Every symbol has an unambiguous role, making parsing predictable and efficient for AI interpretation and manipulation.
Semantic Layering: Syntax elements are designed to convey not just data, but also context, association, and causal flow for direct interpretation and visualization.
Hierarchical Flexibility: Data and definitions can be nested to any depth, creating rich associations and detailed explanations.

# Goal
We're just creating Python with a more indepth structure for pulling information.
With Python we can 'from folder import key as term'
We're doing the exact same thing except it is 'term: path/to.key.'
We're taking it a step farther and making everything inside of a Python file parseable without having to pass it as a parameter.
We're just extending the ability of 'from folder import key' where we can 'term: path/to.key.or:item-value;'
Because we're opening the availability one way we'll open the availability the otherway as well.
item-path/to.key.or:item-value/n;/p;
Instead of being limited to how these values are parsed by only being able to grab def in a python file,
We're making every key. an item that is parseable.
Whether is it key., -class key., or -func key. they're all treated the same by
term: folder/file.key. or item- folder/file.key./p;
A term inside of the folder will behave like
--
py.
base_dir = Path(__file__).parent.resolve()
configs_dir = base_dir / "configs"
--
Where both base_dir and configs_dir are terms.
They are just words with meaning.

# Structure
We want everything pushed against the wall.
We're removing white space and creating the structure within the format of how the containers, (), create separation.
AI has tended to think I want everything on a single line since I don't want indention. But I don't need indention to see the separation of concerns,
Indention doesn't equal human readability. It helps for sure, but if we're creating nested information we'll end up with 10,000 tokens in indentation that is completely unnecessary for AI or Human readability.
- Proposal
##
#file.qps
item- value/p;
key.
(term: item- value;, item- value;, item- value;,,\)
(term: item- value;, item- value;, item- value;,,\);

-func key. {
-let _
-if _
-else _
-try _
-loop _
};
##
We're not losing the value because we're not using column's to distinguish nesting,
We're just defining how we see nesting and separating the distinction by how it stacks against the wall.
It's a win win for everyone involved,
You get less white space,
I get a more readable structure.

# File Structure & Access
File Extension: All QPS source files use the .qps extension.

# Implicit Library/Module:
The .qps file itself acts as the implicit Library or Module. It is the top-level container for all declarations within it.
The engine automatically recognizes the file as a QPS library, even without explicit wrapping delimiters.

# _index.qps (Module Manifest):
Behaves exactly like Python's __init__.py.
When a directory is referenced as a module, its _index.qps file is automatically processed by the runtime's PathResolver.
It defines which elements from the directory are exposed publicly and can contain module-level initialization logic.

# Top-Level File Content:
A .qps file consists of surface declarations exposed by that file's implicit Library/Module.

Valid surface declarations include:
Key. entries (identifier. <content>;)
Dictionary entries ([])
Item- entries (identifier- <value>;)
Term: entries (identifier: <content>;)
Function declarations (-func)
Class declarations (-class)

Surface Declaration Boundary:
A blank line separates one complete surface declaration from the next peer declaration in the file/module.

A single newline does not create a new surface declaration. It continues the current logical declaration or bundle.

Every surface declaration must already be syntactically complete through its normal explicit QPS delimiters before the blank-line boundary is reached.

# Directory Navigation:
folder/file.key: Navigates into folder, then to file, accessing key within it.
/folder/file.key: Navigates into a nested folder from the current file's directory, effectively setting that as a temporary base.
//folder/file.key: Retracts one folder level up from the current directory. /// retracts two levels, and so on.

## Scoping Rules
# Module Scope:
Any Key., Dictionary, Item-, Term:, Function, or Class declaration appearing directly "against the wall" (at the top-level of a .qps file, not nested) is part of that file's module scope.
These module-level declarations are callable/referencable via their path (e.g., folder/file.item-).

# Local Scope:
Any declaration nested inside a Key., Term:, () Container, or [] Dictionary exists within the local scope of that parent block.
These nested declarations are only callable/referencable through their full hierarchical path (e.g., folder/file.key.nested_term.item-).

## Core Syntax Constructs
# Comments:
Purpose: To allow human-readable notes within .qps files that are ignored by the QPS engine.
- Single-Line Comments:
Format: # <text>
Rule: All characters from # to the end of the line are considered a comment and are ignored by the lexer/parser.
- Multi-Line Comments (Block Comments):
Format: ## <text content> ##
Rule: All characters between the opening ## and the next closing ## (inclusive) are considered a multi-line comment. These comments can span multiple lines. Multi-line comments cannot be nested (i.e., you cannot have a ## inside another ## ... ## block, as the inner ## would be interpreted as the closing delimiter for the outer block).

# Execution Blocks ({}):
Purpose: Define explicit blocks of executable statements or sequences of operations.
Format: { <executable_statements> }
Contents: Can contain calls to functions, references to callable entities, control flow statements (-if, -for), variable declarations (-let), print- statements, etc.
Nature: This is where control flow and operational logic resides.
Mathematical Expressions use % inside an Execution Block.
Anonymous form: {% <expression> _}
Named form: {%ID: <expression> _}
The ID is optional. Use one only when the calculation itself needs to be addressable.

# Dictionaries ([]):
Purpose: Structured data storage for indexed and associative data.
Format: [<numeric_id>: <content>]
Content: Can contain Item- entries, Term: entries, nested Dictionary entries, Containers, Causal Relations, and References. Dictionaries provide and organize values used by executable calculations.
Input/Output Reference Access:
[<ID: ...]: Denotes input to a dictionary entry.
[>ID: ...]: Denotes output from a dictionary entry.
file.key.[>.ID]: Accessing dictionary content via a path.
- [1: item- value;, item- value;]
--
[1: [<.1: item- value/n;], [<.2: item- value/n;],,\ ]
{% [>1.1:] * [>1.2:] /n;_}
{%output: [>1.1:] * [>1.2:] /n;_}
--
--
[1: key. ([<.1: term: def" statement";]), (term: [<.2: item- value/a;], [<.3: item- value/n;])\ ]

-func key. [>1.1], [>1.2], [>1.3]\ ;
--

# Key (key.):
Purpose: A top-level or nested named access point that defines a structural section or module entry point.
Format: identifier. <content> (e.g., Alternator. <content>)
Content: A Key. can be directly followed by any of the following:
A Definition String: key. def"My description";
A Container (): key. (term: def";), (item- val/p;);
A Dictionary []: key. [1: item- val/n;];
A Term:: key. term: item- val/n;; (This defines a nested hierarchy of terms, where each colon indicates a new nested Term node).
- [1: key. term: [<.1:item- value/n;], [<.2: item- value/a;]\;]

# Term (term:):
Purpose: Represents an association, a conceptual folder, or a contextual block for nested data.
Format: identifier: <content>;
Content: The content is a collection of other QPS constructs. A Term: itself does not directly hold a literal value;. Its content can be:
A Container (): input: (mv, rpm;);
A Definition String: my_term: def"This is my definition";
A Dictionary []: equation: [1: ...];
A Causal Relation: some_relation: (ME = AC); (if a causal relation is the 'content' of a term).
An Item-: my_term: item- value; (This is the end of a recursive chain, e.g., key. term: nested_term: item- value;)
- key. term: def" statement";, item- value/n;, item- value/a;;

# Item (item-):
Purpose: Directly associates an identifier with a single, literal value;. It's the most granular named data assignment.
Format: identifier- <value>; (e.g., radius- 10 /n;, material- "steel" /a;).
Nature: It's a leaf node in the data structure, holding a specific literal value.
Reference Import: Can be used to import references: item- path/to.key; (The path/to.key is interpreted as a Reference due to the Implicit Reference Rule).
- item- "value"/a;

# Value (value;):
Purpose: The actual data content inside an Item-.
Type Suffixes (Mandatory):
/p;: Paths to variables. Example: folder/file.key.term:item-/type;
/n;: Numeric values (integers, floats, scientific notation). Example: my_item- 10 /n;
"value"/a;: Alphanumeric (string) values. Content begins after - and ends before /a;. Supports \n, \t, \r escapes. No double quotes. Example: my_text- "Hello World" /a;
/b;: Boolean values (true, false). Example: is_active- true /b;
/null;: Null value. Example: no_value- null /null;

# Literal Rules:
Numbers: Sequence of digits, optional +/-. Floats include .. Scientific notation uses e or E. No commas.
Strings: Content is everything between : and /a;, including internal whitespace.
Booleans: Exactly true or false (lowercase).
Null: Exactly null (lowercase).

# Implicit Reference Rule:
If a value (following an item-) does not have a /type; suffix, it is assumed to be a reference to another QPS construct.
This means the parser will attempt to parse it as a path (folder/file.key), a dictionary/function ID ([>ID]), or another valid reference syntax. Parsing errors occur if it does not conform to a valid reference syntax.

# List (,):
Purpose: Separates multiple Term: entries or Item- entries within a common container such as () or [].
Format: element1, element2, element3,,\
Rule: , separates members. ,,\, the explicit list closer, terminates the logical list before the enclosing container or dictionary is closed.
--
key.
(term: item- value/a;, item- value/p;, item- value/n;,,\)
(term: item- value/a;, item- value/p;, item- value/n;,,\);
--

# Closer (;):
Purpose: Necessary to explicitly terminate Term: entries, Item- entries.

# Container (()):
Purpose: Allows flexible, nested grouping of data without reliance on indentation.
Format: ( <content> )
Content: Can contain Dictionary entries, Term: entries, Item- entries, or other nested Containers.

# Definition (def"statement;):
Purpose: To attach an open-ended descriptive string to a Term:.
Format: term: def" <text content> ";
Content: The string content is open until terminated by ";. Supports \n, \t, \r escapes.

# Causal Relationship (=):
Purpose: Defines a transformation or chaining of inputs to outputs between entities.
Format: EntityA: (InputA = OutputA) = EntityB: (InputB = OutputB);
Meaning: The output of the preceding entity becomes the input of the next. Chaining A = B = C implies sequential flow.

# Basic Mathematical Operations (Infix Notation):
Operators: *, +, -, /.
Precedence: Standard mathematical rules (multiplication/division before addition/subtraction).

Calculation Marker: %
% tells the engine to evaluate the following content mathematically inside an Execution Block.

Anonymous Calculation:
{% <expression> _}

Named Calculation:
{%ID: <expression> _}

The ID is optional. An anonymous calculation is valid when the result is only needed as part of the current executable process. A named calculation is used when the calculation or its result needs a stable parseable identity.

Dictionaries and references provide and organize the values used by calculations. Calculations execute inside the {} machine-room context rather than using [] as an equation container.
Executable Constructs

# Function (-func):
Purpose: Defines an executable code block.
Format: -func key. [> p1, p2]. { <body_statements> }; (Note: key is the function's name).
Parameters ([> p1, p2]): Passed within the dictionary context for flexible parameter handling.

# Class (-class):
Purpose: A container for grouping functions and potentially other data or declarations.
Format: -class key. { <member_definitions> }; (Note: key is the class name).
Members: Can include func- definitions and Key., Term:, Item- definitions.

# Control Flow Keywords (statements):
-if, -else, -elif: Conditional execution.
-return: Returns a value from a function.
-print: Outputs data.
-try, -raise: Exception handling.
-assert: Debugging assertion.
-while, -for, -loop: Iteration/loops.
-let, -set: Variable declaration and assignment.
-break, -continue, -pass: Loop control.

## Execution Delimiter (_)
Purpose: inside of statements we deliminate with _.
Executable Code Statement Terminator: _ (ONLY inside {})
Declaration/Data Element Terminator: ; (Everywhere else)
--
-func key. {
-let _
-if _
-else _
-try _
-return _
};
--

# Separation of Concerns (|):
Purpose: Separates distinct concerns that belong to the same structural bundle.
Nature: | does not close a declaration, return from execution, or establish scope. It provides an explicit semantic division inside otherwise related information.
Examples:
component: (input: source_data; | output: result_data;);
component: (design: dimensions; | behavior: operating_values;);

# Whitespace: Zero-Tolerance for Indentation (Unnecessary Tokens)
Your Clarification: "I'm calling indentions themselves white space, so we're not speaking the same language and I'm taking precedence because the white space was the unnecessary tokens that I specifically said."
Revised Rule: QPS syntax does not use indentation to establish structural hierarchy. Delimiters such as (), [], and {} define nesting and scope. A single newline continues the current logical paragraph or bundle. One or more blank lines terminate the current bundle and establish a new paragraph boundary. Spaces and indentation remain non-semantic. The goal is to preserve compact, human-readable structure without making indentation responsible for nesting.

# List Delimiter (,,\): The Explicit List Closer
Your Clarification: "I want the closer for the interpreter to easily distinguish between ;\; because of how I use []. We are doing ,,\ That's for the parser itself."
Revised Rule: The sequence ,,\ is the mandatory explicit list terminator within any container () or [] where a list of elements is present. This is not a line continuation, but a specific signal to the parser that the logical list of comma-separated elements has concluded, even if the enclosing container is not yet closed. This provides an unambiguous signal, particularly when dealing with complex nested [] dictionary structures.
Example: (item- value1/n;, item- value2/n;,,\)
Example in a Dictionary: [1: [<.1: item- value/n;], [<.2: item- value/n;],,\ ] (The ,,\ explicitly closes the list of items within dictionary 1 before the ] closes the dictionary itself).

# Statement Terminators: Every Declaration Gets a Delimiter
Your Clarification: "We had already agreed everything gets the delimiter. key.;, term:;, item-;"
Revised Rule: Every declaration or statement in QPS must be explicitly terminated.
; (Semicolon): This terminates declarations or data element assignments (e.g., key. content;, term: content;, item- value/type;).
_ (Underscore): This terminates executable code statements specifically inside execution blocks ({}).

# Paragraph / Bundle Boundary:
A single newline remains part of the current logical bundle.

At file/module surface scope, one or more blank lines terminate the current surface declaration and begin the next peer surface declaration.

A paragraph boundary does not replace any explicit QPS closer or delimiter. The preceding structure must already be syntactically complete.

Nested structures do not automatically use blank lines as structural delimiters. Their structure remains governed by their explicit QPS delimiters.

Explicit closure remains the responsibility of:
;   declaration/data closure
_   executable statement closure inside {}
,,\ explicit list closure
)   Container closure
]   Dictionary closure
}   Execution Block closure

Paragraph boundaries provide semantic separation between complete structures. They do not define nesting or substitute for syntax closure.

# Examples
--
#file.qps

item- value/p;

key.
term: def" statement";;
term: (item- value/n;, item- value/n;,,\);

[1: item- value/p;]

[2: [<.1: item- value/n;], [<.2: item- value/n;],,\ ]

-func key. {%1: [>2.1] * [>1] + [>2.2] /n;_}
--