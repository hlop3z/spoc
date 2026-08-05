"""
Isolation and mode-override scopes, promoted from the suite's proven fixtures.

Everything here composes the kernel's public API. The isolation scope owns the
process state a boot mutates — import search paths and loaded modules — and
guarantees restoration on every exit path; the kernel itself never touches
``sys.path`` (that contract is pinned by the kernel's own tests).
"""

from __future__ import annotations

import sys
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..core.declaration import KindSpec
from ..framework import Framework

__all__ = ["MissingDependencyError", "import_state", "isolated", "mode"]


class MissingDependencyError(ImportError):
    """A capability is supported, but the extra that enables it is not installed.

    Mirrors the ``spoc.formats`` contract: name the extra to install, never
    leak a transitive ``ImportError``.
    """

    def __init__(self, capability: str, extra: str) -> None:
        self.capability, self.extra = capability, extra
        super().__init__(
            f"{capability} requires the {extra!r} extra, which is not "
            f'installed. Install it with: pip install "spoc[{extra}]"'
        )


def dump_toml(value: dict[str, Any]) -> str:
    """Serialize a dict to TOML text, or refuse loudly without the extra."""
    try:
        import tomli_w
    except ImportError as exc:
        raise MissingDependencyError(
            "the test harness's TOML emission", "toml"
        ) from exc
    return tomli_w.dumps(value)


@contextmanager
def import_state() -> Iterator[None]:
    """Snapshot ``sys.path`` and ``sys.modules``; restore both on exit.

    The building block under :func:`isolated`, exposed for suites that manage
    framework lifecycles themselves but still must not leak app imports
    between tests.
    """
    path_before = list(sys.path)
    modules_before = set(sys.modules)
    try:
        yield
    finally:
        sys.path[:] = path_before
        for name in set(sys.modules) - modules_before:
            del sys.modules[name]


@contextmanager
def isolated(
    base_dir: Path | str,
    *kinds: str | KindSpec,
    framework: Framework | None = None,
    start: bool = True,
) -> Iterator[Framework]:
    """Yield a framework booted against `base_dir`, torn down on every exit.

    The scope makes `base_dir` importable (exactly as a real entry point's
    script directory would be), snapshots ``sys.path`` and ``sys.modules``,
    and on exit — normal or exceptional — shuts the framework down and
    restores both snapshots, so consecutive scopes observe nothing from each
    other.

    Pass ``kinds`` to have the scope construct the framework, or a prebuilt
    ``framework=`` to configure declaration (hooks, :class:`KindSpec`) first —
    stating both is contradictory and refused. ``start=False`` yields an inert
    framework for tests that exercise boot itself.
    """
    if framework is not None and kinds:
        raise ValueError("state kinds or pass a prebuilt framework, not both")
    base = Path(base_dir)
    fw = framework if framework is not None else Framework(*kinds)

    with import_state():
        sys.path.insert(0, str(base))
        try:
            if start:
                fw.start(base)
            yield fw
        finally:
            if fw.started:
                fw.shutdown()


def _config_path(base_dir: Path) -> Path:
    """The tree's config file, in the kernel's own search order."""
    for candidate in (base_dir / "config" / "spoc.toml", base_dir / "spoc.toml"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"no spoc.toml under {base_dir} (looked in config/spoc.toml and spoc.toml)"
    )


@contextmanager
def mode(base_dir: Path | str, mode_name: str) -> Iterator[Path]:
    """Run the body with the tree's declared mode swapped to `mode_name`.

    Rewrites ``spoc.mode`` in the tree's ``spoc.toml`` on entry and restores
    the file's original bytes on exit, so mode-dependent behavior can be
    exercised without permanently altering the tree. Boot inside the scope —
    the kernel reads the file at ``start()``.
    """
    path = _config_path(Path(base_dir))
    original = path.read_bytes()
    config = tomllib.loads(original.decode("utf-8"))
    config.setdefault("spoc", {})["mode"] = mode_name
    path.write_text(dump_toml(config), encoding="utf-8")
    try:
        yield path
    finally:
        path.write_bytes(original)
