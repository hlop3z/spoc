## Why

A framework built on SPOC publishes SPOC's commands under its own name — `hello init`,
`hello check` — by mounting them onto its own parser. The mechanism exists and the shipped
`spoc` program is built on it, but every mount point is `internal`, so a framework author is
promised the template path (`ENTRY_POINT_GROUP` and `template-set:default` are public) and
not the command path. Half a guaranteed extension point is worse than neither, because the
unguaranteed half is the one that looks most like an invitation.

Nothing in the specs describes mounting at all, which is why the gap went unnoticed: the
contract was never wrong, it was absent. This closes it at the spec level and gives the
mount points a tier that says what is true — intended for downstream use, shape not yet
settled.

## What Changes

- The four shipped command groups — project generation, diagnostics, projection, and stubs —
  gain a stated contract for being mounted onto a caller's own parser: what a caller must
  supply, what appears on the parser afterwards, and what the caller still owns.
- Each mount point moves from `internal` to `provisional`: publicly documented, explicitly
  unsettled, breakable in a minor release but never in a patch. Each states what would
  settle it.
- The surface contract gains a requirement that the parts of one extension point carry
  coherent tiers, so a promise cannot again cover one half of a path a consumer must walk
  end to end.
- The scaffolder's mount point additionally accepts the two injection points a composition
  root supplies — kind derivation and template resolution — and that injection becomes part
  of the stated contract rather than an implementation convenience.
- Not a breaking change. Every promotion is a tier being raised, which the contract already
  permits unconditionally, and no signature changes.

## Capabilities

### New Capabilities

- `cli-command-mounting`: mounting SPOC's shipped command groups onto a parser the caller
  owns — what each group contributes, what the caller injects, what the caller keeps
  responsibility for, and what the mount does not promise.

### Modified Capabilities

- `public-api-surface`: a new requirement that an extension point's parts carry coherent
  tiers — where a consumer must reference several elements to complete one path the artifact
  offers, the contract may not promise some and stay silent on the others.

## Impact

- **Promised surface**: four elements move `internal` → `provisional`. `apidiff` will report
  the additions; none is a breakage.
- **Code**: `spoc/scaffold/__init__.py`, `spoc/diagnostics/__init__.py`,
  `spoc/projection/__init__.py`, `spoc/stubs/__init__.py` re-export `register`; each
  `cli.py` docstring carries the provisional notice and what would settle it.
- **Docs**: `docs/docs/how-to/ship-a-framework.md`'s tiering warning becomes a tier
  statement and grows the inspection commands; the stability page's element list gains the
  four.
- **Decisions**: closes the open question in `DECISIONS.md`, recorded as decided rather than
  deleted.
- **Not affected**: the shipped `spoc` program's own composition, every command's behavior,
  and the `argparse` signature — deliberately unchanged, and the reason it is `provisional`
  rather than `public`.
