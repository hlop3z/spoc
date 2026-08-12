# Start & Stop

A SPOC project has a simple life: **asleep → starting → running → stopped**.
Nothing happens by accident, and every step either finishes or fails loudly.

## What `start()` does, in order

```python test="skip"
framework.start(BASE_DIR)
```

1. **Read settings** — `spoc.toml` and the active mode's env file.
2. **Import apps** — every installed app's modules, in dependency order.
3. **Fill the shelf** — discover every decorated block, tag it, register it.
4. **Ready callbacks** — your `@framework.on_ready` functions run once, with
   the full registry.
5. **Wake the modules** — for each app module: the kind's `on_startup` hook
   fires, then the module's own `initialize()` runs.

If *anything* fails, SPOC tears down what already came up and returns the
framework to its inert state — fix the cause and `start()` again cleanly.

`shutdown()` walks the same road backwards: each module's `teardown()` and the
kind's `on_shutdown` hook run in **reverse** order, then everything resets.

## Per-module wake-up and clean-up

Any app module may define two plain functions:

```python title="apps/blog/models.py"
from framework import model


@model
class Post: ...


def initialize():
    print("blog models are awake")


def teardown():
    print("blog models are done")
```

No decorator, no registration — if the functions exist, SPOC calls them at the
right moments. A module whose `initialize()` never completed is never asked to
`teardown()`.

Around it, the quick-start shape — rules, settings, start button — and both
moments print on cue:

```python title="framework.py"
import spoc

framework = spoc.Framework("models")

model = framework.kind("models")
```

```toml title="config/spoc.toml"
[spoc.apps]
development = ["apps.blog"]
```

```python title="main.py"
from pathlib import Path

from framework import framework

BASE_DIR = Path(__file__).resolve().parent

framework.start(BASE_DIR)     # blog models are awake
framework.shutdown()          # blog models are done
```

## Per-kind hooks

A kind can watch all its blocks come and go. The hook fires **once per app
module**, receiving that app's blocks of the kind, in tag order:

```python
import spoc


def warm_up(components):
    for c in components:
        print("starting:", c)


framework = spoc.Framework(
    spoc.KindSpec("models", on_startup=warm_up),
)
```

## Async projects

Everything above has an async twin. Declare coroutine hooks or an async
`initialize()`/`teardown()`, and boot with:

```python test="skip"
await framework.astart(BASE_DIR)
...
await framework.ashutdown()
```

The rule is strict on purpose: the sync path (`start`) **refuses** coroutine
hooks with a clear error instead of quietly not awaiting them. Pick one path
per project.

## Guard rails

- **Starting twice** → error. Stop first.
- **Calling `start()` or `shutdown()` from inside a hook or ready callback**
  → error. The boot is half-built; there is nothing correct that call could do.
- **Two threads racing to start** → exactly one boots; the other gets the
  already-started error.
- **A `teardown()` that raises** → the error reaches you unchanged, *and* the
  framework still goes back to sleep. You can fix the cause and `start()` again;
  it never gets stuck reporting itself running.
- **An `async def` hook or `initialize()` on the synchronous path** → refused
  before anything runs, naming every one it found. Use `astart()`.

!!! warning "A failing `teardown()` skips the ones behind it"

    Teardown stops at the module that raised, so modules earlier in the reverse
    order do not get torn down — and because shutdown resets the framework, they
    will not get a second chance. Anything they held open stays open for the life
    of the process.

    This is deliberate. The alternative is to keep going and hand you a bundle of
    errors, which would mean you no longer receive the exact exception your code
    raised. So the kernel gives you the real error and a framework you can
    restart, and leaves the leak to you: a `teardown()` that can raise should
    catch its own failures if what it releases matters.

## Reading SPOC's own log records

SPOC configures no logging and prints nothing. It writes to the **`spoc`**
logger, which is the handle to configure:

```python
import logging

logging.getLogger("spoc").addHandler(logging.StreamHandler())
logging.getLogger("spoc").setLevel(logging.DEBUG)
```

Names below `spoc` follow the module path — `spoc.framework`, `spoc.core.loader`
— so you can turn one subsystem up without the rest. Treat those as internal:
they can move between releases. `spoc` itself will not.

## The whole life, at a glance

```mermaid
stateDiagram-v2
    [*] --> Asleep: Framework(...)
    Asleep --> Running: start() — settings, apps, shelf, ready, initialize
    Running --> Asleep: shutdown() — teardown in reverse, reset
    Asleep --> Asleep: failed start() rolls itself back
    Running --> Asleep: failed teardown() — error raised, reset happens anyway
```

Next: [plugins — blocks declared in settings](plugins.md).
