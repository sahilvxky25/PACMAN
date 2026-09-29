"""Everything that draws: maze walls, dots, actors, HUD and banners."""

import math

import pygame

from .settings import (BLACK, DOT_COL, FRIGHT_BLUE, HUD_BOTTOM, HUD_TOP,
                       LEFT, RED, WALL_BLUE, WHITE, YELLOW)


class Renderer:
    def __init__(self, game):
        self.game = game
        self.tile = game.tile
        w = game.cols * self.tile
        h = game.rows * self.tile + HUD_TOP + HUD_BOTTOM
        self.screen = pygame.display.set_mode((w, h))
        t = self.tile
        self.font = pygame.font.Font(None, int(t * 1.35))
        self.font_big = pygame.font.Font(None, int(t * 2.0))
        self.font_small = pygame.font.Font(None, max(14, int(t * 0.85)))
        self.wall_surf = self.wall_flash = None

    # ---- static maze -------------------------------------------------------
    def build_walls(self, maze):
        """Pre-render the maze once per level (normal + white 'level clear' flash)."""
        self.wall_surf = self._render_walls(maze, WALL_BLUE)
        self.wall_flash = self._render_walls(maze, WHITE)

    def _render_walls(self, maze, color):
        t = self.tile
        surf = pygame.Surface((maze.cols * t, maze.rows * t))
        surf.fill(BLACK)
        g = maze.grid
        outer = int(t * 0.62)
        inner = max(1, int(t * 0.30))

        def shapes(w, col):
            for y in range(maze.rows):
                for x in range(maze.cols):
                    if g[y][x] != 1:
                        continue
                    if col == BLACK and maze.is_isolated_wall(x, y):
                        continue              # keep lone pillars solid
                    cx, cy = x * t + t // 2, y * t + t // 2
                    pygame.draw.rect(surf, col, (cx - w // 2, cy - w // 2, w, w),
                                     border_radius=max(1, w // 3))
                    if x + 1 < maze.cols and g[y][x + 1] == 1:
                        pygame.draw.rect(surf, col, (cx - w // 2, cy - w // 2, t + w, w))
                    if y + 1 < maze.rows and g[y + 1][x] == 1:
                        pygame.draw.rect(surf, col, (cx - w // 2, cy - w // 2, w, t + w))

        shapes(outer, color)      # bright outline
        shapes(inner, BLACK)      # hollow it out -> neon tube look
        return surf

    # ---- coordinates ---------------------------------------------------------
    def to_px(self, x, y):
        t = self.tile
        return int((x + 0.5) * t), HUD_TOP + int((y + 0.5) * t)

    def _blit_wrapped(self, x, y, fn):
        """Draw at (x, y) and, near the tunnel edges, also on the other side."""
        cols = self.game.maze.cols
        x %= cols
        fn(*self.to_px(x, y))
        if x < 1:
            fn(*self.to_px(x + cols, y))
        elif x > cols - 2:
            fn(*self.to_px(x - cols, y))

    # ---- frame -----------------------------------------------------------------
    def draw(self):
        game, s, t = self.game, self.screen, self.tile
        s.fill(BLACK)
        flash = game.state == "clear" and int(game.time * 6) % 2 == 0
        s.blit(self.wall_flash if flash else self.wall_surf, (0, HUD_TOP))

        # AI debug view: safe reachable region
        if game.debug and game.state in ("play", "ready"):
            ov = pygame.Surface((t, t), pygame.SRCALPHA)
            ov.fill((0, 255, 120, 45))
            for (x, y) in game.ai.debug_safe:
                s.blit(ov, (x * t, HUD_TOP + y * t))

        # dots and power pellets
        blink = int(game.time * 4) % 2 == 0
        for (x, y), k in game.dots.items():
            cx, cy = self.to_px(x, y)
            if k == 1:
                pygame.draw.circle(s, DOT_COL, (cx, cy), max(2, int(t * 0.10)))
            elif blink or game.paused:
                pygame.draw.circle(s, DOT_COL, (cx, cy), int(t * 0.30))

        if game.debug and game.ai.debug_target and game.state == "play":
            cx, cy = self.to_px(*game.ai.debug_target)
            pygame.draw.circle(s, (255, 255, 0), (cx, cy), int(t * 0.45), 2)

        # ghosts
        for g in game.ghosts:
            gx, gy = g.pos()
            if g.state == "wait":
                gy += math.sin(game.time * 6 + g.idx) * 0.12
            self._blit_wrapped(gx, gy, lambda cx, cy, g=g: self.draw_ghost(g, cx, cy))
            if game.debug and g.state == "active" and g.fright_t <= 0 and game.state == "play":
                tx, ty = self.to_px(*game.ghost_brain.target(g))
                gcx, gcy = self.to_px(gx, gy)
                pygame.draw.line(s, g.color, (gcx, gcy), (tx, ty), 1)

        # Pac-Man
        pac = game.pac
        px, py = pac.pos()
        if game.state == "dying":
            prog = 1 - max(0.0, game.state_t) / 1.6
            self._blit_wrapped(px, py, lambda cx, cy: self.draw_pacman(
                cx, cy, -math.pi / 2, prog * math.pi))
        elif game.state != "over":
            d = pac.dir if pac.dir != (0, 0) else LEFT
            mouth = 0.05 + 0.75 * abs(math.sin(pac.anim))
            self._blit_wrapped(px, py, lambda cx, cy: self.draw_pacman(
                cx, cy, math.atan2(d[1], d[0]), mouth))

        # floating score popups
        for p in game.popups:
            img = self.font_small.render(p["text"], True, (0, 255, 255))
            s.blit(img, img.get_rect(center=(p["x"], p["y"] - int((0.9 - p["t"]) * 20))))

        self.draw_hud()
        self.draw_banner()

    # ---- sprites -----------------------------------------------------------------
    def draw_pacman(self, cx, cy, ang, mouth):
        r = int(self.tile * 0.46)
        if mouth <= 0.03:
            pygame.draw.circle(self.screen, YELLOW, (cx, cy), r)
            return
        if mouth >= math.pi - 0.02:
            return
        pts = [(cx, cy)]
        a0, a1 = ang + mouth, ang + 2 * math.pi - mouth
        for i in range(25):
            a = a0 + (a1 - a0) * i / 24
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(self.screen, YELLOW, pts)

    def draw_ghost(self, g, cx, cy):
        s, game = self.screen, self.game
        r = int(self.tile * 0.45)
        if g.state != "eaten":
            if g.fright_t > 0:
                flashing = g.fright_t < 2.0 and int(game.time * 6) % 2 == 0
                col = WHITE if flashing else FRIGHT_BLUE
            else:
                col = g.color
            pygame.draw.circle(s, col, (cx, cy - int(r * 0.2)), r)
            pygame.draw.rect(s, col, (cx - r, cy - int(r * 0.2), 2 * r, int(r * 0.8)))
            phase = int(game.time * 8) % 2
            n = 3
            pts = [(cx - r, cy), (cx + r, cy)]
            for i in range(2 * n + 1):
                x = cx + r - i * (r / n)
                y = cy + r if (i + phase) % 2 == 0 else cy + int(r * 0.68)
                pts.append((x, y))
            pygame.draw.polygon(s, col, pts)

        if g.state == "eaten" or g.fright_t <= 0:            # normal eyes
            d = g.dir if g.dir != (0, 0) else (0, 1)
            for sx in (-1, 1):
                ex, ey = cx + int(sx * r * 0.38), cy - int(r * 0.25)
                pygame.draw.circle(s, WHITE, (ex, ey), max(2, int(r * 0.32)))
                pygame.draw.circle(s, (20, 20, 200),
                                   (ex + int(d[0] * r * 0.14), ey + int(d[1] * r * 0.14)),
                                   max(1, int(r * 0.16)))
        else:                                                # scared face
            blink = g.fright_t < 2.0 and int(game.time * 6) % 2
            eye = (255, 200, 200) if blink else (255, 230, 170)
            for sx in (-1, 1):
                pygame.draw.circle(s, eye, (cx + int(sx * r * 0.35), cy - int(r * 0.2)), 2)
            zz = [(cx - r * 0.6 + i * r * 0.3, cy + r * (0.35 if i % 2 else 0.15))
                  for i in range(5)]
            pygame.draw.lines(s, eye, False, zz, 2)

    # ---- HUD / banners -------------------------------------------------------------
    def draw_hud(self):
        game, s, t = self.game, self.screen, self.tile
        w = game.cols * t
        s.blit(self.font.render(f"SCORE {game.score:06d}", True, WHITE), (8, 10))
        hi = self.font.render(f"HI {game.hi:06d}", True, (255, 200, 60))
        s.blit(hi, hi.get_rect(midtop=(w // 2, 10)))
        lv = self.font.render(f"LEVEL {game.level}", True, (120, 200, 255))
        s.blit(lv, lv.get_rect(topright=(w - 8, 10)))

        by = HUD_TOP + game.rows * t
        cy = by + HUD_BOTTOM // 2
        for i in range(max(0, game.lives)):                  # life icons
            self.draw_pacman(14 + i * (t + 2), cy, 0.0, 0.6)

        power = max([g.fright_t for g in game.ghosts if g.state == "active"] + [0.0])
        ptxt = f"  |  POWER {power:0.1f}s" if power > 0 else ""
        info = (f"{'AUTOPILOT' if game.autopilot else 'MANUAL'}{ptxt}  |  ghosts {game.n_ghosts}"
                f"  |  dots {len(game.dots)}  |  x{game.time_scale:g}  |  "
                f"{'CHASE' if game.chase else 'SCATTER'}")
        img = self.font_small.render(info, True, (255, 230, 90) if power > 0 else (170, 170, 200))
        info_rect = img.get_rect(midleft=(20 + max(0, game.lives) * (t + 2), cy))
        s.blit(img, info_rect)

        for txt in ("N maze  +/- ghosts  M mode  D debug  SPACE pause", "N  +/-  M  D  SPACE"):
            hint = self.font_small.render(txt, True, (110, 110, 140))
            hr = hint.get_rect(midright=(w - 8, cy))
            if hr.left > info_rect.right + 12:               # only if it fits
                s.blit(hint, hr)
                break

    def draw_banner(self):
        game = self.game
        text, col = None, YELLOW
        if game.paused:
            text = "PAUSED"
        elif game.state == "ready":
            text = f"LEVEL {game.level}  READY!"
        elif game.state == "over":
            text, col = "GAME OVER", RED
        if text:
            img = self.font_big.render(text, True, col)
            cx, cy = self.to_px(game.cols / 2 - 0.5, game.maze.home_y + 2)
            rect = img.get_rect(center=(cx, cy))
            pygame.draw.rect(self.screen, BLACK, rect.inflate(20, 10), border_radius=8)
            pygame.draw.rect(self.screen, col, rect.inflate(20, 10), 2, border_radius=8)
            self.screen.blit(img, rect)
