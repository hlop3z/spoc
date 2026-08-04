# lab/ — disposable scripts

Single-file, self-contained, expected to die. Exploration, research, data gathering, spikes.

Every script starts with PEP 723 inline dependencies and a header stating why it exists:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Purpose: <one line>. Created: <YYYY-MM-DD>. Expires: <when this stops being useful>."""
```

Run with `uv run scripts/py/lab/<name>.py`. No workspace membership, no lockfile entry, no
package layout.

## The rules that keep this from becoming a junk drawer

- **The header is mandatory.** Purpose, created date, and an expiry condition.
- **Prune on sight.** A script past its expiry gets deleted, not archived. Git history is the
  archive.
- **Promote at two uses.** Used more than twice, or depended on by something else? It has
  stopped being disposable — move it to `../tools/<name>/` and delete it from here.
- **One file.** The moment a lab script wants a second module, it is asking to be promoted.

These are committed so they can be seen, reviewed, and promoted — not so they can accumulate.
