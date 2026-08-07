"""
What a generated project records about where it came from.

The record exists so a later operation can notice that the template set it is
about to render is not the one that produced the project. Emitting a mismatched
app shape silently is the failure this prevents; it is a report, never a refusal,
because a project may legitimately draw from more than one set.

Nothing reads this at runtime. A project whose record is deleted still starts —
the record is a note for tooling, not configuration.

**The scaffolder writes it; a template set cannot.** Both directions of the
record's shape live here, so the writer and the reader cannot drift, and the
values it carries never pass through template substitution — there is no
rendering path by which a set could suppress the record or supply its content.
:data:`RECORD_NAME` is reserved for that reason, enforced in the pure core.

JSON, not TOML: a reference is whatever the author typed — ``C:\\templates\\mine``
carries backslashes, and nothing forbids a quote — so emitting the record is
serialization, not substitution. The standard library writes JSON and reads it;
it has no TOML writer, and hand-rolling escaping for a standard format is the
rule this project does not break. See the ADR in ``DECISIONS.md``.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .plan import PlannedFile

#: Where the record lives inside a generated project. Dotted so it sits with the
#: other tooling metadata rather than in the project's own namespace.
RECORD_NAME = ".spoc-template.json"

#: Carried inside the record because JSON has no comments, and a generated file
#: that cannot say what it is for invites deletion by guesswork.
NOTE = (
    "Where this project came from. Written once, by `spoc init`. Nothing reads "
    "it at runtime — deleting this file leaves a project that still starts. "
    "`spoc app` reads it to notice when the template set it is about to render "
    "differs from the one that generated the project, so a mismatched app shape "
    "is never emitted silently."
)


@dataclass(frozen=True, slots=True)
class Origin:
    """The template set a project was generated from."""

    reference: str
    revision: str
    set_name: str

    def describe(self) -> str:
        """One line naming this origin as precisely as it can be named."""
        if self.revision:
            return f"{self.reference} (revision {self.revision})"
        return self.reference or self.set_name


def record_content(origin: Origin) -> str:
    """Serialize an origin into the record's text.

    Built as a data structure and handed to a serializer — no format is
    assembled here, which is what keeps every value the caller can supply
    round-trippable through :func:`read_origin`.
    """
    document = {
        "note": NOTE,
        "template": {
            "reference": origin.reference,
            "revision": origin.revision,
            "set": origin.set_name,
        },
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def record_file(origin: Origin) -> PlannedFile:
    """The record as a plan entry.

    Contributed by the generating operation rather than by the rendered template
    set, but an ordinary :class:`PlannedFile` once contributed — so it inherits
    never-overwrite and all-or-nothing like any other generated file.
    """
    return PlannedFile(path=RECORD_NAME, content=record_content(origin))


def read_origin(project_root: Path) -> Origin | None:
    """Read a project's origin record, or None when it carries none.

    A malformed or partial record reads as absent rather than raising: the
    record is advisory, and failing an unrelated operation because a note is
    unparseable would make it a liability instead of a help.
    """
    record = project_root / RECORD_NAME
    if not record.is_file():
        return None

    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    template = data.get("template") if isinstance(data, dict) else None
    if not isinstance(template, dict):
        return None

    return Origin(
        reference=str(template.get("reference", "")),
        revision=str(template.get("revision", "")),
        set_name=str(template.get("set", "")),
    )


def describe_divergence(recorded: Origin | None, rendering: Origin) -> str | None:
    """Compare a project's recorded origin against what is about to be rendered.

    Returns the message to report, or None when there is nothing to say. An
    absent record is reported as unknown rather than treated as agreement — the
    author should know the comparison could not be made.
    """
    if recorded is None:
        return (
            f"This project records no origin, so its template set could not be "
            f"compared with {rendering.describe()}. The generated app may not "
            f"match the shape of the rest of the project."
        )

    if _matches(recorded, rendering):
        return None

    return (
        f"This project was generated from {recorded.describe()}, but the app is "
        f"being rendered from {rendering.describe()}. The generated app may not "
        f"match the shape of the rest of the project."
    )


def _matches(recorded: Origin, rendering: Origin) -> bool:
    """Same set, and — where both name one — the same revision.

    A recorded revision compared against a set that has none is not a mismatch:
    a local directory legitimately has no revision, and reporting that as
    divergence every time would train the author to ignore the message.
    """
    if recorded.reference != rendering.reference:
        return False
    if recorded.revision and rendering.revision:
        return recorded.revision == rendering.revision
    return True
