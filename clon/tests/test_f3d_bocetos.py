# -*- coding: utf-8 -*-
"""Bocetos de un .f3d: los perfiles planos que Fusion guarda en `Breps.BlobParts/BREP.*.smb` pasan a pasos Boceto.

Los bloques se arman acá mismo en SAB (como en test_f3d_nativo): un cuadrado de 1 cm, un círculo de 0,25 cm y un
semicírculo, todos sobre el mismo plano. La prueba con un archivo real (BINCHA.f3d, 10 bocetos) está en test_f3d_reales."""
import math

import pytest
from test_f3d_nativo import _CARPETA, _caras, _cuerpo_vacio, _Modelo, _sab, _sab_cilindro, _sab_cubo, _vertice, _zip_f3d

from omnicad import api
from omnicad.io_archivos import f3d_bocetos, f3d_nativo
from omnicad.io_archivos.abrir_externo import documento_desde_archivo
from omnicad.nucleo import geometria as geo


def _sab_perfiles(z=0.0, normal=(0.0, 0.0, 1.0)):
    """Un cuerpo de hoja con tres caras en el plano z: un cuadrado de 1 cm, un disco de 0,25 cm y un semidisco."""
    m = _Modelo()
    _, shell = _cuerpo_vacio(m, con_marca=False)
    u = (1.0, 0.0, 0.0)

    def plano():
        return m.nuevo("plane-surface", (0.0, 0.0, z), normal, u, False, False, False, False, False)

    def recta(a, b):
        va, vb = _vertice(m, a), _vertice(m, b)
        curva = m.nuevo("straight-curve", a, tuple(q - p for p, q in zip(a, b, strict=True)), False, False)
        e = m.nuevo("edge", va, 0.0, vb, math.dist(a, b), m.N, curva, False, "unknown")
        m.poner(va, 3, e)
        m.poner(vb, 3, e)
        return e

    esquinas = [(0.0, 0.0, z), (1.0, 0.0, z), (1.0, 1.0, z), (0.0, 1.0, z)]
    cuadrado = [(recta(esquinas[i], esquinas[(i + 1) % 4]), False) for i in range(4)]
    v = _vertice(m, (3.25, 3.0, z))
    curva = m.nuevo("ellipse-curve", (3.0, 3.0, z), (0.0, 0.0, 1.0), (0.25, 0.0, 0.0), 1.0, False, False)
    circulo = m.nuevo("edge", v, 0.0, v, 2 * math.pi, m.N, curva, False, "unknown")
    m.poner(v, 3, circulo)
    va, vb = _vertice(m, (5.25, 0.5, z)), _vertice(m, (4.75, 0.5, z))
    curva = m.nuevo("ellipse-curve", (5.0, 0.5, z), (0.0, 0.0, 1.0), (0.25, 0.0, 0.0), 1.0, False, False)
    arco = m.nuevo("edge", va, 0.0, vb, math.pi, m.N, curva, False, "unknown")
    m.poner(va, 3, arco)
    m.poner(vb, 3, arco)
    base = recta((4.75, 0.5, z), (5.25, 0.5, z))
    _caras(m, shell, [(plano(), False, [cuadrado]), (plano(), False, [[(circulo, False)]]),
                      (plano(), False, [[(arco, False), (base, False)]])])
    return m


def _curvas(boceto):
    cuenta = {}
    for c in boceto.curvas.values():
        cuenta[c.tipo] = cuenta.get(c.tipo, 0) + 1
    return cuenta


def test_los_perfiles_planos_salen_como_un_boceto_en_mm():
    bocetos, avisos = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles().r))
    assert avisos == [] and len(bocetos) == 1
    b = bocetos[0]
    assert b["marco"] == {"origen": [0.0, 0.0, 0.0], "normal": [0.0, 0.0, 1.0], "u": [1.0, 0.0, 0.0]}
    assert _curvas(b["boceto"]) == {"linea": 5, "circulo": 1, "arco": 1} and b["caras"] == 3
    boceto = b["boceto"]
    largos = sum(math.dist(boceto.coords(c.p1), boceto.coords(c.p2)) for c in boceto.curvas.values() if c.tipo == "linea")
    assert largos == pytest.approx(4 * 10.0 + 5.0)                                  # el cuadrado de 1 cm y la base del semidisco
    circulo, = [c for c in boceto.curvas.values() if c.tipo == "circulo"]
    assert circulo.radio == pytest.approx(2.5) and boceto.coords(circulo.centro) == pytest.approx((30.0, 30.0))
    arco, = [c for c in boceto.curvas.values() if c.tipo == "arco"]
    assert boceto.coords(arco.centro) == pytest.approx((50.0, 5.0))
    assert boceto.coords(arco.inicio) == pytest.approx((52.5, 5.0)) and boceto.coords(arco.fin) == pytest.approx((47.5, 5.0))
    # las esquinas del cuadrado son puntos compartidos: 4 + circulo (centro) + arco (centro, 2 extremos, 1 compartido) …
    assert len(boceto.puntos) == 4 + 1 + 3


def test_las_caras_con_la_normal_al_reves_dan_el_mismo_boceto():
    """Un perfil mirando hacia abajo se dibuja en el marco XY de siempre: las coordenadas no se espejan."""
    b = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles(normal=(0.0, 0.0, -1.0)).r))[0][0]
    assert b["marco"]["normal"] == [0.0, 0.0, 1.0] and _curvas(b["boceto"]) == {"linea": 5, "circulo": 1, "arco": 1}
    esquinas = {tuple(round(x, 6) for x in b["boceto"].coords(p)) for p in b["boceto"].puntos}
    assert {(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)} <= esquinas


def test_un_cuerpo_con_superficies_curvas_no_es_un_boceto():
    assert f3d_bocetos.leer_bocetos(_sab(_sab_cilindro().r)) == ([], [])
    assert f3d_bocetos.leer_bocetos(_sab(_sab_cubo().r)) == ([], [])               # seis planos, pero no coplanares


def test_un_bloque_que_no_es_sab_se_avisa_y_no_tumba_nada():
    bocetos, avisos = f3d_bocetos.leer_bocetos(b"no es un bloque SAB", "pieza")
    assert bocetos == [] and "pieza" in avisos[0]


def test_un_plano_desplazado_conserva_su_altura():
    b = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles(z=2.0).r))[0][0]
    assert b["marco"]["origen"] == pytest.approx([0.0, 0.0, 20.0])


def test_la_tapa_de_una_extrusion_no_cuenta_como_otro_boceto():
    """Los perfiles guardan también las tapas de las extrusiones: la misma forma en otro plano paralelo. Queda la más
    cercana al origen."""
    uno = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles(z=0.0).r))[0]
    tapa = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles(z=-0.5).r))[0]
    otro = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles(z=3.0, normal=(0.0, 0.0, -1.0)).r))[0]
    elegidos = f3d_bocetos.sin_repetidos(tapa + uno + otro)
    assert len(elegidos) == 1 and elegidos[0]["marco"]["origen"][2] == pytest.approx(0.0)


def test_el_tope_de_bocetos_avisa_lo_que_deja_afuera(monkeypatch):
    uno = f3d_bocetos.leer_bocetos(_sab(_sab_perfiles().r))[0] * 5
    monkeypatch.setattr(f3d_bocetos, "BOCETOS_MAX", 3)
    avisos = []
    assert len(f3d_bocetos.limitar(uno, avisos, "pieza")) == 3 and "primeros 3" in avisos[0]


def _f3d_con_bocetos(tmp_path, z=0.0):
    return _zip_f3d(tmp_path / "pieza.f3d", [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)),
                                             (_CARPETA + "BREP.bbbb.smb", _sab(_sab_perfiles(z=z).r))])


def test_abrir_un_f3d_crea_un_paso_boceto_con_su_plano(tmp_path):
    doc, _ = documento_desde_archivo(_f3d_con_bocetos(tmp_path))
    assert [o.TIPO for o in doc.operaciones] == ["operacion_base", "boceto"] and doc.marcador == 2
    op = doc.operaciones[1]
    assert op.nombre == "Boceto1" and op.p["plano"] == "XY"
    assert _curvas(op.boceto) == {"linea": 5, "circulo": 1, "arco": 1}
    assert len(doc.estado_final.cuerpos) == 1 and geo.volumen(next(iter(doc.estado_final.cuerpos.values())).forma) \
        == pytest.approx(1000.0, rel=1e-9)


def test_el_boceto_desplazado_va_sobre_su_marco(tmp_path):
    doc, _ = documento_desde_archivo(_f3d_con_bocetos(tmp_path, z=2.0))
    op = doc.operaciones[1]
    assert op.p["plano"] == "cara" and op.p["marco"]["origen"] == pytest.approx([0.0, 0.0, 20.0])
    assert doc.resultados[1].estado == "ok"


def test_un_f3d_con_bocetos_se_guarda_y_reabre_igual(tmp_path):
    from omnicad.io_archivos import proyecto
    doc, _ = documento_desde_archivo(_f3d_con_bocetos(tmp_path))
    ruta = tmp_path / "salida.omnicad"
    proyecto.guardar(doc, ruta)
    otro = proyecto.abrir(ruta)
    assert [o.TIPO for o in otro.operaciones] == ["operacion_base", "boceto"]
    assert _curvas(otro.operaciones[1].boceto) == {"linea": 5, "circulo": 1, "arco": 1}


def test_inspect_f3d_cuenta_los_bocetos(tmp_path):
    r = api.llamar(api.Sesion(), "inspect_f3d", {"path": str(_f3d_con_bocetos(tmp_path))})
    assert r["ok"], r
    assert r["result"]["sketches"] == {"count": 1, "curves": {"linea": 5, "circulo": 1, "arco": 1}}


def test_con_varios_componentes_los_bocetos_no_se_importan_y_se_avisa(tmp_path):
    """El bloque de bocetos no dice de qué componente es: con dos componentes no se adivina."""
    f3d = _zip_f3d(tmp_path / "dos.f3d", [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)),
                                          (_CARPETA + "BREP.cccc.smbh", _sab(_sab_cubo(lado=2.0).r)),
                                          (_CARPETA + "BREP.bbbb.smb", _sab(_sab_perfiles().r))])
    bocetos = []
    _, avisos = f3d_nativo.leer_componentes(f3d, bocetos=bocetos)
    assert bocetos == [] and any("1 bocetos" in a and "2 componentes" in a for a in avisos)
    doc, _ = documento_desde_archivo(f3d)
    assert [o.TIPO for o in doc.operaciones] == ["operacion_base"]


def test_el_boceto_sigue_la_matriz_del_unico_componente(tmp_path):
    """Un solo componente movido: sus bocetos van con él (aquí, 100 mm en X)."""
    from test_p11a_f3d_instancias import _Malla, _cuerpo, _f3d, _matriz, _nodo
    malla = _Malla()
    world = _nodo(0x10, 0xC0, _matriz(), _nodo(0x11, 0xC1, _matriz(10, 0, 0), _cuerpo(malla)))      # 10 cm = 100 mm
    ruta = _f3d(tmp_path, world, malla, [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)),
                                         (_CARPETA + "BREP.bbbb.smb", _sab(_sab_perfiles().r))])
    bocetos = []
    f3d_nativo.leer_componentes(ruta, bocetos=bocetos)
    assert len(bocetos) == 1 and bocetos[0]["marco"]["origen"] == pytest.approx([100.0, 0.0, 0.0])
