"""The autopilot: decides where Pac-Man goes when nobody is steering."""

import heapq
from collections import deque


class AutoPilot:
    """Time-aware safe planner.

    Every decision runs a Dijkstra/BFS from Pac-Man's position, but a tile is
    only expanded if Pac-Man can get there *before* every dangerous ghost
    (with a safety margin).  Dots, power pellets and edible ghosts inside that
    safe region are valued with a distance decay, and the first step towards
    the best-scoring area is returned.  While no ghost is close, Pac-Man
    commits to a goal dot so it never dithers between equal options.
    """

    MARGIN = 0.16      # seconds of safety
    DECAY = 0.88       # value falloff per tile

    def __init__(self, game):
        self.game = game
        self.reset()

    def reset(self):
        self.goal = None
        self.debug_safe = set()      # tiles Pac-Man could safely reach (for 'D' view)
        self.debug_target = None

    # ---- helpers -----------------------------------------------------------
    def _threats(self):
        """Ghosts that could hurt Pac-Man, as ([(dist_map, offset)...], speed)."""
        game, m = self.game, self.game.maze
        threats = []
        for g in game.ghosts:
            if g.state == "eaten":
                continue
            if g.state == "wait":
                if g.wait_t > 1.2:
                    continue
                srcs = [(m.dist_map(g.tile), 0.0)]
            else:
                if g.fright_t > 1.2:          # harmless (for now)
                    continue
                if g.moving:                  # could be at either end of its edge
                    srcs = [(m.dist_map(g.nxt), 1 - g.p), (m.dist_map(g.tile), g.p)]
                else:
                    srcs = [(m.dist_map(g.tile), 0.0)]
            threats.append((srcs, game.g_speed * 1.03))
        return threats

    def _dot_distance_map(self):
        m = self.game.maze
        dist, q = {}, deque()
        for t in self.game.dots:
            dist[t] = 0
            q.append(t)
        while q:
            t = q.popleft()
            for nb, _ in m.adj[t]:
                if nb not in dist:
                    dist[nb] = dist[t] + 1
                    q.append(nb)
        return dist

    # ---- main entry point --------------------------------------------------
    def plan(self):
        """Return the direction Pac-Man should take next (or None)."""
        game = self.game
        m, pac = game.maze, game.pac
        speed = pac.speed
        threats = self._threats()

        def slack(tile, d):
            """Seconds by which Pac-Man beats the fastest ghost to `tile`."""
            pt = d / speed
            s = 99.0
            for srcs, gs in threats:
                gt = min(dm[tile] + off for dm, off in srcs) / gs
                if gt - pt < s:
                    s = gt - pt
            return s

        rev = (-pac.dir[0], -pac.dir[1])
        if not pac.moving:
            entries = [(1.0, nb, d) for nb, d in m.adj[pac.tile]]
        else:
            entries = [(1.0 - pac.p, pac.nxt, pac.dir), (pac.p, pac.tile, rev)]
        if not entries:
            return None

        # --- time-aware safe search -----------------------------------------
        heap = list(entries)
        heapq.heapify(heap)
        best, bad = {}, set()
        if any(g.state == "wait" for g in game.ghosts):
            bad.add(m.home)                        # ghost(s) sitting at home
        while heap:
            d, tile, key = heapq.heappop(heap)
            if tile in best or tile in bad:
                continue
            if threats and slack(tile, d) < self.MARGIN:
                bad.add(tile)
                continue
            best[tile] = (d, key)
            for nb, _ in m.adj[tile]:
                if nb not in best and nb not in bad:
                    heapq.heappush(heap, (d + 1, nb, key))
        self.debug_safe = set(best)
        safe_keys = {k for _, k in best.values()}

        # --- nothing is safe: flee to where the ghosts are farthest ---------
        if not safe_keys:
            bk, bv = None, -1e9
            for d, tile, key in entries:
                md = 0
                if threats:
                    md = min(min(dm[tile] + off for dm, off in srcs) for srcs, _ in threats)
                sc = md + 0.1 * len(m.adj[tile]) + game.rng.random() * 1e-3
                if key == rev:
                    sc -= 0.3
                if sc > bv:
                    bk, bv = key, sc
            return bk

        # --- between tiles: keep going unless forced to turn around ---------
        if pac.moving:
            if pac.dir in safe_keys:
                return pac.dir
            if rev in safe_keys:
                return rev

        # --- is any ghost close? ---------------------------------------------
        near = any(min(dm[pac.tile] + off for dm, off in srcs) <= 7
                   for srcs, _ in threats)

        # commitment: while safe, keep heading for the chosen goal
        goal = self.goal
        if (not near and goal is not None and goal in best
                and goal in game.dots and goal != pac.tile):
            self.debug_target = goal
            return best[goal][1]
        self.goal = None

        # --- score every first move -------------------------------------------
        scores, tgt = {}, {}

        def add(key, val, tile):
            scores[key] = scores.get(key, 0.0) + val
            if val > tgt.get(key, (0, None))[0]:
                tgt[key] = (val, tile)

        for tile, (d, key) in best.items():
            k = game.dots.get(tile)
            if k == 1:
                add(key, self.DECAY ** d, tile)
            elif k == 2:                          # save power pellets for danger
                add(key, (5.0 if near else 0.4) * self.DECAY ** d, tile)
        for g in game.ghosts:                     # hunt frightened ghosts in time
            if g.state == "active" and g.fright_t > 0:
                gt = g.nxt if g.moving else g.tile
                if gt in best:
                    d, key = best[gt]
                    if d / speed < g.fright_t - 0.4:
                        add(key, 12.0 * self.DECAY ** d, gt)

        if scores and max(scores.values()) > 1e-12:
            key = max(scores, key=lambda k: scores[k] * (0.9 if k == rev else 1.0)
                      + game.rng.random() * 1e-9)
            self.debug_target = tgt[key][1]
            if self.debug_target in game.dots:
                self.goal = self.debug_target
            return key

        # no dot reachable safely: creep towards the nearest dot through safe tiles
        dd = self._dot_distance_map()
        tile = min(best, key=lambda t: dd.get(t, 999) - 0.5 * min(slack(t, best[t][0]), 3.0)
                   if threats else dd.get(t, 999))
        self.debug_target = tile
        if tile in game.dots:
            self.goal = tile
        return best[tile][1]
