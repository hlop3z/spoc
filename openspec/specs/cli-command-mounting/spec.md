# CLI Command Mounting

## Purpose

A framework built on this system publishes the system's commands under its own program name,
so its users never learn a second command-line tool. This capability defines that extension
point: which command groups can be mounted onto a parser the caller owns, what each group
contributes, what a caller must inject for a group to reach its own project, what remains the
caller's responsibility after mounting, and — because the mount is described in terms of a
parsing technology the system does not own — which part of it is promised and which part is
not.

## Requirements

### Requirement: Every shipped command group is mountable onto a parser the caller owns

The system MUST let a caller mount each shipped command group onto a command-line parser the
caller constructed, so a downstream framework can publish those commands under its own
program name rather than requiring its users to run a second program.

The mountable groups MUST be exactly the groups the shipped program itself composes —
project generation, project diagnostics, registry projection, and stub generation — and the
shipped program MUST obtain them by the same mount every other caller uses. There is no
second, privileged assembly path.

A mount MUST be additive: it contributes its own commands and leaves every command already
present on the parser untouched.

#### Scenario: A group's commands appear under the caller's program name

- **WHEN** a caller mounts a shipped command group onto its own parser
- **THEN** that group's commands become available on the caller's program, named as the
  group names them, and invoking one performs the same operation the shipped program's
  equivalent performs

#### Scenario: Mounting several groups composes them

- **WHEN** a caller mounts more than one shipped group onto the same parser
- **THEN** every mounted group's commands are present together, and no group's mount removes
  or redefines the commands of another

#### Scenario: The shipped program is not a special case

- **WHEN** the shipped program assembles its own commands
- **THEN** it does so through the same mount available to any caller, so a defect in the
  mount is observable from the shipped program rather than only downstream

### Requirement: A mount leaves parsing, dispatch, and process outcome with the caller

A mount MUST confine itself to describing commands on the parser it is given. It MUST NOT
read the process arguments, write to the process output streams, or end the process.

The caller MUST retain responsibility for parsing its own arguments, for choosing how a
parsed command is dispatched, and for translating a command's outcome into a process result.
This keeps a downstream program free to wrap, reorder, rename, or refuse any command it
mounted.

#### Scenario: Mounting performs no work of its own

- **WHEN** a caller mounts a command group but never invokes any mounted command
- **THEN** nothing has been read from the process arguments, nothing has been written to the
  process output, and the process has not been ended

#### Scenario: The caller decides the process outcome

- **WHEN** a mounted command completes, whether by succeeding or by refusing
- **THEN** its outcome is returned to the caller for translation, rather than the mount
  ending the process on the caller's behalf

### Requirement: The generation group accepts the derivations its host supplies

The project-generation group MUST accept, at mount time, the two derivations that only a
composition root can provide: how the kinds of a project are derived from that project's own
declaration, and how a template reference is resolved to a template set.

Each derivation MUST be optional. When a derivation is not supplied, the group MUST remain
usable with a stated fallback rather than failing at mount time or at invocation.

#### Scenario: A supplied derivation is used

- **WHEN** a caller mounts the generation group supplying kind derivation, and a user invokes
  the command that adds to an existing project
- **THEN** the kinds are derived from that project's own declaration, and the user is not
  required to restate them

#### Scenario: An omitted derivation falls back rather than failing

- **WHEN** a caller mounts the generation group without supplying either derivation
- **THEN** the mount succeeds, kind derivation falls back to requiring the kinds to be stated
  on invocation, and template resolution falls back to the template sets installed locally

### Requirement: The mount promises the commands, not the parser it is described to

The contract MUST promise which commands a mount contributes and what invoking them does. It
MUST NOT promise the shape of the parser object a mount is handed, because that shape is
owned by the parsing technology the system happens to use and not by the system.

A caller that mounts a group therefore MUST be told that the parser type may change, and that
such a change is a change to this contract to be released accordingly.

#### Scenario: Command behavior is the promised part

- **WHEN** a caller depends on a mounted command's name, arguments, and effect
- **THEN** those are covered by the contract at the tier the mount point carries

#### Scenario: The parser shape is the unpromised part

- **WHEN** the system changes the parsing technology its mounts are described to
- **THEN** the mount contract has changed, and the change is released under the guarantee the
  mount point's tier states rather than treated as internal
