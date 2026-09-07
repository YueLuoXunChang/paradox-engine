# paradox-engine · The Paradox Engine

> The smallest engine that treats "contradiction" as a first-class research object.
> Stance: **diagnose only, never decide** — measure it, annotate it, report it,
> and leave the judgment to whoever uses it.
>
> 🌐 **中文**：[README.md](README.md)

**paradox-engine** is a small, focused prototype engine for paradox /
contradiction detection, built from carefully selected core mechanisms of the
"Luoluo Logic System" (落落逻辑体系, original work by YueLuoXunChang / 月落寻常).
This repository is an **independent open-source container**: it contains only
the parts the author chose to make public, fully separated from the full body
of the system (documentation library and complete mechanism library).

> **What it is, in one sentence for a stranger**: a pure-Python toolbox of
> logic utilities — feed it a contradictory argument, a self-referential
> sentence, or conflicting requirements, and it will not argue for you or
> eliminate the contradiction. Instead it tells you: how sharp the paradox
> is (μ), what type it is, whether it can stably exist, and which positions
> can stand up to attack — every answer with its evidence, fully auditable.
> What classical logic can decide, it decides first (propositional /
> first-order / temporal / modal / lambda-calculus / types). What cannot be
> decided (self-reference and paradox) goes through a "wall pipeline" that
> returns a five-way diagnosis (decidable / benign self-reference /
> resonance-band self-reference / divergent wall / creatable). Zero
> third-party dependencies; `python demo.py` walks through all fifteen
> capabilities in about two minutes.

---

## 1. What this project claims (30 seconds)

| The usual way | paradox-engine's way |
|---|---|
| Eliminate contradictions, avoid them, pretend they do not exist | **Contradiction first**: admit it exists |
| Argue about whether something "counts" as a paradox | **Measure it**: paradox strength μ ∈ [0,1], one number |
| Give conclusions without process | **White-box**: every conclusion carries its evidence |
| Silently make decisions for the user | **Diagnose only**: leave judgment to the user |

One sentence: **we do not solve paradoxes — we turn them into measurable,
annotatable, traceable objects.**

---

## 2. Quick start (2 minutes)

```bash
# After cloning, from the repository root
python demo.py
```

`demo.py` demonstrates fifteen things (①②③ the paradox trio → ④-⑩ the
classical-logic foundation → ⑪ wall pipeline → ⑫ five-step controller →
⑬ MT-MP-TL skeleton → ⑭ cold logics → ⑮ AI mounting):

| Step | Demonstration | Layer |
|---|---|---|
| ① paradox measure | 50/50 evidence → μ = 1.0 (strong paradox) — how sharp is the contradiction, one number says it | L2 |
| ② paradox annotation | A contradiction gets an 8-field "ID card" + grade (P-A/P-B/P-C) | L2 |
| ③ convergence check | Will the iteration stop (contraction mapping → converges) | L2 |
| ④ propositional logic | Syllogism validity / counterexample / law of excluded middle | L1 |
| ⑤ first-order logic | ∀/∃ quantifier reasoning (finite-domain expansion) | L1 |
| ⑥ temporal LTL | G/F/U evolution properties + violation location | L1 |
| ⑦ modal logic | □/◇ Kripke semantics (K/T/S4/S5) | L1 |
| ⑧ lambda calculus | β-reduction / Y combinator / Church encoding (self-reference as computation) | L1 |
| ⑨ Turing machine | Simulation + honest answer to the undecidable halting problem | L1 |
| ⑩ STLC types | Types block self-application (well-typed ⇒ terminates) — contrast with ⑧ | L1 |
| ⑪ wall pipeline | Liar sentence → **five-way diagnosis** (measure→annotate→drill→view→bypass→create) | L2 |
| ⑫ five-step controller | Chinese text → classify→complexity→route→execute→judge (Chinese report) | Control |
| ⑬ MT-MP-TL skeleton | Multi-thread parallel → merge + topology classification (structure only, no judging) | L0 |
| ⑭ cold logics | Contradiction takes value "both" (Belnap four-valued) + stance analysis (Dung) | L3 |
| ⑮ AI mounting | All 23 engine functions = AI-callable tools (function-calling schemas auto-generated) | Mounting |

You can also call a mechanism directly:

```python
from engine.mechanisms.paradox_measure import run as measure

r = measure({'mode': 'mu1', 'wA': 5, 'wNotA': 5})
print(r['mu'])   # 1.0 — perfectly balanced evidence, maximum paradox strength
```

Or a classical-layer component:

```python
from engine.classical.propositional import run as pl

r = pl({'premises': ['人→会死', '人'], 'conclusion': '会死',
        'mode': 'validity'})
print(r['verdict'])   # valid
```

---

## 3. Directory structure

```
paradox-engine/
├── engine/
│   ├── ai/                     ← AI mounting (engine functions = function-calling tools)
│   │   ├── tools.py              schemas auto-generated from all 23 components + call_tool
│   │   └── ai_scenarios.py       two end-to-end real scenarios (argument conflict / modeling)
│   ├── control/               ← Controller (the "brain": classify/complexity/route/five-step pipeline)
│   │   ├── classifier.py         12 problem-type classifier + L1/L2/L3 complexity + ROUTE (36 keys)
│   │   └── controller.py         five-step pipeline: classify→complexity→route→execute→judge
│   ├── mechanisms/            ← Paradox mechanisms (L2: run(inputs)->dict + PORTS + self-test)
│   │   ├── paradox_measure.py    paradox strength μ (four branches)
│   │   ├── paradox_annotate.py   paradox annotation (8-field card + P-A/B/C grades)
│   │   ├── converge_check.py     convergence check (compression/finite/asymptotic/oscillation)
│   │   ├── selfref_fixpoint.py   recursive revision × self-reference (three states, wall-driller)
│   │   ├── boundary_paradox.py   boundary-paradox diagnosis (wall = boundary: tension/undermining/rebirth)
│   │   ├── observer_bypass.py    full self-reflexive bypass (main chain never blocks)
│   │   ├── counterpoint_gen.py   counterpoint generation (opposites → third state candidate)
│   │   └── wall_pipeline.py      wall pipeline A (measure→annotate→drill→view→bypass→create → 5-way verdict)
│   ├── skeleton/              ← MT-MP-TL skeleton (L0: structure only, no judging)
│   │   └── mtmp.py               points/threads/topology (12 shapes)/operations (5 kinds)
│   ├── cold/                  ← Cold logics (L3: chosen by need; external consensus marked as borrowed)
│   │   ├── belnap_four.py        Belnap four-valued logic (contradiction = "both", no explosion)
│   │   └── dung_framework.py     Dung argumentation framework (which positions stand)
│   └── classical/             ← Classical-logic foundation (L1: decision/proof/computation/types)
│       ├── propositional.py       propositional logic (validity/counterexample/satisfiable/tautology)
│       ├── nd_propositional.py    natural deduction ND (proof trees, classical/intuitionistic)
│       ├── first_order.py         first-order logic (∀/∃ finite-domain expansion)
│       ├── resolution.py          first-order resolution (Skolem + unification + refutation)
│       ├── equality_tableau.py    equality + tableau (countermodel)
│       ├── ltl.py                 temporal LTL (G/F/X/U along paths)
│       ├── modal.py               modal logic (Kripke semantics K/T/S4/S5)
│       ├── lambda_calculus.py     lambda calculus (β-reduction / Y combinator)
│       ├── turing_machine.py      Turing machine (simulation + UTM + halting demo)
│       └── stlc.py                simply typed lambda calculus (type checking, blocks self-application)
│       (each component ships with a test_*.py formal test)
├── demo.py                  ← 2-minute tour (fifteen steps)
├── docs/
│   ├── mechanisms.md             layered capability index (self-test N + formal M per component)
│   ├── ROADMAP.md                layered roadmap
│   └── formulas/                 concept cards (×10 for the classical layer)
├── README.md                ← Chinese readme (this English one: README.en.md)
└── (will grow as the author selects more parts to make public)
```

Every component is self-contained: `python engine/<layer>/<name>.py` runs its
self-test; `python engine/<layer>/test_<name>.py` runs its formal tests.

---

## 4. Core concepts

### Mechanism = a diagnose-only decision function

One unified interface:
```python
run(inputs: dict) -> dict
```

Three design conventions apply to every mechanism:
- **Honesty**: if input is missing, report what is missing (`*_pending`) — never guess, never fake a verdict;
- **Interception**: illegal input is reported honestly; no fabricated values are produced;
- **White-box**: `advice`/`boundary` fields explain the basis; important paths are traceable.

### Paradox measure μ (paradox_measure)

Four branches measure "how sharp is this contradiction":
- `mu1` evidence weight (default): the more balanced the two sides, the closer μ is to 1;
- `mu2` self-reference: X = ¬X directly yields 1;
- `mu3` layering: contradiction across levels of discourse;
- `mu4` entropy: the more uncertainty, the stronger the paradox tendency.

### Paradox annotation (paradox_annotate)

Once A∧¬A coexistence is detected, the engine does **not** resolve or remove
it; it produces an 8-field annotation card (ID/LV/POS/SRC/CT/EF/ST/AN) graded
by source:
- axiom layer → P-A (structural, highest);
- runtime → P-B;
- observer → P-C.

### Convergence check (converge_check)

Decides whether a recursive revision sequence x_{n+1} = f(x_n, err(x_n))
converges: contraction mapping (default) / finite steps / asymptotic /
oscillation.

---

## 5. Design philosophy (why "diagnose only, never decide")

Many systems react to a contradiction by "fixing it" — but that is often a
**decision made quietly with insufficient evidence**. paradox-engine changes
the order:

```
contradiction appears → measure (μ) → annotate (card) → report (white-box) → judgment returns to the user
```

Diagnosis and decision are separated: the engine describes the contradiction
truthfully; the system or person using it decides what to do with it. The
contradiction is neither eliminated nor ignored — it becomes an object that
can be discussed, compared, and traced.

---

## 6. Scope and roadmap

**Currently implemented (layered)**:
- **Controller (the brain)**: a 12-type classifier (signal table → main type /
  secondary type / confidence) + complexity grading (L1/L2/L3) + a route table
  (36 keys with reasons) + a **five-step pipeline** (classify → complexity →
  route → really run the components → judge the output with five checks) —
  minimal-sufficiency principle: simple problems are never over-processed
  (L1 goes straight through a single mechanism), complex problems are not
  oversimplified (L3 runs the full pipeline);
- **L1 · classical-logic foundation (all 9 families done)**: propositional
  decision → natural deduction → first-order decision → resolution →
  equality/tableau → temporal LTL → modal → lambda calculus → Turing machine →
  simply typed lambda (STLC) — classical consensus, accessible to anyone;
  decidable cases are decided (finite-domain expansion/unification/tableau/
  type checking); proof theory / computability / type theory give honest
  answers (proof trees, refutation chains, halting problem collected as a
  specimen, types blocking self-application);
- **L0 · MT-MP-TL skeleton**: points (heterogeneous/autonomous/deformable) +
  threads (direction/speed/merge/cross) + topology classification (12 shapes)
  + operations (connect/disconnect/replace/fold/spawn) — structure expression
  only, no judging mixed in;
- **L2 · paradox (the five-piece wall pipeline)**: paradox measure (μ) +
  annotation (8-field card + grade) + convergence check + **recursive
  revision × self-reference detection** (three states: fixed point /
  resonance band / divergence) + **boundary-paradox diagnosis** + **full
  self-reflexive bypass** + **counterpoint third-state generation** — when the
  classical layer hits something undecidable it escalates here and returns a
  **five-way diagnosis** (decidable / benign self-reference /
  resonance-band self-reference / divergent wall / creatable). "Contradiction
  as first-class citizen" moves from slogan to runnable pipeline;
- **L3 · cold logics (first two pieces)**: Belnap four-valued logic
  (contradiction = "both", no explosion — a semantic foundation for the
  resonance band) + Dung argumentation framework (grounded/preferred — which
  positions can withstand attack) — chosen by real need; external consensus
  is labeled and kept in the "borrowed" section, never mixed into the
  original-work section;
- **AI mounting layer**: all 23 components wrapped as function-calling tools
  (schemas auto-generated from PORTS, zero hand-maintained drift) + `call_tool`
  dispatch — an AI receives the tool list and can call the whole engine;
  two end-to-end real scenarios (argument-conflict check / discipline
  modeling).

**Extending (see docs/ROADMAP.md)**: stage 7 optional (Kleene recursion
theorem / Gupta-Belnap truth revision / arithmetic hierarchy — borrowed
mathematical foundations, sources labeled) → AGM non-monotonic / relevance
logic (added when a real pain point appears).

- Pure Python standard library, zero third-party dependencies;
- The full body of the system (Luoluo Logic System: complete mechanism
  library and documentation library) is **not in this repository**; only the
  parts the author chose to make public live here;
- This project **does not claim to settle any philosophical/logical dispute**,
  and does not claim to bypass the Turing halting problem or Gödel
  incompleteness (those are theorems). It does two things: decides what
  classical logic can decide; and for what cannot be decided — measure,
  annotate, report honestly, and leave judgment to the user.

---

## 7. Origin, collaboration, and license

- **Conceptual origin**: YueLuoXunChang (月落寻常 / "Luoluo"), author of the
  "Luoluo Logic System". The content of this repository was **selected** by
  the author from that system and authorized to be public; the full body of
  the system (complete documentation and mechanism libraries) is not in this
  repository.
- **AI collaboration note**: the engineering implementation in this
  repository (code, tests, docs, demo choreography) was produced in
  collaboration between the author and an AI — the AI did the implementation
  and assembly; the concepts, design direction, trade-offs, and final
  decisions were led by the author. The layered claims (layer 1: classical
  logic decides what it can; layer 2: contradiction as first-class citizen;
  diagnose-only-never-decide) are the author's original direction.
- **Borrowed material**: classical consensus reused in the code (e.g. Belnap
  four-valued logic, Dung argumentation framework, and the classical-logic
  components) is labeled with its source in the corresponding file's
  docstring and kept in the "borrowed" section — never mixed into the
  original-work section.
- References to concept cards (`formulas/*.md`) are explanatory and may be
  completed as the repository evolves.
- **License**: **MPL-2.0 (Mozilla Public License 2.0)** — commercial use and
  modification allowed; collaboration welcome (fork / pull requests /
  co-development). If you modify a source file, that file stays open under
  the MPL. Full terms in [LICENSE](LICENSE).

---

## 8. For contributors

Want to add a mechanism? Follow the existing file format (PORTS + run +
`__main__` self-test) and get a small case working before extending. The
repository rules:
- every mechanism must be self-contained and independently runnable;
- illegal input must be intercepted honestly — never fabricate values;
- diagnose only, never decide — never draw conclusions for the user.
