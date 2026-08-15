# Validate Your Settings

**How do I validate my own `spoc.toml` tables?** SPOC claims exactly one
top-level table — `[spoc]` — and hands every other table back untouched on
`framework.config.tables`, already parsed
([The Settings File](../getting-started/configuration.md)). Validating what's
in yours is your job, with any schema tool you like: the table is a plain
dict, so any validator that accepts one fits the seam.

The worked example uses [pydantic](https://docs.pydantic.dev)
(`pip install pydantic`) — a plain model over the already-parsed table. Not
`pydantic-settings`: SPOC has already done the file reading.

```toml title="config/spoc.toml"
[spoc]
mode = "development"

[myapp]                # yours: any keys, any shapes
api_url = "https://api.example.com"
retries = 3
```

Put the model and its check next to the declaration, not in an entry point.
`on_ready` fires inside every `start()`, so a bad table refuses the boot
itself — whichever process booted, HTTP server, worker, or one-off script —
rather than surfacing at the first request that reads the value:

```python title="framework.py"
"""The declaration, and the validation that guards every boot of it."""

import spoc
from pydantic import BaseModel, HttpUrl


class MyAppSettings(BaseModel):
    api_url: HttpUrl
    retries: int = 3


framework = spoc.Framework()


@framework.on_ready
def _settings_are_valid(registry):
    """Runs inside start(), after settings load and before the boot returns."""
    MyAppSettings.model_validate(framework.config.tables["myapp"])
```

```python title="main.py"
from pathlib import Path

from framework import MyAppSettings, framework

BASE_DIR = Path(__file__).resolve().parent

framework.start(BASE_DIR)   # a bad [myapp] table would have refused right here

settings = MyAppSettings.model_validate(framework.config.tables["myapp"])
print(settings.retries)   # 3 — typed, defaulted, and validated at the boundary
```

## What the kernel already checks

A typo inside `[spoc]` refuses to boot, loudly, before your code runs — and
`spoc check` reports the same refusal in CI without booting anything
([The Command Line](../tools/cli.md)). Your own tables are outside both on
purpose: the kernel neither validates nor reads them, and the model above is
what makes them fail just as loudly.

The same seam covers the environment. `framework.config.environment` is the
active mode's `env` table as a plain `dict[str, Any]`, so the
model-at-the-boundary pattern fits it unchanged — one more
`model_validate(framework.config.environment)` in the same callback.

Next: [test your app](test-your-app.md).
