# -*- coding: utf-8 -*-
"""P11.a: un .f3d con componentes movidos y repetidos se abre con cada cuerpo en su lugar y las copias como
instancias (`f3d_escena`, `f3d_nativo.leer_componentes`, `OpOperacionBase` con "matriz" y "ref", `inspect_f3d`).

La escena de dibujo que Fusion guarda en el archivo se arma acá mismo con el formato que lee `f3d_escena` (textos
UTF-16 con largo, nodos con su cola `TransformAttribute` + `Instance`, caras con malla y la etiqueta `Body`): las
pruebas no dependen de archivos de nadie."""
import struct
import time

import numpy as np
import pytest
from test_f3d_nativo import _CARPETA, _sab, _sab_cubo, _zip_f3d

from omnicad import api
from omnicad.io_archivos import f3d_escena, f3d_nativo, proyecto
from omnicad.io_archivos.abrir_externo import documento_desde_archivo
from omnicad.nucleo import geometria as geo

_ESCENA = "OGS.BlobFolder/OGS/DefaultScene/"


# ---------------------------------------------------------------- escena sintética
def _s(texto):
    return struct.pack("<I", len(texto)) + texto.encode("utf-16-le")


def _id(n):
    return _s(f"{n:016X}")


def _matriz(tx=0.0, ty=0.0, tz=0.0, giro_z=0.0):
    """TransformAttribute: 5 bytes de cabecera, 16 float32 por filas (traslación en la última, en cm) y 1 byte."""
    c, s_ = np.cos(np.radians(giro_z)), np.sin(np.radians(giro_z))
    m = np.array([[c, s_, 0, 0], [-s_, c, 0, 0], [0, 0, 1, 0], [tx, ty, tz, 1]], "<f4")
    return _s("TransformAttribute") + b"\x00" * 5 + m.tobytes() + b"\x00"


class _Malla:
    """Cubo de 1 cm (de [0,1]³) en caras de dos triángulos, escrito como Fusion_mesh_000: vértices de 32 bytes."""

    def __init__(self):
        self.datos = bytearray()

    def cara(self, eje, lado):
        """Registro de malla de la cara `eje`=`lado` del cubo, con el sentido hacia afuera."""
        u, v = [k for k in range(3) if k != eje]
        esquinas = []
        for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
            p = [0.0, 0.0, 0.0]
            p[eje], p[u], p[v] = float(lado), float(a), float(b)
            esquinas.append(p)
        normal = np.cross(np.subtract(esquinas[1], esquinas[0]), np.subtract(esquinas[2], esquinas[0]))
        afuera = np.eye(3)[eje] * (1 if lado else -1)
        if normal @ afuera < 0:
            esquinas.reverse()
        desplazamiento = len(self.datos)
        for p in esquinas:
            self.datos += struct.pack("<8f", *p, *afuera, 0.0, 0.0)
        self.datos += struct.pack("<6I", 0, 1, 2, 0, 2, 3)
        return struct.pack("<5I", desplazamiento, 12, 12, 8, 6)


def _cara(malla, eje, lado, con_malla=True):
    relleno = b"\x00" * 30
    return _s("Face") + relleno + (malla.cara(eje, lado) if con_malla else b"\x00" * 20) + b"\x00" * 20


def _cuerpo(malla, con_malla=True):
    """Seis caras y la etiqueta Body (un cubo de 1 cm)."""
    return b"".join(_cara(malla, e, lado, con_malla) for e in range(3) for lado in (0, 1)) + _s("Body") + b"\x00" * 45


def _nodo(W, C, matriz, contenido=b""):
    """Componente: su cabecera (envoltorio W y contenido C), lo que trae adentro y la cola con matriz e `Instance`."""
    cabecera = (_s("GroupNode") + _id(W) + b"\x00" * 11 + _s("SingleNodeWorld") + b"\x00" * 8
                + _s("GroupNode") + _id(C))
    cola = _s("Component") + matriz + _id(W) + b"\x00" * 29 + _s("Instance") + b"\x00" * 50
    return cabecera + contenido + cola


def _f3d(tmp_path, world, malla, bloques=None):
    """.f3d con un cubo de 1 cm (10 mm) como único componente y la escena `world` + `malla`."""
    bloques = [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r))] if bloques is None else bloques
    return _zip_f3d(tmp_path / "ensamble.f3d", bloques + [
        ("FusionAssetName[Active]/" + _ESCENA + "world", world),
        ("FusionAssetName[Active]/" + _ESCENA + "Fusion_mesh_000", bytes(malla.datos))])


def _centro(forma):
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    return np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])


def _ensamble(tmp_path, con_malla=True):
    """Raíz con un cubo movido 2 cm en X y una copia del mismo componente 3 cm en Y, girada 90° alrededor de Z."""
    malla = _Malla()
    cubo = _nodo(0x11, 0xC1, _matriz(2, 0, 0), _cuerpo(malla, con_malla))
    copia = _nodo(0x12, 0xC1, _matriz(0, 3, 0, giro_z=90))           # mismo contenido: no repite las caras
    world = _nodo(0x10, 0xC0, _matriz(), cubo + copia)
    return _f3d(tmp_path, world, malla)


# ---------------------------------------------------------------- la escena
def test_escena_nodos_copias_y_marcos_anidados():
    malla = _Malla()
    hijo = _nodo(0x21, 0xD1, _matriz(0, 2, 0, giro_z=90), _cuerpo(malla))
    repetido = _nodo(0x22, 0xD1, _matriz(0, 0, 5))
    world = _nodo(0x20, 0xD0, _matriz(1, 0, 0), hijo + repetido)
    e = f3d_escena.Escena(world, bytes(malla.datos))
    assert len(e.nodos) == 3 and [n["es_ref"] for n in e.nodos] == [False, True, False]
    assert e.nodos[0]["padre"] == 2 and e.nodos[1]["padre"] == 2 and e.nodos[2]["padre"] is None
    (cuerpo,) = e.cuerpos
    assert cuerpo["caras"] == 6 and cuerpo["nodo"] == 0
    assert cuerpo["vol_mm3"] == pytest.approx(1000.0) and tuple(cuerpo["hi"]) == pytest.approx((10, 10, 10))
    marcos = e.marcos()[0]                                           # el contenido tiene dos ocurrencias
    assert len(marcos) == 2
    # hijo: gira 90° en Z y va 2 cm en Y; el padre lo corre 1 cm en X → origen del hijo en (10, 20, 0) mm
    assert marcos[0][:3, 3] == pytest.approx([10, 20, 0], abs=1e-4)
    assert marcos[1][:3, 3] == pytest.approx([10, 0, 50], abs=1e-4)  # la copia: 5 cm en Z y el mismo padre
    assert marcos[0][:3, :3] @ [1, 0, 0] == pytest.approx([0, 1, 0], abs=1e-6)     # el giro de 90° lleva X a Y


def test_escena_ignora_basura_y_no_revienta():
    for datos in (b"", b"\x00" * 500, _s("Instance") * 3 + b"\x01" * 40, _s("Face") + b"\xff" * 3):
        e = f3d_escena.Escena(datos, b"")
        assert e.nodos == [] and e.cuerpos == []


# ---------------------------------------------------------------- el .f3d
def test_f3d_ubica_el_componente_y_su_copia_comparte_la_geometria(tmp_path):
    f3d = _ensamble(tmp_path)
    comps, avisos = f3d_nativo.leer_componentes(f3d)
    assert avisos == [] and len(comps) == 1 and len(comps[0]["marcos"]) == 2
    partes, _ = f3d_nativo.leer(f3d)
    assert len(partes) == 2 and all(t == "solido" for _, t in partes)
    a, b = (p for p, _ in partes)
    assert _centro(a) == pytest.approx([25, 5, 5], abs=1e-3)
    assert _centro(b) == pytest.approx([-5, 35, 5], abs=1e-3)          # girado 90° sobre su esquina: ocupa x de -10 a 0
    assert geo.volumen(a) == pytest.approx(1000.0) == pytest.approx(geo.volumen(b))
    assert a.IsPartner(b) and not a.IsSame(b)                       # la misma geometría con otra ubicación


def test_cuerpo_oculto_sin_malla_se_ubica_por_la_cantidad_de_caras(tmp_path):
    comps, _ = f3d_nativo.leer_componentes(_ensamble(tmp_path, con_malla=False))
    assert len(comps) == 1 and len(comps[0]["marcos"]) == 2


def test_sin_escena_o_sin_componentes_movidos_queda_como_antes(tmp_path):
    sin = _zip_f3d(tmp_path / "solo.f3d", [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r))])
    partes, avisos = f3d_nativo.leer(sin)
    assert len(partes) == 1 and avisos == [] and _centro(partes[0][0]) == pytest.approx([5, 5, 5], abs=1e-3)
    malla = _Malla()
    quieto = _f3d(tmp_path, _nodo(0x30, 0xC3, _matriz(), _cuerpo(malla)), malla)      # un solo componente, sin mover
    partes, avisos = f3d_nativo.leer(quieto)
    assert len(partes) == 1 and avisos == [] and _centro(partes[0][0]) == pytest.approx([5, 5, 5], abs=1e-3)


def test_escena_dañada_deja_los_cuerpos_donde_estaban(tmp_path):
    malla = _Malla()
    roto = _f3d(tmp_path, _s("Instance") + b"\x00" * 10 + _s("TransformAttribute") + b"\x00" * 3, malla)
    partes, _ = f3d_nativo.leer(roto)
    assert len(partes) == 1 and _centro(partes[0][0]) == pytest.approx([5, 5, 5], abs=1e-3)


def test_si_ubicar_falla_con_un_error_de_geometria_el_archivo_abre_igual(tmp_path, monkeypatch):
    """Ubicar es una mejora: `geo.volumen` lanza ErrorGeometria (un RuntimeError) con un cuerpo inválido y el .f3d abre igual."""
    def roto(forma):
        raise geo.ErrorGeometria("la integración falló")
    monkeypatch.setattr(geo, "volumen", roto)
    partes, avisos = f3d_nativo.leer(_ensamble(tmp_path))
    assert len(partes) == 1 and _centro(partes[0][0]) == pytest.approx([5, 5, 5], abs=1e-3)
    assert any("No se pudo leer la posición" in a and "integración" in a for a in avisos)


def _dos_bloques(tmp_path, escena_extra=b""):
    otro = _sab(_sab_cubo(lado=2.0).r)
    malla = _Malla()
    world = _nodo(0x10, 0xC0, _matriz(), _nodo(0x11, 0xC1, _matriz(2, 0, 0), _cuerpo(malla)) + escena_extra)
    f3d = _f3d(tmp_path, world, malla, [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)), (_CARPETA + "BREP.bbbb.smbh", otro)])
    return f3d_nativo.leer(f3d)


def test_un_bloque_sin_componente_en_la_escena_no_entra(tmp_path):
    """P-11j: todos los componentes de la escena tienen su bloque: el bloque que sobra es de un componente borrado
    (Sherpa: 2 bloques de 1593 y 952 mm³ que Fusion no tiene)."""
    partes, avisos = _dos_bloques(tmp_path)
    assert [tuple(np.round(_centro(p), 1)) for p, _ in partes] == [(25.0, 5.0, 5.0)]
    assert any("no están en el diseño actual" in a for a in avisos)


def test_un_bloque_se_queda_si_la_escena_tiene_un_componente_sin_bloque(tmp_path):
    """Un cuerpo actual sin malla (la «tela» del abanico) deja un componente de la escena sin bloque: el bloque
    suelto es suyo (mismas caras) y se conserva."""
    sin_malla = _nodo(0x12, 0xC2, _matriz(), _cuerpo(_Malla(), con_malla=False))
    partes, avisos = _dos_bloques(tmp_path, sin_malla)
    centros = sorted(tuple(np.round(_centro(p), 1)) for p, _ in partes)
    assert centros == [(10.0, 10.0, 10.0), (25.0, 5.0, 5.0)]


def _bloque_con_un_cuerpo_viejo():
    """Un bloque como los de Fusion: el cubo actual y un cuerpo viejo del historial (otro cubo, a 5 cm)."""
    m = _sab_cubo()
    _sab_cubo(m=m, origen=(5.0, 5.0, 5.0))
    return [(_CARPETA + "BREP.aaaa.smbh", _sab(m.r))]


def test_un_cuerpo_viejo_del_historial_que_la_escena_no_muestra_no_entra(tmp_path):
    """El bloque de un componente guarda también cuerpos viejos (el panel de la cartera de ejemplo: 83 cuerpos y el
    diseño tiene 1). Si la escena ya explica todos los cuerpos del componente, los demás no están en el diseño."""
    malla = _Malla()
    world = _nodo(0x10, 0xC0, _matriz(), _nodo(0x11, 0xC1, _matriz(2, 0, 0), _cuerpo(malla)))
    visto = {}
    comps, avisos = f3d_nativo.leer_componentes(_f3d(tmp_path, world, malla, _bloque_con_un_cuerpo_viejo()), visto)
    assert len(comps) == 1 and _centro(f3d_nativo.expandir(comps)[0][0]) == pytest.approx([25, 5, 5], abs=1e-3)
    assert visto["descartados"] == 1 and visto["sin_ubicar"] == 0
    assert any("no están en el diseño actual" in a for a in avisos)


def test_un_cuerpo_actual_sin_malla_en_la_escena_no_se_descarta(tmp_path):
    """La «tela» del abanico de ejemplo es un cuerpo del diseño sin malla en la escena: su registro (mismas caras) lo
    salva; el cuerpo viejo no tiene registro y se descarta."""
    malla = _Malla()
    m = _sab_cubo()
    _sab_cubo(m=m, origen=(5.0, 5.0, 5.0))
    _sab_cubo(m=m, origen=(9.0, 9.0, 9.0), lado=0.5)                 # también 6 caras: el registro sin malla salva a uno
    bloques = [(_CARPETA + "BREP.aaaa.smbh", _sab(m.r))]
    contenido = _cuerpo(malla) + _cuerpo(malla, con_malla=False)
    world = _nodo(0x10, 0xC0, _matriz(), _nodo(0x11, 0xC1, _matriz(2, 0, 0), contenido))
    visto = {}
    comps, _ = f3d_nativo.leer_componentes(_f3d(tmp_path, world, malla, bloques), visto)
    assert len(comps) == 2 and visto["descartados"] == 1


def test_si_la_escena_tiene_un_cuerpo_sin_su_solido_no_se_descarta_nada(tmp_path):
    """Con un cuerpo de la escena sin explicar no se puede saber cuál sobra: queda todo, como antes."""
    malla = _Malla()
    dos = _cuerpo(malla) + _cuerpo(malla)                            # el segundo no tiene sólido propio
    world = _nodo(0x10, 0xC0, _matriz(), _nodo(0x11, 0xC1, _matriz(2, 0, 0), dos))
    visto = {}
    comps, _ = f3d_nativo.leer_componentes(_f3d(tmp_path, world, malla, _bloque_con_un_cuerpo_viejo()), visto)
    assert len(comps) == 2 and visto["descartados"] == 0


def test_dos_componentes_iguales_hechos_a_mano_entran_los_dos(tmp_path):
    """Copiar/pegar un componente como nuevo deja dos bloques BREP idénticos: el lector descarta uno y la escena sigue
    teniendo dos componentes (sale de revisar `EXTRUSOR XOX.f3z`: 36 componentes en la escena y 35 bloques)."""
    malla = _Malla()
    uno = _nodo(0x11, 0xC1, _matriz(2, 0, 0), _cuerpo(malla))
    otro = _nodo(0x12, 0xC2, _matriz(0, 3, 0), _cuerpo(malla))             # otro contenido (no es una copia ligera)
    cubo = _sab(_sab_cubo().r)
    f3d = _f3d(tmp_path, _nodo(0x10, 0xC0, _matriz(), uno + otro), malla,
               [(_CARPETA + "BREP.aaaa.smbh", cubo), (_CARPETA + "BREP.bbbb.smbh", cubo)])
    partes, avisos = f3d_nativo.leer(f3d)
    assert avisos == []
    assert sorted(_centro(p).round(3).tolist() for p, _ in partes) == [[5, 35, 5], [25, 5, 5]]


# ---------------------------------------------------------------- un archivo hostil no cuelga la app
def _anidado(profundidad):
    """Cada nivel tiene un componente y una copia suya, y adentro del primero el nivel siguiente: 2^n ocurrencias."""
    def nivel(k):
        if k == profundidad:
            return b""
        c = 0xC000 + k
        return (_nodo(0x1000 + 2 * k, c, _matriz(1, 0, 0), nivel(k + 1))
                + _nodo(0x1001 + 2 * k, c, _matriz(0, 1, 0)))
    return _nodo(0x10, 0xC0, _matriz(), nivel(0))


def test_copias_anidadas_pasan_el_tope_y_el_archivo_abre_con_aviso(tmp_path):
    mundo = _anidado(40)                                          # 2^40 marcos sin el tope; ~100 KB
    with pytest.raises(ValueError, match="demasiadas copias"):
        f3d_escena.Escena(mundo, b"").marcos()
    t0 = time.perf_counter()
    partes, avisos = f3d_nativo.leer(_f3d(tmp_path, mundo, _Malla()))
    assert time.perf_counter() - t0 < 5.0
    assert len(partes) == 1 and _centro(partes[0][0]) == pytest.approx([5, 5, 5], abs=1e-3)
    assert any("No se pudo leer la posición" in a and "demasiadas copias" in a for a in avisos)


def test_muchas_etiquetas_suelta_no_son_cuadraticas():
    t0 = time.perf_counter()
    with pytest.raises(ValueError, match="demasiados componentes"):
        f3d_escena.Escena(_s("Instance") * (f3d_escena.NODOS_MAX + 1), b"")
    mundo = _s("Instance") * f3d_escena.NODOS_MAX                    # sin ninguna matriz: antes cada una recorría todo
    assert f3d_escena.Escena(mundo, b"").nodos == []
    assert time.perf_counter() - t0 < 5.0


def test_nodos_sin_cabecera_no_recorren_todo_el_archivo():
    cola = b"".join(_matriz() + _id(i) + _s("Instance") for i in range(1, 2001))
    t0 = time.perf_counter()
    e = f3d_escena.Escena(cola + b"\x00" * 5_000_000, b"")           # sin SingleNodeWorld: antes ~25 s
    assert len(e.nodos) == 2000 and all(n["C"] is None for n in e.nodos)
    assert time.perf_counter() - t0 < 5.0


def test_caras_que_apuntan_a_la_misma_malla_no_se_decodifican_mil_veces():
    malla = _Malla()
    una = _cuerpo(malla)                                             # el cubo honesto: 6 mallas distintas
    registro = _Malla().cara(0, 0)
    tramposo = b"".join(_s("Face") + b"\x00" * 30 + registro + b"\x00" * 20 for _ in range(500)) + _s("Body") + b"\x00" * 45
    e = f3d_escena.Escena(_nodo(0x10, 0xC0, _matriz(), una + tramposo), bytes(malla.datos))
    honesto, aliasado = e.cuerpos
    assert honesto["vol_mm3"] == pytest.approx(1000.0)
    assert aliasado["vol_mm3"] is None                               # pasó el tope de vértices: no se mide


# ---------------------------------------------------------------- el documento
def test_abrir_guarda_la_copia_como_cita_y_reabre_igual(tmp_path):
    f3d = _ensamble(tmp_path)
    doc, _ = documento_desde_archivo(f3d)
    cuerpos = doc.operaciones[0].p["cuerpos"]
    assert "brep" in cuerpos[0] and "matriz" in cuerpos[0]
    assert cuerpos[1].get("ref") == cuerpos[0]["id"] and "brep" not in cuerpos[1]         # no repite el B-rep
    formas = [c.forma for c in doc.estado_final.cuerpos.values()]
    assert len(formas) == 2 and formas[0].IsPartner(formas[1])
    assert [_centro(f).round(3).tolist() for f in formas] == [[25, 5, 5], [-5, 35, 5]]
    ruta = tmp_path / "ensamble.omnicad"
    proyecto.guardar(doc, ruta)
    abierto = proyecto.abrir(ruta)
    otras = [c.forma for c in abierto.estado_final.cuerpos.values()]
    assert [_centro(f).round(3).tolist() for f in otras] == [[25, 5, 5], [-5, 35, 5]] and otras[0].IsPartner(otras[1])


def test_la_operacion_base_sin_matriz_ni_ref_sigue_igual(tmp_path):
    """Un .f3d de una sola pieza (o un .omnicad viejo) no trae "matriz" ni "ref"."""
    f3d = _zip_f3d(tmp_path / "pieza.f3d", [(_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r))])
    doc, _ = documento_desde_archivo(f3d)
    (c,) = doc.operaciones[0].p["cuerpos"]
    assert set(c) == {"id", "nombre", "tipo", "apariencia", "brep"}
    assert len(doc.estado_final.cuerpos) == 1


def test_operacion_base_rechaza_una_cita_o_una_matriz_mal_hechas(tmp_path):
    doc, _ = documento_desde_archivo(_ensamble(tmp_path))
    op = doc.operaciones[0]
    mala = op.copia()
    mala.p["cuerpos"][1]["ref"] = "op1.c99"
    r = doc.reemplazar(op.id, mala)
    assert r.estado == "error" and "ref" in r.mensaje
    otra = op.copia()
    otra.p["cuerpos"][0]["matriz"] = [1, 2, 3]
    assert doc.reemplazar(op.id, otra).estado == "error"
    rara = op.copia()
    rara.p["cuerpos"][0]["matriz"] = [0.0] * 16
    assert doc.reemplazar(op.id, rara).estado == "error"


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), 1e300, 1e9, True])
def test_operacion_base_rechaza_una_matriz_con_numeros_imposibles(tmp_path, valor):
    """Un .omnicad de otro con NaN o un número absurdo dejaba un cuerpo con caja (nan, …) y rompía la vista."""
    doc, _ = documento_desde_archivo(_ensamble(tmp_path))
    op = doc.operaciones[0]
    mala = op.copia()
    mala.p["cuerpos"][0]["matriz"][3] = valor
    r = doc.reemplazar(op.id, mala)
    assert r.estado == "error" and "matriz" in r.mensaje


# ---------------------------------------------------------------- la API
def test_inspect_f3d_cuenta_cuerpos_volumen_y_copias(tmp_path):
    s = api.Sesion()
    r = api.llamar(s, "inspect_f3d", {"path": str(_ensamble(tmp_path))})
    assert r["ok"], r
    d = r["result"]
    assert d["bodies_stored"] == 1 and d["bodies_placed"] == 2
    assert d["volume_stored_mm3"] == pytest.approx(1000.0) and d["volume_placed_mm3"] == pytest.approx(2000.0)
    assert d["components_moved"] == 1 and d["components_with_copies"] == 1 and d["unplaced_bodies"] == 0
    assert d["scene"]["nodes"] == 3 and d["scene"]["copies"] == 1
    (c,) = d["components"]
    assert c["copies"] == 2 and c["positions_mm"] == [[20.0, 0.0, 0.0], [0.0, 30.0, 0.0]] and c["rotated"]
    assert api.llamar(s, "inspect_f3d", {"path": str(tmp_path / "no_existe.f3d")})["error_kind"] == "FILE_NOT_FOUND"
    assert api.llamar(s, "inspect_f3d", {"path": str(tmp_path / "x.step")})["error_kind"] == "UNSUPPORTED_FILE_TYPE"


def test_open_document_e_insert_file_traen_las_copias(tmp_path):
    f3d = _ensamble(tmp_path)
    s = api.Sesion()
    assert api.llamar(s, "open_document", {"path": str(f3d)})["ok"]
    assert len(s.doc.estado_final.cuerpos) == 2
    r = api.llamar(s, "insert_file", {"path": str(f3d)})
    assert r["ok"] and len(r["result"]["new_bodies"]) == 2


# ---------------------------------------------------------------- piezas espejo (upgrades3)
class _EscenaFalsa:
    """Lo que `asignar` lee de una escena: nodos, cuerpos con su malla medida y las matrices de cada componente."""

    def __init__(self, nodos, cuerpos, marcos):
        self.nodos, self.cuerpos, self._marcos = nodos, cuerpos, marcos

    def marcos(self):
        return self._marcos


def _traslacion(x):
    M = np.eye(4)
    M[0, 3] = x
    return M


def test_dos_piezas_espejo_con_la_misma_caja_y_volumen_no_se_cruzan():
    """Una escuadra izquierda y una derecha: misma caja, mismo volumen, centro de masa a un lado u otro. El emparejado
    tiene que dar a cada componente SU pieza (antes, a igual puntaje, ganaba el orden de los bloques)."""
    caja = (np.zeros(3), np.full(3, 10.0))
    nodos = [{"primario": 0}, {"primario": 1}]
    cuerpos = [{"nodo": 0, "caras": 8, "vol_mm3": 500.0, "lo": caja[0], "hi": caja[1], "centro": np.array([3.0, 5, 5])},
               {"nodo": 1, "caras": 8, "vol_mm3": 500.0, "lo": caja[0], "hi": caja[1], "centro": np.array([7.0, 5, 5])}]
    marcos = {0: [_traslacion(100.0)], 1: [_traslacion(-100.0)]}

    def solido(bloque, centro):
        return {"bloque": bloque, "tipo": "solido", "caras": 8, "lo": caja[0], "hi": caja[1], "caja": lambda: caja,
                "vol": lambda: 500.0, "centro": lambda: centro}
    derecha, izquierda = solido(0, (7.0, 5, 5)), solido(1, (3.0, 5, 5))     # el bloque 0 es la pieza del componente 1
    matrices, _ = f3d_escena.asignar(_EscenaFalsa(nodos, cuerpos, marcos), [derecha, izquierda])
    assert matrices[0][0][0, 3] == pytest.approx(-100.0) and matrices[1][0][0, 3] == pytest.approx(100.0)


def test_la_escena_mide_el_centro_de_masa_de_la_malla():
    malla = _Malla()
    e = f3d_escena.Escena(_nodo(0x10, 0xC0, _matriz(), _cuerpo(malla)), bytes(malla.datos))
    assert e.cuerpos[0]["centro"] == pytest.approx([5, 5, 5], abs=1e-6)       # el cubo de 1 cm, en mm


# ---------------------------------------------------------------- nombres (upgrades3, P11.a d)
_FLUJO = "FusionAssetName[Active]/FusionDesignSegmentType1/BulkStream.dat"


def _con_flujo(tmp_path, previo, entre=None):
    """Ensamble con el flujo de diseño: `previo` es el texto que Fusion escribió antes del bloque BREP.aaaa.smbh (y
    `entre`, otro texto en medio)."""
    malla = _Malla()
    cubo = _nodo(0x11, 0xC1, _matriz(2, 0, 0), _cuerpo(malla))
    copia = _nodo(0x12, 0xC1, _matriz(0, 3, 0, giro_z=90))
    flujo = (b"\x00" * 30 + _s(previo) + b"\x00\x00\x03\x00\x00\x00370" + b"\x00" * 300
             + (_s(entre) + b"\x00" * 40 if entre else b"") + _s("BREP.aaaa.smbh"))
    return _zip_f3d(tmp_path / "con_nombre.f3d", [
        (_CARPETA + "BREP.aaaa.smbh", _sab(_sab_cubo().r)),
        ("FusionAssetName[Active]/" + _ESCENA + "world", _nodo(0x10, 0xC0, _matriz(), cubo + copia)),
        ("FusionAssetName[Active]/" + _ESCENA + "Fusion_mesh_000", bytes(malla.datos)), (_FLUJO, flujo)])


def test_el_nombre_del_componente_sale_del_flujo_de_diseno(tmp_path):
    """Como en la cartera de ejemplo («Pernos», «Panel», «Asa (1)»…: los de Fusion): el registro anterior al bloque."""
    f3d = _con_flujo(tmp_path, "Perno M3")
    comps, _ = f3d_nativo.leer_componentes(f3d)
    assert comps[0]["nombre"] == "Perno M3"
    doc, _ = documento_desde_archivo(f3d)
    assert [c.nombre for c in doc.estado_final.cuerpos.values()] == ["Perno M3:1", "Perno M3:2"]
    r = api.llamar(api.Sesion(), "inspect_f3d", {"path": str(f3d)})
    assert r["ok"] and r["result"]["components"][0]["name"] == "Perno M3"


@pytest.mark.parametrize("previo", ["PrismOpaque", "00000000-0000-0000-0000-000000000000", "BREP.bbbb.smb", "1_1513"])
def test_si_lo_que_precede_no_es_un_nombre_no_se_inventa(tmp_path, previo):
    """Así guarda Fusion los componentes que vienen de un STEP (el extrusor de ejemplo): material, GUID o boceto."""
    comps, _ = f3d_nativo.leer_componentes(_con_flujo(tmp_path, previo))
    assert comps[0]["nombre"] is None
    doc, _ = documento_desde_archivo(_con_flujo(tmp_path, previo))
    assert all(c.nombre.startswith("con_nombre") for c in doc.estado_final.cuerpos.values())


def test_un_texto_separado_del_bloque_por_el_de_un_boceto_no_es_su_nombre(tmp_path):
    """El extrusor de ejemplo: «CrearComponentes» (una operación), el BREP.*.smb del boceto y recién el bloque."""
    comps, _ = f3d_nativo.leer_componentes(_con_flujo(tmp_path, "CrearComponentes", entre="BREP.cccc.smb"))
    assert comps[0]["nombre"] is None
