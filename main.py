#!/usr/bin/env python3
"""Entry point:  python main.py [options]   (see --help)"""

import argparse
import sys

try:
    import pygame  # noqa: F401
except ImportError:
    sys.exit("This game needs pygame.  Install it with:  pip install pygame")

from pacman import Game
from pacman.settings import MAX_GHOSTS


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Autonomous Pac-Man with random mazes")
    ap.add_argument("--ghosts", type=int, default=4, help=f"number of ghosts (0-{MAX_GHOSTS})")
    ap.add_argument("--cols", type=int, default=31, help="maze width in tiles (adjusted to 4k+3)")
    ap.add_argument("--rows", type=int, default=21, help="maze height in tiles (adjusted to odd)")
    ap.add_argument("--tile", type=int, default=24, help="tile size in pixels")
    ap.add_argument("--lives", type=int, default=3)
    ap.add_argument("--seed", type=int, default=None, help="random seed (repeatable mazes)")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--manual", action="store_true", help="start in manual mode (arrow keys)")
    ap.add_argument("--no-power", action="store_true",
                    help="no power pellets: ghosts are always deadly and can never be eaten")
    ap.add_argument("--frames", type=int, default=0, help="quit after N frames (testing)")
    ap.add_argument("--turbo", action="store_true", help="fixed timestep, no frame cap (testing)")
    return ap.parse_args(argv)


def main():
    Game(parse_args()).run()


if __name__ == "__main__":
    main()
