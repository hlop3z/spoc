---
name: "AI: Decide"
description: Build-vs-adopt gate — for each critical concern, decide Rent/Adopt/Extend/Fork/Build and record it as an ADR
category: AI
tags: [ai, decision, adopt, architecture]
---

Resolve the **build-vs-adopt** question for a piece of work before implementing it.

For each critical concern, walk the hierarchy `Rent > Adopt > Extend > Fork > Build`, research
current options, recommend one, and record the decision as an ADR block. Choosing to **build**
something a mature tool already does well is the failure this gate prevents.

**This command is self-contained.** It works inside the OpenSpec pipeline when OpenSpec is
present, and equally well without it — the hierarchy and rubric below are the authority, not a
pointer into `openspec/`. If `.canon/guidelines.md` exists it is the fuller reference and wins
on any detail; if it doesn't, nothing here degrades.

**Input**: Optionally a scope name (e.g. `/ai:decide add-auth`) — an OpenSpec change name, a
feature name, or nothing. If omitted, infer from context; if ambiguous, ask via
**AskUserQuestion**. Announce: "Deciding for: <scope>".

## Steps

1. **Resolve where the decision gets recorded** — take the first that applies:

   | Condition                                                 | Target                                                                                 |
   | --------------------------------------------------------- | -------------------------------------------------------------------------------------- |
   | `openspec` CLI available **and** an active change matches | `openspec status --change "<name>" --json` → `artifactPaths.design.resolvedOutputPath` |
   | `openspec/changes/<scope>/design.md` exists on disk       | that file                                                                              |
   | `PROJECT.md` exists (post-`/ai:migration`)                | its `## Decisions (ADRs)` section                                                      |
   | none of the above                                         | ask the user; default `DECISIONS.md` at the project root                               |

   Read whatever context exists for the scope (proposal, specs, design, or the surrounding
   code) before deciding. If the CLI reports `actionContext.mode: workspace-planning`, STOP —
   not supported here.

2. **List the critical concerns** — the correctness-, security-, or reliability-sensitive parts
   of this work. Take them from the proposal's flagged capabilities if present; otherwise scan
   the scope and propose a short list, then confirm with the user.

3. **For each concern, run the gate:**
   - **Infrastructure?** → decision is `Rent`, no further evaluation.
   - **On the never-hand-roll list?** → the decision is _which_ tool, never _whether_ to build.
   - Otherwise **research with WebSearch** — find current, actively-maintained options. Do NOT
     rely on memory; tooling moves.
   - Score candidates against the maturity rubric. Apply hard rejects.
   - Present **at most 3 options** as **pure-build vs adopt-a-tool**, each a one-line trade-off,
     and **always end with a clear recommendation** (which, and why) plus its hierarchy tier.
   - **Wait for the user's pick** before treating any tool as settled. Each decision is `draft`
     until the user confirms, then `approved`. (No "rejected" state — an unpicked option is
     simply dropped.)

4. **Record it** — append/update a `## Decisions` section in the target, one block per concern:

   ```markdown
   ### Decision: <concern> — <Rent|Adopt|Extend|Fork|Build> <tool-or-"hand-written">

   - **Status**: approved
   - **Why**: <one line>
   - **Considered**: <other 1–2 options, one line each>
   - **Isolation**: <the adapter/boundary the choice lives behind>
   ```

   Concrete tool names live here only — never push them into `config.yaml` or `specs/`, which
   stay abstract. If the target is `PROJECT.md`, match its existing ADR shape instead.

5. **Summary** — each concern → decision → status. Note any left in `draft`.

## The hierarchy (EDF)

Default order — moving **down** requires explicit justification:

- **Rent** — compute, storage, networking, CDN/DNS, clusters. Infra is never "proprietary software."
- **Adopt** — OSS meets ~90% of needs → configure, don't rewrite. Contribute upstream where possible.
- **Extend** — gaps remain → plugin / middleware / adapter / wrapper. Preserve upstream compatibility.
- **Fork** — only if upstream is unmaintained, divergence is unavoidable, and extension isn't viable. Record maintenance burden + sync strategy.
- **Build** — last resort: no viable OSS, architecturally incompatible, or genuinely differentiating value.

Defaults by situation: infrastructure → Rent · OSS ≥ 90% match → Adopt · 70–90% → Extend ·
small gap and OSS close → Fork · no OSS or strategic differentiation → Build · commodity → Adopt.

## Maturity rubric

Feature coverage 30% · Extensibility 20% · Maintenance activity 15% · Documentation 10% ·
Community size 10% · Security history 10% · License compatibility 5%.

Hard rejects (override score): active security risk · incompatible license · abandoned maintenance.

Evaluate **lifecycle** cost (integration, upgrades, patching, ops), not just first build.
Revisit decisions every 6–12 months — none are permanent.

## Never hand-roll (mandatory adopt)

Subtle failure modes, mature standards already exist. Record _which_ tool, never _whether_:
cryptography & hashing · authentication & authorization · secrets management · observability
& telemetry (OpenTelemetry API) · standard-format parsing/serialization · time, locale, money.

## Guardrails

- Research before recommending — current options, not remembered ones.
- ≤3 options per concern, always with a recommendation.
- Default toward Adopt/Extend; a `Build` decision needs an explicit one-line justification.
- Decisions are draft → approved only.
- Tool names live in the ADR; specs and config stay language-agnostic.
- This gate decides HOW, not WHAT — don't change scope or behavior here; if a decision reveals
  a scope problem, suggest updating the proposal/specs instead.
- Never fail because OpenSpec is absent — fall back down the target table and keep going.
