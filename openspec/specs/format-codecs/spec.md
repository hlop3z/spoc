# Format Codecs

## Purpose

Reading any supported data format produces one intermediate representation — the JSON
data model, and nothing else — so that every consumer above the boundary is written once
rather than once per format. Writing accepts that same model. This capability defines the
representation contract, how a format is selected from a path or declared explicitly, how
a format requiring an optional dependency fails, and the two mappings that are not
one-to-one: tabular data, which carries no types, and hierarchical markup, whose
repetition cannot be inferred from a single document.

## Requirements

### Requirement: Every supported format normalizes to one intermediate representation

Reading any supported format MUST produce a value drawn from the JSON data model — object,
array, string, number, boolean, null — and nothing else. No format-specific node type, parser
object, or library-defined value may cross the boundary. Writing MUST accept that same model.

A value that has been read and then written back in the same format MUST re-read equal to
itself, for every format declared to support writing.

#### Scenario: Reading yields only JSON-model values

- **WHEN** any supported format is read from text or from a file
- **THEN** the result contains only objects, arrays, strings, numbers, booleans, and nulls, and
  no value carrying format- or parser-specific identity

#### Scenario: Round trip through the representation is stable

- **WHEN** a value is read from a format that supports writing, written back to that format, and
  read again
- **THEN** the second result equals the first

#### Scenario: Cross-format conversion needs no per-pair knowledge

- **WHEN** a value read from one supported format is written to a different supported format
- **THEN** the operation succeeds without any conversion rule specific to that pair of formats,
  provided the target format can express the value

### Requirement: Reading accepts both text and files

Every supported format MUST be readable from an in-memory string and from a filesystem path,
producing identical results for identical content. When reading from a path, the format MUST be
inferrable from the file extension, and MUST also be overridable by an explicit caller
declaration.

#### Scenario: Text and file agree

- **WHEN** the same content is read once as text with a declared format and once from a file
  carrying that format's extension
- **THEN** both produce equal results

#### Scenario: Explicit format overrides the extension

- **WHEN** a file is read with an explicitly declared format that differs from its extension
- **THEN** the declared format is used

#### Scenario: Unknown extension is refused

- **WHEN** a file is read whose extension maps to no supported format and no format is declared
- **THEN** the operation fails naming the extension and listing the supported formats

### Requirement: Formats requiring an optional dependency fail by naming it

A format whose support requires a dependency outside the standard library MUST NOT cause a
failure when the surface is imported. The failure MUST occur when that format is first
requested, and MUST name the optional extra to install. It MUST NOT surface as an unresolved
import from a transitive module.

Formats supported by the standard library MUST remain usable when no optional dependency is
installed at all.

#### Scenario: Import succeeds with nothing optional installed

- **WHEN** the surface is imported in an environment with no optional dependency present
- **THEN** the import succeeds, and no optional dependency is loaded

#### Scenario: Missing extra is reported actionably

- **WHEN** a format is requested whose optional dependency is absent
- **THEN** the operation fails with a message naming the extra required to enable it, rather
  than reporting a missing module

#### Scenario: Standard-library formats work bare

- **WHEN** an environment has no optional dependency installed
- **THEN** every format declared as standard-library-supported reads and writes normally

### Requirement: Read and write support are declared per format, independently

Support for reading a format and support for writing it MUST be declared separately, because a
format may be readable without being writable. Requesting an unsupported direction MUST fail
naming that direction and what would enable it.

#### Scenario: Write-unsupported format is refused clearly

- **WHEN** a value is written to a format that is currently readable but not writable
- **THEN** the operation fails stating that writing is unavailable and naming what would enable
  it, rather than failing as though the format were unknown

#### Scenario: Supported directions are enumerable

- **WHEN** the supported formats are queried
- **THEN** the result states, for each format, whether it can currently be read, written, or
  both, in the current environment

### Requirement: Tabular data maps to a sequence of records

A tabular format MUST read as an array of objects, one per data row, with the header row
supplying the keys. This mapping MUST match the minimal-mode output defined by the adopted
tabular-to-JSON standard.

Every value MUST read as a string, because the format carries no type information and
inferring one from a value's appearance would make a row's type depend on its contents. This
consequence — that comparisons over tabular values are lexicographic, not numeric — MUST be
stated wherever the format is documented, since it is silent rather than loud.

#### Scenario: Rows become records

- **WHEN** a tabular source with a header row is read
- **THEN** the result is an array containing one object per data row, each keyed by the header
  values

#### Scenario: A single data row is still an array

- **WHEN** a tabular source containing exactly one data row is read
- **THEN** the result is an array of length one, not a bare object

#### Scenario: Values are strings regardless of appearance

- **WHEN** a tabular source containing numeric-looking values is read
- **THEN** every value in the result is a string, and no value has been converted to a number
  on the basis of how it is written

#### Scenario: The untyped consequence is not hidden

- **WHEN** a comparison is applied to a value read from a tabular source
- **THEN** it compares as a string, and this ordering behavior is stated in the format's
  documentation rather than left for a caller to discover from a wrong result

### Requirement: Hierarchical markup maps to nested objects with declared repetition

A hierarchical markup format MUST read as nested objects, with element attributes and element
text distinguishable from child elements by a stated convention. Repetition MUST be resolved
from caller-declared paths rather than inferred from how many times an element occurs in the
document being read.

A path declared as repeating MUST yield an array regardless of how many elements are present,
including one and including none. A path not declared as repeating MUST NOT change shape based
on the document's contents.

The lossy aspects of this mapping — element ordering, comments, and mixed content — MUST be
stated as declared limits of the format's support.

#### Scenario: Declared repetition is stable at one occurrence

- **WHEN** a document containing exactly one element at a path declared as repeating is read
- **THEN** that path holds an array of length one

#### Scenario: Declared repetition is stable at many occurrences

- **WHEN** a document containing several elements at a path declared as repeating is read
- **THEN** that path holds an array with one entry per element, in document order

#### Scenario: Shape does not depend on the data

- **WHEN** two documents differing only in how many elements appear at a declared repeating path
  are read with the same declaration
- **THEN** both results hold an array at that path, and consuming code needs no test of which
  case occurred

#### Scenario: Same tag at different depths is declared independently

- **WHEN** the same element name appears at two different paths, one declared repeating and one
  not
- **THEN** each path takes the shape its own declaration specifies

#### Scenario: Attributes and text remain distinguishable

- **WHEN** a document containing both element attributes and element text is read
- **THEN** the result distinguishes attribute values from child elements and from element text,
  and writing that result back reproduces the same distinction
