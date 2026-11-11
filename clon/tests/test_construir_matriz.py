# -*- coding: utf-8 -*-
"""Portón de AG-7 (docs/auditorias/porton_auditoria.md, punto 1): matriz de combinaciones de CONSTRUIR.

Cada plano, eje, punto y SCU se arma sobre una caja de alto paramétrico (también uno sobre el resultado de otro) y se
comprueba con números contra la geometría esperada en cada estado: recién creado, con la cota cambiada, deshacer,
rehacer y guardar y reabrir. Una referencia perdida no se reasigna callada (B-252): ese caso vive en
test_api_construccion.py."""
import copy

import numpy as np
import pytest

from omnicad import api

H0, H1 = 10.0, 25.0
R2 = 2 ** -0.5


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


# nombre → (herramienta, argumentos, qué es, esperado(h)): un plano es (punto suyo, normal); un eje, (punto, dirección)
CASOS = {
    "desfase": ("create_construction_plane", dict(plane=">Z", offset=5), "plano", lambda h: ((0, 0, h + 5), (0, 0, 1))),
    "angulo": ("create_construction_plane", dict(type="angle", references=["edges:>Z and >X"], angle=30), "plano",
               lambda h: ((20, 0, h), (0.5, 0, 3 ** 0.5 / 2))),
    # P-92: con arista vertical el 0° es el plano frontal, como en Fusion (medido 2026-11-08)
    "angulo_0_vertical": ("create_construction_plane", dict(type="angle", references=["edges:>X and >Y"], angle=0),
                          "plano", lambda h: ((20, 20, h / 2), (0, 1, 0))),
    "medio": ("create_construction_plane", dict(type="middle", references=[">Z", "<Z"]), "plano",
              lambda h: ((0, 0, h / 2), (0, 0, 1))),
    "dos_aristas": ("create_construction_plane", dict(type="two_edges", references=["edges:>Z and >X", "edges:<Z and <X"]),
                    "plano", lambda h: ((20, 0, h), (-h, 0, 20))),
    "tres_puntos": ("create_construction_plane", dict(type="three_points", references=[[20, 0, H0], [20, 20, H0], [0, 0, 0]]),
                    "plano", lambda h: ((20, 0, h), (-h, 0, 20))),
    "perpendicular": ("create_construction_plane", dict(type="perpendicular", references=[">X", [20, 20, H0]]), "plano",
                      lambda h: ((20, 20, h), (0, 1, 0))),
    "ruta": ("create_construction_plane", dict(type="path", references=["edges:>X and >Y"], position=0.5), "plano",
             lambda h: ((20, 20, h / 2), (0, 0, 1))),
    "tangente": ("create_construction_plane", dict(type="tangent", references=["faces:%CYLINDER"], body="Cuerpo2"), "plano",
                 lambda h: ((50, 0, 0), (1, 0, 0))),
    "eje_dos_planos": ("create_construction_axis", dict(type="dos_planos", references=[">Z", ">X"]), "eje",
                       lambda h: ((20, 0, h), (0, 1, 0))),
    "eje_dos_puntos": ("create_construction_axis", dict(type="dos_puntos", references=[[20, 0, H0], [0, 20, H0]]), "eje",
                       lambda h: ((20, 0, h), (-R2, R2, 0))),
    "eje_arista": ("create_construction_axis", dict(type="arista", references=["edges:>X and >Y"]), "eje",
                   lambda h: ((20, 20, 0), (0, 0, 1))),
    "eje_perpendicular": ("create_construction_axis", dict(type="perpendicular_cara", references=[">Z"], location=[5, 5, H0]),
                          "eje", lambda h: ((5, 5, h), (0, 0, 1))),
    "eje_cilindro": ("create_construction_axis", dict(type="cilindro", references=["faces:%CYLINDER"], body="Cuerpo2"), "eje",
                     lambda h: ((40, 0, 0), (0, 0, 1))),
    "punto_vertice": ("create_construction_point", dict(type="vertice", references=[[20, 20, H0]]), "punto",
                      lambda h: (20, 20, h)),
    "punto_tres_planos": ("create_construction_point", dict(type="tres_planos", references=[">Z", ">X", ">Y"]), "punto",
                          lambda h: (20, 20, h)),
    "punto_dos_aristas": ("create_construction_point", dict(type="dos_aristas", references=["edges:>Z and >X", "edges:>X and >Y"]),
                          "punto", lambda h: (20, 20, h)),
    "punto_ruta": ("create_construction_point", dict(type="ruta", references=["edges:>X and >Y"], position=0.25), "punto",
                   lambda h: (20, 20, h / 4)),
    "punto_centro": ("create_construction_point", dict(type="centro", references=["edges:%CIRCLE and >Z"], body="Cuerpo2"),
                     "punto", lambda h: (40, 0, 5)),
}


def _armar():
    s = api.Sesion()
    llamar(s, "create_parameter", name="alto", expression=f"{H0} mm")
    llamar(s, "create_box", length=20, width=20, height="alto", anchor="corner")
    llamar(s, "create_cylinder", radius=10, height=5, x=40, y=0)
    return s


def _mide(s, que, i):
    e = s.doc.estado_final
    if que == "plano":
        return e.planos[i].origen, e.planos[i].normal
    if que == "eje":
        return e.ejes[i][0], e.ejes[i][1]
    return e.puntos[i][0], None


def _comprobar(s, que, i, esperado, h):
    p, d = _mide(s, que, i)
    if que == "punto":
        assert np.allclose(p, esperado(h), atol=1e-6)
        return
    q, n = (np.asarray(v, float) for v in esperado(h))
    n /= np.linalg.norm(n)
    assert abs(abs(float(np.dot(d, n))) - 1) < 1e-6            # misma normal o dirección
    lejos = (q - p) @ n if que == "plano" else np.linalg.norm(np.cross(q - p, n))
    assert abs(lejos) < 1e-6                                   # el punto esperado está en el plano o el eje


@pytest.mark.parametrize("caso", CASOS)
def test_construir_sigue_a_la_cota_deshacer_y_reabrir(caso, tmp_path):
    herramienta, args, que, esperado = CASOS[caso]
    s = _armar()
    r = llamar(s, herramienta, **{"body": "Cuerpo1", **args})
    i = next(v["id"] for v in r.values() if isinstance(v, dict) and "id" in v)
    _comprobar(s, que, i, esperado, H0)
    llamar(s, "set_parameter", name="alto", expression=f"{H1} mm")
    _comprobar(s, que, i, esperado, H1)
    llamar(s, "undo")
    _comprobar(s, que, i, esperado, H0)
    llamar(s, "redo")
    _comprobar(s, que, i, esperado, H1)
    ruta = tmp_path / "m.omnicad"
    llamar(s, "save_document", path=str(ruta))
    otra = api.Sesion()
    llamar(otra, "open_document", path=str(ruta))
    _comprobar(otra, que, i, esperado, H1)


def test_construir_encadenada_y_scu_siguen_a_la_cota():
    """El resultado de una herramienta de CONSTRUIR alimenta a otra (plano → eje → punto) y la SCU se apoya en un vértice."""
    s = _armar()
    pid = llamar(s, "create_construction_plane", plane=">Z", offset=5, body="Cuerpo1")["plane"]["id"]
    eid = llamar(s, "create_construction_axis", type="dos_planos", references=[pid, "YZ"])["axis"]["id"]
    qid = llamar(s, "create_construction_point", type="arista_plano", references=[eid, "XZ"])["point"]["id"]
    u = llamar(s, "create_ucs", origin=[20, 20, H0], rz=90, body="Cuerpo1")
    for h in (H0, H1):
        llamar(s, "set_parameter", name="alto", expression=f"{h} mm")
        e = s.doc.estado_final
        assert np.allclose(e.puntos[qid][0], (0, 0, h + 5), atol=1e-6)
        assert np.allclose(e.puntos[f"{u['ucs']['id']}_o"][0], (20, 20, h), atol=1e-6)
        m = np.array([e.ejes[f"{u['ucs']['id']}_{k}"][1] for k in "xyz"])
        assert np.allclose(m @ m.T, np.eye(3), atol=1e-9) and np.linalg.det(m) == pytest.approx(1)


def test_edit_feature_valida_el_plano_como_al_crearlo():
    """B-261: editar no se saltea el filtro de la creación ni deja pasar una lista como expresión; null = por defecto."""
    s = _armar()
    pid = llamar(s, "create_construction_plane", plane=">Z", offset=2, body="Cuerpo1")["plane"]["id"]
    for params, texto in (({"tipo": "angulo"}, "necesita un eje"), ({"distancia": [1]}, "no una lista"),
                          ({"distancia": {"a": 1}}, "no un objeto")):
        r = api.llamar(s, "edit_feature", {"feature": pid, "params": params})
        assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED" and texto in r["mensaje"], r
        _comprobar(s, "plano", pid, lambda h: ((0, 0, h + 2), (0, 0, 1)), H0)
    assert llamar(s, "edit_feature", feature=pid, params={"distancia": None})["params"]["distancia"] == "10 mm"


def test_punto_por_dos_aristas_que_se_cruzan_sin_tocarse_da_error():
    """B-258: aristas alabeadas no tienen intersección (ni prolongadas): error, no el punto medio entre las rectas."""
    s = _armar()
    r = api.llamar(s, "create_construction_point", {"type": "dos_aristas", "body": "Cuerpo1",
                                                     "references": ["edges:>Z and >X", "edges:<Z and >Y"]})
    assert not r["ok"] and "no se cortan" in r["mensaje"], r
    assert not s.doc.estado_final.puntos


@pytest.mark.parametrize("x, z", [("Z", "Z"), ("X", "X")])
def test_scu_con_x_paralelo_a_z_da_error(x, z):
    """B-259: un X elegido paralelo a Z no se descarta callado; da el mismo error que X paralelo a Y."""
    s = _armar()
    r = api.llamar(s, "create_ucs", {"origin": [0, 0, 0], "x_axis": x, "z_axis": z})
    assert not r["ok"] and "paralelos" in r["mensaje"], r


def test_scu_sin_x_con_z_en_x_elige_su_x():
    """Sin X elegido, el X por defecto (+X) paralelo a Z no es error: el SCU elige uno perpendicular."""
    s = _armar()
    u = llamar(s, "create_ucs", origin=[0, 0, 0], z_axis="X")["ucs"]["id"]
    assert np.allclose(s.doc.estado_final.ejes[f"{u}_z"][1], (1, 0, 0), atol=1e-9)


@pytest.mark.parametrize("eje, giro0, esperada", [
    ("Y", 0, lambda g: (0, 1, 0)), ("Y", 30, lambda g: (0, 1, 0)), ("X", 30, lambda g: (1, 0, 0)),
    ("X", 0, lambda g: (0, np.cos(np.radians(g)), np.sin(np.radians(g))))])
def test_plano_en_angulo_no_salta_al_girar_la_arista(eje, giro0, esperada):
    """B-257: el 0° se elige al crear (eje del mundo más perpendicular a la arista) y un parámetro que gira la arista no
    lo hace saltar 90°. Esperados medidos en Fusion el 2026-11-08 (caja girada por un parámetro con Mover)."""
    s = api.Sesion()
    llamar(s, "create_parameter", name="giro", expression=f"{giro0} deg")
    llamar(s, "create_box", length=20, width=30, height=40, anchor="corner")
    llamar(s, "move_body", body="Cuerpo1", rotate=[0, "giro", 0] if eje == "Y" else ["giro", 0, 0], pivot="origin")
    arista = max((a for a in llamar(s, "find_edges", body="Cuerpo1")["edges"] if abs(a["length"] - 40) < 1e-6),
                 key=lambda a: a["center"][0] + a["center"][1])
    pid = llamar(s, "create_construction_plane", type="angle", references=[arista["id"]], angle=0, body="Cuerpo1")["plane"]["id"]
    for g in (0, 10, 25, 26, 30, 60):
        llamar(s, "set_parameter", name="giro", expression=f"{g} deg")
        n = s.doc.estado_final.planos[pid].normal
        assert abs(abs(float(np.dot(n, esperada(g)))) - 1) < 1e-6, (g, n)


def test_plano_en_angulo_guarda_su_eje_0_y_se_edita():
    """B-257: crear fija eje_0; edit_feature lo cambia; uno paralelo a la arista cae en el que elige eje_cero."""
    s = _armar()
    pid = llamar(s, "create_construction_plane", type="angle", references=["edges:>Z and >X"], angle=0,
                 body="Cuerpo1")["plane"]["id"]
    assert s.paso(pid).p["eje_0"] == "Z"                              # arista a lo largo de Y: horizontal
    for eje, normal in (("X", (1, 0, 0)), ("Y", (0, 0, 1))):         # Y es paralelo a la arista
        llamar(s, "edit_feature", feature=pid, params={"eje_0": eje})
        assert np.allclose(np.abs(s.doc.estado_final.planos[pid].normal), normal, atol=1e-9)


def test_planos_del_scu_sirven_como_texto():
    """B-263: los planos que anuncia create_ucs («op2_xy») sirven en create_sketch y create_construction_plane, y el
    boceto depende del SCU (borrarlo no deja el boceto colgado sin aviso)."""
    s = _armar()
    planos = llamar(s, "create_ucs", origin="O", dz=7)["planes"]
    xy = planos["xy"]
    b = llamar(s, "create_sketch", plane=xy)["sketch"]
    pl = next(v for v in llamar(s, "create_construction_plane", plane=xy.upper(), offset=3).values()
              if isinstance(v, dict) and "id" in v)["id"]
    assert np.isclose(s.doc.estado_final.planos[pl].origen[2], 10)
    scu = xy.split("_")[0]
    assert scu in s.paso(b["id"]).dependencias() and scu in s.paso(pl).dependencias()


_EXT = lambda tipo: lambda i: {"objeto_extension": {"tipo": tipo, "id": i}, "tipo_extension": "objeto"}  # noqa: E731


@pytest.mark.parametrize("herramienta, args, propia", [
    ("create_construction_plane", dict(plane="XY", offset=3), _EXT("plano")),
    ("create_construction_axis", dict(type="dos_planos", references=["XY", "XZ"]), _EXT("eje")),
    ("create_construction_point", dict(type="tres_planos", references=["XY", "XZ", "YZ"]),
     lambda i: {"refs": [{"tipo": "punto", "id": i}, {"tipo": "plano", "id": "XZ"}, {"tipo": "plano", "id": "YZ"}]}),
    ("create_ucs", dict(origin="O"), lambda i: {"origen": {"tipo": "punto", "id": i}})])
def test_construccion_que_se_referencia_a_si_misma_se_rechaza(herramienta, args, propia):
    """B-260: un plano, eje, punto o SCU que se usa a sí mismo (vía edit_feature o receta) se rechaza con mensaje claro,
    y su referencia propia no lo traba: se puede borrar."""
    s = _armar()
    i = next(v["id"] for v in llamar(s, herramienta, **args).values() if isinstance(v, dict) and "id" in v)
    r = api.llamar(s, "edit_feature", {"feature": i, "params": propia(i)})
    assert not r["ok"] and "a sí mismo" in r["mensaje"], r
    op = s.paso(i).copia()
    op.p.update(propia(i))
    assert i not in op.dependencias()
    llamar(s, "delete_feature", feature=i)


def test_receta_con_ids_repetidos_o_nombre_sin_tope_se_rechaza():
    """B-262: apply_recipe rechaza dos pasos con el mismo id (uno tapaba al otro) y un nombre de paso de más de 255
    caracteres o con NUL; rename aplica el mismo tope. El documento queda como estaba."""
    s = _armar()
    pl = llamar(s, "create_construction_plane", plane="XY", offset=3)["plane"]["id"]
    receta = llamar(s, "get_recipe")["recipe"]
    antes = len(s.doc.operaciones)
    for cambio in (lambda r: r["operaciones"][-1].update(id=r["operaciones"][0]["id"]),
                   lambda r: r["operaciones"][-1].update(nombre="x" * 300),
                   lambda r: r["operaciones"][-1].update(nombre="a\0b"),
                   lambda r: r.setdefault("propiedades", {}).setdefault("op1.c1", {}).update(nombre="z" * 300)):
        mala = copy.deepcopy(receta)
        cambio(mala)
        r = api.llamar(s, "apply_recipe", {"recipe": mala})
        assert not r["ok"] and r["error_kind"] == "INVALID_RECIPE", r
        assert len(s.doc.operaciones) == antes
    r = api.llamar(s, "rename", {"target": pl, "new_name": "y" * 300})
    assert not r["ok"] and "255" in r["mensaje"], r
    llamar(s, "rename", target=pl, new_name="y" * 255)
    r = api.llamar(s, "rename", {"target": "op1.c1", "new_name": "z" * 300, "kind": "body"})
    assert not r["ok"] and "255" in r["mensaje"], r

def test_guardas_de_construir_como_fusion():
    """P-93: eje por esfera, plano en ángulo sobre arista circular, plano medio de dos planos que coinciden, lo que cae a
    más de 1 km del origen y nombres con NUL o enormes se rechazan sin tocar el documento. La ruta deja pasar del final."""
    s = _armar()
    llamar(s, "create_sphere", radius=5, x=-30, y=0, z=0)
    antes = len(s.doc.operaciones)
    malos = [("create_construction_axis", dict(type="cilindro", references=["faces:%SPHERE"], body="Cuerpo3")),
             ("create_construction_plane", dict(type="angle", references=["edges:%CIRCLE and >Z"], angle=30, body="Cuerpo2")),
             ("create_construction_plane", dict(type="middle", references=["<Z", "XY"], body="Cuerpo1")),
             ("create_construction_plane", dict(type="path", references=["edges:>X and >Y"], position=1e9, body="Cuerpo1")),
             ("create_construction_point", dict(type="ruta", references=["edges:>X and >Y"], position=1e9, body="Cuerpo1")),
             ("create_construction_axis", dict(type="perpendicular_cara", references=[">Z"], location=[2e6, 0, 0], body="Cuerpo1")),
             ("create_construction_plane", dict(type="perpendicular", references=[">Z"], location=[2e6, 0, 0], body="Cuerpo1")),
             ("create_construction_plane", dict(plane="XY", offset=3, name="a\0b")),
             ("create_construction_plane", dict(plane="XY", offset=3, name="x" * 5000))]
    for herramienta, args in malos:
        r = api.llamar(s, herramienta, args)
        assert not r["ok"] and r["error_kind"] not in ("AMBIGUOUS_REFERENCE", "NO_MATCH"), (herramienta, args, r)
        assert len(s.doc.operaciones) == antes
    pl = llamar(s, "create_construction_plane", type="path", references=["edges:>X and >Y"], position=2,
               body="Cuerpo1")["plane"]["id"]
    assert np.isclose(s.doc.estado_final.planos[pl].origen[2], 2 * H0)       # pasar del final de la ruta, como Fusion


def test_copia_de_patron_de_un_plano_sirve_como_texto():
    """B-263: la copia de un plano por un patrón («op5_k1») sirve en create_sketch y create_construction_plane; un plano
    que no existe da PLANE_NOT_FOUND con la pista de cómo se nombran los planos de un SCU y de una copia."""
    s = _armar()
    pl = llamar(s, "create_construction_plane", plane="XY", offset=3)["plane"]["id"]
    patron = llamar(s, "rectangular_pattern", construction=[pl], x_count=2, axis1="z", x_spacing=4)
    copia = f"{patron['feature']['id']}_k1"
    assert np.isclose(s.doc.estado_final.planos[copia].origen[2], 7)
    llamar(s, "create_sketch", plane=copia)
    otro = llamar(s, "create_construction_plane", plane=copia, offset=1)["plane"]["id"]
    assert np.isclose(s.doc.estado_final.planos[otro].origen[2], 8)
    r = api.llamar(s, "create_sketch", {"plane": "op99_xy"})
    assert not r["ok"] and r["error_kind"] == "PLANE_NOT_FOUND", r
    assert any("_xy" in p and "_k" in p for p in r["pistas"]), r


def test_b284_un_nombre_con_un_sustituto_suelto_se_rechaza_y_el_documento_se_guarda(tmp_path):
    """B-284: «\ud800x» entraba como nombre (plano, eje, punto, SCU, receta o rename) y después save_document fallaba
    con UnicodeEncodeError. Se rechaza al crearlo, como un NUL, y el documento se sigue guardando."""
    s = _armar()
    malo = "\ud800x"
    antes = len(s.doc.operaciones)
    for herramienta, args in (("create_construction_plane", dict(type="offset", plane="XY", offset=1)),
                              ("create_construction_axis", dict(type="dos_planos", references=["XY", "XZ"])),
                              ("create_construction_point", dict(type="vertice", references=["O"])),
                              ("create_ucs", dict(origin="O"))):
        r = api.llamar(s, herramienta, {**args, "name": malo})
        assert not r["ok"] and "no es válido" in r["mensaje"], (herramienta, r)
    pl = llamar(s, "create_construction_plane", plane="XY", offset=3)["plane"]["id"]
    r = api.llamar(s, "rename", {"target": pl, "new_name": malo})
    assert not r["ok"], r
    receta = llamar(s, "get_recipe")["recipe"]
    receta["operaciones"][-1]["nombre"] = malo
    r = api.llamar(s, "apply_recipe", {"recipe": receta})
    assert not r["ok"] and r["error_kind"] == "INVALID_RECIPE", r
    assert len(s.doc.operaciones) == antes + 1
    llamar(s, "create_parameter", name="p284", expression="5", comment=malo)     # gemelo: otro texto que se guarda
    llamar(s, "save_document", path=str(tmp_path / "b284.omnicad"))
    s2 = api.Sesion()
    llamar(s2, "open_document", path=str(tmp_path / "b284.omnicad"))
    assert malo in [p.get("comentario") for p in s2.doc.a_dict()["parametros"]]


@pytest.mark.parametrize("malo", [None, 7, 1.5, "", "  ", ["a"]])
def test_b285_receta_con_id_de_paso_que_no_es_texto_se_rechaza(malo):
    """B-285: apply_recipe aceptaba ids None, 7, 1.5 o vacíos; después delete_feature daba INTERNAL_ERROR (TypeError)."""
    s = _armar()
    llamar(s, "create_construction_plane", plane="XY", offset=3)
    receta = llamar(s, "get_recipe")["recipe"]
    antes = len(s.doc.operaciones)
    receta["operaciones"][-1]["id"] = malo
    r = api.llamar(s, "apply_recipe", {"recipe": receta})
    assert not r["ok"] and r["error_kind"] == "INVALID_RECIPE" and "id de texto" in r["mensaje"], r
    assert len(s.doc.operaciones) == antes
