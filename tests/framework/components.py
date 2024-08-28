# -*- coding: utf-8 -*-
"""
Components
"""

from typing import Any
import functools
import spoc
import click

components = spoc.Components()
components.add("view")
components.add("command", {"is_click": True})


# Define your components.
def old_command(obj: Any = None):
    """Command Component"""
    components.register("command", obj)
    return obj


def view(obj: Any = None):
    """View Component"""
    components.register("view", obj)
    return obj


def command(obj: Any = None, *, group: bool = False):
    """Click Commands and Groups"""
    if obj is None:
        return functools.partial(command, group=group)

    # Real Wrapper (click)
    obj = click.command(obj) if not group else click.group(obj)
    components.register("command", obj)

    # Return Modified Class
    return obj
