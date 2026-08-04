"""
Data-surface tests: one per scenario in the `format-codecs`, `data-collection`, and
`data-access` specs, plus the structural guarantees from design.md.

The optional extras are installed in this project's dev environment, so "the extra is
missing" is simulated with a codec whose factory raises `ImportError` rather than by
uninstalling anything — which is also the only way to test it deterministically.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from spoc import formats
from spoc.core.exceptions import InvalidSegmentError
from spoc.formats.core import READ, WRITE, Codec, FormatRegistry
from spoc.formats.errors import (
    CollectionError,
    DuplicateEntryError,
    MissingDependencyError,
    PointerResolutionError,
    UnknownFormatError,
    UnsupportedDirectionError,
)

WRITABLE = ("json", "csv", "toml", "yaml", "xml")

#: A value in every format's expressible intersection, used for cross-format conversion.
COMMON = {"server": {"host": "localhost", "port": 8080}}

SAMPLES: dict[str, str] = {
    "json": '{"server": {"host": "localhost", "port": 8080}}',
    "toml": '[server]\nhost = "localhost"\nport = 8080\n',
    "yaml": "server:\n  host: localhost\n  port: 8080\n",
}


def scalars(value: object) -> bool:
    """True when `value` is drawn only from the JSON data model."""
    if isinstance(value, dict):
        return all(isinstance(k, str) and scalars(v) for k, v in value.items())
    if isinstance(value, list):
        return all(scalars(v) for v in value)
    return value is None or isinstance(value, (str, int, float, bool))


# ── format-codecs: one representation ─────────────────────────────────────


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_reading_yields_only_json_model_values(name: str):
    """Nothing format- or parser-specific crosses the boundary."""
    assert scalars(formats.loads(SAMPLES[name], name))


def test_reading_xml_and_csv_yields_only_json_model_values():
    assert scalars(formats.loads("a,b\n1,2\n", "csv"))
    assert scalars(formats.loads("<c><b id='1'>x</b></c>", "xml"))


@pytest.mark.parametrize("name", WRITABLE)
def test_round_trip_through_the_representation_is_stable(name: str):
    """Read -> write -> read is equal at the value level, for every writable format."""
    value = {"a": [{"b": "1"}]} if name == "csv" else COMMON
    value = [{"b": "1", "c": "2"}] if name == "csv" else value
    first = formats.loads(formats.dumps(value, name), name)
    second = formats.loads(formats.dumps(first, name), name)
    assert first == second


def test_cross_format_conversion_needs_no_per_pair_knowledge():
    """Any format to any other, through the representation, with no pairwise rule."""
    for source in ("json", "toml", "yaml"):
        value = formats.loads(SAMPLES[source], source)
        for target in ("json", "toml", "yaml"):
            assert formats.loads(formats.dumps(value, target), target) == value


# ── format-codecs: text, files, and extensions ────────────────────────────


def test_text_and_file_agree(tmp_path: Path):
    target = tmp_path / "settings.yaml"
    target.write_text(SAMPLES["yaml"], encoding="utf-8")
    assert formats.read(target) == formats.loads(SAMPLES["yaml"], "yaml")


def test_explicit_format_overrides_the_extension(tmp_path: Path):
    """The file says .txt; the caller says json, and the caller wins."""
    target = tmp_path / "payload.txt"
    target.write_text(SAMPLES["json"], encoding="utf-8")
    assert formats.read(target, format="json") == COMMON


def test_unknown_extension_is_refused(tmp_path: Path):
    target = tmp_path / "notes.rst"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(UnknownFormatError) as exc:
        formats.read(target)
    assert ".rst" in str(exc.value)
    assert ".json" in str(exc.value)  # the supported set is listed


def test_write_infers_the_format_from_the_extension(tmp_path: Path):
    formats.write(COMMON, tmp_path / "out.toml")
    assert formats.read(tmp_path / "out.toml") == COMMON


# ── format-codecs: optional extras ────────────────────────────────────────


def _registry_missing_extra() -> FormatRegistry:
    """A registry whose one codec cannot import what it needs."""

    def explode():
        raise ImportError("no module named 'pretend'")

    return FormatRegistry(
        (Codec("pretend", (".pretend",), explode, explode, "pretend", "pretend"),)
    )


def test_missing_extra_is_reported_actionably():
    """Never a bare ImportError — the message names the extra to install."""
    registry = _registry_missing_extra()
    with pytest.raises(MissingDependencyError) as exc:
        registry.function("pretend", READ)
    assert "pip install spoc[pretend]" in str(exc.value)


def test_missing_extra_does_not_claim_the_direction_is_unsupported():
    registry = _registry_missing_extra()
    with pytest.raises(MissingDependencyError):
        registry.function("pretend", WRITE)


def test_unsupported_direction_is_refused_clearly():
    """A direction nothing can enable fails differently from a missing extra."""
    registry = FormatRegistry((Codec("readonly", (".ro",), lambda: str),))
    with pytest.raises(UnsupportedDirectionError) as exc:
        registry.function("readonly", WRITE)
    assert "unsupported" in str(exc.value)


def test_supported_directions_are_enumerable():
    """Enumeration reports what this environment can actually do, probed not assumed."""
    by_name = {s.name: s for s in formats.supported()}
    assert set(by_name) == {"json", "csv", "toml", "yaml", "xml"}
    assert by_name["json"].can_read and by_name["json"].can_write
    assert ".yml" in by_name["yaml"].extensions

    degraded = {s.name: s for s in _registry_missing_extra().supported()}
    assert degraded["pretend"].can_read is False
    assert degraded["pretend"].can_write is False


def test_standard_library_formats_declare_no_extra():
    """JSON and CSV must work on a bare install, so neither may name an extra."""
    from spoc.formats.codecs import CODECS

    stdlib = {c.name: c for c in CODECS}
    for name in ("json", "csv"):
        assert stdlib[name].read_extra is None
        assert stdlib[name].write_extra is None
    # TOML reads on the standard library but nothing in it writes TOML.
    assert stdlib["toml"].read_extra is None
    assert stdlib["toml"].write_extra == "toml"


# ── format-codecs: tabular ────────────────────────────────────────────────


def test_rows_become_records():
    """CSVW minimal mode: one object per data row, keyed by the header."""
    assert formats.loads("a,b\n1,2\n3,4\n", "csv") == [
        {"a": "1", "b": "2"},
        {"a": "3", "b": "4"},
    ]


def test_a_single_data_row_is_still_an_array():
    assert formats.loads("a,b\n1,2\n", "csv") == [{"a": "1", "b": "2"}]


# ── format-codecs: hierarchical markup ────────────────────────────────────

ONE_BOOK = "<catalog><book id='1'/></catalog>"
TWO_BOOKS = "<catalog><book id='1'/><book id='2'/></catalog>"


def test_declared_repetition_is_stable_at_one_occurrence():
    result = formats.loads(ONE_BOOK, "xml", repeating=("book",))
    assert result["catalog"]["book"] == [{"@id": "1"}]


def test_declared_repetition_is_stable_at_many_occurrences():
    result = formats.loads(TWO_BOOKS, "xml", repeating=("book",))
    assert result["catalog"]["book"] == [{"@id": "1"}, {"@id": "2"}]


def test_shape_does_not_depend_on_the_data():
    """The whole point of declaring paths: consuming code needs no cardinality test."""
    one = formats.loads(ONE_BOOK, "xml", repeating=("book",))
    two = formats.loads(TWO_BOOKS, "xml", repeating=("book",))
    assert isinstance(one["catalog"]["book"], list)
    assert isinstance(two["catalog"]["book"], list)


def test_same_tag_at_different_depths_is_declared_independently():
    """`item` repeats under `cart` but not under `meta` — a tag-keyed hint could not say so."""
    doc = "<r><cart><item>a</item></cart><meta><item>solo</item></meta></r>"
    result = formats.loads(doc, "xml", repeating=("cart.item",))
    assert result["r"]["cart"]["item"] == ["a"]
    assert result["r"]["meta"]["item"] == "solo"


def test_attributes_and_text_remain_distinguishable():
    doc = "<book id='1'><title>Dune</title></book>"
    parsed = formats.loads(doc, "xml")
    assert parsed["book"]["@id"] == "1"
    assert parsed["book"]["title"] == "Dune"
    assert "@id" in formats.dumps(parsed, "xml") or 'id="1"' in formats.dumps(
        parsed, "xml"
    )


def test_namespaces_survive_the_round_trip():
    """design.md D3 spike: namespaces are *not* in the lossy set, so this must hold."""
    doc = '<c xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:t>x</dc:t></c>'
    parsed = formats.loads(doc, "xml")
    assert parsed["c"]["dc:t"] == "x"
    assert formats.loads(formats.dumps(parsed, "xml"), "xml") == parsed


# ── data-collection ───────────────────────────────────────────────────────


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "blog").mkdir(parents=True)
    (root / "settings.toml").write_text(SAMPLES["toml"], encoding="utf-8")
    (root / "blog" / "posts.json").write_text('[{"id": 1}]', encoding="utf-8")
    (root / "blog" / "authors.yaml").write_text("- name: a\n", encoding="utf-8")
    (root / "README.md").write_text("not a data file", encoding="utf-8")
    return root


def test_mixed_formats_collect_together(tree: Path):
    collected = formats.collect(tree)
    assert collected["settings"] == COMMON
    assert collected["blog.posts"] == [{"id": 1}]
    assert collected["blog.authors"] == [{"name": "a"}]


def test_unsupported_files_are_skipped_not_fatal(tree: Path):
    collected = formats.collect(tree)
    assert any(s.endswith("README.md") for s in collected.skipped)
    assert "README" not in collected


def test_nested_directories_are_included(tree: Path):
    assert "blog.posts" in formats.collect(tree)


def test_empty_or_absent_directory_is_not_an_error(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    assert dict(formats.collect(tmp_path / "empty")) == {}
    assert dict(formats.collect(tmp_path / "never-created")) == {}


def test_keys_derive_from_relative_location(tmp_path: Path):
    """Same stem in different subdirectories occupies distinct keys."""
    for sub in ("a", "b"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "items.json").write_text("[]", encoding="utf-8")
    assert set(formats.collect(tmp_path)) == {"a.items", "b.items"}


def test_key_segment_violating_the_grammar_is_refused(tmp_path: Path):
    (tmp_path / "Posts.json").write_text("[]", encoding="utf-8")
    with pytest.raises(InvalidSegmentError) as exc:
        formats.collect(tmp_path)
    assert "Posts" in str(exc.value)


def test_dotted_filename_is_refused_rather_than_reinterpreted(tmp_path: Path):
    """`my.data.json` must not quietly become the two-segment key `my.data`."""
    (tmp_path / "my.data.json").write_text("[]", encoding="utf-8")
    with pytest.raises(InvalidSegmentError):
        formats.collect(tmp_path)


def test_same_stem_in_two_formats_is_refused(tmp_path: Path):
    (tmp_path / "settings.json").write_text("{}", encoding="utf-8")
    (tmp_path / "settings.yaml").write_text("{}", encoding="utf-8")
    with pytest.raises(DuplicateEntryError) as exc:
        formats.collect(tmp_path)
    assert "settings.json" in str(exc.value)
    assert "settings.yaml" in str(exc.value)


def test_a_malformed_file_fails_the_collection(tmp_path: Path):
    (tmp_path / "good.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(CollectionError) as exc:
        formats.collect(tmp_path)
    assert "bad.json" in str(exc.value)


def test_enumeration_is_truthful(tree: Path):
    """Keys present are exactly the values loaded — nothing raises on access."""
    collected = formats.collect(tree)
    assert set(collected) == {"settings", "blog.posts", "blog.authors"}
    assert len(collected) == 3
    for key in collected:
        assert collected[key] is not None


def test_collection_applies_per_format_options(tmp_path: Path):
    (tmp_path / "catalog.xml").write_text(ONE_BOOK, encoding="utf-8")
    collected = formats.collect(tmp_path, options={"xml": {"repeating": ("book",)}})
    assert collected["catalog"]["catalog"]["book"] == [{"@id": "1"}]


# ── data-access: exact addressing ─────────────────────────────────────────


def test_a_valid_address_resolves_to_its_value():
    assert formats.pointer(COMMON, "/server/port") == 8080


def test_a_misspelled_address_fails_naming_the_segment():
    with pytest.raises(PointerResolutionError) as exc:
        formats.pointer(COMMON, "/serverr/port")
    assert exc.value.segment == "serverr"


def test_absent_and_null_are_distinguishable():
    value = {"present": None}
    assert formats.pointer(value, "/present") is None
    with pytest.raises(PointerResolutionError):
        formats.pointer(value, "/absent")


def test_array_positions_are_addressable():
    value = {"items": ["a", "b"]}
    assert formats.pointer(value, "/items/1") == "b"
    with pytest.raises(PointerResolutionError):
        formats.pointer(value, "/items/9")


# ── data-access: querying ─────────────────────────────────────────────────

USERS = {"users": [{"n": "a", "active": True}, {"n": "b", "active": False}]}


def test_a_matching_query_returns_its_matches():
    assert formats.query(USERS, "$.users[*].n") == ["a", "b"]


def test_a_non_matching_query_returns_empty_not_an_error():
    assert formats.query(USERS, "$.missing[*]") == []


def test_filtering_selects_records_from_tabular_data():
    rows = formats.loads("name,role\nada,admin\nbob,guest\n", "csv")
    assert formats.query(rows, "$[?@.role == 'admin'].name") == ["ada"]


def test_tabular_values_are_strings_so_comparisons_are_lexicographic():
    """A consequence of CSV carrying no types, pinned so it cannot surprise anyone.

    `'9' > '40'` is true as strings, so a numeric-looking filter over CSV silently
    means something other than it appears to. Convert before comparing, or use a
    format that carries types. CSVW standard mode is the named upgrade path.
    """
    rows = formats.loads("name,age\nada,9\nbob,41\n", "csv")
    assert rows == [{"name": "ada", "age": "9"}, {"name": "bob", "age": "41"}]
    # Both match: '41' > '40' and '9' > '40', the second because '9' > '4'.
    assert formats.query(rows, "$[?@.age > '40'].name") == ["ada", "bob"]


def test_the_same_missing_location_behaves_differently_by_mode():
    """The distinction the two standards exist to draw."""
    assert formats.query(COMMON, "$.serverr.port") == []
    with pytest.raises(PointerResolutionError):
        formats.pointer(COMMON, "/serverr/port")


# ── data-access: RFC 9535 conformance (tasks.md 6.3) ──────────────────────

CONFORMANT = [
    # A bare relative query in a filter is an EXISTENCE test, not a truthiness test.
    ("$.users[?@.active].n", ["a", "b"]),
    ("$.users[?@.active == true].n", ["a"]),
    ("$.users[*].n", ["a", "b"]),
    ("$..n", ["a", "b"]),
    ("$.users[0:1].n", ["a"]),
    ("$.users[?length(@.n) == 1].n", ["a", "b"]),
]

#: Every `python-jsonpath` extension RFC 9535 does not define. Accepting one would mean
#: shipping a dialect: the query would work here and fail on any conformant engine.
NON_RFC = ["$.users[~]", "$.users[0]|$.users[1]", "$.users[0]&$.users[1]", "$[^]"]


@pytest.mark.parametrize(("expression", "expected"), CONFORMANT)
def test_conformant_queries_behave_per_rfc_9535(expression: str, expected: list):
    assert formats.query(USERS, expression) == expected


@pytest.mark.parametrize("expression", NON_RFC)
def test_non_rfc_extensions_are_rejected(expression: str):
    """The strict environment must reject the superset, not merely avoid using it."""
    import jsonpath

    with pytest.raises(jsonpath.JSONPathError):
        formats.query(USERS, expression)


def test_the_rfc_regex_functions_are_available():
    """`match()` and `search()` need I-Regexp; without it conformance is partial."""
    import jsonpath.env

    assert jsonpath.env.IREGEXP_AVAILABLE
    assert formats.query(USERS, '$.users[?match(@.n, "a")].n') == ["a"]


# ── data-access: uniformity across formats ────────────────────────────────


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_one_address_works_across_formats(name: str):
    assert formats.pointer(formats.loads(SAMPLES[name], name), "/server/port") == 8080


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_one_query_works_across_formats(name: str):
    assert formats.query(formats.loads(SAMPLES[name], name), "$.server.host") == [
        "localhost"
    ]


def test_collected_entries_are_addressable_the_same_way(tree: Path):
    collected = formats.collect(tree)
    assert formats.pointer(collected["settings"], "/server/port") == 8080
    assert formats.query(collected["blog.posts"], "$[*].id") == [1]


# ── Dependency footprint ──────────────────────────────────────────────────


def test_kernel_does_not_import_the_data_surface():
    """The dependency runs one way, so the surface is removable."""
    code = (
        "import sys, spoc; "
        "spoc.Framework('models'); "
        "print([m for m in sys.modules if 'formats' in m])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_importing_the_surface_loads_no_optional_dependency():
    """Extras stay optional only if importing the package never reaches for them."""
    code = (
        "import sys; from spoc import formats; "
        "print(sorted(m for m in sys.modules "
        "if m.split('.')[0] in {'ruamel', 'xmltodict', 'tomli_w', 'jsonpath'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_standard_library_formats_work_with_no_optional_dependency():
    """A bare install still reads JSON, CSV, and TOML — nothing optional is touched."""
    code = (
        "import sys\n"
        "for name in ('ruamel', 'ruamel.yaml', 'xmltodict', 'tomli_w', 'jsonpath'):\n"
        "    sys.modules[name] = None\n"
        "from spoc import formats\n"
        "assert formats.loads('{\"a\": 1}', 'json') == {'a': 1}\n"
        "assert formats.loads('a\\nb\\n', 'csv') == [{'a': 'b'}]\n"
        "assert formats.loads('a = 1', 'toml') == {'a': 1}\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "ok"


@pytest.mark.parametrize("module", ["core.py", "operations.py"])
def test_core_imports_nothing_beyond_stdlib_and_kernel(module: str):
    """design.md D2: the port, the registry, and the operations stay pure."""
    root = Path(__file__).parent.parent / "src/spoc/formats"
    tree = ast.parse((root / module).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names, alias.name
        elif isinstance(node, ast.ImportFrom) and not node.level:
            # Absolute imports must be standard library; everything of ours is relative.
            assert (node.module or "").split(".")[0] in sys.stdlib_module_names, (
                node.module
            )


def test_only_the_codecs_and_access_layer_touch_adopted_packages():
    """Third-party imports are confined, and every one of them is lazy."""
    root = Path(__file__).parent.parent / "src/spoc/formats"
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            absolute = (
                isinstance(node, ast.ImportFrom) and not node.level and node.module
            ) or isinstance(node, ast.Import)
            if not absolute:
                continue
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for name in names:
                if name.split(".")[0] in sys.stdlib_module_names:
                    continue
                assert path.name in {"codecs.py", "access.py"}, f"{path.name}: {name}"
                assert node.col_offset > 0, f"{path.name}: {name} imported eagerly"


def test_published_dependencies_stay_empty():
    """Every adopted package is quarantined behind an extra."""
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []
    extras = data["project"]["optional-dependencies"]
    assert set(extras) == {"yaml", "xml", "toml", "query", "full"}


def test_collection_is_not_invoked_by_framework_startup(tmp_path: Path):
    """Startup performs no collection and loads no optional dependency."""
    (tmp_path / "apps").mkdir()
    code = (
        "import sys, pathlib, spoc\n"
        f"spoc.Framework('models').start(pathlib.Path(r'{tmp_path}'))\n"
        "print(sorted(m for m in sys.modules "
        "if m.split('.')[0] in {'ruamel', 'xmltodict', 'tomli_w', 'jsonpath'}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip().endswith("[]")
