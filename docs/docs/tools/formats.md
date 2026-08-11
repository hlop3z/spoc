# Reading Data Files

`spoc.formats` is a small toolbox for structured data files — JSON, TOML,
CSV, YAML, XML — that all land in **one shape**: plain Python dicts, lists,
strings, numbers, booleans, and `None` (the JSON data model). Read any format,
work with one shape, write any format.

It's a side toolbox: the kernel never uses it, and importing `spoc` never
loads it.

```python
from spoc import formats
```

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
library. YAML, XML, and TOML *writing* each need
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
Two files that would claim the same key (`users.json` *and* `users.csv`) are
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
