from engine.interiors import INTERIORS
from engine.stages.base import SfxEvent, Stage, register


@register
class Revelacion(Stage):
    tipo = "revelacion"
    live = True  # el interior está animado (LEDs), no se cachea

    def flash_time(self, scene):
        return self.e.inicio_seg + scene.revelacion.flash_offset_seg

    def apply_state(self, st, t):
        pass

    def draw(self, canvas, t, ctx):
        if ctx.t + 1e-6 < self.flash_time(ctx.scene):
            return
        INTERIORS[ctx.scene.revelacion.tipo_interior].draw(canvas, ctx, ctx.t - self.flash_time(ctx.scene))

    def sfx_events(self, t0, t1):
        return []  # el flash y los callouts los sonoriza engine.audio a partir de la escena
