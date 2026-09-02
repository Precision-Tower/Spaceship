## Gravitus Principia Syntax Rules
Here are the fundamental rules governing the Gravitus Principia language, designed for human conciseness and machine precision.

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

# File Structure & Access
File Extension: All Gravitus Principia source files use the .grav extension.

# Implicit Library/Module:
The .grav file itself acts as the implicit Library or Module. It is the top-level container for all declarations within it.
The engine automatically recognizes the file as a Gravitus Principia library, even without explicit wrapping delimiters.

# {index}.grav (Module Manifest):
Behaves exactly like Python's __init__.py.
When a directory is referenced as a module, its {index}.grav file is automatically processed by the runtime's PathResolver.
It defines which elements from the directory are exposed publicly and can contain module-level initialization logic.

# Top-Level File Content:
A .grav file consists of a sequential list of any valid top-level declarations, including:
Key. entries (identifier. <content>;)
Dictionary entries ([])
Item- entries (identifier: <value>;)
Term: entries (identifier: <content>;)
Function declarations (-func)
Class declarations (-class)

# Directory Navigation:
folder/file.key: Navigates into folder, then to file, accessing key within it.
/folder/file.key: Navigates into a nested folder from the current file's directory, effectively setting that as a temporary base.
//folder/file.key: Retracts one folder level up from the current directory. /// retracts two levels, and so on.


## Scoping Rules
# Module Scope:
Any Key., Dictionary, Item-, Term:, Function(-func), or Class(-class) declaration appearing directly "against the wall" (at the top-level of a .grav file, not nested) is part of that file's module scope.
These module-level declarations are callable/referencable via their path (e.g., folder/file.item-).

# Local Scope:
Any declaration nested inside a Key., Term:, () Container, or [] Dictionary exists within the local scope of that parent block.
These nested declarations are only callable/referencable through their full hierarchical path (e.g., folder/file.key.nested_term.item-).


## Core Syntax Constructs
# Comments:
Purpose: To allow human-readable notes within .grav files that are ignored by the Gravitus Principia engine.
- Single-Line Comments:
Format: # <text>
Rule: All characters from # to the end of the line are considered a comment and are ignored by the lexer/parser.
- Multi-Line Comments (Block Comments):
Format: ## <text content> ##
Rule: All characters between the opening ## and the next closing ## (inclusive) are considered a multi-line comment. These comments can span multiple lines. Multi-line comments cannot be nested (i.e., you cannot have a ## inside another ## ... ## block, as the inner ## would be interpreted as the closing delimiter for the outer block).

# Execution Blocks ({}):
Purpose: Define explicit blocks of executable statements or sequences of operations.
Format: {-ID: <executable_statements> ;}
Contents: Can contain calls to functions, references to callable entities, control flow statements (-if, -for), variable declarations (-let), -print statements, etc.
Nature: This is where control flow and operational logic resides.
Mathematical Expressions: {#ID: <expression> ;} for infix notation.


# Dictionaries ([]):
Purpose: Structured data storage for indexed and associative data.
Format: [<numeric_id>: <content>]
Content: Can contain Item- entries, Term: entries, nested Dictionary entries, Containers, Causal Relations, References, or Mathematical Expressions.
Input/Output Reference Access:
[<ID: ...]: Denotes input to a dictionary entry.
[>ID: ...]: Denotes output from a dictionary entry.
file.key.[>.ID]: Accessing dictionary content via a path.
- [1: item- value;, item- value;;]
--
[1: [<.1: item- value/n;], [<.2: item- value/n;]\]
{#output: [>1.1:] * [>1.2:] /n;}
--
--
[1: key. ([<.1: term: def" statement;]), (term: [<.2: item- value/a;], [<.3: item- value/n;])\;]

-func key. [>1.1], [>1.2], [>1.3]\;
--

# Key (key.):
Purpose: A top-level or nested named access point that defines a structural section or module entry point.
Format: identifier. <content> (e.g., Alternator. <content>)
Content: A Key. can be directly followed by any of the following:
A Definition String: key. def"My description";
A Container (): key. (term: def";), (item- val/p;);
A Dictionary []: key. [1: item- val/n;];
A Term:: key. term: item- val/n;; (This defines a nested hierarchy of terms, where each colon indicates a new nested Term node).
- [1: key. term: [<.1:item- value/n;], [<.2: item- value/a;];]

# Term (term:):
Purpose: Represents an association, a conceptual folder, or a contextual block for nested data.
Format: identifier: <content>;
Content: The content is a collection of other Gravitus Principia constructs. A Term: itself does not directly hold a literal value;. Its content can be:
A Container (): input: (mv, rpm;);
A Definition String: my_term: def"This is my definition";
A Dictionary []: equation: [1: ...];
A Causal Relation: some_relation: (ME = AC); (if a causal relation is the 'content' of a term).
An Item-: my_term: item- value; (This is the end of a recursive chain, e.g., key. term: nested_term: item- value;)
- key. term- def" statement;, item- value/n;, item- value/a;;

# Item (item-):
Purpose: Directly associates an identifier with a single, literal value;. It's the most granular named data assignment.
Format: identifier- <value>; (e.g., radius- 10 /n;, material- "steel" /a;).
Nature: It's a leaf node in the data structure, holding a specific literal value.
Reference Import: Can be used to import references: item- path/to.key; (The path/to.key is interpreted as a Reference due to the Implicit Reference Rule).
- item- value/p;

# Value (value;):
Purpose: The actual data content inside an Item-.
Type Suffixes (Mandatory):
/p;: Paths to variables. Example: folder/file.key.term:item-/type;
/n;: Numeric values (integers, floats, scientific notation). Example: my_item- 10 /n;
/a;: Alphanumeric (string) values. Content begins after : and ends before /a;. Supports \n, \t, \r escapes. No double quotes. Example: my_text: Hello World /a;
/b;: Boolean values (true, false). Example: is_active: true /b;
/null;: Null value. Example: no_value- null /null;

# Literal Rules:
Numbers: Sequence of digits, optional +/-. Floats include .. Scientific notation uses e or E. No commas.
Strings: Content is everything between : and /a;, including internal whitespace.
Booleans: Exactly true or false (lowercase).
Null: Exactly null (lowercase).

# Implicit Reference Rule:
If a value (following an item-) does not have a /type; suffix, it is assumed to be a reference to another Gravitus Principia construct.
This means the parser will attempt to parse it as a path (folder/file.key), a dictionary/function ID ([>ID]), or another valid reference syntax. Parsing errors occur if it does not conform to a valid reference syntax.

# List (,):
Purpose: Separates multiple Term: entries or Item- entries within a common container (e.g., inside (), []).
Format: element1, element2, element3\;
Note: Opening a list with , has to be closed itself with \.
--
key.
(term: item- value/a;, item- value/p;, item- value/n;\;),
(term: item- value/a;, item- value/p;, item- value/n;\;)\;
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
Usage: Always within dictionaries using [#ID: <expression> ;].
Executable Constructs

# Function (-func):
Purpose: Defines an executable code block.
Format: -func key. [> p1, p2]. { <body_statements> }; (Note: key is the function's name).
Parameters ([> p1, p2]): Passed within the dictionary context for flexible parameter handling.

# Class (-class):
Purpose: A container for grouping functions and potentially other data or declarations.
Format: -class key. { <member_definitions> }; (Note: key is the class name).
Members: Can include -func definitions and Key., Term:, Item- definitions.

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

# Forced Return (|):
Purpose: Allows explicit line continuation/separation without newlines in code.
Format: statement1 | statement2;

# Normal Separation: 
1 line between starts the next structure.

# Examples
--
#file.grav

item- value/p;

key.
term: def" statement;
term: (item- value/n;, item- value/n;\);

[1: item- value/p;]

[2: [<.1: item- value/n;], [<.2: item- value/n;]\]

func- key. {#1: [>2.1] * [>1] + [>2.2] /n;}
--