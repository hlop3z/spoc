"""
The five codecs.

Standard-library modules are imported at the top — they cost nothing and are always present.
Every adopted dependency is imported *inside* its factory, so nothing here loads ruamel.yaml,
xmltodict, or tomli-w until that direction of that format is actually used.

Each decoder declares the options it accepts rather than swallowing ``**kwargs``: a
misspelled option is then a ``TypeError`` naming it, instead of silently doing nothing.
"""

from __future__ import annotations

import csv
import io
import json
import tomllib
from collections.abc import Callable
from typing import Any

from .core import Codec, DecodeFn, EncodeFn

# ── JSON — standard library, both directions ──────────────────────────────


def _json_reader() -> DecodeFn:
    def decode(text: str) -> Any:
        return json.loads(text)

    return decode


def _json_writer() -> EncodeFn:
    def encode(value: Any) -> str:
        return json.dumps(value, indent=2, ensure_ascii=False)

    return encode


# ── CSV — standard library, both directions ───────────────────────────────
#
# The mapping is CSVW minimal mode: an array of one object per data row, keyed by the
# header. `csv.DictReader` already produces exactly that, so standards alignment is free.


def _csv_reader() -> DecodeFn:
    def decode(text: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row in csv.DictReader(io.StringIO(text)):
            # DictReader files overflow cells under a None key — a value outside
            # the JSON data model that would round-trip as corrupted output.
            if None in row:
                raise ValueError(
                    f"Malformed CSV: row {len(rows) + 2} has more cells "
                    "than the header has columns"
                )
            rows.append(row)
        return rows

    return decode


def _csv_writer() -> EncodeFn:
    def encode(value: list[dict[str, Any]]) -> str:
        # CSVW minimal mode is the whole contract: anything but an array of
        # objects has no tabular meaning, so refuse it before csv mangles it.
        if not isinstance(value, list):
            raise ValueError(
                f"CSV encodes an array of objects, got {type(value).__name__}"
            )
        for index, row in enumerate(value):
            if not isinstance(row, dict):
                raise ValueError(
                    "CSV encodes an array of objects, "
                    f"but item {index} is {type(row).__name__}"
                )
        if not value:
            return ""
        # The header is the union of every row's keys, first appearance wins —
        # deriving it from row 0 alone would crash on any later row's new key.
        fieldnames = list(dict.fromkeys(key for row in value for key in row))
        out = io.StringIO()
        writer = csv.DictWriter(
            out, fieldnames=fieldnames, restval="", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(value)
        return out.getvalue()

    return encode


# ── TOML — reads on the standard library, writes only with the extra ──────


def _toml_reader() -> DecodeFn:
    def decode(text: str) -> Any:
        return tomllib.loads(text)

    return decode


def _toml_writer() -> EncodeFn:
    import tomli_w

    def encode(value: Any) -> str:
        return tomli_w.dumps(value)

    return encode


# ── YAML — ruamel.yaml, safe mode only ────────────────────────────────────


def _yaml_reader() -> DecodeFn:
    from ruamel.yaml import YAML

    def decode(text: str) -> Any:
        return YAML(typ="safe", pure=True).load(text)

    return decode


def _yaml_writer() -> EncodeFn:
    from ruamel.yaml import YAML

    def encode(value: Any) -> str:
        out = io.StringIO()
        YAML(typ="safe", pure=True).dump(value, out)
        return out.getvalue()

    return encode


# ── XML — xmltodict, with repetition declared by path ─────────────────────


def _repeating_predicate(paths: tuple[str, ...]) -> Callable[..., bool]:
    """Turn declared dotted paths into xmltodict's ``force_list`` callable.

    The callable receives ``(path, key, value)`` where ``path`` is a tuple of
    ``(name, attrs)`` ancestor pairs. Declared paths are relative to the document's root
    element, which is excluded — so ``book.author`` matches ``<catalog><book><author>``.
    """
    wanted = {tuple(p.split(".")) for p in paths}

    def predicate(path: Any, key: str, value: Any) -> bool:
        ancestors = tuple(name for name, _ in path)[1:]
        return (*ancestors, key) in wanted

    return predicate


def _xml_reader() -> DecodeFn:
    import xmltodict

    def decode(text: str, repeating: tuple[str, ...] = ()) -> Any:
        # Namespace processing stays off: prefixes then survive verbatim and round-trip
        # exactly, which enabling it would lose (design.md D3, spike findings).
        return xmltodict.parse(
            text,
            force_list=_repeating_predicate(tuple(repeating)) if repeating else None,
        )

    return decode


def _xml_writer() -> EncodeFn:
    import xmltodict

    def encode(value: Any) -> str:
        return xmltodict.unparse(value, pretty=True)

    return encode


#: Every declared format. The registry is assembled from this in ``__init__.py``.
CODECS: tuple[Codec, ...] = (
    Codec("json", (".json",), _json_reader, _json_writer),
    Codec("csv", (".csv",), _csv_reader, _csv_writer),
    Codec("toml", (".toml",), _toml_reader, _toml_writer, write_extra="toml"),
    Codec(
        "yaml",
        (".yaml", ".yml"),
        _yaml_reader,
        _yaml_writer,
        read_extra="yaml",
        write_extra="yaml",
    ),
    Codec(
        "xml",
        (".xml",),
        _xml_reader,
        _xml_writer,
        read_extra="xml",
        write_extra="xml",
    ),
)
