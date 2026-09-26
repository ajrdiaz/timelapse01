from engine.stages.base import SfxEvent, Stage, register


@register
class Pregunta(Stage):
    tipo = "pregunta"

    def sfx_events(self, t0, t1):
        if not self.e.sfx:
            return []
        return [SfxEvent(t0, "whoosh", 0.8), SfxEvent(t0 + (t1 - t0) * 0.5, "whoosh", 0.6)]
