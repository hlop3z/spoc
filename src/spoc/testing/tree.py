"""
Declarative app-tree builder — ``make_project`` generalized and shipped.

A :class:`ProjectTree` declares apps, their modules' source, and the config
table; :meth:`ProjectTree.build` materializes a bootable project directory.
The builder owns the layout conventions (``config/spoc.toml``, package
``__init__.py``); callers own only content.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import dump_toml

__all__ = ["ProjectTree"]


@dataclass
class ProjectTree:
    """A declarative description of a SPOC project on disk.

    ``apps`` maps app name → (module name → source). Source strings are
    dedented on write, so triple-quoted literals indent naturally at the call
    site. ``config`` entries merge over the generated ``[spoc]`` table —
    by default every declared app is listed under the ``development`` mode.
    """

    apps: dict[str, dict[str, str]] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    def build(self, root: Path | str, name: str = "project") -> Path:
        """Materialize the tree under ``root`` and return the project base."""
        base = Path(root) / name
        spoc_table: dict[str, Any] = {
            "mode": "development",
            "debug": True,
            "apps": {"development": sorted(self.apps)},
            **self.config,
        }
        (base / "config").mkdir(parents=True)
        (base / "config" / "spoc.toml").write_text(
            dump_toml({"spoc": spoc_table}), encoding="utf-8"
        )
        for app, modules in self.apps.items():
            app_dir = base / app
            app_dir.mkdir(parents=True)
            (app_dir / "__init__.py").write_text("", encoding="utf-8")
            for module, source in modules.items():
                (app_dir / f"{module}.py").write_text(
                    textwrap.dedent(source), encoding="utf-8"
                )
        return base
