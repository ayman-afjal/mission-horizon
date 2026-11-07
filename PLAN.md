# Mission Horizon — Build Plan

Goal: playable prototype of the README loop
`Choose mission -> Design craft -> Plan (Δv) -> Script -> Launch -> Simulate -> Adapt -> Succeed`

Design decisions (keeps scope honest)
* Real-scale Earth + Moon, 2D, SI units. Earth does not rotate (yet).
* One propellant type; stages are split by decouplers; engines burn the fuel of their own stage.
* Physics: kick-drift-kick (velocity Verlet), adaptive step, time warp up to 100,000x in vacuum.
* Moon is "on rails" (circular orbit) but pulls on the ship, so lunar transfers are real 3-body-ish trajectories.
* Mission scripts: small line-based language (no eval), executed every physics step.

| # | Milestone | Done when | Status |
|---|-----------|-----------|--------|
| M0 | Foundation: loop with dt, settings, UI kit, save file, data files | menu -> space center -> back works | DONE |
| M1 | Physics core: vectors, bodies, Kepler elements, Verlet, predictor | unit tests: LEO stays circular, escape works | DONE |
| M2 | Spacecraft + Vehicle Assembly Building (parts, stages, Δv, TWR, cost) | can build + validate a rocket vs mission limits | DONE |
| M3 | Flight scene: launch, drag, staging, SAS, camera, map, warp, HUD | fly Mission 1 by hand | DONE |
| M4 | Missions + Mission Control + results/stars + unlocks | M1 & M2 completable, progress saved | DONE |
| M5 | Scripting: parser, executor, in-game editor | M1/M2 flown by the autopilot script | DONE |
| M6 | Moon missions: lunar orbit + soft landing | M3/M4 verified by headless bot flights (DONE) | |
| M7 | (next) Research lab upgrades, sample return, Earth rotation, reentry heating, crew | — | |

