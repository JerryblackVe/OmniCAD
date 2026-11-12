"""Lo que pidió la tarea del 2026-11-04: valores de fábrica, texto útil, trazas, topes y pausa por disco."""
import json
import os
import time

import pytest

from omnicad import registro_uso as ru
from omnicad.registro_uso import ganchos


def eventos(carpeta):
    return [json.loads(l) for p in sorted(carpeta.glob("sesion_*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


def dar_viejo(p, dias):
    os.utime(p, (time.time() - dias * 86400, time.time() - dias * 86400))


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    ru.aplicar(ru.FABRICA)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    yield
    ru.configurar(False)
    ru.ultimo = None
    ru.aplicar(ru.FABRICA)


def test_valores_de_fabrica_y_rangos():
    assert ru.FABRICA["retencion_dias"] == 7
    assert ru.FABRICA["tope_total_mb"] == 150
    assert ru.FABRICA["tope_capturas_mb"] == 50
    assert ru.FABRICA["disco_libre_min_gb"] == 2
    assert ru.FABRICA["memoria_cada_s"] == 30
    assert ru.FABRICA["detallado"] is False and ru.FABRICA["captura_error"] is False
    assert ru.RANGOS["retencion_dias"] == (1, 90)
    assert ru.RANGOS["tope_total_mb"] == (20, 2000)
    assert ru.RANGOS["tope_capturas_mb"] == (0, 500)
    assert ru.RANGOS["disco_libre_min_gb"] == (0.5, 50)
    assert ru.RANGOS["memoria_cada_s"] == (5, 300)


@pytest.mark.parametrize("clave,valor", [("retencion_dias", 0), ("retencion_dias", 91), ("retencion_dias", 1),
                                         ("retencion_dias", 90), ("tope_total_mb", 19), ("tope_total_mb", 20),
                                         ("tope_capturas_mb", 501), ("disco_libre_min_gb", 0.4),
                                         ("disco_libre_min_gb", 50.1), ("memoria_cada_s", 4), ("memoria_cada_s", 301),
                                         ("retencion_dias", "siete"), ("tope_total_mb", None)])
def test_normalizar_rechaza_lo_invalido(clave, valor):
    if valor in (1, 90, 20, 50, 50.0):
        assert ru.normalizar({clave: valor})[clave] == pytest.approx(valor)
    else:
        with pytest.raises(ValueError):
            ru.normalizar({clave: valor})


@pytest.mark.parametrize("escrito,esperado", [("7 dias", 7), ("7", 7), (" 7 días ", 7), ("2,5", 2.5),
                                              ("0.5 GB", 0.5), ("150 MB", 150), ("veinte", None), ("", None),
                                              ("-3", None), ("1e9", None), ("2.", None), (".5", None),
                                              ("2,,5", None), ("2.5.5", None)])
def test_parse_numero_acepta_unidades_y_coma(escrito, esperado):
    valor = ru.parse_numero(escrito)
    if esperado is None:
        assert valor is None
    else:
        assert valor == pytest.approx(esperado)


def test_nombres_reales_en_lugar_de_sin_clave():
    from types import SimpleNamespace
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication, QMenu
    from omnicad.ui.registro_uso import RegistroVentana
    QApplication.instance() or QApplication([])
    app = SimpleNamespace(_ultima_accion="")
    accion = QAction("Ajustar a la vista")     # ni clave ni objectName: entra su texto
    menu = QMenu()
    menu.addAction(accion)
    menu.setActiveAction(accion)
    ru.configurar(True)
    try:
        RegistroVentana.eventFilter(app, menu, QEvent(QEvent.MouseButtonRelease))
        assert app._ultima_accion == "Ajustar a la vista"
    finally:
        ru.configurar(False)


@pytest.mark.parametrize("herramienta,accion", [("extrude", "api.extrude"), ("", "Preferencias"), (None, "Preferencias")])
def test_b322_bloqueo_ui_identifica_la_api_en_curso(monkeypatch, herramienta, accion):
    from types import SimpleNamespace
    from omnicad.ui import bench, registro_uso
    from omnicad.ui.registro_uso import RegistroVentana

    doble = SimpleNamespace(
        _ultima_accion="Preferencias", _ultimo=0.5, _pausado=False,
        _capturar_error=lambda: None, _comando=lambda: "",
        ventana=SimpleNamespace(panel=None), _rss=2**20, _muestra=1.0)
    if herramienta is not None:
        doble.herramienta_api = herramienta
    monkeypatch.setattr(registro_uso, "time", SimpleNamespace(perf_counter=lambda: 1.0))
    monkeypatch.setattr(bench, "memoria_mb", lambda: (1, 0))
    monkeypatch.setattr(ru, "toca_podar", lambda: False)
    ru.configurar(True)
    try:
        RegistroVentana._latido(doble)
        ru.activo.cola.join()
        bloqueos = [e["datos"] for e in eventos(ru.carpeta()) if e["tipo"] == "bloqueo_ui"]
        assert len(bloqueos) == 1
        assert bloqueos[0]["duracion_ms"] == pytest.approx(450)
        assert bloqueos[0]["accion"] == accion
    finally:
        ru.configurar(False)


def test_texto_no_privado_completo_y_recortado(tmp_path):
    largo = "E" * 700
    r = ru.Registro(destino=tmp_path, datos={"proyecto": "x"})
    r.emitir("error", {"origen": "api", "comando": "extruir", "excepcion": "ErrorAPI", "mensaje": largo})
    r.emitir("op_ejecutada", {"paso": "Placa base", "tipo_op": "extrusion", "mensaje": "sin contacto", "exito": False})
    r.emitir("boceto_cota", {"tipo": "distancia", "valor": "20 mm"})
    r.cerrar()
    es = eventos(tmp_path)
    error = next(e for e in es if e["tipo"] == "error")
    assert len(error["datos"]["mensaje"]) == 500 and error["datos"]["mensaje"].startswith("EEEE")
    op = next(e for e in es if e["tipo"] == "op_ejecutada")
    assert op["datos"]["paso"] == "Placa base" and op["datos"]["mensaje"] == "sin contacto"
    cota = next(e for e in es if e["tipo"] == "boceto_cota")
    assert cota["datos"]["valor"] == "20 mm"


def test_rutas_de_casa_y_largo_seguiran_redactados(tmp_path):
    from pathlib import Path
    casa = str(Path.home()).replace("\\", "/")
    r = ru.Registro(destino=tmp_path)
    r.emitir("error", {"origen": "operacion", "mensaje": f"No se pudo abrir {casa}/privado/pii.step"})
    r.emitir("comando_abierto", {"comando": "texto", "valores": {"contenido": "hola" * 400}})
    r.emitir("comando_cambio", {"comando": "extruir", "valores": {"perfil": ["1000000000000000000000000000000"],
                                                                  "sentido": "dos sentidos", "direccion": "Hacia Arriba",
                                                                  "alto": 5.0}})
    r.emitir("bloqueo_ui", {"duracion_ms": 512.0, "comando": "", "accion": ""})
    r.cerrar()
    es = {e["tipo"]: e for e in eventos(tmp_path)}
    assert casa.split("/")[-1].lower() not in json.dumps(list(es), ensure_ascii=False).lower()
    assert es["error"]["datos"]["mensaje"] == "No se pudo abrir ~/privado/pii.step"
    assert es["comando_abierto"]["datos"]["valores"]["contenido"] == {"longitud": 1600}
    assert es["comando_cambio"]["datos"]["valores"]["perfil"] == [{"longitud": 31}]
    assert es["comando_cambio"]["datos"]["valores"]["sentido"] == "dos sentidos"
    assert es["comando_cambio"]["datos"]["valores"]["direccion"] == "Hacia Arriba"   # etiqueta de una lista fija
    assert es["comando_cambio"]["datos"]["valores"]["alto"] == 5.0
    assert es["bloqueo_ui"]["datos"]["comando"] == ""           # vacío sigue vacío: {"longitud": 0} era ruido
    assert es["bloqueo_ui"]["datos"]["accion"] == ""


def test_detalizado_abre_el_texto_libre_y_los_nombres(tmp_path):
    ru.aplicar({"detallado": True})
    r = ru.Registro(destino=tmp_path)
    r.emitir("comando_abierto", {"comando": "boletin", "valores": {"nota": "la nota libre", "ruta": "C:/a/b/p.txt"}})
    r.emitir("marca", {"label": "etiqueta ia"})
    r.cerrar()
    es = {e["tipo"]: e for e in eventos(tmp_path)}
    assert es["comando_abierto"]["datos"]["valores"]["nota"] == "la nota libre"
    assert isinstance(es["comando_abierto"]["datos"]["valores"]["ruta"], dict)   # rutas: ni en detallado


def test_traza_con_archivo_y_linea_hasta_15():
    ru.configurar(True)
    try:
        def hondo(n):
            if n:
                return hondo(n - 1)
            raise ValueError("fondo")
        try:
            hondo(20)
        except ValueError as e:
            ganchos.error(e, origen="ui")
        ru.activo.cola.join()
        errs = [ev["datos"] for ev in eventos(ru.carpeta()) if ev["tipo"] == "error" and ev["datos"].get("origen") == "ui"]
        print("ERRORES:", json.dumps(errs, ensure_ascii=False)[:400])
        traza = errs[-1]["traza"]
        assert len(traza) == 15, json.dumps(traza)[:300]
        assert all("archivo" in m and "funcion" in m and m["linea"] for m in traza)
        assert str(traza[-1].get("archivo", traza[-1])).replace("\\", "/").startswith("tests/")
        assert not any("site-packages" in str(m) for m in traza)
    finally:
        ru.configurar(False)


def test_tope_de_capturas_y_umbral_bajo_al_achicar(tmp_path):
    r = ru.Registro(destino=tmp_path, tope_total=20 * 2**20, tope_capturas=5 * 2**20)
    r.cola.join()                                       # la cabecera ya está escrita
    sesion = r.archivos[0]
    for i in range(3):
        (tmp_path / f"marca_{i}a.png").write_bytes(b"x" * 2_100_000)   # 6,3 MB > 5 MB
        time.sleep(0.02)
    r.emitir("clic", {})
    r.cerrar()
    r.podar()
    assert sesion.exists()
    restantes = list(tmp_path.glob("marca_*.png"))
    assert restantes and len(restantes) < 3          # se poda al tope (5 MB), no todo
    ru.aplicar({"retencion_dias": 1, "tope_total_mb": 150})
    viejo = tmp_path / "sesion_vieja_vieja_0001.jsonl"
    viejo.write_bytes(b"{}\n")
    dar_viejo(viejo, 3)
    ru.podar(tmp_path)
    assert not viejo.exists()


def test_disco_libre_bajo_pausa_y_avisa(tmp_path, monkeypatch):
    from omnicad.registro_uso import sistema
    monkeypatch.setattr(sistema, "disco_libre", lambda ruta: 1)
    r = ru.Registro(destino=tmp_path)
    r._libre, r._libre_lectura = None, 0.0
    assert r.estado()["paused_low_disk"] is True
    assert r.emitir("clic", {}) is None
    monkeypatch.setattr(sistema, "disco_libre", lambda ruta: 10**12)
    r._libre_lectura = 0.0                                   # sin esperar los 30 s de la lectura cacheada
    assert r.estado()["paused_low_disk"] is False
    assert r.emitir("clic", {}) is not None
    r.cerrar()


def test_100000_eventos_no_crecen_mas_de_20_mb(tmp_path):
    from omnicad.ui.bench import memoria_mb
    ru.aplicar({"tope_total_mb": 2000})
    r = ru.Registro(destino=tmp_path)
    antes = memoria_mb()[0]
    for tanda in range(100):
        for i in range(1000):
            r.emitir("op_ejecutada", {"paso": f"p{i}", "duracion_ms": i, "exito": True})
        r.cola.join()
    despues = memoria_mb()[0]
    r.cerrar()
    assert despues - antes < 20
    assert r.descartados == 0


@pytest.mark.parametrize("detallado,esperado", [(False, {"longitud": 4}), (True, "hola")])
def test_un_dialogo_distingue_opcion_de_texto_libre(tmp_path, detallado, esperado):
    from types import SimpleNamespace
    from omnicad.ui.comando import Opciones, PanelComando, Texto
    ru.aplicar({"detallado": detallado})
    ru.configurar(True)
    try:
        panel = SimpleNamespace(
            campos=[Texto("nota_libre", "Nota"), Opciones("tipo", "Tipo", {"solida": ("Extruir", "x"),
                                                                           "delgada": ("Delgada", "y")})],
            valores={"nota_libre": "hola", "tipo": "delgada"}, ctx=SimpleNamespace(op=None),
            comando=SimpleNamespace(CLAVE="extruir"), _uso_inicio=None, _uso_cambios=0)
        PanelComando._registrar_uso(panel, "comando_abierto")
        ru.activo.cola.join()
        e = [x for x in eventos(ru.carpeta()) if x["tipo"] == "comando_abierto"][-1]
        assert e["datos"]["valores"]["nota_libre"] == esperado    # texto libre: largo, o guardado si es detallado
        assert e["datos"]["valores"]["tipo"] == "delgada"         # la opción elegida, siempre por su clave
    finally:
        ru.configurar(False)
        ru.ultimo = None


def test_el_aspecto_elegido_se_registra_por_su_nombre(tmp_path):
    """B-199 (video del 2026-11-05): Aspecto aceptado quedaba con «aspecto»: null aunque se había elegido negro."""
    from types import SimpleNamespace
    from omnicad.ui.comando import PanelComando, Personalizado
    ru.configurar(True)
    try:
        panel = SimpleNamespace(campos=[Personalizado("aspecto", "", None, None)],
                                valores={"aspecto": {"id": "asp1", "nombre": "Plástico - Brillante (Negro)", "color": [0, 0, 0]}},
                                ctx=SimpleNamespace(op=None), comando=SimpleNamespace(CLAVE="aspecto"),
                                _uso_inicio=None, _uso_cambios=0)
        PanelComando._registrar_uso(panel, "comando_aceptado")
        ru.activo.cola.join()
        e = [x for x in eventos(ru.carpeta()) if x["tipo"] == "comando_aceptado"][-1]
        assert e["datos"]["valores"]["aspecto"] == "Plástico - Brillante (Negro)"
    finally:
        ru.configurar(False)
        ru.ultimo = None


def test_nombres_de_pasos_y_cuerpos_se_guardan(tmp_path):
    r = ru.Registro(destino=tmp_path)
    r.emitir("op_ejecutada", {"paso": "op3", "nombre": "Extruir la placa", "tipo_op": "extrusion",
                              "cuerpos": ["Cuerpo1", "Placa base"], "duracion_ms": 12.0, "exito": True,
                              "mensaje": ""})
    r.cerrar()
    e = [x for x in eventos(tmp_path) if x["tipo"] == "op_ejecutada"][0]["datos"]
    assert e["nombre"] == "Extruir la placa"                 # el nombre real del paso, no su largo
    assert e["cuerpos"] == ["Cuerpo1", "Placa base"]
    assert e["mensaje"] == ""


def test_cada_error_deja_pediendo_una_captura(tmp_path):
    ru.aplicar({"detallado": True, "captura_error": True})
    r = ru.Registro(destino=tmp_path)
    seq = r.emitir("error", {"origen": "operacion", "mensaje": "no se pudo extruir"})
    assert r._captura_pendiente == seq                             # la ventana la toma en el próximo latido
    r._captura_pendiente = None
    r.emitir("clic", {})
    assert r._captura_pendiente is None                            # solo los errores piden foto
    r.cerrar()
    ru.aplicar({"captura_error": False})
    r2 = ru.Registro(destino=tmp_path)
    r2.emitir("error", {"origen": "operacion", "mensaje": "otro"})
    assert r2._captura_pendiente is None                           # apagada la opción, no se pide
    r2.cerrar()


def test_podar_al_arrancar_y_cada_hora(tmp_path, monkeypatch):
    ru.marcar_podar()
    r = ru.Registro(destino=tmp_path)
    r.cola.join()
    curso = r.archivos[0]
    viejo = tmp_path / "sesion_vieja_vieja_0001.jsonl"
    viejo.write_bytes(b"{}\n")
    dar_viejo(viejo, 30)
    ru.podar(tmp_path, sesion_id="noexiste")   # arranque de un proceso nuevo: se poda todo lo viejo
    assert not viejo.exists()
    ru.podar(tmp_path)               # y la sesión en curso nunca se borra
    assert curso.exists()
    r.cerrar()
    monkeypatch.setattr(ru, "ULTIMO_PODA", time.monotonic() - 3601)
    assert ru.toca_podar()           # pasó la hora: toca podar de nuevo
    ru.marcar_podar()
    assert not ru.toca_podar()


def test_otro_proceso_no_borra_el_archivo_que_se_esta_escribiendo(tmp_path):
    """Sin sesión propia (CLI u otra ventana) la poda respeta la parte MÁS NUEVA: la que otro proceso tiene abierta.
    Aquí esa parte sola pasa del tope: sin la protección se la llevaría (en Linux un archivo abierto se borra)."""
    viva = tmp_path / "sesion_viva_viva_0002.jsonl"
    viva.write_bytes(b"x" * (21 * 2**20))                     # 21 MB con un tope de 20 MB
    ru.aplicar({"retencion_dias": 7, "tope_total_mb": 20, "tope_capturas_mb": 0})
    ru.podar(tmp_path, sesion_id="la_de_otro_proceso")
    assert viva.exists()
    vieja = tmp_path / "sesion_vieja_vieja_0001.jsonl"
    vieja.write_bytes(b"x" * 1024)
    dar_viejo(vieja, 30)
    ru.podar(tmp_path, sesion_id="la_de_otro_proceso")
    assert not vieja.exists() and viva.exists()
