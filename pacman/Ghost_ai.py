"""Ghost behaviour: where each personality wants to go and how it steers."""


class GhostBrain:
    """Decides ghost movement.  Reads the shared Game object for the maze,
    Pac-Man, the other ghosts and the current scatter / chase mode."""

    def __init__(self, game):
        self.game = game

    # ---- targeting -------------------------------------------------------
    def target(self, g):
        game = self.game
        m, pac, rng = game.maze, game.pac, game.rng
        if not game.chase:                           # scatter: go to a corner
            return m.corners[g.idx % 4]

        pt, pd = pac.tile, pac.dir
        k = g.kind
        if k == 0:                                   # Blinky - direct chase
            return pt
        if k == 1:                                   # Pinky - 4 tiles ahead
            return m.nearest_open(pt[0] + 4 * pd[0], pt[1] + 4 * pd[1])
        if k == 2:                                   # Inky - flank via Blinky
            b = game.ghosts[0]
            ax, ay = pt[0] + 2 * pd[0], pt[1] + 2 * pd[1]
            return m.nearest_open(2 * ax - b.tile[0], 2 * ay - b.tile[1])
        if k == 3:                                   # Clyde - shy when close
            d = m.dist_map(pt).get(g.tile, 0)
            return pt if d > 8 else m.corners[g.idx % 4]
        if k == 4:                                   # Wanderer - semi-random
            if g.wander is None or g.tile == g.wander:
                g.wander = pt if rng.random() < 0.4 else rng.choice(m.open)
            return g.wander
        # Hunter - long-range ambush
        return m.nearest_open(pt[0] + 8 * pd[0], pt[1] + 8 * pd[1])

    # ---- steering --------------------------------------------------------
    def choose(self, g):
        """Called whenever a ghost stands on a tile; returns a direction."""
        game = self.game
        m = game.maze
        if g.state == "wait":
            return None
        opts = m.adj[g.tile]
        if not opts:
            return None

        rev = (-g.dir[0], -g.dir[1])
        if g.state == "eaten":                       # eyes race back home
            dm = m.dist_map(m.home)
            return min(opts, key=lambda o: dm[o[0]])[1]

        if g.want_reverse:                           # mode switch / power pellet
            g.want_reverse = False
            for _, d in opts:
                if d == rev:
                    return d

        cand = [o for o in opts if o[1] != rev] or opts    # no U-turns normally
        if g.fright_t > 0:                                 # frightened: wander
            return game.rng.choice(cand)[1]
        dm = m.dist_map(self.target(g))
        return min(cand, key=lambda o: (dm.get(o[0], 999), game.rng.random()))[1]

    def arrive(self, g):
        """Called each time a ghost reaches a tile."""
        m = self.game.maze
        if g.state == "eaten" and g.tile == m.home:
            g.state, g.wait_t, g.dir = "wait", 1.2, (0, 0)
