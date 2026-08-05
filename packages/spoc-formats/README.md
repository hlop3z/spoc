# spoc-formats

Read, write, collect, and address structured data. Five formats normalize to
one representation drawn from the JSON data model — `Any Format → JSON → Any
Format` — so everything above the boundary is written once, not once per
format.

```python
import spoc_formats as formats

settings = formats.read("config/app.yaml")
data = formats.collect("data")                            # a tree of mixed formats, one mapping
port = formats.pointer(settings, "/server/port")          # exact — raises if absent
live = formats.query(data["users"], "$[?@.active == true].email")
```

JSON, CSV, and TOML *reading* are standard library and work on a bare install;
YAML, XML, and TOML *writing* live behind extras and say so when missing:

```bash
pip install spoc-formats            # stdlib formats only
pip install spoc-formats[full]      # everything
```

This distribution is a sidecar of the [SPOC](https://pypi.org/project/spoc)
kernel and shares its repository, but neither package imports the other —
install either alone.
