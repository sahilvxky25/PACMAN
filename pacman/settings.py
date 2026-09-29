"""Constants and tiny helpers shared by every module."""

# ---- directions (dx, dy) ----------------------------------------------------
UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
DIR_LIST = [UP, LEFT, DOWN, RIGHT]

# ---- colours ------------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 221, 0)
WALL_BLUE = (33, 60, 255)
DOT_COL = (255, 214, 170)
FRIGHT_BLUE = (30, 30, 255)
RED = (255, 60, 60)

GHOST_COLORS = [
    (255, 0, 0),       # Blinky
    (255, 150, 255),   # Pinky
    (0, 230, 255),     # Inky
    (255, 165, 60),    # Clyde
    (90, 255, 120),    # Wanderer
    (190, 100, 255),   # Hunter
]
GHOST_NAMES = ["Blinky", "Pinky", "Inky", "Clyde", "Wanderer", "Hunter"]

# ---- gameplay tuning ------------------------------------------------------------
PAC_SPEED = 6.2            # tiles per second
FRIGHT_SPEED = 3.2
EATEN_SPEED = 11.0
MAX_GHOSTS = 12

# (duration in seconds, chase?) - classic scatter / chase alternation
MODE_SCHEDULE = [(7, False), (20, True), (7, False), (20, True),
                 (5, False), (20, True), (5, False), (1e9, True)]

# ---- layout ---------------------------------------------------------------------
HUD_TOP = 44
HUD_BOTTOM = 34


def norm_dims(cols, rows):
    """Mirror symmetry needs cols % 4 == 3; rows must be odd."""
    cols = max(11, cols)
    rows = max(9, rows)
    cols += (3 - cols % 4) % 4
    if rows % 2 == 0:
        rows += 1
    return cols, rows
