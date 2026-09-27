"""Catálogo de lo que el motor sabe dibujar. Se usa en validación y en los prompts del LLM."""

STAGE_TYPES: dict[str, str] = {
    "marcado": "Marcado del terreno: estacas e hilo/cal delimitan el área sobre el pasto.",
    "excavacion": "Excavación del pozo con excavadora; la tierra se apila a un lado.",
    "grava_acero": "Cama de grava en el fondo y parrilla de varillas de acero.",
    "losa": "Vaciado de la losa de piso de concreto (bomba de concreto).",
    "muros": "Muros: encofrado de madera → vaciado de concreto → desencofrado.",
    "techo": "Techo: puntales → acero → vaciado → ducto de escotilla.",
    "impermeabilizacion": "Pintura impermeabilizante negra sobre el exterior del búnker.",
    "relleno": "Relleno: la tierra apilada vuelve a cubrir el búnker.",
    "acabados": "Acabados: pasto en rollos, tubo de ventilación y escotilla.",
    "terminado": "Patio terminado: nadie sospecha lo que hay debajo.",
    "pregunta": "La cámara se acerca y pregunta '¿Y POR DENTRO?' con la falsa expectativa.",
    "revelacion": "Flash y revelación del interior (cuarto gamer, cine, etc.) con callouts.",
    "cierre": "Cierre con texto final y CTA.",
}

# Orden lógico recomendado (el motor tolera otros órdenes, pero se ve mejor así).
STAGE_ORDER = list(STAGE_TYPES.keys())

POSES: dict[str, str] = {
    "parado": "de pie, mirando",
    "pala": "palear",
    "martillo": "martillar",
    "carretilla": "empujar carretilla",
    "cargar": "cargar tablones/varillas",
    "apuntar": "señalar / inspeccionar",
    "celebrar": "brazos arriba celebrando",
}

MACHINES: dict[str, str] = {
    "ninguna": "sin máquina",
    "excavadora": "excavadora (brazo con cinemática inversa)",
    "bomba_concreto": "manguera de bomba de concreto",
}

INTERIOR_TYPES: dict[str, str] = {
    "gamer": "cuarto gamer: escritorio, 3 monitores, silla gamer, LEDs, pósters, mini-refri",
    "cine": "cine en casa: pantalla gigante, proyector, sillones reclinables, palomitas",
    "gimnasio": "gimnasio: rack de sentadillas, mancuernas, caminadora, espejo",
    "spa": "spa: jacuzzi, sauna de madera, plantas, velas",
    "bodega_snacks": "bodega de snacks: estantes llenos, máquina expendedora, refri de bebidas",
    "streaming": "estudio de streaming: micrófono, cámara, ring light, panel acústico, pantalla verde",
    "oficina": "oficina: escritorio de madera, librero, lámpara, planta, pizarra",
}

# Progresiones de acordes de la música generada. Todas en tono menor para conservar el carácter del canal.
PROGRESSIONS: dict[str, list[str]] = {
    "A menor: Am-F-C-G": ["Am", "F", "C", "G"],
    "E menor: Em-C-G-D": ["Em", "C", "G", "D"],
    "D menor: Dm-Bb-F-C": ["Dm", "Bb", "F", "C"],
    "A menor: Am-Dm-G-C": ["Am", "Dm", "G", "C"],
    "B menor: Bm-G-D-A": ["Bm", "G", "D", "A"],
    "C menor: Cm-Ab-Eb-Bb": ["Cm", "Ab", "Eb", "Bb"],
    "G menor: Gm-Eb-Bb-F": ["Gm", "Eb", "Bb", "F"],
    "F# menor: F#m-D-A-E": ["F#m", "D", "A", "E"],
    "E menor: Em-G-D-C": ["Em", "G", "D", "C"],
}

VISUAL_STYLES = ["corte_lateral"]

TONES = ["divertido", "serio", "misterioso"]


def catalog_text() -> str:
    """Texto compacto para incluir en prompts de sistema."""
    from engine.interiors import INTERIORS

    lines = ["TIPOS DE ETAPA (campo etapas[].tipo):"]
    lines += [f"- {k}: {v}" for k, v in STAGE_TYPES.items()]
    lines.append("POSES de obreros: " + ", ".join(POSES))
    lines.append("MÁQUINAS: " + ", ".join(MACHINES))
    lines.append("TIPOS DE INTERIOR (revelacion.tipo_interior) y sus objetos para callouts:")
    for k, v in INTERIOR_TYPES.items():
        objs = ", ".join(INTERIORS[k].OBJECTS.keys())
        lines.append(f"- {k}: {v}. objetos: {objs}")
    lines.append("ESTILOS VISUALES: " + ", ".join(VISUAL_STYLES))
    return "\n".join(lines)
