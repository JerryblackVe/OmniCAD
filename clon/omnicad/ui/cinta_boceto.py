# -*- coding: utf-8 -*-
"""
Grupos de la pestaña contextual BOCETO de la cinta (CREAR, MODIFICAR, RESTRICCIONES), con el orden
de los menús de Fusion. `cinta.py` les agrega los grupos compartidos y TERMINAR BOCETO.
Un ítem sin clave de acción queda grisado (no implementado). Todas las claves `sk_*` son acciones
que crea `modo_boceto.ModoBoceto` (con los atajos de Fusion).
"""
from .cinta_items import SEP, _i, _sub

# Pestaña contextual del entorno de boceto (capturas de Fusion: CREAR, MODIFICAR, RESTRICCIONES…).
_RESTR = ["r_horizontal_vertical", "r_coincidente", "r_tangente", "r_igual", "r_paralela", "r_perpendicular",
          "r_fijo", "r_punto_medio", "r_concentrica", "r_colineal", "r_simetria", "r_curvatura", "r_poligono"]
GRUPOS_BOCETO = [
    # íconos fijos como en el video de Fusion 2026: Línea, Círculo, Rectángulo, Spline, Simetría y Cota
    ("CREAR", ["sk_linea", "sk_circulo", "sk_rectangulo", "sk_spline_ajuste", "sk_simetria", "sk_cota"], [
        _i("Línea", "sk_linea"), _i("Línea de punto medio", "sk_linea_medio"),
        _sub("Rectángulo", [_i("", "sk_rectangulo"), _i("", "sk_rectangulo_3p"), _i("", "sk_rectangulo_centro")]),
        _sub("Círculo", [_i("", "sk_circulo"), _i("", "sk_circulo_2p"), _i("", "sk_circulo_3p"),
                         _i("", "sk_circulo_2t"), _i("", "sk_circulo_3t")]),
        _sub("Arco", [_i("", "sk_arco"), _i("", "sk_arco_centro"), _i("", "sk_arco_tangente")]),
        _sub("Polígono", [_i("", "sk_poligono_circunscrito"), _i("", "sk_poligono_inscrito"),
                          _i("", "sk_poligono_arista")]),
        _i("Elipse", "sk_elipse"),
        _sub("Ranura", [_i("", "sk_ranura_centro"), _i("", "sk_ranura_total"), _i("", "sk_ranura_punto"),
                        _i("", "sk_ranura_arco_3p"), _i("", "sk_ranura_arco_centro")]),
        _sub("Spline", [_i("", "sk_spline_ajuste"), _i("", "sk_spline_control")]),
        _i("Curva cónica", "sk_conica"), _i("Punto", "sk_punto"),
        _sub("Texto", [_i("", "sk_texto"), _i("", "sk_desglosar_texto")]), SEP,
        _i("Simetría", "sk_simetria"), _i("Patrón circular", "sk_patron_circular"),
        _i("Patrón rectangular", "sk_patron_rectangular"), SEP,
        _sub("Proyectar/Incluir", [_i("", "sk_proyectar"), _i("", "sk_intersecar"), _i("", "sk_incluir_3d")]), SEP,
        _i("Cota de boceto", "sk_cota"), SEP, _i("Helix / Spiral", "sk_espiral")]),
    ("MODIFICAR", ["sk_empalme", "sk_recortar", "sk_desfase", "sk_curva_fusion"], [
        _i("Empalme", "sk_empalme"),
        _sub("Chaflán", [_i("", "sk_chaflan"), _i("", "sk_chaflan_dist_angulo"), _i("", "sk_chaflan_dos_dist")]),
        _i("Curva de fusión", "sk_curva_fusion"), _i("Desfase", "sk_desfase"), SEP,
        _i("Recortar", "sk_recortar"), _i("Alargar", "sk_alargar"),
        _i("Partir", "sk_partir"), _i("Escala del boceto", "sk_escala"),
        _i("Mover/copiar", "sk_mover"), SEP,
        _i("Cambiar parámetros", "parametros")]),
    ("RESTRICCIONES", [f"sk_{r}" for r in _RESTR],
     [_i("", f"sk_{r}") for r in _RESTR] + [SEP, _i("", "sk_autorestringir")]),
]
