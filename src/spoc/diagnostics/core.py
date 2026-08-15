"""
The diagnostic operations — library-first, CLI-agnostic.

Each operation is an isolated dry boot composed from :mod:`spoc.testing`'s
scopes: process state (``sys.path``, ``sys.modules``) is restored and the
framework is shut down before the call returns, so nothing outlives it.

Findings reuse the kernel's own error text verbatim — the diagnostics never
rephrase a failure the kernel already states precisely. A non-SPOC exception
raised by an app's own module code propagates untouched, the same doctrine
the lifecycle holds: that error is the app author's, and check imports your
apps.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from ..core.config import load_spoc_toml
from ..core.exceptions import ConfigurationError, SpocError, UnknownKindError
from ..framework import Framework
from ..locate import DEFAULT_FRAMEWORK_REF, LocateError, locate_framework
from ..projection import ComponentEntry
from ..testing import import_state

__all__ = [
    "CheckReport",
    "ComponentEntry",
    "Finding",
    "check",
    "explain",
    "list_records",
]

#: The marker the loader's sync-path refusal carries; seeing it means the
#: declaration is async-lifecycle and the dry boot should retry via astart.
_ASYNC_REFUSAL_MARKER = "use astart()"


@dataclass(frozen=True)
class Finding:
    """One problem check found. ``area`` is the phase that caught it
    (``config`` / ``locate`` / ``lifecycle`` / ``boot``); ``message`` is the
    kernel's own text."""

    area: str
    message: str


@dataclass(frozen=True)
class CheckReport:
    """Everything check gathered; ``ok`` is the exit-code truth."""

    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


def _start_any(fw: Framework, base: Path) -> str:
    """Boot on the sync path, falling back to astart when the declaration is
    async-lifecycle. Returns which path booted ('sync' | 'async'); re-raises
    the refusal so the caller decides whether it is a finding."""
    fw.start(base)
    return "sync"


def _teardown(fw: Framework, booted: str | None) -> None:
    if fw.started:
        if booted == "async":
            asyncio.run(fw.ashutdown())
        else:
            fw.shutdown()


@contextmanager
def _booted(
    base_dir: Path | str, framework_ref: str
) -> Iterator[tuple[Framework, str]]:
    """Locate, boot (either lifecycle path), yield, tear everything down."""
    base = Path(base_dir)
    with import_state():
        sys.path.insert(0, str(base))
        fw = locate_framework(framework_ref)
        try:
            booted = _start_any(fw, base)
        except SpocError as exc:
            if _ASYNC_REFUSAL_MARKER not in str(exc):
                raise
            asyncio.run(fw.astart(base))
            booted = "async"
        try:
            yield fw, booted
        finally:
            _teardown(fw, booted)


def check(
    base_dir: Path | str, framework_ref: str = DEFAULT_FRAMEWORK_REF
) -> CheckReport:
    """Validate a project before runtime; every finding is gathered, none
    stops the rest from being looked for."""
    base = Path(base_dir)
    findings: list[Finding] = []

    # Config phase: syntax, typing, and shape — no app code is imported.
    try:
        load_spoc_toml(base)
    except ConfigurationError as exc:
        # Unreadable configuration: the boot phase would only restate it.
        return CheckReport((Finding("config", str(exc)),))

    # Boot phase: a dry run surfaces everything the first real start would —
    # unresolvable apps/plugins, cycles, collisions, mode-cascade problems.
    with import_state():
        sys.path.insert(0, str(base))
        try:
            fw = locate_framework(framework_ref)
        except LocateError as exc:
            return CheckReport((*findings, Finding("locate", str(exc))))
        booted: str | None = None
        try:
            booted = _start_any(fw, base)
        except SpocError as exc:
            if _ASYNC_REFUSAL_MARKER in str(exc):
                # The sync path would refuse this declaration at first boot —
                # worth flagging — but the declaration itself may be fine, so
                # the dry run continues on the async path.
                findings.append(Finding("lifecycle", str(exc)))
                try:
                    asyncio.run(fw.astart(base))
                    booted = "async"
                except SpocError as async_exc:
                    findings.append(Finding("boot", str(async_exc)))
            else:
                findings.append(Finding("boot", str(exc)))
        finally:
            _teardown(fw, booted)

    return CheckReport(tuple(findings))


def list_records(
    base_dir: Path | str,
    framework_ref: str = DEFAULT_FRAMEWORK_REF,
    kind: str | None = None,
    namespace: str | None = None,
) -> list[ComponentEntry]:
    """Enumerate the registry, optionally narrowed by facet. An unknown kind
    fails with the kernel's candidate-naming error; namespaces are an open
    set, so an unknown one is simply empty.

    Records are described by the registry projection — the one structure that
    describes a component — so what `spoc list` reports and what the projection
    publishes cannot drift. Only the boot depth differs, and deliberately: this
    reports on a *started* project, which is the question `list` answers.

    A kind narrowing is answered by *reading that kind's facet*, not by walking
    everything registered and discarding what does not match. That is the whole
    point of the registry being keyed by the grammar's own segments — a facet is
    a sub-dictionary of the store — and this was the one reader asking for the
    store when it wanted a facet.

    Order comes from that read rather than being re-established here. Both
    readers enumerate in canonical identifier order, so sorting again was a
    second claim to a guarantee the registry already makes — the kind that stays
    correct right up until the two disagree. The namespace narrowing stays a
    filter: namespaces are an open set, and it runs over records already reduced
    to one kind."""
    with _booted(base_dir, framework_ref) as (fw, _):
        # Ahead of the read, and staying so: `by_kind` answers an undeclared
        # kind with an empty facet, and "unknown kind" must not degrade into
        # "nothing registered".
        if kind is not None and kind not in fw.registry.kinds:
            raise UnknownKindError(kind, fw.registry.kinds)
        records = fw.registry.all() if kind is None else fw.registry.by_kind(kind)
        return [
            ComponentEntry.from_component(c)
            for c in records
            if namespace is None or c.namespace == namespace
        ]


def explain(
    identifier: str,
    base_dir: Path | str,
    framework_ref: str = DEFAULT_FRAMEWORK_REF,
) -> ComponentEntry:
    """Resolve one identifier and describe its record. Resolution failures
    are the kernel's own — a typo names the failing segment and candidates."""
    with _booted(base_dir, framework_ref) as (fw, _):
        return ComponentEntry.from_component(fw.resolve(identifier))
