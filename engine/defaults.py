"""Etapas por defecto: reproducen el video de referencia de 62 s (búnker → cuarto gamer)."""
from __future__ import annotations

HOOK = 2.5

# tipo, título, subtítulo, duración, día ini, día fin, obreros, pose, máquina
DEFAULT_STAGES = [
    ("marcado", "DÍA 1: EL PLAN", "mi esposa cree que es un huerto", 2.5, 1, 1, 2, "apuntar", "ninguna"),
    ("excavacion", "EXCAVACIÓN", "4 metros de pura tierra", 7.0, 2, 9, 1, "pala", "excavadora"),
    ("grava_acero", "GRAVA Y ACERO", "la base de todo", 3.5, 10, 12, 2, "carretilla", "ninguna"),
    ("losa", "LOSA DE PISO", "concreto del bueno", 3.5, 13, 15, 2, "pala", "bomba_concreto"),
    ("muros", "MUROS", "encofrar, vaciar, desencofrar", 7.0, 16, 27, 2, "martillo", "bomba_concreto"),
    ("techo", "TECHO DE CONCRETO", "25 cm de concreto armado", 6.5, 28, 37, 2, "martillo", "bomba_concreto"),
    ("impermeabilizacion", "IMPERMEABILIZANTE", "ni una gota va a entrar", 3.0, 38, 41, 2, "pala", "ninguna"),
    ("relleno", "RELLENO", "a esconder la evidencia", 4.5, 42, 48, 2, "carretilla", "excavadora"),
    ("acabados", "ACABADOS", "pasto nuevo, nadie sospecha", 4.0, 49, 58, 2, "cargar", "ninguna"),
    ("terminado", "TERMINADO", "parece un patio normal…", 2.5, 60, 60, 2, "celebrar", "ninguna"),
    ("pregunta", "", "", 4.0, 60, 60, 0, "parado", "ninguna"),
    ("revelacion", "", "", 8.5, 60, 60, 0, "parado", "ninguna"),
    ("cierre", "", "", 3.0, 60, 60, 0, "parado", "ninguna"),
]


def default_stages():
    from engine.schema import Etapa

    out = []
    t = HOOK
    for tipo, tit, sub, dur, d0, d1, n, pose, maq in DEFAULT_STAGES:
        out.append(Etapa(tipo=tipo, titulo=tit, subtitulo=sub, inicio_seg=round(t, 3), duracion_seg=dur,
                         dia_inicio=d0, dia_fin=d1, obreros=n, pose=pose, maquina=maq, sfx=True))
        t += dur
    return out
