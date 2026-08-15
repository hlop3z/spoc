# Rule 9 — Adopt global standards, identifiers, and vocabularies

**Trigger:** defining a schema, an API contract, an identifier, a vocabulary, or a data
classification.

This is Rule 7's never-reinvent principle applied to **data**: an invented schema format, ID
scheme, or vocabulary is a wheel reinvented, and it costs interoperability forever. Prefer the
recognized standard; deviating from an applicable one is a decision recorded in
`DECISIONS.md`, never a silent default.

## Contracts and schemas

| Contract               | Standard        |
| ---------------------- | --------------- |
| Data shape, validation | **JSON Schema** |
| Synchronous HTTP APIs  | **OpenAPI**     |
| Events and messaging   | **AsyncAPI**    |

Schemas are native-format files loaded through an adapter, never string literals in code —
see _Externalize native-format content_ in `.canon/guidelines.md`.

## Identity

When an entity has a globally recognized identifier, **store it** — a private key alone makes
the data an island.

| Entity                          | Identifier                                     |
| ------------------------------- | ---------------------------------------------- |
| Knowledge entities              | **Wikidata QID**                               |
| Research publications, datasets | **DOI**                                        |
| Researchers                     | **ORCID**                                      |
| Legal entities                  | **LEI**                                        |
| System-level records            | **UUID** (v7 where ordering by creation helps) |

The pattern: a system-level UUID as the internal key, plus the external global identifier as
an attribute. Never mint a bespoke ID scheme for a category that already has one.

## Semantics

- **Schema.org** for structured web-facing data.
- **RDF concepts** (subject–predicate–object, IRIs) when modeling semantic relationships or
  linked data — don't invent a private graph vocabulary first.
- **ISO standards** for industry classifications the domain touches (country codes 3166,
  currencies 4217, dates and times 8601, language tags 639) — these are never hand-rolled,
  per the mandatory-adopt list in `.canon/guidelines.md`.

## Guardrails

- A schema, ID scheme, or vocabulary invented where a recognized one applies is a defect.
- Adopting a standard **partially** (a "JSON Schema-ish" validator, a "UUID-like" string) is
  worse than not adopting it — it signals compatibility it doesn't have.
- Standards enter the system at the boundary layer: parsing and validation live in adapters
  (Rule 2); the domain sees typed, validated values.
