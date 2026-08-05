# Reunify the Formats Distribution

## Why

The formats toolkit is not an unrelated add-on — SPOC is the single point of
connections for a project, and reading data files is a capability of that point. The
two-distribution split solved problems this project does not have (independent release
cadence, wheel purity) at costs it pays immediately: a second PyPI project to claim
and operate, a second import name to discover, and a weaker one-install story. The
real defects the split fixed — `FormatError` subclassing `SpocError` and a blurred
import boundary — are orthogonal to packaging and are kept. `v0.5.0` is untagged and
`spoc-formats` has never been published, so this is the last cheap moment to decide.

## What Changes

- **BREAKING** (against unreleased 0.5.0 commits only): the `spoc-formats`
  distribution is dissolved. Its package returns as the contained subpackage
  `spoc.formats`; the uv workspace reverts to a single project; one artifact is
  built and published.
- The extras (`yaml`, `xml`, `toml`, `query`, `full`) move back onto `spoc`
  (`pip install "spoc[full]"`). The bare install keeps `dependencies = []`.
- The containment boundary becomes a pinned contract: the kernel never imports
  `spoc.formats`, importing `spoc` never loads it, and `FormatError` stays
  independent of `SpocError` — enforced by a test, not by packaging.
- Release/CI collapse to the single-artifact path; docs, README, example, and the
  changelog return to one install/import story.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `data-collection`: the "Collection does not participate in framework startup"
  requirement gains a containment scenario — importing the kernel does not load the
  data surface, now that both live in one distribution.

## Impact

- **Code**: `packages/spoc-formats/src/spoc_formats/` → `src/spoc/formats/`;
  internal imports rename; `packages/` is deleted (Rule 5).
- **Packaging**: root `pyproject.toml` regains the extras; workspace tables and the
  `spoc-formats` source reference are removed; dev group depends on the extras; the
  lockfile regenerates.
- **Tests**: `packages/spoc-formats/tests/test_formats.py` → `tests/`; a new
  boundary test pins containment; `testpaths` and the ty override shrink.
- **CI/Release**: `release.yml` builds/publishes one artifact; the wheel check
  inverts (formats code MUST now be present).
- **Docs**: install/import instructions, architecture diagram, README(s),
  CHANGELOG's unreleased 0.5.0 section, `DECISIONS.md` (supersedes the
  multi-distribution ADR).
