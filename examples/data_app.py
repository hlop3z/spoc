"""
Loading a project's own data with ``spoc.formats``.

Run with:  uv run python examples/data_app.py

Nothing here is wired into the framework. The kernel reads ``config/spoc.toml`` and stops;
everything below is the *project* loading its own files, which is the whole point of the
sidecar. Requires the extras:  pip install spoc[full]
"""

from pathlib import Path

from spoc import formats

BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    # One call for a whole tree of mixed formats — no loader per file, no format per call.
    data = formats.collect(BASE_DIR / "data")

    print("Collected:", ", ".join(sorted(data)))
    if data.skipped:
        print("Skipped:  ", len(data.skipped), "unsupported file(s)")

    # Exact addressing: configuration, where a typo must be loud.
    settings = data["settings"]
    host = formats.pointer(settings, "/server/host")
    port = formats.pointer(settings, "/server/port")
    print(f"\nServing on {host}:{port}")

    try:
        formats.pointer(settings, "/server/prt")
    except formats.PointerResolutionError as exc:
        print("Typo caught:", exc.segment)

    # Querying: datasets, where an empty result is a valid answer.
    books = data["catalog.books"]
    available = formats.query(books, "$[?@.status == 'available'].title")
    print("\nAvailable:", available)
    print("Missing:  ", formats.query(books, "$[?@.status == 'lost'].title"))

    featured = formats.query(data["catalog.tags"], "$[?@.featured == true].name")
    print("Featured tags:", featured)

    # The representation is format-agnostic, so writing it out is a one-liner.
    #
    # Note the target is *outside* `data/`. Writing `books.json` next to `books.csv`
    # would make both derive the key `catalog.books`, and the next collect() would
    # refuse the whole tree. Generated output does not belong in a collected tree.
    build = BASE_DIR / "build"
    build.mkdir(exist_ok=True)
    formats.write(books, build / "books.json")
    print("\nWrote build/books.json from the CSV, via the representation")
