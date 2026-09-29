"""Moving things: the generic Actor, Pac-Man and the Ghosts."""

from .settings import GHOST_COLORS, GHOST_NAMES, LEFT, PAC_SPEED


class Actor:
    """Tile-based mover with smooth interpolation between tiles."""

    def __init__(self, maze, tile, speed):
        self.step = maze.step
        self.tile = tile          # tile we are at / leaving
        self.nxt = tile           # tile we are heading to
        self.p = 0.0              # progress along the current edge, 0..1
        self.dir = (0, 0)
        self.speed = speed        # tiles per second

    @property
    def moving(self):
        return self.nxt != self.tile

    def pos(self):
        """Exact (float) position in tile coordinates."""
        x, y = self.tile
        if self.nxt == self.tile:
            return (float(x), float(y))
        return (x + self.dir[0] * self.p, y + self.dir[1] * self.p)

    def reverse(self):
        """Turn around in the middle of a corridor."""
        if self.nxt != self.tile:
            self.tile, self.nxt = self.nxt, self.tile
            self.p = 1.0 - self.p
            self.dir = (-self.dir[0], -self.dir[1])

    def advance(self, dt, choose, arrive=None):
        """Move for dt seconds.  `choose(actor)` returns a direction whenever the
        actor stands on a tile; `arrive(actor)` fires each time a tile is reached."""
        dist = self.speed * dt
        guard = 0
        while dist > 1e-9 and guard < 8:
            guard += 1
            if self.nxt == self.tile:
                d = choose(self)
                if d is None:
                    return
                nb = self.step[self.tile].get(d)
                if nb is None:
                    return
                self.nxt, self.dir, self.p = nb, d, 0.0
            rem = 1.0 - self.p
            if dist >= rem:
                dist -= rem
                self.tile, self.p = self.nxt, 0.0
                if arrive:
                    arrive(self)
            else:
                self.p += dist
                dist = 0.0


class Pacman(Actor):
    def __init__(self, maze, tile):
        super().__init__(maze, tile, PAC_SPEED)
        self.anim = 0.0           # mouth animation phase
        self.want = None          # requested direction in manual mode
        self.dir = LEFT


class Ghost(Actor):
    def __init__(self, maze, idx, speed, wait):
        super().__init__(maze, maze.home, speed)
        self.idx = idx
        self.kind = idx % 6                    # personality
        self.color = GHOST_COLORS[self.kind]
        self.name = GHOST_NAMES[self.kind]
        self.state = "wait"                    # wait | active | eaten
        self.wait_t = wait                     # seconds before leaving home
        self.fright_t = 0.0                    # >0 while frightened (blue)
        self.want_reverse = False
        self.wander = None                     # target used by the Wanderer
        self.dir = (0, 0)
