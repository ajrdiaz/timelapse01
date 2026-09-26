from engine.stages.base import SfxEvent, Stage, register


@register
class Cierre(Stage):
    tipo = "cierre"

    def sfx_events(self, t0, t1):
        return [SfxEvent(t0, "whoosh", 0.6)] if self.e.sfx else []
