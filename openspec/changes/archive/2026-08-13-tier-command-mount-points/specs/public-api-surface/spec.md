## ADDED Requirements

### Requirement: An extension point's parts carry coherent tiers

Where a consumer outside the artifact MUST reference several elements to complete one path
the artifact offers, those elements MUST NOT be left at tiers that promise some parts of the
path and stay silent on the others. The whole path MUST carry a stated tier.

The elements of such a path MAY sit at different tiers, provided every one of them is stated.
A consumer can plan around a path whose parts are `public` and `provisional`, because both
say what will happen; a consumer cannot plan around a path where one part says nothing,
because silence is indistinguishable from an oversight and the unpromised part is usually the
one that most looks like an invitation.

The obligation attaches to the path, not to any single element: admitting one element of a
path to a published namespace MUST be treated as a decision about the path, and the change
that admits it MUST state the tier of every other element the same path requires.

#### Scenario: A path with an unstated part is a defect

- **WHEN** a consumer must reference several elements in sequence to complete one offered
  path, and at least one carries a stated tier while another carries none
- **THEN** the surface is defective, to be corrected either by stating a tier for every
  element of the path or by withdrawing the stated ones so the path promises nothing at all

#### Scenario: Mixed but stated tiers are permitted

- **WHEN** every element of one path carries a stated tier, and those tiers differ
- **THEN** the surface is coherent, and a consumer plans against the weakest guarantee among
  them

#### Scenario: Admitting one element raises the question for the rest

- **WHEN** a change admits an element to a published namespace, and that element is one step
  of a path with further steps
- **THEN** the change states the tier of every remaining step, rather than deferring them to
  a later change

#### Scenario: A wholly unpromised path is coherent

- **WHEN** no element of a path carries a stated tier
- **THEN** the surface is coherent, because the consumer is told nothing rather than told
  half of something
