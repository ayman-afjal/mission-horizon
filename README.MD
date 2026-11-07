# Mission Control

### A 2D Space Mission Design, Strategy & Simulation Game

> Design the spacecraft. Plan the trajectory. Program the mission. See if you can get it home.

Mission Control is a student-developed 2D space mission simulator inspired by games such as Spaceflight Simulator and Juno: New Origins, but with a different core focus.

Instead of trying to recreate a full-scale rocket sandbox, Mission Control focuses on mission planning, orbital mechanics, spacecraft engineering, automation, and strategic decision-making.

Players design spacecraft under limited resources, calculate orbital transfers, plan trajectories, write autonomous mission scripts, and watch their spacecraft execute the mission.

---

## Concept

Real space missions involve many interconnected engineering decisions:

- Rocket design
- Mass constraints
- Fuel and Delta-v
- Power consumption
- Communications
- Mission budgets
- Orbital mechanics
- Trajectory planning
- Scientific objectives

Mission Control turns these concepts into an interactive game.

The player does not simply pilot a rocket.

They design and operate an entire mission.

---

## Core Gameplay Loop

```text
          CHOOSE MISSION
                |
                v
        DESIGN SPACECRAFT
                |
                v
        PLAN TRAJECTORY
                |
                v
          CALCULATE Δv
                |
                v
          WRITE SCRIPT
                |
                v
             LAUNCH
                |
                v
           SIMULATE
                |
                v
        MONITOR / ADAPT
                |
                v
       MISSION SUCCESS

---

# Playing the prototype

```bash
pip install -r requirements.txt
python main.py
```

**Loop:** Space Center → *Mission Control* (read the brief, edit your script) → *Vehicle Assembly* (stack parts, watch Δv / TWR / cost) → *Launch Pad* → fly by hand or press **P** to run your script.
Finishing a mission unlocks new parts (see *Research Lab*) and the next mission. Progress is saved to `save.json`.

| Mission | Goal |
|---------|------|
| 1 First Light | Cross 100 km altitude |
| 2 Park in Orbit | Stable Earth orbit, periapsis > 160 km |
| 3 Lunar Orbiter | Capture a satellite into lunar orbit |
| 4 Touchdown | Soft-land on the Moon (< 5 m/s) |
| 5 Sample Return | *coming soon* |

Each mission ships a template craft and script (use *Template* in the VAB and *Load template script* in Mission Control). Stars: 1 = done, 2 = under 70 % of budget, 3 = under 50 %.

## Flight controls
`Z`/`X` full/cut throttle · `Shift`/`Ctrl` throttle up/down · `A`/`D` rotate · `1-5` SAS (hold, prograde, retrograde, radial out/in) · `Space` stage · `.`/`,` time warp · `M` map · `Tab` Earth/Moon map focus · `F` fit map · wheel zoom (`C` auto camera) · `P` autopilot script · `H` help · `Esc` pause.

## Craft model
A craft is a vertical stack, top to bottom. A **decoupler starts a new stage**; the bottom stage fires first, its engines burn *its own* tanks, and `Space` drops it. Top part must be a pod. One propellant type; engines have vacuum and sea-level Isp.

## Mission scripts
Plain text, one command per line, `#` comments. Evaluated every physics step.
```
throttle <expr>                      pitch <expr>        (deg above local horizon, 90 = up, heading east)
sas hold|prograde|retrograde|radial_out|radial_in         stage     end
wait <seconds>      wait until <cond>      warp <n>       print <text>
if <cond> then <command>
throttle <expr> until <cond>         (closed-loop: re-evaluated every step; also for pitch)
```
Expressions: `+ - * /`, parentheses, `sqrt() abs() min(,) max(,)`, suffixes `km min h`.
Variables: `altitude apoapsis periapsis speed vertical_speed horizontal_speed eta_apoapsis eta_periapsis mission_time throttle stage_fuel mass stages twr thrust q eccentricity moon_angle moon_distance in_moon_soi gravity landed`.
`moon_angle` is how far (deg) the Moon is *ahead* of you along your orbit - use it to time the trans-lunar burn. See mission 3 and 4 templates for ascent, TLI, orbit capture and a suicide-burn landing.

## Project layout
```
core/        settings, scene base, game state + save, time warp
physics/     vector, bodies + gravity (Earth, Moon on rails), Kepler elements + trajectory predictor, headless flight sim
spacecraft/  parts (data/parts.json), engines, fuel, craft/stage model + Δv analysis
missions/    mission + objective evaluators (data/missions.json)
scripting/   parser + executor for mission scripts
scenes/      menu, space center, mission control, VAB, flight, research lab, tracking station
ui/          button, panels, list box, script editor
tests/       test_physics.py, test_missions.py (flies all missions headless), ui_smoke.py, tools/ (tuning scripts)
```
Modelling shortcuts (see PLAN.md for the roadmap): Earth does not rotate, 2D, Moon on a circular orbit, one propellant, simple drag (Cd 0.2), no re-entry heating.

## Tests
```bash
python tests/test_physics.py
python tests/test_missions.py     # ~25 s: flies missions 1-4 with their template scripts
python tests/ui_smoke.py          # headless UI walkthrough, screenshots in /tmp/shots
```
