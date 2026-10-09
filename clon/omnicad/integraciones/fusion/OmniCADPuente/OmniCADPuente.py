# -*- coding: utf-8 -*-
"""
OmniCADPuente: complemento de Fusion 360 que deja a OmniCAD abrir archivos .f3d/.f3z.

Parte de OmniCAD (GPL-3.0 o posterior). Escrito desde cero con la API pública de Fusion
(adsk.core / adsk.fusion); no contiene código ni recursos de Autodesk.

Qué hace: al arrancar Fusion escucha pedidos en 127.0.0.1 (puerto libre) y deja el puerto y una clave al azar en
`puente_fusion.json` (%LOCALAPPDATA%/OmniCAD, la carpeta que lee `omnicad/io_archivos/puente_fusion.py`).
Cada pedido de conversión abre el archivo en un documento nuevo, exporta STEP a una carpeta temporal, lee los
parámetros de usuario y los cuerpos (nombre, componente, volumen y caja, para controlar la conversión) y cierra
el documento sin guardar. La API de Fusion solo se puede usar desde su hilo principal: el servidor HTTP corre en
otro hilo y le pasa cada pedido con un evento propio (`fireCustomEvent`).

Lo instala `omnicad setup --cliente fusion --aplicar` en la carpeta AddIns del usuario.
"""
import json
import os
import secrets
import shutil
import tempfile
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import adsk.core
    import adsk.fusion
except ImportError:        # fuera de Fusion (pruebas de OmniCAD): solo se usan las partes sin `adsk`
    adsk = None

VERSION = 1
EVENTO = "OmniCADPuente.pedido"
TIEMPO_INICIO_S = 60       # para que Fusion EMPIECE a atender un pedido
TIEMPO_MAXIMO_S = 600      # para que lo termine (un ensamblaje grande tarda)
LARGO_MAXIMO = 64 * 1024
EXTENSIONES = (".f3d", ".f3z")
VARIABLE_CARPETA = "OMNICAD_PUENTE_FUSION_DIR"

_activo = {}               # lo que tiene que seguir vivo mientras corre el complemento (servidor, manejadores)


# ---------------------------------------------------------------- archivo de descubrimiento
def carpeta_info():
    """La misma regla que `puente_fusion.carpeta_info` de OmniCAD (no se puede importar desde Fusion)."""
    propia = os.environ.get(VARIABLE_CARPETA)
    if propia:
        return Path(propia)
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / "OmniCAD"


def ruta_info():
    return carpeta_info() / "puente_fusion.json"


def escribir_info(puerto, token):
    carpeta = carpeta_info()
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / f"puente_fusion.{os.getpid()}.tmp"
    temporal.write_text(json.dumps({"puerto": puerto, "token": token, "pid": os.getpid(), "version": VERSION}),
                        encoding="utf-8")
    os.replace(temporal, ruta_info())


def borrar_info():
    """Borra el archivo solo si es de este proceso (otro Fusion abierto puede haberlo escrito después)."""
    try:
        if json.loads(ruta_info().read_text(encoding="utf-8")).get("pid") == os.getpid():
            ruta_info().unlink()
    except (OSError, ValueError, AttributeError):
        pass


# ---------------------------------------------------------------- servidor HTTP (sin adsk)
class Servidor:
    """HTTP en 127.0.0.1 que pasa cada pedido a `atender(pedido) -> dict`. Exige la clave en `X-OmniCAD-Token`
    (un navegador no puede mandar esa cabecera a otro origen sin permiso, y el servidor no lo da)."""

    def __init__(self, atender, token=None):
        self.atender = atender
        self.token = token or secrets.token_hex(16)
        servidor = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _responder(self, codigo, datos):
                cuerpo = json.dumps(datos).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def _autorizado(self):
                if secrets.compare_digest(self.headers.get("X-OmniCAD-Token", ""), servidor.token):
                    return True
                self._responder(403, {"ok": False, "mensaje": "Clave del puente inválida."})
                return False

            def do_GET(self):
                if not self._autorizado():
                    return
                if self.path != "/estado":
                    self._responder(404, {"ok": False, "mensaje": f"No existe {self.path}."})
                    return
                self._responder(200, servidor.atender({"accion": "estado"}))

            def do_POST(self):
                if not self._autorizado():
                    return
                if self.path != "/convertir":
                    self._responder(404, {"ok": False, "mensaje": f"No existe {self.path}."})
                    return
                largo = int(self.headers.get("Content-Length") or 0)
                if largo <= 0 or largo > LARGO_MAXIMO:
                    self._responder(413, {"ok": False, "mensaje": "Pedido vacío o demasiado grande."})
                    return
                try:
                    datos = json.loads(self.rfile.read(largo).decode("utf-8"))
                except ValueError:
                    self._responder(400, {"ok": False, "mensaje": "El pedido no es JSON."})
                    return
                ruta = datos.get("ruta") if isinstance(datos, dict) else None
                if not isinstance(ruta, str) or not ruta:
                    self._responder(400, {"ok": False, "mensaje": "Falta «ruta»."})
                    return
                self._responder(200, servidor.atender({"accion": "convertir", "ruta": ruta}))

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.http.daemon_threads = True
        self.puerto = self.http.server_address[1]
        self._hilo = threading.Thread(target=self.http.serve_forever, name="OmniCADPuente", daemon=True)

    def iniciar(self, publicar=True):
        self._hilo.start()
        if publicar:
            escribir_info(self.puerto, self.token)

    def detener(self):
        borrar_info()
        self.http.shutdown()
        self.http.server_close()


def f3d_principal(f3z, carpeta):
    """Un .f3z es un paquete ZIP con los diseños (.f3d), dibujos (.f2d) y un `DesignDescription.json` que dice quién
    referencia a quién. Extrae a `carpeta` y devuelve la ruta del diseño principal: el .f3d que ningún otro .f3d
    referencia (el ensamblaje de arriba); si hay varios, el más grande."""
    import zipfile
    with zipfile.ZipFile(f3z) as z:
        nombres = [n for n in z.namelist() if n.lower().endswith(".f3d") and "/" not in n.strip("/")]
        if not nombres:
            raise ValueError("El .f3z no trae ningún diseño .f3d.")
        try:
            objetos = json.loads(z.read("DesignDescription.json"))["designDescription"]["designGraphs"][0]["designObjects"]
        except (KeyError, IndexError, ValueError, TypeError):
            objetos = []
        disenos = {o.get("id"): o for o in objetos if o.get("contentType") == "f3d"}
        referidos = {i for o in disenos.values() for ref in o.get("references") or [] for i in ref.get("ids") or []}
        arriba = [o.get("relativePath") for i, o in disenos.items() if i not in referidos]
        candidatos = [n for n in nombres if n in arriba] or nombres
        elegido = max(candidatos, key=lambda n: z.getinfo(n).file_size)
        try:
            z.extractall(carpeta, [n for n in z.namelist() if n.lower().endswith(".f3d")])
        except NotImplementedError:
            raise ValueError("El .f3z usa una compresión que este Python no lee (Zstandard).") from None
    return os.path.join(carpeta, elegido)


def validar_ruta(ruta):
    """Solo se abren archivos de Fusion que existan (el puente no abre cualquier cosa que le pidan)."""
    p = Path(ruta)
    if p.suffix.lower() not in EXTENSIONES:
        return f"Solo se convierten archivos .f3d o .f3z (llegó «{p.name}»)."
    if not p.is_file():
        return f"No existe el archivo: {ruta}"
    return None


# ---------------------------------------------------------------- pedidos al hilo principal de Fusion
class Despachador:
    """Llamado desde el hilo HTTP: dispara el evento propio y espera a que el hilo principal lo atienda."""

    def __init__(self, app, funcion):
        self.app, self.funcion, self._pendientes = app, funcion, {}
        self.version_fusion = app.version
        self.evento = app.registerCustomEvent(EVENTO)
        self.manejador = _crear_manejador(self)
        self.evento.add(self.manejador)

    def __call__(self, pedido):
        if pedido["accion"] == "estado":
            return {"ok": True, "version": VERSION, "fusion": self.version_fusion}
        ident = uuid.uuid4().hex
        empezo, listo = threading.Event(), threading.Event()
        self._pendientes[ident] = {"pedido": pedido, "empezo": empezo, "listo": listo, "resultado": None}
        # Ojo: fireCustomEvent devuelve False aunque el evento SÍ llega (Fusion 2704): no se mira su resultado.
        self.app.fireCustomEvent(EVENTO, json.dumps({"id": ident}))
        if not empezo.wait(TIEMPO_INICIO_S):
            self._pendientes.pop(ident, None)       # Fusion está ocupado (diálogo o comando abierto) o el evento murió
            return {"ok": False, "mensaje": f"Fusion no atendió el pedido en {TIEMPO_INICIO_S} s: puede tener un diálogo "
                                            "o un comando abierto. Cerralo y probá de nuevo; si sigue, reiniciá Fusion."}
        if not listo.wait(TIEMPO_MAXIMO_S):
            self._pendientes.pop(ident, None)
            return {"ok": False, "mensaje": f"Fusion no terminó en {TIEMPO_MAXIMO_S} s."}
        return self._pendientes.pop(ident)["resultado"]

    def procesar(self, info):
        """En el hilo principal de Fusion."""
        entrada = self._pendientes.get(json.loads(info).get("id"))
        if entrada is None:
            return
        entrada["empezo"].set()
        try:
            entrada["resultado"] = self.funcion(entrada["pedido"])
        except Exception as e:  # noqa: BLE001 — cualquier falla vuelve como mensaje, nunca tumba a Fusion
            entrada["resultado"] = {"ok": False, "mensaje": f"{type(e).__name__}: {e}"}
            _registrar(traceback.format_exc())
        finally:
            entrada["listo"].set()

    def detener(self):
        self.evento.remove(self.manejador)
        self.app.unregisterCustomEvent(EVENTO)


def _crear_manejador(despachador):
    class Manejador(adsk.core.CustomEventHandler):
        def notify(self, args):
            despachador.procesar(args.additionalInfo)
    return Manejador()


def _registrar(texto):
    try:
        adsk.core.Application.get().log(f"OmniCADPuente: {texto}")
    except Exception:  # noqa: BLE001 — sin registro no pasa nada
        pass


# ---------------------------------------------------------------- conversión (API pública de Fusion)
def convertir(pedido):
    """Abre el .f3d/.f3z en un documento nuevo, exporta STEP y devuelve parámetros y cuerpos. Unidades de la API:
    cm, cm³ y radianes; se mandan en mm y mm³ salvo `valor` de los parámetros (lo convierte OmniCAD)."""
    ruta = pedido["ruta"]
    problema = validar_ruta(ruta)
    if problema:
        return {"ok": False, "mensaje": problema}
    carpeta = tempfile.mkdtemp(prefix="omnicad_fusion_")
    resultado = None
    try:
        resultado = _convertir(ruta, carpeta)
        return resultado
    finally:
        if not (resultado or {}).get("ok"):     # en una falla OmniCAD no va a leer nada: se limpia acá
            shutil.rmtree(carpeta, ignore_errors=True)


def _convertir(ruta, carpeta):
    if ruta.lower().endswith(".f3z"):           # la importación de archivo de Fusion solo acepta .f3d
        try:
            ruta = f3d_principal(ruta, os.path.join(carpeta, "f3z"))
        except (ValueError, OSError) as e:
            return {"ok": False, "mensaje": f"No se pudo leer el .f3z: {e}"}
    app = adsk.core.Application.get()
    gestor = app.importManager
    documento = gestor.importToNewDocument(gestor.createFusionArchiveImportOptions(ruta))
    if documento is None:
        return {"ok": False, "mensaje": "Fusion no pudo abrir el archivo."}
    try:
        diseno = adsk.fusion.Design.cast(documento.products.itemByProductType("DesignProductType"))
        if diseno is None:
            return {"ok": False, "mensaje": "El archivo no tiene un diseño 3D."}
        step = os.path.join(carpeta, "modelo.step")
        exportar = diseno.exportManager
        if not exportar.execute(exportar.createSTEPExportOptions(step, diseno.rootComponent)) or not os.path.isfile(step):
            return {"ok": False, "mensaje": "Fusion no pudo exportar el STEP."}
        parametros = [{"nombre": p.name, "expresion": p.expression, "unidad": p.unit, "valor": p.value,
                       "comentario": p.comment} for p in diseno.userParameters]
        raiz = diseno.rootComponent
        cuerpos = [_cuerpo(c, "") for c in raiz.bRepBodies]
        componentes = []
        for ocurrencia in raiz.allOccurrences:
            componentes.append(ocurrencia.fullPathName)
            cuerpos += [_cuerpo(c, ocurrencia.fullPathName) for c in ocurrencia.bRepBodies]
        return {"ok": True, "step": step, "documento": documento.name, "parametros": parametros,
                "cuerpos": cuerpos, "componentes": componentes}
    finally:
        documento.close(False)


def _cuerpo(cuerpo, componente):
    caja = cuerpo.boundingBox
    return {"nombre": cuerpo.name, "componente": componente, "visible": bool(cuerpo.isVisible),
            "volumen_mm3": cuerpo.volume * 1000.0 if cuerpo.isSolid else None,
            "caja_mm": [[caja.minPoint.x * 10, caja.minPoint.y * 10, caja.minPoint.z * 10],
                        [caja.maxPoint.x * 10, caja.maxPoint.y * 10, caja.maxPoint.z * 10]]}


# ---------------------------------------------------------------- entrada y salida del complemento
def run(context):
    try:
        despachador = Despachador(adsk.core.Application.get(), convertir)
        servidor = Servidor(despachador)
        servidor.iniciar()
        _activo.update(despachador=despachador, servidor=servidor)
        _registrar(f"escuchando en 127.0.0.1:{servidor.puerto}")
    except Exception:  # noqa: BLE001 — un error al arrancar se anota y Fusion sigue
        _registrar(traceback.format_exc())


def stop(context):
    try:
        if "servidor" in _activo:
            _activo.pop("servidor").detener()
        if "despachador" in _activo:
            _activo.pop("despachador").detener()
    except Exception:  # noqa: BLE001
        _registrar(traceback.format_exc())
