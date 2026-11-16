# -*- coding: utf-8 -*-
"""B-562: en Windows un archivo abierto por otro proceso (el trabajador, el antivirus, el Explorador) da PermissionError
(WinError 32). Cada punto del intercambio por archivos lo aguanta: lo auxiliar (`avance`, `recibido`, `despierto`) no
voltea el cálculo; lo esencial se reintenta y, si sigue trabado, la tarea la hace un hijo nuevo en otra carpeta; si igual
falla, el aviso es de un renglón y sin ruta. Se prueba sobre un cuerpo ya modificado (un cilindro con chaflán)."""
import json
import os
import time
from pathlib import Path

import pytest

from omnicad import api, reintentos
from omnicad.api import protocolo_puente as proto
from omnicad.io_archivos import proyecto
from omnicad.nucleo import aislado
from omnicad.timeline.documento import Documento, ErrorDocumento

TRABAJADOR, TAREA, PREVIA = "omnicad_trabajador_", "omnicad_tarea_", "omnicad_previa_"


@pytest.fixture(autouse=True)
def _sin_pausas(monkeypatch):
    monkeypatch.setattr(reintentos, "PAUSAS", (0, 0, 0))
    yield
    aislado.cerrar_trabajador()          # el siguiente test arranca con un trabajador limpio


def _receta():
    s = api.Sesion()
    for nombre, args in (("create_cylinder", {"radius": 5, "height": 30}), ("chamfer", {"edges": ">Z", "distance": 1})):
        assert api.llamar(s, nombre, args)["ok"]
    return {"receta": s.doc.a_dict(), "sin_memoria": True}


def _trabar(monkeypatch, objeto, metodo, cumple, veces=None):
    """`objeto.metodo` da PermissionError cuando `cumple(args)`: las primeras `veces` (None: siempre). Devuelve la lista
    de las rutas que trabó."""
    original, trabadas = getattr(objeto, metodo), []

    def trabado(*a, **k):
        if cumple(a) and (veces is None or len(trabadas) < veces):
            trabadas.append(Path(a[0]))
            raise PermissionError(13, "El proceso no tiene acceso al archivo porque está siendo utilizado", str(a[0]))
        return original(*a, **k)
    monkeypatch.setattr(objeto, metodo, trabado)
    return trabadas


def _en(carpeta, nombre):
    return lambda a: a[0].name == nombre and a[0].parent.name.startswith(carpeta)


def _calcular():
    salida = aislado.correr_json("recalcular_documento", _receta(), 120)
    assert salida and "_fallo" not in salida
    return salida


def test_b562_reintentar_repite_solo_permissionerror():
    llamadas = []
    with pytest.raises(PermissionError):
        reintentos.reintentar(lambda: llamadas.append(1) or (_ for _ in ()).throw(PermissionError(13, "ocupado")))
    assert len(llamadas) == 4                               # 1 + 3 reintentos
    with pytest.raises(FileNotFoundError):
        reintentos.reintentar(lambda: llamadas.append(1) or (_ for _ in ()).throw(FileNotFoundError(2, "no está")))
    assert len(llamadas) == 5                               # sin reintentos: repetirlo da lo mismo


# ------------------------------------------------------------------------------------------------- el padre
@pytest.mark.parametrize("metodo,nombre", [("unlink", "avance"), ("unlink", "recibido")])
def test_b562_lo_auxiliar_trabado_no_voltea_el_calculo(monkeypatch, metodo, nombre):
    trabadas = _trabar(monkeypatch, Path, metodo, lambda a: a[0].name == nombre)
    _calcular()
    assert trabadas


def test_b562_la_barra_con_avance_trabado_queda_sin_dato(monkeypatch):
    _calcular()
    _trabar(monkeypatch, Path, "read_text", lambda a: a[0].name == "avance")
    assert aislado.avance() is None


@pytest.mark.parametrize("metodo,carpeta,nombre", [
    ("write_text", TRABAJADOR, "args.json"), ("read_text", TRABAJADOR, "salida.json"),
    ("unlink", TRABAJADOR, "salida.json"), ("unlink", TRABAJADOR, "listo"),
    ("write_text", TAREA, "args.json"), ("read_text", TAREA, "salida.json")])
def test_b562_lo_esencial_trabado_un_rato_se_reintenta(monkeypatch, metodo, carpeta, nombre):
    if carpeta == TAREA:
        monkeypatch.setattr(aislado, "TRABAJADOR", False)     # el hijo de una sola tarea
    trabadas = _trabar(monkeypatch, Path, metodo, _en(carpeta, nombre), veces=2)
    _calcular()
    assert len(trabadas) == 2


@pytest.mark.parametrize("metodo,nombre", [("write_text", "args.json"), ("read_text", "salida.json")])
def test_b562_lo_esencial_trabado_siempre_lo_hace_un_hijo_nuevo_en_otra_carpeta(monkeypatch, metodo, nombre):
    trabadas = _trabar(monkeypatch, Path, metodo, _en(TRABAJADOR, nombre))
    leidas, leer = [], Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: leidas.append(self) or leer(self, *a, **k))
    _calcular()                                             # sin error ni aviso
    assert len(trabadas) == 4
    hijo = [p.parent for p in leidas if p.name == "salida.json" and p.parent.name.startswith(TAREA)]
    assert hijo and all(c != trabadas[0].parent for c in hijo)      # la respuesta vino de otra carpeta


def test_b562_si_no_puede_limpiar_su_carpeta_el_trabajador_se_cambia(monkeypatch):
    _trabar(monkeypatch, Path, "unlink", _en(TRABAJADOR, "listo"))
    _calcular()
    viejo = aislado._trabajador
    assert viejo is None or viejo.proceso.poll() is not None    # cerrado: el próximo pedido arranca otro
    monkeypatch.undo()
    monkeypatch.setattr(reintentos, "PAUSAS", (0, 0, 0))
    _calcular()


def _sondear(previa):
    limite = time.monotonic() + 120
    while (resultado := previa.sondear()) is None:
        assert time.monotonic() < limite
        time.sleep(0.05)
    assert "_fallo" not in resultado


def test_b562_la_previa_con_el_pedido_trabado_la_hace_un_hijo_nuevo(monkeypatch):
    _trabar(monkeypatch, Path, "write_text", _en(TRABAJADOR, "args.json"))
    previa = aislado.CalculoPendiente("recalcular_documento", _receta())
    assert previa.trabajador is None                        # no quedó colgada del trabajador
    _sondear(previa)


@pytest.mark.parametrize("metodo,nombre", [("write_text", "args.json"), ("read_text", "salida.json")])
def test_b562_la_previa_en_su_hijo_reintenta(monkeypatch, metodo, nombre):
    monkeypatch.setattr(aislado, "TRABAJADOR", False)
    trabadas = _trabar(monkeypatch, Path, metodo, _en(PREVIA, nombre), veces=2)
    _sondear(aislado.CalculoPendiente("recalcular_documento", _receta()))
    assert len(trabadas) == 2


def test_b562_errores_txt_trabado_no_tapa_el_motivo(monkeypatch, tmp_path):
    ruta = tmp_path / "errores.txt"
    ruta.write_bytes(b"algo")
    _trabar(monkeypatch, Path, "read_bytes", lambda a: a[0] == ruta)
    assert aislado._leer_errores(ruta) == b""


# ------------------------------------------------------------------------------------------------- el hijo
@pytest.fixture
def hijo(monkeypatch, tmp_path):
    """El hijo, en este proceso: su carpeta con el pedido, como la deja `enviar`, y una sola línea del padre."""
    monkeypatch.chdir(os.getcwd())                          # `_atender` vuelve a la raíz del repo al terminar
    for nombre in ("formas_enviadas", "carpeta_avance", "documento_vivo", "EN_HIJO"):
        monkeypatch.setattr(aislado, nombre, getattr(aislado, nombre))
    datos = dict(_receta(), _marca=None, _tope_mb=4096, _cwd=os.getcwd())
    (tmp_path / "args.json").write_text(json.dumps(datos, default=aislado._a_json), encoding="utf-8")
    monkeypatch.setattr(aislado, "pedidos_del_padre", lambda: iter([b"recalcular_documento\n"]))
    abiertos, abrir = [], Path.open
    monkeypatch.setattr(Path, "open", lambda self, *a, **k: abiertos.append(abrir(self, *a, **k)) or abiertos[-1])
    yield tmp_path
    for f in abiertos:          # `pila.txt`: el hijo real lo cierra al salir del proceso
        f.close()


@pytest.mark.parametrize("metodo,nombre,veces", [
    ("open", "pila.txt", 2), ("touch", "despierto", None), ("touch", "recibido", None), ("read_text", "args.json", 2),
    ("write_text", "salida.json", 2), ("touch", "listo", 2)])
def test_b562_el_trabajador_aguanta_cada_archivo_trabado(monkeypatch, hijo, metodo, nombre, veces):
    trabadas = _trabar(monkeypatch, Path, metodo, lambda a: a[0] == hijo / nombre, veces)
    aislado._trabajar(hijo)
    assert trabadas and (hijo / "listo").is_file()
    assert "_fallo" not in json.loads((hijo / "salida.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("metodo,nombre", [("read_text", "args.json"), ("write_text", "salida.json")])
def test_b562_el_hijo_de_una_tarea_aguanta_cada_archivo_trabado(monkeypatch, hijo, metodo, nombre):
    args = json.loads((hijo / "args.json").read_text(encoding="utf-8"))
    for clave in ("_marca", "_tope_mb"):
        args.pop(clave)
    (hijo / "args.json").write_text(json.dumps(args), encoding="utf-8")
    trabadas = _trabar(monkeypatch, Path, metodo, lambda a: a[0] == hijo / nombre, veces=2)
    assert aislado.principal(["recalcular_documento", str(hijo)]) == 0
    assert len(trabadas) == 2 and "_fallo" not in json.loads((hijo / "salida.json").read_text(encoding="utf-8"))


def test_b562_un_hijo_que_cae_por_un_archivo_trabado_se_reconoce():
    assert isinstance(aislado._caida(1, b"Traceback...\nPermissionError: [WinError 32] ... 'C:\\x\\args.json'"),
                      aislado.ArchivoTrabado)


# ------------------------------------------------------------------------------------------------- el aviso
@pytest.mark.parametrize("error", [PermissionError(13, "ocupado", r"C:\Users\x\AppData\Local\Temp\omnicad_trabajador_0\avance"),
                                   aislado.ArchivoTrabado(), FileNotFoundError(2, "no está", r"C:\Temp\OmniCAD.exe")])
def test_b562_si_igual_falla_sale_en_un_renglon_sin_ruta(monkeypatch, error):
    def envuelto(*a, **k):        # como `_correr`: el OSError llega como causa de una TareaAislada con su ruta
        raise aislado.TareaAislada(f"el proceso aparte dejó un resultado ilegible ({error})") from error
    for causa in (lambda *a, **k: (_ for _ in ()).throw(error), envuelto)[:2 if isinstance(error, OSError) else 1]:
        monkeypatch.setattr(aislado, "correr_json", causa)
        with pytest.raises(ErrorDocumento) as e:
            Documento().calcular_aparte("recalcular_documento", {})
        texto = str(e.value)
        assert "\n" not in texto and "Temp" not in texto and len(texto) < 80
        assert ("ocupado" in texto) == (not isinstance(error, FileNotFoundError))   # no dice «ocupado» si no lo estaba


# ------------------------------------------------------------------------------------------------- la familia
def test_b562_guardar_con_el_proyecto_abierto_por_otro_programa(monkeypatch, tmp_path):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    cuenta = _trabar(monkeypatch, os, "replace", lambda a: str(a[1]).endswith(".omnicad"), veces=2)
    ruta = proyecto.guardar(s.doc, tmp_path / "pieza.omnicad")
    assert len(cuenta) == 2 and Path(ruta).is_file()
    copia = tmp_path / "pieza.autoguardado.omnicad"
    copia.write_bytes(b"x")
    cuenta = _trabar(monkeypatch, Path, "unlink", lambda a: a[0] == copia, veces=2)
    proyecto.suprimir_copia(copia)
    assert len(cuenta) == 2 and not copia.exists()


def test_b562_puente_json_leido_por_un_cliente_mientras_se_escribe(monkeypatch, tmp_path):
    ruta = tmp_path / "puente.json"
    datos = {"port": 1234, "token": "t", "pid": 1}
    cuenta = _trabar(monkeypatch, os, "replace", lambda a: Path(a[1]) == ruta, veces=2)
    proto.escribir_info(ruta, datos)
    lecturas = _trabar(monkeypatch, Path, "read_text", lambda a: a[0] == ruta, veces=2)
    assert proto.leer_info(ruta) == datos and len(cuenta) == len(lecturas) == 2
