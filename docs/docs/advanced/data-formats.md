# Data & Formats

`spoc.formats` reads, writes, collects, and addresses structured data. It ships inside the
`spoc` distribution as a **contained subpackage** — the kernel never imports it, importing
`spoc` never loads it, and `Framework.start()` never calls it (a boundary the test suite
enforces). Reading `spoc.toml` remains the kernel's own job through the standard library.

Use it when your project needs to load its *own* data — fixtures, lookup tables, seed files,
per-app settings — without hand-writing a loader per file and per format.

## One representation

Every format normalizes to the same thing: a value drawn from the **JSON data model** — object,
array, string, number, boolean, null. Nothing format-specific crosses the boundary, which is
what lets one query language work over all of them.

```
Any format ──► JSON representation ──► Any format
```

```python
from spoc import formats

settings = formats.read("config/app.yaml")     # format inferred from the extension
formats.write(settings, "build/app.json")      # converted, no pairwise rule needed
```

## What costs a dependency

The bare `spoc` install acquires nothing. JSON, CSV, and TOML *reading* are standard
library and work with no extras; the rest is opt-in — the extras are the feature flags.

| Format | Read | Write | Extra |
| ------ | ---- | ----- | ----- |
| JSON   | ✅ stdlib | ✅ stdlib | — |
| CSV    | ✅ stdlib | ✅ stdlib | — |
| TOML   | ✅ stdlib | needs extra | `spoc[toml]` |
| YAML   | needs extra | needs extra | `spoc[yaml]` |
| XML    | needs extra | needs extra | `spoc[xml]` |
| *addressing* | — | — | `spoc[query]` |

```bash
pip install "spoc[full]"     # everything
pip install "spoc[yaml]"     # just YAML
```

A format whose extra is missing fails **when you ask for it**, naming what to install — never
as an `ImportError` from somewhere inside the library:

```python
>>> formats.read("app.yaml")
MissingDependencyError: Cannot read 'yaml': it needs an optional dependency
that is not installed. Install it with: pip install "spoc[yaml]"
```

Ask what the current environment can actually do:

```python
for fmt in formats.supported():
    print(fmt.name, fmt.can_read, fmt.can_write)
```

## Collecting a tree

Point `collect()` at a directory and get one mapping. Keys are the file's location with the
extension dropped and separators rendered as dots.

```
data/
├── settings.toml          →  "settings"
└── blog/
    ├── posts.json         →  "blog.posts"
    └── authors.yaml       →  "blog.authors"
```

```python
data = formats.collect("data")
data["blog.posts"]        # already parsed
data.skipped              # files whose extension matched no format
```

An existing empty directory collects to an empty mapping; a root that does not exist fails
with `CollectionError` — a typo'd path is a defect, not an empty result.

Three things this deliberately will **not** do:

- **It is not lazy.** Everything is parsed before `collect()` returns, so a malformed file
  fails *here* rather than in whatever code path first reads that key. `data.keys()` is
  therefore always truthful — every key present is a value already loaded.
- **It never picks a winner.** `settings.toml` and `settings.yaml` in one directory derive the
  same key, and that fails naming both paths. A silent precedence rule is the worse failure.

    !!! warning "Never write generated output into a collected tree"
        Converting `books.csv` and writing `books.json` beside it makes both derive the key
        `catalog.books` — and the *next* `collect()` refuses the whole directory. Write
        conversions somewhere outside the collection root.
- **It does not invent a name.** Every key segment must satisfy the same grammar the kernel
  uses for component names (`^[a-z][a-z0-9_]*$`), so `Posts.json` and `my.data.json` are
  rejected rather than quietly reshaped.

## Addressing: two standards, split by failure

This is the part worth reading twice. There are two ways to reach into the representation and
**they differ in what happens when nothing is there.**

| | `pointer()` | `query()` |
| --- | --- | --- |
| Standard | RFC 6901 (JSON Pointer) | RFC 9535 (JSONPath) |
| Syntax | `/server/port` | `$.users[?@.active == true]` |
| Returns | exactly one value | a list, possibly empty |
| On no match | **raises**, naming the segment | returns `[]` |
| Use for | configuration | datasets |

```python
formats.pointer(settings, "/server/port")        # 8080
formats.pointer(settings, "/serverr/port")       # PointerResolutionError: ... segment 'serverr'

formats.query(users, "$[?@.active == true].email")   # ['a@example.com']
formats.query(users, "$[?@.nonesuch].email")         # []
```

The split exists because a typo in a config path should be loud, while a filter matching zero
rows is a legitimate answer. Neither can be relaxed into the other.

!!! note "One RFC 9535 subtlety"
    A bare relative query inside a filter is an **existence** test, not a truthiness test.
    `$.users[?@.active]` matches every user that *has* an `active` key, including
    `active: false`. To test the value, compare it: `$.users[?@.active == true]`.

!!! warning "CSV carries no types — every value is a string"
    A tabular row reads as `{"age": "9"}`, never `{"age": 9}`. So a numeric-looking filter is
    a **lexicographic** comparison and quietly means something else:

    ```python
    rows = formats.loads("name,age\nada,9\nbob,41\n", "csv")
    formats.query(rows, "$[?@.age > '40'].name")   # ['ada', 'bob'] — '9' > '40' as strings
    ```

    Convert before comparing, or keep typed data in a format that carries types. The standard
    answer for typed CSV columns is CSVW's standard mode, which SPOC does not implement.

SPOC pins the engine to strict RFC 9535 — the underlying library's non-standard extensions
(keys selector, unions, intersections, pseudo-root) are **rejected**, so a query that works
here works on any conformant engine.

## XML: declare what repeats

XML is the one format whose shape is genuinely ambiguous. A single `<book>` could be the only
one or one of many, and the document does not say which. Rather than guess from occurrence
counts — which breaks the moment a document has exactly one row — you declare it:

```python
formats.read("catalog.xml", repeating=("book", "book.author"))
```

Declared paths are relative to the root element, which is excluded. A declared path **always**
yields a list, at one element and at fifty, so consuming code never tests which case it got.

### What XML does not preserve

These are stated limits, not bugs. If you need them, XML is the wrong format for that data:

- **Comments are dropped** entirely.
- **Mixed content is merged, not just reordered.** `<p>Hello <b>world</b>!</p>` reads as
  `{"b": "world", "#text": "Hello !"}` — the two text fragments are concatenated and their
  position relative to the child element is gone.
- **Element ordering** among differently-named siblings is not preserved.

Namespaces *are* preserved: prefixes survive verbatim as key text (`dc:title`) and round-trip
exactly.

Round-tripping is stable at the **value** level — read → write → read is equal — but not at the
byte level, for the reasons above.

## Where it does not reach

- It performs no schema validation. Normalizing and addressing only.
- It does not register anything in the component registry. Collected data is plain data; it
  does not become `data:blog.posts` or take part in resolution.
- It does not stream. Files must fit in memory.
- It is not a command-line converter. [`dasel`](https://github.com/TomWright/dasel) already
  covers exactly these five formats.
