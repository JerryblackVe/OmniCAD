"""B-196: Barrer y Labio revisan si el resultado se cruza consigo mismo; desde B-462 es un error, como en Fusion."""
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


def _exigir_error(r, que, causa):
    assert not r["ok"], r
    mensaje = r["mensaje"].lower()
    assert "se autointerseca" in mensaje and que in mensaje and causa in mensaje, r


def _sin_revisar():
    """Sin el análisis: así se crea el barrido cruzado (B-462 lo rechaza) y se usa su geometría real."""
    return patch.object(rev, "_autointersecciones_seguras", return_value=(0, [], True))


def _cruzado():
    s = _preparar_barrido(True)
    with _sin_revisar():
        return s, _barrer(s)


def test_barrido_cruzado_falla_aunque_el_kernel_lo_de_valido():
    s, r = _cruzado()
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert rev._autointersecciones_seguras(forma, 1, 5.0)[0] == 4
    assert math.isclose(geo.volumen(forma), math.pi * (30 + 2 * math.hypot(30, 20)), rel_tol=1e-6)
    s = _preparar_barrido(True)
    _exigir_error(api.llamar(s, "sweep", {"sketch": "Perfil", "path_sketch": "Ruta", "operation": "new_body"}),
                  "barrido", "ruta")
    assert not s.doc.estado_final.cuerpos


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
    cruzada = _forma(*_cruzado())
    s = _preparar_barrido()
    _r(s, "create_box", length=2, width=2, height=2, name="Taco")
    with patch.object(sc, "barrer_cuerpo", return_value=cruzada):
        r = api.llamar(s, "sweep", {"sweep_bodies": "Taco", "path_sketch": "Ruta", "orientation": "parallel"})
    _exigir_error(r, "barrido", "cuerpo")


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
    return api.llamar(s, "create_lip_groove", dict( body="Base", edges="|X and >Z and <Y", lip_type=tipo,
              groove_body="Tapa" if tipo == "lip_and_groove" else None,
              width=1, height=1.5, clearance=0.1, direction="Z"))


def test_labio_y_ranura_revisan_el_resultado():
    """La geometría cruzada es real; se sustituye solo la salida del núcleo de Labio."""
    cruzada = _forma(*_cruzado())
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        funcion = "labio_y_ranura" if tipo == "lip_and_groove" else "labio_ranura"
        resultado = {"labio": cruzada, "ranura": cruzada} if tipo == "lip_and_groove" else cruzada
        with patch.object(sc, funcion, return_value=resultado):
            r = _labio(s, tipo)
        _exigir_error(r, "labio" if tipo != "groove" else "ranura", "ancho")
        assert "se autointerseca (3)" in r["mensaje"], r


def test_labio_y_ranura_normales_no_avisan():
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        r = _labio(s, tipo)
        assert r["ok"], r
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


def test_recalcular_y_editar_otro_paso_no_vuelven_a_analizar():
    s = _preparar_barrido()
    with patch.object(rev, "_autointersecciones_seguras", wraps=rev._autointersecciones_seguras) as analisis:
        uid = _barrer(s)["result"]["feature"]["id"]
        assert analisis.call_count == 1
        for _ in range(2):
            _r(s, "recompute_all")
            assert s.doc.resultado(uid).estado == "ok"
        hechos = analisis.call_count
        caja = _r(s, "create_box", length=2, width=2, height=2)["result"]["feature"]["id"]
        _r(s, "edit_feature", feature=caja, params={"height": "3 mm"})
        assert analisis.call_count == hechos                 # el barrido no se recalcula: su resultado ya estaba revisado


def test_previa_no_analiza_y_aceptar_y_editar_si_aunque_haya_previa():
    s, r = _cruzado()
    uid = r["result"]["feature"]["id"]
    receta = s.doc.operacion(uid).a_dict()
    s.doc.eliminar(uid)
    op = operacion_desde_dict(receta)
    with patch.object(rev, "_autointersecciones_seguras", wraps=rev._autointersecciones_seguras) as analisis:
        s.doc.previsualizar(op)
        assert analisis.call_count == 0
        assert s.doc.agregar(op).estado == "error"
        assert analisis.call_count == 1
        nueva = op.copia()
        nueva.p["distancia"] = "0.1"
        s.doc.previsualizar(nueva, s.doc.indice(uid))
        assert analisis.call_count == 1
        assert s.doc.reemplazar(uid, nueva).estado == "ok"
        assert analisis.call_count == 2


def test_previa_aislada_no_analiza_y_aceptar_no_reusa_su_resultado_sin_revision():
    """Ejecuta el protocolo real del hijo en el proceso actual para contar el análisis."""
    s, r = _cruzado()
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
        assert s.doc.agregar(op).estado == "error"
        assert analisis.call_count == 1
        nueva = op.copia()
        nueva.p["distancia"] = "0.1"
        s.doc.previsualizar(nueva, s.doc.indice(uid))     # el hijo puede ponerse al día con la receta (cálculo real)
        hechos = analisis.call_count
        assert s.doc.reemplazar(uid, nueva).estado == "ok"
        assert analisis.call_count > hechos                # aceptar analiza: no reusa la previa sin revisión


def test_b358_deshacer_y_rehacer_vuelven_a_revisar():
    """B-358: el paso que vuelve con deshacer o rehacer se rearma de la receta y se revisa; antes volvía en «ok»
    callado. El barrido cruzado se creó sin el análisis: al volver, el análisis lo encuentra y es un error."""
    s, r = _cruzado()
    uid = r["result"]["feature"]["id"]
    _r(s, "delete_feature", feature=uid)
    _r(s, "undo")
    assert s.doc.resultado(uid).estado == "error" and "se autointerseca" in s.doc.resultado(uid).mensaje


def test_b358_un_cambio_de_parametro_vuelve_a_revisar():
    """B-358: con t = 0 el barrido sale sano; con t = 30 el análisis lo encuentra cruzado (se simula la cuenta, que
    depende del parámetro) y falla, y al volver a 0 queda sano."""
    s = _preparar_barrido()
    _r(s, "create_parameter", name="t", expression="0 deg")
    cruce = {"mensaje": "Autointersección entre cara y cara."}
    cuenta = lambda forma, *a, **k: (24, [cruce] * 24, True) if s.doc.parametros.valores()["t"] else (0, [], True)  # noqa: E731
    with patch.object(rev, "_autointersecciones_seguras", side_effect=cuenta):
        uid = _r(s, "sweep", sketch="Perfil", path_sketch="Ruta", operation="new_body",
                 twist_angle="t")["result"]["feature"]["id"]
        assert "autointersec" not in s.doc.resultado(uid).mensaje
        r = api.llamar(s, "set_parameter", {"name": "t", "expression": "30 deg"})
        assert "se autointerseca (24)" in (r.get("mensaje") or s.doc.resultado(uid).mensaje), r
        _r(s, "set_parameter", name="t", expression="0 deg")
        assert s.doc.resultado(uid).estado == "ok"


def test_b358_labio_no_culpa_al_labio_de_lo_que_el_cuerpo_ya_traia():
    """B-358: un labio sano no avisa por las autointersecciones que el cuerpo ya traía (antes: «El labio de «Base»
    quedó con 212 autointersecciones»). El análisis cuenta 212 antes y después: el labio no agregó ninguna."""
    s = _preparar_labio()
    with patch.object(rev, "_autointersecciones_seguras", return_value=(212, [], True)):
        r = _r(s, "create_lip_groove", body="Base", edges="|X and <Z and <Y", lip_type="lip", width=1, height=1.5,
               direction="Z", reverse=True)
    assert not any("autointersec" in a for a in r["avisos"]), r["avisos"]

def test_b859_labio_y_ranura_avisan_si_antes_no_llega():
    """Sin conteo previo no se atribuyen los cruces del resultado al paso."""
    cruce = {"mensaje": "Autointersección entre cara y cara."}
    vencido = {"mensaje": "No se revisaron las autointersecciones: plazo agotado."}
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        cuentas = [(1, [cruce], True), (None, [vencido], False)]
        if tipo == "lip_and_groove":
            cuentas += [(0, [], True)]       # la ranura del segundo cuerpo sigue revisándose
        with patch.object(rev, "_autointersecciones_seguras", side_effect=cuentas) as analisis:
            r = _labio(s, tipo)
        assert r["ok"], r
        assert "Autointersecciones previas sin revisar." in r["avisos"], r
        assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "aviso"
        assert analisis.call_count == len(cuentas)
        forma = s.cuerpo("Base").forma
        esperado = 16000 - 40 * 1.1 * 1.6 if tipo == "groove" else 16000 + 40 * 1 * 1.5
        assert geo.es_valida(forma)
        assert math.isclose(geo.volumen(forma), esperado, rel_tol=1e-6)
