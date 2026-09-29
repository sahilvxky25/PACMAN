# Autonomous Pac-Man

A self-playing Pac-Man with a new random maze every level and a configurable
number of ghosts. Written in Python with pygame.

## Run
```bash
pip install -r requirements.txt
python main.py                       # 4 ghosts, autopilot
python main.py --ghosts 8 --cols 35 --rows 23
python main.py --no-power --ghosts 5 # ghosts always deadly
python main.py --manual              # steer with the arrow keys
python main.py --seed 42             # repeatable mazes
```

## Keys
| Key | Action |
|-----|--------|
| SPACE / P | pause |
| N | new random maze |
| R | restart game |
| + / - | add / remove a ghost |
| M / A | toggle autopilot / manual |
| Arrow keys | steer (manual mode) |
| D | debug view: AI's safe region, target, ghost targets |
| [ / ] | slower / faster simulation |
| ESC / Q | quit |

## Project layout
```
main.py                 command-line entry point
pacman/
  settings.py           constants, colours, tuning values
  maze.py               random symmetric maze, tunnels, BFS distance maps
  entities.py           Actor (movement), Pacman, Ghost
  ghost_ai.py           ghost personalities, targeting and steering
  pacman_ai.py          autopilot: time-aware safe planner
  renderer.py           all drawing (walls, sprites, HUD, banners)
  game.py               game state, rules, input, main loop
```

## How the pieces talk
`Game` owns everything: it builds a `Maze`, spawns `Pacman` and `Ghost`
entities, and holds an `AutoPilot` (Pac-Man's brain), a `GhostBrain` and a
`Renderer`. The brains and renderer read the shared `Game` state; only `Game`
changes the rules (scoring, lives, levels).

## Ghost personalities
Blinky chases directly, Pinky aims 4 tiles ahead, Inky flanks using Blinky,
Clyde backs off when close, the Wanderer picks semi-random targets and the
Hunter aims 8 tiles ahead. With more than six ghosts the personalities repeat.

## Autopilot in short
Each decision searches the maze but only expands tiles Pac-Man can reach
before every dangerous ghost. Dots, power pellets and edible ghosts inside
that safe region are scored with a distance decay; Pac-Man reverses mid-corridor
when a ghost closes in and commits to a goal while nothing is near.
