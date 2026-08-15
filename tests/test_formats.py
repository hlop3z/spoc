"""
Data-surface tests: one per scenario in the `format-codecs`, `data-collection`, and
`data-access` specs, plus the structural guarantees from design.md.

The optional extras are installed in this project's dev environment, so "the extra is
missing" is simulated with a codec whose factory raises `ImportError` rather than by
uninstalling anything — which is also the only way to test it deterministically.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from spoc import formats
from spoc.formats.core import READ, WRITE, Codec, FormatRegistry
from spoc.formats.errors import (
    CollectionError,
    DuplicateEntryError,
    FormatError,
    MissingDependencyError,
    PointerResolutionError,
    UnknownFormatError,
    UnsupportedDirectionError,
)
from spoc.formats.operations import derive_key

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
    assert 'pip install "spoc[pretend]"' in str(exc.value)


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


def test_a_ragged_row_is_refused_not_smuggled():
    """A row wider than the header would decode outside the JSON data model."""
    with pytest.raises(formats.DecodeError, match="row 2"):
        formats.loads("a,b\n1,2,3\n", "csv")


def test_a_short_row_is_refused_like_an_overflowing_one():
    """Padding with nulls leaves the declared list[dict[str, str]] model."""
    with pytest.raises(formats.DecodeError, match="row 2") as exc:
        formats.loads("a,b\n1\n", "csv")
    assert "'b'" in str(exc.value)


def test_every_csv_failure_stays_in_the_format_family():
    """One `except FormatError` covers the surface, per the family's own claim."""
    for text in ("a,b\n1,2,3\n", "a,b\n1\n"):
        with pytest.raises(formats.FormatError):
            formats.loads(text, "csv")


def test_heterogeneous_rows_share_a_union_header():
    """Later rows may introduce keys; the header is the union, gaps stay empty."""
    text = formats.dumps([{"a": "1"}, {"a": "2", "b": "3"}], "csv")
    assert text == "a,b\n1,\n2,3\n"


@pytest.mark.parametrize(
    "value", [{"a": "1"}, "text", [{"a": "1"}, ["not", "a", "row"]]]
)
def test_non_tabular_values_are_refused_by_the_csv_writer(value):
    """Only an array of objects has tabular meaning — anything else is refused."""
    with pytest.raises(formats.EncodeError, match="array of objects"):
        formats.dumps(value, "csv")


def test_an_inexpressible_value_fails_inside_the_format_family():
    """A serializer's own exception never reaches the caller."""
    with pytest.raises(formats.EncodeError) as exc:
        formats.dumps({"tags": {"a", "b"}}, "json")
    assert "json" in str(exc.value)


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


def test_empty_directory_is_an_empty_collection(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    assert dict(formats.collect(tmp_path / "empty")) == {}


def test_absent_root_fails_loudly(tmp_path: Path):
    """A typo'd root is a failure, not an empty result — collection is eager and loud."""
    with pytest.raises(CollectionError, match="not a directory"):
        formats.collect(tmp_path / "never-created")


def test_keys_derive_from_relative_location(tmp_path: Path):
    """Same stem in different subdirectories occupies distinct keys."""
    for sub in ("a", "b"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "items.json").write_text("[]", encoding="utf-8")
    assert set(formats.collect(tmp_path)) == {"a.items", "b.items"}


def test_key_segment_violating_the_grammar_is_refused(tmp_path: Path):
    """A bad key stays inside the FormatError family, naming file and segment."""
    (tmp_path / "Posts.json").write_text("[]", encoding="utf-8")
    with pytest.raises(CollectionError) as exc:
        formats.collect(tmp_path)
    message = str(exc.value)
    assert "Posts" in message and "Posts.json" in message


def test_dotted_filename_is_refused_rather_than_reinterpreted(tmp_path: Path):
    """`my.data.json` must not quietly become the two-segment key `my.data`."""
    (tmp_path / "my.data.json").write_text("[]", encoding="utf-8")
    with pytest.raises(CollectionError):
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
    with pytest.raises(formats.MalformedAddressError) as exc:
        formats.query(USERS, expression)
    assert "RFC 9535" in str(exc.value)


def test_a_malformed_query_stays_in_the_format_family():
    """The engine's own exception type never reaches the caller."""
    import jsonpath

    with pytest.raises(formats.FormatError) as exc:
        formats.query(USERS, "$.users[")
    assert not isinstance(exc.value, jsonpath.JSONPathError)


def test_a_malformed_pointer_stays_in_the_format_family():
    with pytest.raises(formats.MalformedAddressError) as exc:
        formats.pointer({"a": 1}, "no-leading-slash")
    assert "RFC 6901" in str(exc.value)


def test_the_suppressed_extension_set_matches_the_engine():
    """Drift guard for the RFC 9535 narrowing.

    The strict environment works by rebinding every ``python-jsonpath``
    extension token to an unmatchable sentinel. That list is written here, not
    derived — so an upgrade that renames a token or adds an extension would
    silently widen the accepted syntax back to the superset. Compare the two
    and fail the suite instead.
    """
    import jsonpath

    from spoc.formats.access import _EXTENSION_TOKENS, _SENTINEL, _strict_env

    base = jsonpath.JSONPathEnvironment
    unknown = [name for name in _EXTENSION_TOKENS if not hasattr(base, name)]
    assert not unknown, (
        f"suppressed tokens no longer exist upstream: {unknown}. "
        "The RFC 9535 narrowing is silently incomplete"
    )

    # Every token the engine declares as a non-standard extension must be one
    # we suppress. Tokens are class attributes ending in `_token`; the standard
    # ones stay reachable, so compare against what the strict env actually
    # blanked rather than re-deriving the RFC's grammar here.
    env = _strict_env()
    suppressed = {
        name
        for name in dir(env)
        if name.endswith("_token") and getattr(env, name, None) == _SENTINEL
    }
    assert suppressed == set(_EXTENSION_TOKENS)


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


def test_format_errors_are_not_kernel_errors():
    """One repo, two error families: catching SpocError never swallows a data failure."""
    from spoc.core.exceptions import SpocError

    assert not issubclass(FormatError, SpocError)


def test_no_kernel_module_imports_the_data_surface():
    """Containment is a contract, not a packaging accident: the boundary holds in
    source, whatever distribution the two sides share."""
    root = Path(__file__).parent.parent / "src/spoc"
    for path in sorted(root.rglob("*.py")):
        if (root / "formats") in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                # A relative import can reach the surface too (`from .formats
                # import ...` / `from . import formats`), so both the module
                # path and the imported names are checked.
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                continue
            for name in names:
                assert "formats" not in name.split("."), f"{path.name}: {name}"


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
def test_core_imports_nothing_beyond_stdlib(module: str):
    """design.md D2: the port, the registry, and the operations stay pure —
    and nothing here imports the SPOC kernel."""
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


# ── data-collection: hidden entries and ignore patterns ───────────────────


def test_a_hidden_directory_is_skipped_not_fatal(tmp_path):
    """One stray `.cache` must not take the whole collection down with it."""
    (tmp_path / "ok.json").write_text('{"a": 1}')
    cache = tmp_path / ".cache"
    cache.mkdir()
    (cache / "stale.json").write_text('{"b": 2}')

    result = formats.collect(tmp_path)

    assert dict(result) == {"ok": {"a": 1}}
    # The directory under its own name — a substring match here would also be
    # satisfied by a path to a file inside it, which is what this must not be.
    assert result.skipped == (str(cache),)


def test_a_hidden_file_is_skipped(tmp_path):
    (tmp_path / "ok.json").write_text('{"a": 1}')
    (tmp_path / ".secret.json").write_text('{"b": 2}')

    result = formats.collect(tmp_path)

    assert dict(result) == {"ok": {"a": 1}}
    assert any(".secret" in path for path in result.skipped)


def test_ignore_patterns_extend_the_skip_set(tmp_path):
    (tmp_path / "keep.json").write_text('{"a": 1}')
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "dep.json").write_text('{"b": 2}')

    result = formats.collect(tmp_path, ignore=("vendor",))

    assert dict(result) == {"keep": {"a": 1}}
    # The directory is named, not its contents: a skipped directory is not
    # descended, so there is nothing beneath it the collection could report.
    assert result.skipped == (str(vendor),)


def test_a_skipped_directory_reports_as_one_entry_whatever_it_holds(tmp_path):
    """Skipping is a decision about a directory, not about each file under it.

    The report staying one entry wide is what a caller can observe of the walk
    never descending — the alternative implementation, which enumerates and then
    discards, cannot help but grow this set with the tree it was told to skip.
    """
    (tmp_path / "keep.json").write_text('{"a": 1}')
    vendor = tmp_path / "vendor"
    (vendor / "nested" / "deeper").mkdir(parents=True)
    (vendor / "a.json").write_text("{}")
    (vendor / "README.md").write_text("unsupported, and still not reported")
    (vendor / "nested" / "b.json").write_text("{}")
    (vendor / "nested" / "deeper" / "c.toml").write_text("x = 1")

    populated = formats.collect(tmp_path, ignore=("vendor",))

    assert dict(populated) == {"keep": {"a": 1}}
    assert populated.skipped == (str(vendor),)

    # And the same tree with the skipped directory empty collects identically.
    bare = tmp_path / "bare"
    (bare / "vendor").mkdir(parents=True)
    (bare / "keep.json").write_text('{"a": 1}')
    empty = formats.collect(bare, ignore=("vendor",))

    assert dict(empty) == dict(populated)
    assert len(empty.skipped) == len(populated.skipped)


def test_the_skipped_set_is_ordered_deterministically(tmp_path):
    """A directory read returns entries in the filesystem's order, not one order.

    Sorting is what makes two collections of one tree agree across machines —
    the whole-tree sort this traversal replaced provided it without saying so.
    """
    (tmp_path / "keep.json").write_text('{"a": 1}')
    for name in ("zeta", "alpha", "middle"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "x.json").write_text("{}")
    (tmp_path / "b.md").write_text("unsupported")

    result = formats.collect(tmp_path, ignore=("zeta", "alpha", "middle"))

    assert list(result.skipped) == sorted(result.skipped)
    assert dict(result) == {"keep": {"a": 1}}


def test_enumeration_order_is_the_whole_tree_path_order(tmp_path):
    """Pruning changed which entries are walked, and must not change their order.

    A walk yields directory by directory, so the collection sorts what survived
    it. The claim that buys — that enumeration is what a whole-tree path sort
    would have given — is asserted against that sort rather than against a
    hand-written list, because the ordering `Path` defines is not the ordering
    its string spelling suggests: comparison is by parts, so `a/c.json` precedes
    `a.json`. A literal here would pin whatever the author guessed.
    """
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "z.json").write_text("{}")
    (tmp_path / "a" / "c.json").write_text("{}")
    (tmp_path / "a.json").write_text("{}")
    nested = tmp_path / "a" / "deep"
    nested.mkdir()
    (nested / "m.json").write_text("{}")

    result = formats.collect(tmp_path)

    expected = [
        derive_key(tmp_path, p)
        for p in sorted(q for q in tmp_path.rglob("*") if q.is_file())
    ]
    assert list(result) == expected
    # Pinned as a value too, so a change to *both* sides cannot pass unnoticed.
    assert expected == ["a.c", "a.deep.m", "a.z", "a", "b"]


def test_pruning_does_not_reorder_what_survives_it(tmp_path):
    """The kept entries hold the order they had when the skipped ones were there.

    Dropping elements from a sorted sequence leaves the rest in order, which is
    why pruning is free to skip them: this pins that the traversal actually
    behaves that way rather than that the argument sounds right.
    """
    for name in ("b.json", "a.json"):
        (tmp_path / name).write_text("{}")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "c.json").write_text("{}")
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "a.json").write_text("{}")

    with_skip = formats.collect(tmp_path, ignore=("vendor",))
    # The same tree with the ignored directory absent rather than skipped.
    shutil.rmtree(vendor)
    without = formats.collect(tmp_path)

    assert list(with_skip) == list(without)


def test_skipping_happens_before_the_key_grammar_is_applied(tmp_path):
    """A skipped directory can never fail the collection on a key it never used."""
    (tmp_path / "ok.json").write_text('{"a": 1}')
    bad = tmp_path / ".Not-A-Valid-Segment"
    bad.mkdir()
    (bad / "x.json").write_text("{}")

    result = formats.collect(tmp_path)  # would raise CollectionError before

    assert dict(result) == {"ok": {"a": 1}}


def test_a_collected_directory_still_fails_loudly_on_the_grammar(tmp_path):
    """Only *skipped* entries are exempt — what is collected stays strict."""
    bad = tmp_path / "Not-A-Valid-Segment"
    bad.mkdir()
    (bad / "x.json").write_text("{}")

    with pytest.raises(formats.CollectionError):
        formats.collect(tmp_path)


def test_a_malformed_collected_file_still_names_its_path(tmp_path):
    """Decode failures reach the caller as a collection failure naming the file."""
    (tmp_path / "broken.json").write_text("{not json")

    with pytest.raises(formats.CollectionError) as exc:
        formats.collect(tmp_path)
    assert "broken.json" in str(exc.value)


# ── format-codecs: writing creates the path it was given ──────────────────


def test_write_creates_missing_parent_directories(tmp_path):
    target = tmp_path / "generated" / "nested" / "out.json"

    written = formats.write({"a": 1}, target)

    assert written.is_file()
    assert formats.read(written) == {"a": 1}
