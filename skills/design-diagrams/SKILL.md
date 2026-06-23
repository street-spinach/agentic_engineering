---
name: Design Diagrams
description: >-
  Sketch a software design as plain-text block diagrams a reviewer can read in a
  minute — sequence flows, module/component interactions, high-level class
  structures, and ER / data models. Drawn with box-drawing characters so they
  render anywhere (PRs, terminals, Markdown) with zero tooling. Use when the user
  wants to "diagram", "draw", "sketch the design", "show how X talks to Y", "model
  the data", or explain a flow/architecture visually. This is for communication,
  not a full design spec — keep diagrams small and legible.
---

# Design Diagrams

Draw the design so a reviewer *gets it fast*. The goal is shared understanding,
not exhaustive documentation. One focused block diagram that fits on a screen
beats a sprawling one that's technically complete. Diagrams are plain text in a
```` ``` ```` fenced block — no renderer, no dependencies.

## Pick the right diagram

| The question being answered | Diagram |
|---|---|
| "What happens, in what order, between who?" | Sequence |
| "How do the pieces fit / who calls what?" | Module / component |
| "What are the main types and how do they relate?" | HL class |
| "How is the data shaped and related?" | ER / data model |

Unsure? Ask one question or default to the user's verb ("flow"→sequence,
"talks to"→module, "model the data"→ER).

## Principles (apply to every diagram)

- **Altitude over completeness.** Show the boxes that matter to the decision;
  collapse the rest. ~5–12 boxes is the sweet spot. If it needs more, split it.
- **Label the arrows, not just the boxes.** An arrow that says *what* crosses it
  (`POST /orders`, `publishes OrderPlaced`, `1..*`) carries the real information.
- **Name things as the code does.** Real service/class/table names so the diagram
  maps to the repo, not an idealized version of it.
- **One concern per diagram.** Don't fold a sequence flow into a class diagram —
  stack several small diagrams instead.
- **Keep it aligned.** Use box-drawing chars (`┌ ┐ └ ┘ │ ─ ├ ┤`) and arrows
  (`──>`, `<──`, `│`, `▼`). Pad boxes so columns line up; ragged ASCII reads as
  sloppy thinking.

## Templates

**Sequence** — order of interactions over time. Vertical lifelines, arrows left
to right with the message on them, time flows downward.

```
  User            API            DB
   │               │              │
   │  POST /orders │              │
   │ ─────────────>│              │
   │               │ insert order │
   │               │ ────────────>│
   │               │      id      │
   │               │ <────────────│
   │  201 Created  │              │
   │ <─────────────│              │
   │               │              │
```

**Module / component** — who depends on / talks to whom. Boxes + labeled arrows;
group related boxes by placing them in the same row/column.

```
  ┌──────────┐  REST   ┌───────────────┐  SQL   ┌────────────┐
  │ Web App  │ ──────> │ Order Service │ ─────> │ Orders DB  │
  └──────────┘         └───────┬───────┘        └────────────┘
                               │ publishes
                               ▼
                       ┌───────────────┐        ┌────────────────────┐
                       │   Event Bus   │ ─────> │ Fulfillment Worker │
                       └───────────────┘        └────────────────────┘
```

**High-level class** — the few types that carry the design. List only the
fields/methods that matter; note the relation on the connector
(`*── composition`, `──> association`, `─▷ inherits`).

```
  ┌─────────────────┐  1     1..* ┌────────────┐
  │ Order           │ *────────── │ LineItem   │
  ├─────────────────┤             ├────────────┤
  │ + id            │             │ + qty      │
  │ + total()       │             │ + price    │
  └─────────────────┘             └────────────┘
```

**ER / data model** — entities, key attributes, and cardinality on the line
(`1──*`, `1──1`, `*──*`). Mark `PK` / `FK`.

```
  ┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
  │ CUSTOMER     │ 1     * │ ORDER            │ 1     * │ LINE_ITEM    │
  ├──────────────┤ ────────┤──────────────────┤ ────────┤──────────────┤
  │ id        PK │  places │ id            PK │ contains │ id        PK │
  │ email        │         │ customer_id   FK │         │ order_id  FK │
  └──────────────┘         └──────────────────┘         └──────────────┘
```

## Output

Lead with one line on *what the diagram shows and why this view*, then the fenced
block diagram. For a multi-part design, give a short stack of small diagrams (e.g.
one module map + one sequence for the key flow) rather than one dense
everything-diagram. Stop there — this skill conveys the design; it doesn't write
the spec.
