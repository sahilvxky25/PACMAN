"""Game state, rules, input handling and the main loop."""

import math
import random

import pygame

from .entities import Ghost, Pacman
from .ghost_ai import GhostBrain
from .maze import Maze
from .pacman_ai import AutoPilot
from .renderer import Renderer
from .settings import (DOWN, EATEN_SPEED, FRIGHT_SPEED, LEFT, MAX_GHOSTS, MODE_SCHEDULE,
                       RIGHT, UP, norm_dims)


class Game:
    def __init__(self, args):
        self.args = args
        pygame.init()
        pygame.display.set_caption("Autonomous Pac-Man")

        self.tile = args.tile
        self.cols, self.rows = norm_dims(args.cols, args.rows)
        self.rng = random.Random(args.seed)
        self.n_ghosts = max(0, min(MAX_GHOSTS, args.ghosts))

        self.autopilot = not args.manual
        self.debug = False
        self.paused = False
        self.running = True
        self.time = 0.0
        self.time_scale = 1.0
        self.hi = 0
        self.stats = dict(deaths=0, levels=0, ghosts_eaten=0, games=0, best=0)

        # collaborators
        self.renderer = Renderer(self)
        self.ai = AutoPilot(self)              # Pac-Man's brain
        self.ghost_brain = GhostBrain(self)    # the ghosts' brain

        self.new_game()

    # ---- setup -----------------------------------------------------------
    def new_game(self):
        self.score = 0
        self.lives = self.args.lives
        self.level = 1
        self.extra_life_given = False
        self.stats["games"] += 1
        self.start_level(new_maze=True)

    @property
    def g_speed(self):
        """Ghost speed grows with the level."""
        return min(7.0, 5.3 + 0.25 * (self.level - 1))

    @property
    def fright_duration(self):
        return max(2.5, 7.0 - 0.6 * (self.level - 1))

    def start_level(self, new_maze=True):
        if new_maze:
            self.maze = Maze(self.cols, self.rows, self.rng)
            self.renderer.build_walls(self.maze)
            m = self.maze
            self.dots = {t: 1 for t in m.open if t not in (m.pac_start, m.home)}
            if not self.args.no_power:
                for c in m.corners:
                    if c in self.dots:
                        self.dots[c] = 2       # power pellet
        self.reset_actors()

    def reset_actors(self):
        m = self.maze
        self.pac = Pacman(m, m.pac_start)
        self.ghosts = [Ghost(m, i, self.g_speed, 0.6 + i * 2.0)
                       for i in range(self.n_ghosts)]
        self.mode_idx, self.mode_t = 0, 0.0
        self.chase = MODE_SCHEDULE[0][1]
        self.state, self.state_t = "ready", 2.0    # ready | play | dying | clear | over
        self.popups = []
        self.eat_chain = 0
        self.ai_cd = 0.0
        self.ai.reset()

    def set_ghosts(self, n):
        n = max(0, min(MAX_GHOSTS, n))
        if n != self.n_ghosts:
            self.n_ghosts = n
            self.reset_actors()

    # ---- Pac-Man control callbacks -------------------------------------------
    def pac_choose(self, pac):
        if self.autopilot:
            return self.ai.plan()
        st = self.maze.step[pac.tile]
        if pac.want in st:
            return pac.want
        if pac.dir in st:
            return pac.dir
        return None

    def pac_arrive(self, pac):
        k = self.dots.pop(pac.tile, None)
        if k == 1:
            self.add_score(10)
        elif k == 2:                               # power pellet
            self.add_score(50)
            self.eat_chain = 0
            dur = self.fright_duration
            for g in self.ghosts:
                if g.state == "active":
                    g.fright_t = dur
                    g.want_reverse = True

    def add_score(self, n):
        self.score += n
        self.hi = max(self.hi, self.score)
        if not self.extra_life_given and self.score >= 10000:
            self.extra_life_given = True
            self.lives += 1

    # ---- update ------------------------------------------------------------------
    def update(self, dt):
        if self.paused:
            return
        self.time += dt
        for p in self.popups:
            p["t"] -= dt
        self.popups = [p for p in self.popups if p["t"] > 0]

        if self.state == "ready":
            self.state_t -= dt
            if self.state_t <= 0:
                self.state = "play"
        elif self.state == "play":
            self._update_play(dt)
        elif self.state == "dying":
            self.state_t -= dt
            if self.state_t <= 0:
                if self.lives > 0:
                    self.reset_actors()
                else:
                    self.state, self.state_t = "over", 4.0
                    self.stats["best"] = max(self.stats["best"], self.score)
        elif self.state == "clear":
            self.state_t -= dt
            if self.state_t <= 0:
                self.level += 1
                self.stats["levels"] += 1
                self.start_level(new_maze=True)
        elif self.state == "over":
            self.state_t -= dt
            if self.state_t <= 0:
                self.new_game()

    def _update_play(self, dt):
        pac = self.pac

        # scatter / chase timer
        self.mode_t += dt
        dur, is_chase = MODE_SCHEDULE[self.mode_idx]
        scale = 1.0 if is_chase else max(0.4, 1.0 - 0.1 * (self.level - 1))
        if self.mode_t >= dur * scale and self.mode_idx < len(MODE_SCHEDULE) - 1:
            self.mode_idx += 1
            self.mode_t = 0.0
            self.chase = MODE_SCHEDULE[self.mode_idx][1]
            for g in self.ghosts:
                if g.state == "active" and g.fright_t <= 0:
                    g.want_reverse = True

        # emergency re-plan while between tiles (autopilot only)
        self.ai_cd -= dt
        if self.autopilot and pac.moving and self.ai_cd <= 0:
            px, py = pac.pos()
            for g in self.ghosts:
                if g.state != "active" or g.fright_t > 0:
                    continue
                gx, gy = g.pos()
                if (px - gx) ** 2 + (py - gy) ** 2 < 16:
                    self.ai_cd = 0.06
                    key = self.ai.plan()
                    if key is not None and key == (-pac.dir[0], -pac.dir[1]):
                        pac.reverse()
                    break

        # move Pac-Man
        pac.advance(dt, self.pac_choose, self.pac_arrive)
        if pac.moving:
            pac.anim += dt * 14

        # move ghosts
        for g in self.ghosts:
            if g.state == "wait":
                g.wait_t -= dt
                if g.wait_t <= 0:
                    g.state = "active"
                    g.want_reverse = False
                continue
            if g.fright_t > 0:
                g.fright_t = max(0.0, g.fright_t - dt)
            if g.state == "eaten":
                g.speed = EATEN_SPEED
            elif g.fright_t > 0:
                g.speed = FRIGHT_SPEED
            else:
                g.speed = self.g_speed
            g.advance(dt, self.ghost_brain.choose, self.ghost_brain.arrive)

        self._check_collisions()
        if self.state == "play" and not self.dots:
            self.state, self.state_t = "clear", 2.0

    def _check_collisions(self):
        cols = self.maze.cols
        px, py = self.pac.pos()
        px %= cols
        for g in self.ghosts:
            if g.state not in ("active", "wait"):      # waiting ghosts are solid too
                continue
            gx, gy = g.pos()
            gx %= cols
            dx = abs(px - gx)
            dx = min(dx, cols - dx)                     # shortest way round the tunnel
            dy = abs(py - gy)
            if dx * dx + dy * dy < 0.30:
                if g.fright_t > 0:                      # eat a frightened ghost
                    g.state, g.fright_t = "eaten", 0.0
                    self.eat_chain += 1
                    pts = 200 * 2 ** min(self.eat_chain - 1, 3)
                    self.add_score(pts)
                    self.stats["ghosts_eaten"] += 1
                    x, y = self.renderer.to_px(px, py)
                    self.popups.append(dict(text=str(pts), x=x, y=y, t=0.9))
                else:                                   # caught!
                    self.lives -= 1
                    self.stats["deaths"] += 1
                    self.state, self.state_t = "dying", 1.6
                    return

    # ---- input -------------------------------------------------------------------
    def handle_key(self, k):
        if k in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif k in (pygame.K_SPACE, pygame.K_p):
            self.paused = not self.paused
        elif k == pygame.K_n:
            self.start_level(new_maze=True)
        elif k == pygame.K_r:
            self.new_game()
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.set_ghosts(self.n_ghosts + 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.set_ghosts(self.n_ghosts - 1)
        elif k in (pygame.K_m, pygame.K_a):
            self.autopilot = not self.autopilot
            self.pac.want = None
        elif k == pygame.K_d:
            self.debug = not self.debug
        elif k == pygame.K_RIGHTBRACKET:
            self.time_scale = min(8.0, self.time_scale * 2)
        elif k == pygame.K_LEFTBRACKET:
            self.time_scale = max(0.25, self.time_scale / 2)
        elif not self.autopilot:
            keymap = {pygame.K_UP: UP, pygame.K_DOWN: DOWN,
                      pygame.K_LEFT: LEFT, pygame.K_RIGHT: RIGHT}
            if k in keymap:
                d = keymap[k]
                self.pac.want = d
                if self.pac.moving and d == (-self.pac.dir[0], -self.pac.dir[1]):
                    self.pac.reverse()

    # ---- main loop -----------------------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()
        frames = 0
        turbo = self.args.turbo
        while self.running:
            ms = clock.tick(0 if turbo else self.args.fps)
            dt = 1 / 60 if turbo else min(ms / 1000.0, 0.05)

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN:
                    self.handle_key(e.key)

            sim = dt * (1.0 if turbo else self.time_scale)
            steps = max(1, int(math.ceil(sim / (1 / 60))))     # keep steps small
            for _ in range(steps):
                self.update(sim / steps)

            if not turbo or frames % 30 == 0:
                self.renderer.draw()
                pygame.display.flip()

            frames += 1
            if self.args.frames and frames >= self.args.frames:
                break

        self.print_summary()
        pygame.quit()

    def print_summary(self):
        st = self.stats
        best = max(st["best"], self.score)
        print(f"\n--- session summary ---\n"
              f"ghosts: {self.n_ghosts}  level reached: {self.level}  score: {self.score}  "
              f"best: {best}\nlevels cleared: {st['levels']}  deaths: {st['deaths']}  "
              f"ghosts eaten: {st['ghosts_eaten']}  games: {st['games']}")
