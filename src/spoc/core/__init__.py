"""
The kernel's internals, reachable for anyone extending it.

The top-level ``spoc`` package is the surface a framework author needs. This layer
sits under it, one module per concern, and nothing here imports anything above it:

- :mod:`spoc.core.identity` — the identifier grammar, and the one conversion feeding it
- :mod:`spoc.core.registry` — the flat component store and its faceted reads
- :mod:`spoc.core.declaration` — kind specs, the marker, and discovery
- :mod:`spoc.core.loader` — dependency-ordered module loading and lifecycle dispatch
- :mod:`spoc.core.config` — the configuration adapter (the only module that reads files)
- :mod:`spoc.core.exceptions` — the kernel's error family

Import the submodule you need; this package re-exports nothing, so the composition
root stays the one place the pieces are wired together.
"""
