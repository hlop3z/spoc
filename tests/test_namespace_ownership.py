"""
One namespace, one package.

The namespace derives from a path's *final* segment, so `apps.shop` and
`vendor.shop` both answer to `shop` without either author doing anything
unusual. Before this rule, the merge was silent: it only surfaced if the two
apps also happened to declare the same object name, and the error then named a
third place. These tests hold the line at the declaration instead.
"""

from __future__ import annotations

import sys
import textwrap

import pytest

from spoc import ConfigurationError, Framework, InvalidSegmentError, KindSpec
from spoc.framework import _parse_app_entry

from .conftest import MODELS_BODY

pytestmark = pytest.mark.usefixtures("clean_sys_path_and_modules")


def _app(base, path: str, body: str = MODELS_BODY, module: str = "models") -> None:
    """Create an importable package at `path` holding one component module."""
    package = base
    for segment in path.split("."):
        package = package / segment
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text("")
    (package / f"{module}.py").write_text(textwrap.dedent(body))


def _project(tmp_path, name: str, config: str):
    base = tmp_path / name
    (base / "config").mkdir(parents=True)
    (base / "config" / "spoc.toml").write_text(config)
    sys.path.insert(0, str(base))
    return base


def _parsed(entry: str) -> tuple[str, str]:
    """The parse as a pair, so the assertions read as the two things it decides."""
    parsed = _parse_app_entry(entry)
    return parsed.path, parsed.namespace


#: Plugin groups populate this kind, so apps need not provide a module for it.
HOOKS = KindSpec("hooks", required=False)


ORDER_BODY = """
    from spoc import component

    @component(kind="models")
    class Order:
        ...
"""


# ── Parsing an entry ──────────────────────────────────────────────────────


class TestParseAppEntry:
    def test_a_bare_path_derives_from_its_final_segment(self):
        assert _parsed("apps.shop") == ("apps.shop", "shop")

    def test_a_single_segment_path_is_its_own_namespace(self):
        assert _parsed("shop") == ("shop", "shop")

    def test_an_as_clause_states_the_namespace(self):
        assert _parsed("vendor.shop as vendor_shop") == (
            "vendor.shop",
            "vendor_shop",
        )

    def test_surrounding_whitespace_is_not_significant(self):
        assert _parsed("  vendor.shop   as   vendor_shop  ") == (
            "vendor.shop",
            "vendor_shop",
        )

    def test_a_segment_containing_the_letters_as_is_unaffected(self):
        """The delimiter needs whitespace, which a module path cannot contain."""
        assert _parsed("aspects.last") == ("aspects.last", "last")
        assert _parsed("as.as") == ("as.as", "as")

    @pytest.mark.parametrize(
        "entry", ["", "   ", " as thing", "apps.shop as", "a as b as c"]
    )
    def test_a_malformed_entry_names_itself(self, entry):
        with pytest.raises(ConfigurationError) as caught:
            _parse_app_entry(entry)
        assert repr(entry) in str(caught.value)

    def test_a_stated_namespace_must_satisfy_the_grammar(self):
        with pytest.raises(InvalidSegmentError) as caught:
            _parse_app_entry("vendor.shop as Vendor-Shop")
        assert "Vendor-Shop" in str(caught.value)


# ── Two apps ──────────────────────────────────────────────────────────────


class TestAppsContestingANamespace:
    def test_two_apps_deriving_one_namespace_fail_naming_both(self, tmp_path):
        base = _project(
            tmp_path,
            "contested",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["apps.shop", "vendor.shop"]\n',
        )
        _app(base, "apps.shop")
        _app(base, "vendor.shop", ORDER_BODY)

        with pytest.raises(ConfigurationError) as caught:
            Framework("models").start(base)
        message = str(caught.value)
        assert "'shop'" in message
        assert "apps.shop" in message
        assert "vendor.shop" in message

    def test_the_failure_does_not_need_a_coinciding_object_name(self, tmp_path):
        """The whole point: `Product` and `Order` never collide, yet the two
        packages still cannot both be `shop`. Before this rule these merged
        silently and produced a working system whose identifiers lied."""
        base = _project(
            tmp_path,
            "nocoincide",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["apps.shop", "vendor.shop"]\n',
        )
        _app(base, "apps.shop")  # Post
        _app(base, "vendor.shop", ORDER_BODY)  # Order

        with pytest.raises(ConfigurationError):
            Framework("models").start(base)

    def test_nothing_registers_when_a_namespace_is_contested(self, tmp_path):
        base = _project(
            tmp_path,
            "nothingreg",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["apps.shop", "vendor.shop"]\n',
        )
        _app(base, "apps.shop")
        _app(base, "vendor.shop", ORDER_BODY)

        fw = Framework("models")
        with pytest.raises(ConfigurationError):
            fw.start(base)
        assert len(fw.registry) == 0
        assert fw.installed_apps == []

    def test_an_as_clause_resolves_the_collision(self, tmp_path):
        base = _project(
            tmp_path,
            "aliased",
            '[spoc]\nmode = "development"\n\n[spoc.apps]\n'
            'development = ["apps.shop", "vendor.shop as vendor_shop"]\n',
        )
        _app(base, "apps.shop")
        _app(base, "vendor.shop", ORDER_BODY)

        fw = Framework("models").start(base)
        assert [c.identifier for c in fw.registry] == [
            "models:shop.post",
            "models:vendor_shop.order",
        ]

    def test_an_aliased_app_reports_its_module_path_as_installed(self, tmp_path):
        """`installed_apps` names what was imported, not what it claimed."""
        base = _project(
            tmp_path,
            "installedpaths",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["vendor.shop as vendor_shop"]\n',
        )
        _app(base, "vendor.shop", ORDER_BODY)

        fw = Framework("models").start(base)
        assert fw.installed_apps == ["vendor.shop"]

    def test_two_apps_stating_the_same_namespace_also_fail(self, tmp_path):
        base = _project(
            tmp_path,
            "bothstated",
            '[spoc]\nmode = "development"\n\n[spoc.apps]\n'
            'development = ["apps.shop as store", "vendor.other as store"]\n',
        )
        _app(base, "apps.shop")
        _app(base, "vendor.other", ORDER_BODY)

        with pytest.raises(ConfigurationError) as caught:
            Framework("models").start(base)
        assert "'store'" in str(caught.value)

    def test_the_same_app_declared_twice_is_not_a_contest(self, tmp_path):
        """Deduplication already collapses this; it must not read as a collision."""
        base = _project(
            tmp_path,
            "declaredtwice",
            '[spoc]\nmode = "development"\n\n[spoc.apps]\n'
            'development = ["apps.shop"]\nproduction = ["apps.shop"]\n',
        )
        _app(base, "apps.shop")

        fw = Framework("models").start(base)
        assert fw.installed_apps == ["apps.shop"]


# ── Plugins ───────────────────────────────────────────────────────────────


HOOK_BODY = """
    class AuditHook:
        ...
"""


class TestPluginsAndNamespaceOwnership:
    def test_a_plugin_inside_its_own_app_registers_there(self, tmp_path):
        base = _project(
            tmp_path,
            "ownplugin",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["apps.shop"]\n\n'
            '[spoc.plugins]\nhooks = ["apps.shop.extras.AuditHook"]\n',
        )
        _app(base, "apps.shop")
        (base / "apps" / "shop" / "extras.py").write_text(textwrap.dedent(HOOK_BODY))

        fw = Framework("models", HOOKS).start(base)
        assert fw.resolve("hooks:shop.audit_hook")

    def test_a_plugin_contesting_an_installed_app_fails(self, tmp_path):
        base = _project(
            tmp_path,
            "plugincontest",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["apps.shop"]\n\n'
            '[spoc.plugins]\nhooks = ["vendor.shop.extras.AuditHook"]\n',
        )
        _app(base, "apps.shop")
        _app(base, "vendor.shop", ORDER_BODY)
        (base / "vendor" / "shop" / "extras.py").write_text(textwrap.dedent(HOOK_BODY))

        with pytest.raises(ConfigurationError) as caught:
            Framework("models", HOOKS).start(base)
        message = str(caught.value)
        assert "'shop'" in message
        assert "apps.shop" in message
        assert "vendor.shop" in message

    def test_a_plugin_outside_every_app_claims_its_own_namespace(self, tmp_path):
        """The primary use of a plugin group: a third-party distribution that
        is not an installed app at all."""
        base = _project(
            tmp_path,
            "thirdparty",
            '[spoc]\nmode = "development"\n\n'
            '[spoc.apps]\ndevelopment = ["apps.shop"]\n\n'
            '[spoc.plugins]\nhooks = ["acme_billing.extras.AuditHook"]\n',
        )
        _app(base, "apps.shop")
        _app(base, "acme_billing", HOOK_BODY, module="extras")

        fw = Framework("models", HOOKS).start(base)
        assert fw.resolve("hooks:acme_billing.audit_hook")

    def test_a_plugin_follows_its_app_s_stated_namespace(self, tmp_path):
        """The package owns the name, not the path segment — so a plugin under
        an aliased app registers under the alias, never the derived segment."""
        base = _project(
            tmp_path,
            "aliasedplugin",
            '[spoc]\nmode = "development"\n\n[spoc.apps]\n'
            'development = ["vendor.shop as vendor_shop"]\n\n'
            '[spoc.plugins]\nhooks = ["vendor.shop.extras.AuditHook"]\n',
        )
        _app(base, "vendor.shop", ORDER_BODY)
        (base / "vendor" / "shop" / "extras.py").write_text(textwrap.dedent(HOOK_BODY))

        fw = Framework("models", HOOKS).start(base)
        assert fw.resolve("hooks:vendor_shop.audit_hook")
        assert fw.resolve("models:vendor_shop.order")

    def test_two_plugins_from_different_packages_contest(self, tmp_path):
        base = _project(
            tmp_path,
            "twoplugins",
            '[spoc]\nmode = "development"\n\n[spoc.plugins]\n'
            'hooks = ["one.shop.extras.AuditHook", "two.shop.extras.AuditHook"]\n',
        )
        for parent in ("one", "two"):
            _app(base, f"{parent}.shop", HOOK_BODY, module="extras")

        with pytest.raises(ConfigurationError) as caught:
            Framework(HOOKS).start(base)
        assert "'shop'" in str(caught.value)
