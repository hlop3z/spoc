# Project Data and Config

`spoc.formats` is how a project reads **its own** configuration and fixtures —
JSON, TOML, CSV, YAML, XML — all landing in **one shape**: plain Python dicts,
lists, strings, numbers, booleans, and `None` (the JSON data model). Read any
format, work with one shape, write any format.

It exists because config management is where a growing project quietly starts
losing time: a loader per file, a format decided once and regretted later, and
fixtures that only a programmer can open.

```python
from spoc import formats
```

## Why five formats

A project does not have one audience for its data, so it should not be forced
into one format. Each of these earns its place by **who writes the file and who
reads it**:

| Format   | Written by → read by          | Why this one                                                                                                                                                                                         |
| -------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **YAML** | a person → the machine        | Comments, block strings, no quoting ceremony. The format to hand someone who edits configuration by hand and does not write Python. Needs the `yaml` extra.                                          |
| **TOML** | the system → the machine      | Unambiguous types and one obvious way to write a table. The same format `spoc.toml` uses, so operational configuration reads the same everywhere. Reading is stdlib; writing needs the `toml` extra. |
| **JSON** | a machine → a machine         | Universal, exact, no dialects to argue about. What you emit for another program to consume, and what every language already parses. Standard library.                                                |
| **CSV**  | a spreadsheet ↔ the machine   | Fixtures a non-programmer can open in Excel, Numbers or Sheets, edit, and hand back. Tabular data stays reviewable by the people who actually own it. Standard library.                              |
| **XML**  | a legacy system → the machine | Present because something upstream still emits it, not because you should reach for it. Needs the `xml` extra.                                                                                       |

Choose per file, not per project. `collect()` reads a tree of mixed formats in
one call, and everything downstream sees the same shape whichever format a
value arrived in — so the choice stays a question about the file's readers, and
never leaks into the code that consumes it.

## One grammar, the registry's own

Collection keys come from a file's **location**, and each segment must match
`^[a-z][a-z0-9_]*$` — the same grammar the registry holds
`kind:namespace.object_name` to:

```
data/settings.toml        →  settings
data/catalog/books.csv    →  catalog.books
data/catalog/tags.yaml    →  catalog.tags
```

So a project addresses its data the way it addresses its components, and a name
that would be illegal as a component name is illegal as a data key too. The two
surfaces share a convention, never code.

## Contained by design

The kernel never imports this, importing `spoc` never loads it, and removing it
entirely would leave startup unchanged — a boundary the test suite enforces
rather than packaging. `spoc.toml` stays the kernel's own business, read through
the standard library. Everything here is the _project_ loading the project's
files.

## Read and write files

The format comes from the file extension, or say it explicitly. Two small
data files serve every example on this page:

```toml title="data/settings.toml"
[server]
port = 8080
```

```json title="data/users.json"
[{ "name": "ada", "active": true, "email": "ada@example.com" }]
```

```python title="main.py"
from spoc import formats

settings = formats.read("data/settings.toml")   # → dict
formats.write(settings, "settings.json")        # dict → file

print(formats.loads('{"port": 8080}', "json"))  # text → value
print(formats.dumps({"port": 8080}, "toml"))    # value → text
```

Works on a bare install: JSON, CSV, and TOML reading are pure standard
library. YAML, XML, and TOML _writing_ each need
[one extra](../getting-started/installation.md#extras-only-if-you-want-them) —
and ask for it by name when missing:

```python
from spoc import formats

formats.supported()   # every format, with read/write available *right here*
```

## Read a whole folder: `collect`

Point at a directory and get one mapping — keys follow the folder layout, not
the file formats:

```python title="main.py"
from spoc import formats

data = formats.collect("data")
# data/settings.toml + data/users.json  →  {"settings": {...}, "users": [...]}
print(sorted(data))   # ['settings', 'users']
```

Collection is all-or-nothing: a malformed file fails the call right there,
naming the file — not later, in whatever code first touches the bad value.
Two files that would claim the same key (`users.json` _and_ `users.csv`) are
a collision and fail loudly. Hidden files are skipped; pass `ignore=` globs to
skip more.

## Reach into the data: `pointer` and `query`

Two tools, because two different questions:

**"Give me exactly this."** — JSON Pointer ([RFC 6901](https://datatracker.ietf.org/doc/html/rfc6901)).
One value comes back, or it's an error naming the step that failed. Use it
when absence means something is broken:

```python title="main.py"
from spoc import formats

settings = formats.read("data/settings.toml")

port = formats.pointer(settings, "/server/port")    # 8080 — or a loud error
print(port)
```

**"Give me whatever matches."** — JSONPath ([RFC 9535](https://datatracker.ietf.org/doc/html/rfc9535),
needs the `query` extra). A list comes back, and empty is a perfectly good
answer. Use it when you're selecting:

```python title="main.py"
from spoc import formats

users = formats.read("data/users.json")

emails = formats.query(users, "$[?@.active == true].email")   # maybe []
print(emails)   # ['ada@example.com']
```

SPOC never blurs the two: `pointer` won't return a default, and `query` won't
raise about an empty match.

Next: [the API reference](../api/public.md).
