"""Random maze generation and the graph / distance queries built on top of it."""

from collections import deque

from .settings import DIR_LIST, norm_dims


class Maze:
    """Random, left/right-symmetric maze with loops and wrap-around tunnels.

    grid[y][x] == 1 is a wall, 0 is open floor.  After construction the maze
    also exposes:
        open        list of every open tile
        adj[tile]   [(neighbour_tile, direction), ...]
        step[tile]  {direction: neighbour_tile}
        home        the ghost home tile (centre of the map)
        pac_start   Pac-Man's start tile (bottom centre)
        corners     [TR, TL, BL, BR] open tiles used as scatter targets
    """

    def __init__(self, cols, rows, rng):
        self.cols, self.rows = norm_dims(cols, rows)
        self.rng = rng
        self.grid = [[1] * self.cols for _ in range(self.rows)]
        self.tunnels = []
        self._dcache = {}
        self._ncache = {}
        self._generate()
        self._build_graph()

    # ---- generation ------------------------------------------------------
    def _generate(self):
        C, R, g, rng = self.cols, self.rows, self.grid, self.rng
        cx = (C - 1) // 2                      # centre column (odd)

        # 1) recursive backtracker on the left half (including centre column)
        start = (1, 1)
        g[1][1] = 0
        visited = {start}
        stack = [start]
        while stack:
            x, y = stack[-1]
            cand = []
            for dx, dy in DIR_LIST:
                nx, ny = x + 2 * dx, y + 2 * dy
                if 1 <= nx <= cx and 1 <= ny <= R - 2 and (nx, ny) not in visited:
                    cand.append((dx, dy, nx, ny))
            if cand:
                dx, dy, nx, ny = rng.choice(cand)
                g[y + dy][x + dx] = 0
                g[ny][nx] = 0
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()

        # 2) mirror to the right half
        for y in range(R):
            for x in range(cx + 1):
                g[y][C - 1 - x] = g[y][x]

        def open_pair(x, y):
            g[y][x] = 0
            g[y][C - 1 - x] = 0

        # 3) braid: knock through walls at dead ends so there are loops
        for y in range(1, R - 1, 2):
            for x in range(1, C - 1, 2):
                if g[y][x] == 0 and self._open_count(x, y) == 1 and rng.random() < 0.85:
                    walls = [(x + dx, y + dy) for dx, dy in DIR_LIST
                             if 1 <= x + 2 * dx <= C - 2 and 1 <= y + 2 * dy <= R - 2
                             and g[y + dy][x + dx] == 1]
                    if walls:
                        open_pair(*rng.choice(walls))

        # 4) a few extra random openings
        for y in range(1, R - 1):
            for x in range(1, cx + 1):
                if (x % 2) != (y % 2) and g[y][x] == 1 and rng.random() < 0.07:
                    open_pair(x, y)

        # 5) central hub (ghost home)
        self.home_y = R // 2
        if self.home_y % 2 == 0:
            self.home_y -= 1
        self.home = (cx, self.home_y)
        g[self.home_y][cx - 1] = 0
        g[self.home_y][cx + 1] = 0

        # 6) wrap-around tunnels
        rows_avail = list(range(3, R - 3, 2))
        rng.shuffle(rows_avail)
        for y in rows_avail[:rng.choice([1, 2])]:
            g[y][0] = 0
            g[y][C - 1] = 0
            self.tunnels.append(y)

        self.pac_start = (cx, R - 2)

    def _open_count(self, x, y):
        return sum(1 for dx, dy in DIR_LIST if self.grid[y + dy][x + dx] == 0)

    def _build_graph(self):
        C, R, g = self.cols, self.rows, self.grid
        self.open = [(x, y) for y in range(R) for x in range(C) if g[y][x] == 0]
        self.adj, self.step = {}, {}
        for (x, y) in self.open:
            lst, st = [], {}
            for d in DIR_LIST:
                nx, ny = (x + d[0]) % C, y + d[1]      # x wraps through tunnels
                if 0 <= ny < R and g[ny][nx] == 0:
                    lst.append(((nx, ny), d))
                    st[d] = (nx, ny)
            self.adj[(x, y)] = lst
            self.step[(x, y)] = st
        self.corners = [self.nearest_open(C - 2, 1), self.nearest_open(1, 1),
                        self.nearest_open(1, R - 2), self.nearest_open(C - 2, R - 2)]

    # ---- queries ---------------------------------------------------------
    def is_isolated_wall(self, x, y):
        """True for a lone wall tile with no wall neighbours (a pillar)."""
        for dx, dy in DIR_LIST:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.cols and 0 <= ny < self.rows and self.grid[ny][nx] == 1:
                return False
        return True

    def nearest_open(self, x, y):
        key = (x, y)
        r = self._ncache.get(key)
        if r is None:
            r = min(self.open, key=lambda t: (t[0] - x) ** 2 + (t[1] - y) ** 2)
            self._ncache[key] = r
        return r

    def dist_map(self, src):
        """BFS distance (in tiles) from src to every open tile (cached)."""
        m = self._dcache.get(src)
        if m is None:
            m = {src: 0}
            q = deque([src])
            while q:
                t = q.popleft()
                d = m[t] + 1
                for nb, _ in self.adj[t]:
                    if nb not in m:
                        m[nb] = d
                        q.append(nb)
            self._dcache[src] = m
        return m
