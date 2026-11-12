"""B-196: Barrer y Labio avisan si el resultado se cruza consigo mismo."""
import math
from unittest.mock import patch

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rev
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import aislado
from omnicad.timeline.calculo_aislado import _leer_calculo
from omnicad.timeline.operaciones import operacion_desde_dict


def _r(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r


def _preparar_barrido(cruzado=False):
    s = api.Sesion()
    _r(s, "create_sketch", plane="YZ", name="Perfil")
    _r(s, "draw_circle", radius=1, sketch="Perfil")
    _r(s, "create_sketch", plane="XY", name="Ruta")
    puntos = [(0, 0), (30, 0), (0, 20), (20, -10)] if cruzado else [(0, 0), (30, 0)]
    for a, b in zip(puntos[:-1], puntos[1:], strict=True):
        _r(s, "draw_line", sketch="Ruta", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])
    return s


def _barrer(s):
    return _r(s, "sweep", sketch="Perfil", path_sketch="Ruta", operation="new_body")


def _forma(s, r):
    return s.cuerpo(r["result"]["bodies_created"][0]["id"]).forma


def _exigir_aviso(s, r, que, causa):
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "aviso", r
    aviso = " ".join(r["avisos"]).lower()
    assert "autointerseccion" in aviso and que in aviso and causa in aviso, r


def test_barrido_cruzado_avisa_aunque_el_kernel_lo_de_valido():
    s = _preparar_barrido(True)
    r = _barrer(s)
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert rev._autointersecciones_seguras(forma, 1, 5.0)[0] == 4
    assert math.isclose(geo.volumen(forma), math.pi * (30 + 2 * math.hypot(30, 20)), rel_tol=1e-6)
    _exigir_aviso(s, r, "barrido", "ruta")


def test_barrido_normal_sigue_ok_sin_aviso_y_con_el_mismo_volumen():
    s = _preparar_barrido()
    r = _barrer(s)
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert math.isclose(geo.volumen(forma), math.pi * 30, rel_tol=1e-6)
    assert r["avisos"] == []
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"


def test_barrido_de_cuerpo_tambien_revisa_el_resultado():
    """Inyecta una forma cruzada real: no depende de cómo una las copias Solid Sweep."""
    origen = _preparar_barrido(True)
    cruzada = _forma(origen, _barrer(origen))
    s = _preparar_barrido()
    _r(s, "create_box", length=2, width=2, height=2, name="Taco")
    with patch.object(sc, "barrer_cuerpo", return_value=cruzada):
        r = _r(s, "sweep", sweep_bodies="Taco", path_sketch="Ruta", orientation="parallel")
    _exigir_aviso(s, r, "barrido", "cuerpo")


def test_barrido_de_cuerpo_normal_no_avisa():
    s = _preparar_barrido()
    _r(s, "create_box", length=2, width=2, height=2, name="Taco")
    r = _r(s, "sweep", sweep_bodies="Taco", path_sketch="Ruta", orientation="parallel")
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert math.isclose(geo.volumen(forma), 2 * 2 * (2 + 30), rel_tol=1e-6)
    assert r["avisos"] == []
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"


def _preparar_labio(combinado=False):
    s = api.Sesion()
    _r(s, "create_box", length=40, width=20, height=20, anchor="corner", name="Base")
    if combinado:
        _r(s, "create_box", length=40, width=20, height=20, z=20, anchor="corner", name="Tapa")
    return s


def _labio(s, tipo):
    return _r(s, "create_lip_groove", body="Base", edges="|X and >Z and <Y", lip_type=tipo,
              groove_body="Tapa" if tipo == "lip_and_groove" else None,
              width=1, height=1.5, clearance=0.1, direction="Z")


def test_labio_y_ranura_revisan_el_resultado():
    """La geometría cruzada es real; se sustituye solo la salida del núcleo de Labio."""
    origen = _preparar_barrido(True)
    cruzada = _forma(origen, _barrer(origen))
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        funcion = "labio_y_ranura" if tipo == "lip_and_groove" else "labio_ranura"
        resultado = {"labio": cruzada, "ranura": cruzada} if tipo == "lip_and_groove" else cruzada
        with patch.object(sc, funcion, return_value=resultado):
            r = _labio(s, tipo)
        _exigir_aviso(s, r, "labio" if tipo == "lip" else "ranura", "ancho")
        aviso = " ".join(r["avisos"])
        assert aviso.count("quedó con 4 autointersecciones") == (2 if tipo == "lip_and_groove" else 1), r
        if tipo == "lip_and_groove":
            assert "El labio de «Base»" in aviso and "La ranura de «Tapa»" in aviso, r


def test_labio_y_ranura_normales_no_avisan():
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        r = _labio(s, tipo)
        forma = s.cuerpo("Base").forma
        esperado = 16000 - 40 * 1.1 * 1.6 if tipo == "groove" else 16000 + 40 * 1 * 1.5
        assert geo.es_valida(forma)
        assert math.isclose(geo.volumen(forma), esperado, rel_tol=1e-6)
        if tipo == "lip_and_groove":
            tapa = s.cuerpo("Tapa").forma
            assert geo.es_valida(tapa)
            assert math.isclose(geo.volumen(tapa), 16000 - 40 * 1.1 * 1.6, rel_tol=1e-6)
        assert r["avisos"] == []
        assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"


def test_barrido_con_revision_agotada_tambien_avisa():
    s = _preparar_barrido()
    with patch.object(rev, "_autointersecciones_seguras", return_value=(
            None, [{"mensaje": "No se revisaron las autointersecciones: plazo agotado."}], False)):
        r = _barrer(s)
    _exigir_aviso(s, r, "autointersecciones", "plazo agotado")


def test_recalcular_conserva_el_aviso_y_editar_otro_paso_no_vuelve_a_analizar():
    s = _preparar_barrido(True)
    with patch.object(rev, "_autointersecciones_seguras", wraps=rev._autointersecciones_seguras) as analisis:
        r = _barrer(s)
        uid = r["result"]["feature"]["id"]
        aviso = s.doc.resultado(uid).mensaje
        assert analisis.call_count == 1
        for _ in range(2):
            _r(s, "recompute_all")
            assert s.doc.resultado(uid).estado == "aviso"
            assert s.doc.resultado(uid).mensaje == aviso
        hechos = analisis.call_count
        caja = _r(s, "create_box", length=2, width=2, height=2)["result"]["feature"]["id"]
        _r(s, "edit_feature", feature=caja, params={"height": "3 mm"})
        assert analisis.call_count == hechos                 # el barrido no se recalcula: su resultado ya traía el aviso
        assert s.doc.resultado(uid).mensaje == aviso
        _r(s, "edit_feature", feature=uid, params={"distancia": "0.1"})
        assert s.doc.resultado(uid).estado == "ok"


def test_previa_no_analiza_y_aceptar_y_editar_si_aunque_haya_previa():
    s = _preparar_barrido(True)
    r = _barrer(s)
    uid = r["result"]["feature"]["id"]
    receta = s.doc.operacion(uid).a_dict()
    s.doc.eliminar(uid)
    op = operacion_desde_dict(receta)
    with patch.object(rev, "_autointersecciones_seguras", wraps=rev._autointersecciones_seguras) as analisis:
        s.doc.previsualizar(op)
        assert analisis.call_count == 0
        assert s.doc.agregar(op).estado == "aviso"
        assert analisis.call_count == 1
        nueva = op.copia()
        nueva.p["distancia"] = "0.1"
        s.doc.previsualizar(nueva, s.doc.indice(uid))
        assert analisis.call_count == 1
        assert s.doc.reemplazar(uid, nueva).estado == "ok"
        assert analisis.call_count == 2


def test_previa_aislada_no_analiza_y_aceptar_no_reusa_su_resultado_sin_revision():
    """Ejecuta el protocolo real del hijo en el proceso actual para contar el análisis."""
    s = _preparar_barrido(True)
    r = _barrer(s)
    uid = r["result"]["feature"]["id"]
    op = s.doc.operacion(uid).copia()
    s.doc.eliminar(uid)

    def solicitar(tarea, datos):
        with patch.object(aislado, "EN_HIJO", True), patch.object(aislado, "formas_enviadas", None):
            return _leer_calculo(getattr(aislado, "_" + tarea)(**datos))

    with (patch.object(s.doc, "_prevuelo_corresponde", return_value=True),
          patch.object(s.doc, "_solicitar_calculo", side_effect=solicitar),
          patch.object(rev, "_autointersecciones_seguras", wraps=rev._autointersecciones_seguras) as analisis):
        s.doc.previsualizar(op)
        assert analisis.call_count == 0
        assert s.doc.agregar(op).estado == "aviso"
        assert analisis.call_count == 1
        aviso = s.doc.resultado(uid).mensaje
        _r(s, "recompute_all")
        assert s.doc.resultado(uid).mensaje == aviso
        nueva = op.copia()
        nueva.p["distancia"] = "0.1"
        s.doc.previsualizar(nueva, s.doc.indice(uid))     # el hijo puede ponerse al día con la receta (cálculo real)
        hechos = analisis.call_count
        assert s.doc.reemplazar(uid, nueva).estado == "ok"
        assert analisis.call_count > hechos                # aceptar analiza: no reusa la previa sin revisión


def test_b358_deshacer_y_rehacer_conservan_el_aviso():
    """B-358: el paso que vuelve con deshacer o rehacer se rearma de la receta; antes volvía en «ok» callado."""
    s = _preparar_barrido(True)
    uid = _barrer(s)["result"]["feature"]["id"]
    aviso = s.doc.resultado(uid).mensaje
    _r(s, "delete_feature", feature=uid)
    _r(s, "undo")
    assert (s.doc.resultado(uid).estado, s.doc.resultado(uid).mensaje) == ("aviso", aviso)
    _r(s, "undo")                                      # deshace el barrido
    _r(s, "redo")
    assert (s.doc.resultado(uid).estado, s.doc.resultado(uid).mensaje) == ("aviso", aviso)


def test_b358_un_cambio_de_parametro_vuelve_a_revisar():
    """B-358: con t = 2 las copias del patrón no se pisan; con t = 6 sí (24 autointersecciones, B-167), y al volver a
    2 el aviso se va."""
    s = api.Sesion()
    _r(s, "create_sketch")
    _r(s, "draw_rectangle", sketch="Boceto1", x1=0, y1=0, x2=20, y2=15)
    _r(s, "create_base_flange", sketch="Boceto1", thickness=0.8)
    _r(s, "create_parameter", name="t", expression="2 mm")
    uid = _r(s, "create_geometric_pattern", faces=["Cuerpo1/F6"], operation="join", distance=5, size1="t",
             size2="t")["result"]["feature"]["id"]
    assert "autointersec" not in s.doc.resultado(uid).mensaje
    _r(s, "set_parameter", name="t", expression="6 mm")
    assert "autointersecciones" in s.doc.resultado(uid).mensaje
    _r(s, "set_parameter", name="t", expression="2 mm")
    assert "autointersec" not in s.doc.resultado(uid).mensaje


def test_b358_labio_no_culpa_al_labio_de_lo_que_el_cuerpo_ya_traia():
    """B-358: el patrón unido con copias que se pisan deja la base cruzada (B-167); un labio sano en el borde de abajo
    no la empeora y no avisa (antes: «El labio de «Base» quedó con 212 autointersecciones»)."""
    s = _preparar_labio()
    _r(s, "create_geometric_pattern", faces=[">Z"], body="Base", operation="join", distance=5, size1=6, size2=6)
    assert rev._autointersecciones_seguras(s.cuerpo("Base").forma, 1, 5.0)[0] > 0
    r = _r(s, "create_lip_groove", body="Base", edges="|X and <Z and <Y", lip_type="lip", width=1, height=1.5,
           direction="Z", reverse=True)
    assert not any("autointersec" in a for a in r["avisos"]), r["avisos"]
