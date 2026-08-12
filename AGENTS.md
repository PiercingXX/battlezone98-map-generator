# Operating instructions for the build agent

You are implementing the toolchain specified in `docs/`. Read `docs/00-project-brief.md`
first, then `docs/05-architecture.md`, then build in the phase order given in
`docs/08-build-plan.md`.

**Asked to MAKE A MAP? Read `docs/16-START-HERE-map-making.md` first** — it
carries the engine facts, the operator's calibration and the play-test ledger,
and routes you to the authoring policy (docs/15) and quality bar (docs/14).

## Ground rules

1. **Do not trust format claims you cannot re-verify.** Every spec in `docs/01` and
   `docs/02` was measured from real files. Before you rely on any of them, re-measure
   against the installed pack. If reality disagrees with the spec, **reality wins** —
   fix the doc in the same commit as the code.

2. **Never modify the installed game or any installed Workshop content.** Treat
   `~/.steam/steam/steamapps/common/Battlezone 98 Redux` and
   `~/.steam/steam/steamapps/workshop/content/301650` as **read-only reference data**.
   Write output only into this repo's `build/` directory. Installing a map for testing
   is done by copying into a *separate* workshop/mod folder, never by editing installed content.

3. **Template-and-mutate, do not synthesize from scratch.** The BZN writer must start
   from a known-good object block (`reference/bzn-object-template.txt`) and substitute
   values. Do not hand-assemble field lists from the spec — field *order* is load-bearing
   and the spec may be incomplete in ways the corpus is not.

4. **Round-trip before you generate.** The first thing that must work is:
   parse a stock corpus `.bzn` → re-emit it → assert byte-identical output. Until that
   passes, do not write a generator. This single test catches almost every format error.

5. **Every generated map must pass the offline validators before it is ever launched.**
   See `docs/06-validation.md`. Launching the game is slow; the validators are seconds.

6. **Ten maps means ten *distinct* maps.** Do not ship ten reskins of one layout with
   different seeds. See the diversity requirement in `docs/00-project-brief.md`.

## Environment notes

- Platform is **Linux**; the game runs under **Proton Experimental**. There is no
  `wine` on PATH. `Edit/MakeTRN.exe` is a Windows binary — if you need it, run it via
  Proton, but prefer reimplementing its output in Python (the formats are known and it
  only does two things you need).
- Python deps for reusing WorldBuilder: `numpy`, `scipy`, `Pillow`, `imageio`.
  `Pillow` and `numpy` are **not currently installed** — use a venv.
- The game exposes **no command-line switch to load a specific map.** In-game testing
  goes through the Lua harness described in `docs/06-validation.md`, not CLI automation.

## When you are blocked

Write the blocker into `docs/09-open-questions.md` with what you tried and what you
observed, then continue with work that does not depend on it. Do not stall the whole
build on one unknown, and do not silently guess and move on — a wrong guess baked into
30 generated files is much more expensive than a stalled sub-task.

## Definition of "done" for any phase

A phase is done when its acceptance criteria in `docs/08-build-plan.md` pass **and**
you have written down what you verified and how. "It looks right" is not evidence.
An audit pass will check your claims against the artifacts.
