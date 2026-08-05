# Format Codecs — delta

## MODIFIED Requirements

### Requirement: Tabular data maps to a sequence of records

A tabular format MUST read as an array of objects, one per data row, with the header row
supplying the keys. This mapping MUST match the minimal-mode output defined by the adopted
tabular-to-JSON standard.

Every value MUST read as a string, because the format carries no type information and
inferring one from a value's appearance would make a row's type depend on its contents. This
consequence — that comparisons over tabular values are lexicographic, not numeric — MUST be
stated wherever the format is documented, since it is silent rather than loud.

A data row whose cell count differs from the header in either direction MUST fail the
read naming the row. A short row is never padded with placeholder values — the refusal
mirrors the refusal of an overflowing row, so every produced record carries exactly the
header's keys with string values.

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

#### Scenario: A short row is refused like an overflowing one

- **WHEN** a tabular source contains a data row with fewer cells than the header
- **THEN** the read fails naming that row, and no record padded with placeholder values
  is produced

## ADDED Requirements

### Requirement: Write failures surface through the declared error family

Writing a value that the target format cannot express MUST fail with the surface's own
declared error family, naming the format and the offending value — never as a raw error
escaping from an underlying serializer.

#### Scenario: An inexpressible value fails within the family

- **WHEN** a value outside the target format's expressible set is written
- **THEN** the operation fails with the surface's own error family naming the format and
  the offending value, and no underlying serializer's error type reaches the caller

### Requirement: Writing creates the path it is given

Writing to a filesystem path whose parent directories do not yet exist MUST create them
and complete the write, rather than failing on the missing directory.

#### Scenario: A fresh output path succeeds

- **WHEN** a value is written to a path under a directory that does not yet exist
- **THEN** the write succeeds and the file exists at exactly that path
