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

```python title="main.py"
from pathlib import Path

import spoc
from pydantic import BaseModel, HttpUrl

BASE_DIR = Path(__file__).resolve().parent


class MyAppSettings(BaseModel):
    api_url: HttpUrl
    retries: int = 3


framework = spoc.Framework()
framework.start(BASE_DIR)

settings = MyAppSettings.model_validate(framework.config.tables["myapp"])
print(settings.retries)   # 3 — typed, defaulted, and validated at the boundary
```

A typo inside `[spoc]` still refuses to boot, loudly, before your code runs.
A typo inside your own table is yours to catch — which is exactly what the
model above does, at the boundary, before the bad value travels.

Next: [test your app](test-your-app.md).
