# -*- coding: utf-8 -*-
"""B-176: export_sketch a SVG/DXF no da vuelta los arcos (planos XY, XZ, YZ y cara de abajo; arcos chicos, grandes,
de tres puntos en los dos sentidos y horarios). Pasaron sin cambiar el código: el bug no se reprodujo."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_activo
from omnicad.io_archivos import dxf as dxf_mod
from omnicad.io_archivos import svg as svg_mod


def _llamar(s, nombre, **kw):
    r = api.llamar(s, nombre, kw)
    assert r["ok"], r
    return r["result"]


def _crear_boceto(s, plane):
    if plane == "bottom":
        _llamar(s, "create_box", length=20, width=20, height=10)
        _llamar(s, "create_sketch", plane="<Z")
    else:
        _llamar(s, "create_sketch", plane=plane)


def _dibujar(s, kind, param):
    if kind == "center":
        _llamar(s, "draw_arc", center_x=0, center_y=0, start_x=10, start_y=0, sweep_angle=param)
    elif kind == "center5":
        _llamar(s, "draw_arc", center_x=0, center_y=0, start_x=5, start_y=0, sweep_angle=param)
    elif kind == "3pt_up":
        _llamar(s, "draw_arc", start_x=10, start_y=0, mid_x=0, mid_y=10, end_x=-10, end_y=0)
    elif kind == "3pt_down":
        _llamar(s, "draw_arc", start_x=10, start_y=0, mid_x=0, mid_y=-10, end_x=-10, end_y=0)
    elif kind == "obround":
        _llamar(s, "draw_line", start_x=-10, start_y=5, end_x=10, end_y=5)
        _llamar(s, "draw_arc", center_x=10, center_y=0, start_x=10, start_y=5, sweep_angle=-180)
        _llamar(s, "draw_line", start_x=10, start_y=-5, end_x=-10, end_y=-5)
        _llamar(s, "draw_arc", center_x=-10, center_y=0, start_x=-10, start_y=-5, sweep_angle=-180)


CASES = [
    ("xy_90", "XY", "center", 90),
    ("xy_270", "XY", "center", 270),
    ("xy_3pt_up", "XY", "3pt_up", 0),
    ("xy_3pt_down", "XY", "3pt_down", 0),
    ("xz_90", "XZ", "center", 90),
    ("yz_90", "YZ", "center", 90),
    ("bottom_90", "bottom", "center5", 90),
    ("bottom_270", "bottom", "center5", 270),
    ("bottom_3pt", "bottom", "3pt_up", 0),
    ("obround", "XY", "obround", 0),
]


def _bbox(prims):
    pts = []
    for p in prims:
        if p[0] == "arco":
            cx, cy = p[2]
            r = p[3]
            a0, a1 = p[4], p[5]
            sweep = (a1 - a0) % (2 * math.pi) or (2 * math.pi)
            pts += [(cx + r * math.cos(a0 + sweep * k / 24),
                     cy + r * math.sin(a0 + sweep * k / 24)) for k in range(25)]
        elif p[0] == "linea":
            pts += [p[2], p[3]]
    if not pts:
        return 0.0, 0.0
    return min(q[0] for q in pts), min(q[1] for q in pts)


def _orig_arc_mids(prims):
    mids = []
    for p in prims:
        if p[0] == "arco":
            cx, cy = p[2]
            r = p[3]
            a0, a1 = p[4], p[5]
            sweep = (a1 - a0) % (2 * math.pi) or (2 * math.pi)
            mids.append((cx + r * math.cos(a0 + sweep / 2),
                         cy + r * math.sin(a0 + sweep / 2)))
    return mids


def _svg_midpoints(prims):
    chains = []
    cur = []
    for p in prims:
        if p[0] == "bezier":
            cur.append(p[1])
        else:
            if cur:
                chains.append(cur)
                cur = []
    if cur:
        chains.append(cur)
    res = []
    for chain in chains:
        pts_chain = []
        for bz in chain:
            arr = np.asarray(bz, float)
            for i in range(11):
                t = i / 10.0
                pt = ((1 - t) ** 3 * arr[0] + 3 * (1 - t) ** 2 * t * arr[1]
                      + 3 * (1 - t) * t ** 2 * arr[2] + t ** 3 * arr[3])
                pt = (float(pt[0]), float(pt[1]))
                if not pts_chain or abs(pts_chain[-1][0] - pt[0]) > 1e-9 or abs(pts_chain[-1][1] - pt[1]) > 1e-9:
                    pts_chain.append(pt)
        if pts_chain:
            res.append(pts_chain[len(pts_chain) // 2])
    return res


def _dxf_midpoints(prims):
    mids = []
    for p in prims:
        if p[0] == "arco":
            cx, cy = p[1]
            r = p[2]
            a0, a1 = p[3], p[4]
            sweep = (a1 - a0) % (2 * math.pi) or (2 * math.pi)
            mids.append((cx + r * math.cos(a0 + sweep / 2),
                         cy + r * math.sin(a0 + sweep / 2)))
    return mids


@pytest.mark.parametrize("nombre,plane,kind,param", CASES)
def test_arcos_svg_y_dxf(nombre, plane, kind, param, tmp_path):
    s = api.Sesion()
    _crear_boceto(s, plane)
    _dibujar(s, kind, param)

    op, br = boceto_activo(s, None)
    orig_prims = br.boceto.geometria()
    orig_mids = _orig_arc_mids(orig_prims)
    minx, miny = _bbox(orig_prims)
    expected_svg = [(m[0] - minx, m[1] - miny) for m in orig_mids]

    # SVG
    svg_path = tmp_path / f"{nombre}.svg"
    _llamar(s, "export_sketch", path=str(svg_path))
    svg_prims = svg_mod.leer_svg(svg_path)
    svg_ms = _svg_midpoints(svg_prims)
    assert len(svg_ms) == len(expected_svg), (nombre, "svg count", len(svg_ms), len(expected_svg))
    for em in expected_svg:
        assert any(math.hypot(em[0] - sm[0], em[1] - sm[1]) <= 0.01 for sm in svg_ms), (nombre, "svg", em, svg_ms)

    # DXF
    dxf_path = tmp_path / f"{nombre}.dxf"
    _llamar(s, "export_sketch", path=str(dxf_path))
    dxf_prims = dxf_mod.leer_dxf(dxf_path)
    dxf_ms = _dxf_midpoints(dxf_prims)
    assert len(dxf_ms) == len(orig_mids), (nombre, "dxf count", len(dxf_ms), len(orig_mids))
    for em in orig_mids:
        assert any(math.hypot(em[0] - dm[0], em[1] - dm[1]) <= 0.01 for dm in dxf_ms), (nombre, "dxf", em, dxf_ms)
