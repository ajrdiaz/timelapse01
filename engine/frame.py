"""Composición de un fotograma a partir de la escena. Determinista: f(escena, t) → imagen."""
from __future__ import annotations

import math
from typing import Optional

from PIL import Image, ImageDraw

from engine.actors import draw_excavator, draw_hose, draw_worker
from engine.assets import Assets
from engine.camera import camera, crop_box, world_to_screen
from engine.grade import apply_flash, apply_night, apply_vignette, flash_amount, night_factor, sky_image
from engine.interiors import INTERIORS
from engine.stages import Ctx, WorldState, make_stage
from engine.ui import UI
from engine.world import Draw, hex_rgb, make_layout, paste_poly, paste_rect


class FrameRenderer:
    def __init__(self, scene, size: Optional[tuple[int, int]] = None, ss: int = 2, preview: bool = False,
                 fonts_dir: Optional[str] = None):
        self.scene = scene
        self.out_w, self.out_h = size or scene.general.size
        self.ss = ss
        self.preview = preview
        W, H = self.out_w * ss, self.out_h * ss
        self.L = make_layout(scene.escenario, W, H)
        self.A = Assets(self.L, scene)
        self.stages = [make_stage(e) for e in scene.etapas]
        self.ui = UI(scene, self.out_w, self.out_h, fonts_dir)
        self.draw_cache: dict = {}
        self._base: Optional[Image.Image] = None
        self._layer: tuple[int, Optional[Image.Image]] = (-99, None)
        p = scene.personajes
        self.colors = {"chaleco": hex_rgb(p.color_chaleco), "casco": hex_rgb(p.color_casco), "pantalon": hex_rgb(p.color_pantalon)}

    # capas --------------------------------------------------------------------
    def base_layer(self) -> Image.Image:
        if self._base is None:
            L = self.L
            img = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 0))
            img.alpha_composite(self.A.fondo)
            paste_rect(img, self.A.suelo, (0, L.ground_y, L.W, L.H))
            paste_rect(img, self.A.pasto, (0, L.ground_y - L.m(0.25), L.W, L.ground_y + L.m(0.18)))
            self._base = img
        return self._base

    def _ctx(self, canvas, i: int, t: float, current: bool, state: WorldState, night: float = 0.0) -> Ctx:
        return Ctx(L=self.L, A=self.A, scene=self.scene, etapa=self.scene.etapas[i], index=i, t=t, current=current,
                   state=state, draw=Draw(canvas), night=night, draw_cache=self.draw_cache)

    def completed_layer(self, idx: int) -> Image.Image:
        """Base + etapas [0, idx) terminadas (sin las 'live'). Se cachea por índice."""
        if self._layer[0] == idx and self._layer[1] is not None:
            return self._layer[1]
        img = self.base_layer().copy()
        st = WorldState()
        for i in range(max(0, idx)):
            s = self.stages[i]
            s.apply_state(st, 1.0)
            if not s.live:
                s.draw(img, 1.0, self._ctx(img, i, self.scene.etapas[i].fin_seg, False, st))
        self._layer = (idx, img)
        return img

    # mundo --------------------------------------------------------------------
    def world(self, t: float, night: float) -> tuple[Image.Image, WorldState]:
        idx, tl = self.scene.stage_at(t)
        st = WorldState()
        for i in range(max(0, idx)):
            self.stages[i].apply_state(st, 1.0)
        if idx >= 0:
            self.stages[idx].apply_state(st, tl)
        canvas = self.completed_layer(idx).copy()
        for i in range(max(0, idx)):
            if self.stages[i].live:
                self.stages[i].draw(canvas, 1.0, self._ctx(canvas, i, t, False, st, night))
        if idx < 0:
            return canvas, st
        stage = self.stages[idx]
        ctx = self._ctx(canvas, idx, t, True, st, night)
        stage.draw(canvas, tl, ctx)
        stage.draw_active(canvas, tl, ctx)
        self.draw_pile(canvas, st)
        self.draw_machines(canvas, stage, tl, ctx)
        hide = self.scene.personajes.ocultar_obreros_noche and night > 0.45
        if not hide and stage.e.obreros > 0:
            for k, (x, y, facing) in enumerate(stage.worker_spots(ctx, tl)):
                draw_worker(ctx.draw, x, y, self.L.ppm, stage.e.pose, t, facing, self.colors, k)
        return canvas, st

    def draw_pile(self, canvas, st: WorldState):
        if st.pile <= 0.01:
            return
        L = self.L
        m = L.m
        cx = L.pit_x1 + m(1.35)
        hw = m(0.8 + 0.7 * st.pile)
        h = m(1.9 * st.pile)
        pts = []
        for i in range(25):
            a = math.pi * i / 24
            bump = 1 + 0.05 * math.sin(i * 2.3)
            pts.append((cx - math.cos(a) * hw, L.ground_y + m(0.05) - math.sin(a) ** 0.8 * h * bump))
        paste_poly(canvas, self.A.relleno, pts)

    def draw_machines(self, canvas, stage, tl, ctx):
        e = stage.e
        L = self.L
        d = ctx.draw
        if e.maquina == "excavadora" and self.scene.personajes.excavadora.activa:
            ex = stage.excavator(ctx, tl)
            if ex:
                soil = self.A.cols[0]
                draw_excavator(d, ex["x"], ex["y"], L.ppm, hex_rgb(self.scene.personajes.excavadora.color), ex["target"],
                               -1, ex["curl"], ex["load"], soil, ctx.t)
        elif e.maquina == "bomba_concreto":
            pp = stage.pour_point(ctx, tl)
            start = (L.W + L.m(0.3), L.ground_y - L.m(4.0))
            if pp is None:
                draw_hose(d, start, (L.pit_x1 + L.m(0.4), L.ground_y - L.m(0.3)), L.ppm, ctx.t, False, sag=0.3)
            else:
                draw_hose(d, start, pp, L.ppm, ctx.t, 0 < tl < 1)

    # fotograma ------------------------------------------------------------------
    def render(self, t: float, preview: Optional[bool] = None) -> Image.Image:
        scene = self.scene
        L = self.L
        preview = self.preview if preview is None else preview
        night = night_factor(scene, t) * scene.escenario.dia_noche.intensidad
        world, st = self.world(t, night)
        box = crop_box(L, camera(scene, L, t))
        view = world.resize((self.out_w, self.out_h), Image.BILINEAR, box=box, reducing_gap=None)
        view = apply_night(view, night)
        frac = (box[0] / L.W, box[1] / L.H, box[2] / L.W, box[3] / L.H)
        sky = sky_image(self.A, scene, t, self.out_w, self.out_h, frac)
        sky.alpha_composite(view)
        img = apply_flash(apply_vignette(sky.convert("RGB"), scene.escenario.vineta), flash_amount(scene, t)).convert("RGBA")
        interior = INTERIORS[scene.revelacion.tipo_interior]
        anchors = []
        for c in scene.revelacion.callouts:
            if c.objeto in interior.OBJECTS:
                wx, wy = interior.anchor(c.objeto, self._ctx(world, 0, t, False, st))
                anchors.append(world_to_screen(box, self.out_w, self.out_h, wx, wy))
            else:
                anchors.append((self.out_w / 2, self.out_h / 2))
        rx0, ry0 = world_to_screen(box, self.out_w, self.out_h, L.ix0, L.roof_top_y)
        rx1, ry1 = world_to_screen(box, self.out_w, self.out_h, L.ix1, L.slab_bot_y)
        self.ui.draw(img, t, anchors, (rx0, ry0, rx1, ry1), preview=preview)
        return img.convert("RGB")
