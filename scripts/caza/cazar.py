# -*- coding: utf-8 -*-
"""Cazador automático de errores de OmniCAD. Especificación: docs/plan_caza_errores.md.

Uso, desde clon/ con el Python del venv:
  ../scripts/caza/cazar.py rapida                 antes de una versión (10 min)
  ../scripts/caza/cazar.py noche --horas 7        búsqueda larga
  ../scripts/caza/cazar.py tema empalme           después de tocar una operación (5 a 15 min)
  ../scripts/caza/cazar.py repetir <firma>        comprueba un arreglo (segundos)

Sale con 0 si no hay hallazgos nuevos. Corre sin modelos ni red; hace fila con `scripts/turno.py` (uno a la vez, 3 GB).
Una corrida cortada sigue donde estaba: el avance vive en evidencias/caza/. `OMNICAD_CODIGO` apunta a otra copia de clon/."""
import argparse
import json
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from datetime import date
from pathlib import Path

from generador import CADENAS_REALES

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
ESTADO = Path(os.environ.get("OMNICAD_CAZA_ESTADO") or RAIZ / "evidencias" / "caza")
CONOCIDOS = AQUI / "conocidos.json"
CORPUS = RAIZ / "clon" / "tests" / "corpus_caza"

RELATIVAS = ("0.5m", "m-e", "m", "m+e", "1.1m", "2m", "10m")
EXTREMAS = ("0", "neg", "1e-6", "1e6")
GRAVEDAD = ("proceso", "memoria", "slot", "numeros", "geometria", "esperado", "identidad", "guardar", "deshacer", "recalcular",
            "exportar", "editar", "mover", "contrato", "rendimiento")
PIEZAS = ("vaciado", "extruido", "solido", "vaciado", "chapa", "malla", "vaciado", "superficie", "ensamble")
FORMATOS = (".omnicad", ".step", ".stl", ".dxf", ".svg", ".f3d")
UMBRAL_SEG = 0.25           # s: por debajo, el doble de tiempo es ruido de la PC
LARGOS = (1, 1, 2, 3, 4, 6, 8)   # pasos después de la pieza semilla: 3 a 12 en total, con muchas historias cortas
MAX_INFORME = 20
GUARDAR_CADA = 5            # s entre escrituras del avance
VECES = 3                   # una firma vista tantas veces ya no corta más cadenas en esta corrida
REINICIO = 40               # pedidos por proceso: las fugas de un caso no se acumulan
RAPIDA = {"B": 260, "A": 70, "C": 40, "D": 70, "E": 20}
CIERRE_RAPIDA = 80           # s para confirmar y reducir: lo que no entra queda listado sin confirmar
TEMA = {"B": 240, "A": 60}
REPARTO_NOCHE = {"B": 0.5, "A": 0.2, "C": 0.1, "D": 0.15, "E": 0.05}


def sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def guardar_json(ruta, datos):
    """Escritura atómica: un corte a la mitad no deja el avance roto."""
    temporal = Path(f"{ruta}.tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=0, default=str), encoding="utf-8")
    os.replace(temporal, ruta)


def leer_json(ruta, defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def firma_de(fallo):
    return f"{fallo['juez']}|{fallo.get('op', '')}|{fallo['kind']}"


class Trabajador:
    """Un proceso aislado con su carpeta de usuario temporal: nada toca los datos de Gerardo."""

    def __init__(self, guion="trabajador.py"):
        self.carpeta = tempfile.mkdtemp(prefix="caza_usuario_")
        local = Path(self.carpeta)
        for sub in ("local", "roaming", "casa"):
            (local / sub).mkdir()
        entorno = {**os.environ, "LOCALAPPDATA": str(local / "local"), "APPDATA": str(local / "roaming"),
                   "USERPROFILE": str(local / "casa"), "HOME": str(local / "casa"), "PYTHONIOENCODING": "utf-8",
                   "OMNICAD_AJUSTES_INI": str(local / "ajustes.ini"), "OMNICAD_REGISTRO_DIR": str(local / "registro"),
                   "OMNICAD_ASISTENTE_DIR": str(local / "chats"), "OMNICAD_SIN_ANIMACION": "1"}
        ESTADO.mkdir(parents=True, exist_ok=True)
        self.bitacora = ESTADO / f"bitacora_{guion}.log"
        self._log = open(self.bitacora, "wb")
        self.proc = subprocess.Popen([sys.executable, str(AQUI / guion)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self._log, env=entorno, encoding="utf-8", cwd=self.carpeta)
        self.cola = queue.Queue()
        self.pedidos = 0
        self.lector = threading.Thread(target=self._leer, daemon=True)
        self.lector.start()

    def _leer(self):
        for linea in self.proc.stdout:
            self.cola.put(linea)
        self.cola.put(None)

    def cerrar(self):
        if self.proc.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True) if os.name == "nt" \
                else self.proc.kill()
        self.proc.wait()
        try:
            self.proc.stdin.close()
        except OSError:                 # el proceso murió con datos sin leer
            pass
        self.lector.join(5)
        self.proc.stdout.close()
        self._log.close()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _caida(self, tipo, marca):
        """Fallo de proceso armado con la bitácora: el último paso y la última línea propia del rastro nativo."""
        texto = self.bitacora.read_bytes()[marca:].decode("utf-8", "replace")
        pasos = [json.loads(x[5:]) for x in texto.splitlines() if x.startswith("PASO ")]
        propias = re.findall(r'File "[^"]*omnicad[\\/]([^"]+)", line (\d+)', texto)
        donde = f"{Path(propias[0][0]).name}:{propias[0][1]}" if propias else ""
        op = pasos[-1]["tool"] if pasos else ""
        return {"fallo": {"juez": "proceso", "kind": f"{tipo}@{donde}" if donde else tipo, "op": op,
                          "detalle": texto[-400:]}, "receta": pasos, "avance": [], "caido": True}

    def pedir(self, pedido, plazo):
        self.pedidos += 1
        marca = self.bitacora.stat().st_size
        try:
            self.proc.stdin.write(json.dumps(pedido, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            linea = self.cola.get(timeout=plazo)
        except queue.Empty:
            self.cerrar()
            return self._caida("colgado", marca)
        except OSError:
            linea = None
        if linea is None:
            codigo = self.proc.wait()
            return self._caida(f"cierre_{codigo & 0xffffffff:x}", marca)
        respuesta = json.loads(linea)
        if "error_cazador" in respuesta:
            raise RuntimeError("Falla del cazador, no de OmniCAD:\n" + respuesta["error_cazador"])
        return respuesta


class Fuente:
    """Da un trabajador vivo y lo renueva cada REINICIO pedidos o después de una caída."""

    def __init__(self, guion="trabajador.py"):
        self.guion, self.actual = guion, None

    def pedir(self, pedido, plazo):
        if self.actual is None or self.actual.proc.poll() is not None or self.actual.pedidos >= REINICIO:
            self.cerrar()
            self.actual = Trabajador(self.guion)
        respuesta = self.actual.pedir(pedido, plazo)
        if respuesta.get("caido"):
            self.cerrar()
        return respuesta

    def cerrar(self):
        if self.actual:
            self.actual.cerrar()
        self.actual = None


class Cobertura:
    """Qué pares de operaciones y qué clases de valor ya corrieron: cada corrida arranca por lo que falta."""

    def __init__(self):
        self.ruta = ESTADO / "cobertura.json"
        d = leer_json(self.ruta, {})
        self.pares, self.clases = d.get("pares", {}), d.get("clases", {})
        self.fallas, self.herramientas = d.get("fallas", {}), d.get("herramientas", {})
        self.contratos, self.ventana = d.get("contratos", {}), d.get("ventana", {})

    def guardar(self):
        guardar_json(self.ruta, {"pares": self.pares, "clases": self.clases, "fallas": self.fallas,
                                 "herramientas": self.herramientas, "contratos": self.contratos,
                                 "ventana": self.ventana})

    def anotar(self, avance, sin_contexto=()):
        previa = None
        for a in avance:
            h = self.herramientas.setdefault(a["tool"], {"ok": 0, "error": 0, "sin_contexto": 0})
            h["ok" if a["ok"] else "error"] += 1
            if a.get("clase"):
                c = self.clases.setdefault(a["tool"], {})
                c[a["clase"]] = c.get(a["clase"], 0) + 1
            if a["ok"]:
                if previa:
                    par = f"{previa}>{a['tool']}"
                    self.pares[par] = self.pares.get(par, 0) + 1
                previa = a["tool"]
        for t in sin_contexto:
            self.herramientas.setdefault(t, {"ok": 0, "error": 0, "sin_contexto": 0})["sin_contexto"] += 1

    def plan(self, rng, nombres, foco, nucleo, largo):
        """Los próximos pasos: el par menos visto entre una muestra, a favor de lo que más falló."""
        pasos, previa = [], ""

        def peso(h):
            d = self.herramientas.get(h, {})
            sin_uso = d.get("sin_contexto", 0) >= 8 and not d.get("ok")     # este documento no le da con qué trabajar
            return min(self.pares.get(f"{previa}>{h}", 0), 3) - min(self.fallas.get(h, 0), 1) + 3 * sin_uso + rng.uniform(0, 4)
        for i in range(largo):
            lista = (foco or nucleo or nombres) if i == 0 or rng.random() < 0.6 else nombres
            h = min(rng.sample(lista, min(24, len(lista))), key=peso)
            vistas = self.clases.get(h, {})
            clases = RELATIVAS if rng.random() < 0.8 else EXTREMAS
            pasos.append((h, min(clases, key=lambda c: (vistas.get(c, 0), rng.random()))))
            previa = h
        return pasos


def reducir(fuente, receta, objetivo, plazo, pesado=False, ignorar=()):
    """Quita pasos y argumentos y simplifica números mientras siga fallando con la misma firma."""
    fin = time.monotonic() + plazo

    def falla(pasos):
        if time.monotonic() > fin:
            return False
        r = fuente.pedir({"tipo": "repetir", "pasos": pasos, "pesado": pesado, "ignorar": ignorar}, 40)
        return bool(r["fallo"]) and firma_de(r["fallo"]) == objetivo

    for _ in range(3):
        antes = len(receta)
        for i in range(len(receta) - 1, -1, -1):
            prueba = receta[:i] + receta[i + 1:]
            if prueba and falla(prueba):
                receta = prueba
        if len(receta) == antes:
            break
    for i, paso in enumerate(receta):
        for clave in list(paso["args"]):
            sin = {k: v for k, v in paso["args"].items() if k != clave}
            prueba = [*receta[:i], {**paso, "args": sin}, *receta[i + 1:]]
            if falla(prueba):
                receta, paso = prueba, prueba[i]
        for clave, v in paso["args"].items():
            if isinstance(v, float) and v != float(f"{v:.2g}"):
                prueba = [*receta[:i], {**paso, "args": {**paso["args"], clave: float(f"{v:.2g}")}}, *receta[i + 1:]]
                if falla(prueba):
                    receta, paso = prueba, prueba[i]
    return receta


class Corrida:
    def __init__(self, modo, tiempos, foco=None):
        self.modo, self.tiempos, self.foco = modo, tiempos, foco
        ESTADO.mkdir(parents=True, exist_ok=True)
        clave = modo if not foco else f"{modo}_{sin_acentos(foco)}"
        self.ruta_avance = ESTADO / f"avance_{clave}.json"
        self.cob = Cobertura()
        self.av = leer_json(self.ruta_avance, None) or {
            "semilla": random.randrange(1 << 30), "capas": {}, "candidatos": leer_json(ESTADO / "pendientes.json", {})}
        self.guardado = time.monotonic()
        self.fuente = Fuente()
        self.conocidos = leer_json(CONOCIDOS, {})
        self.pesado = modo == "noche"
        self.plazo = 300 if self.pesado else 40      # s por caso: pasado esto es un cuelgue
        self.ramas = {"A": self.capa_a, "B": self.capa_b, "C": self.capa_c, "D": self.capa_d, "E": self.capa_e}

    def capa(self, nombre):
        return self.av["capas"].setdefault(nombre, {"hechos": 0, "seg": 0.0})

    def anotar_fallo(self, capa, res, ignorar=()):
        f = res["fallo"]
        firma = firma_de(f)
        c = self.av["candidatos"].setdefault(firma, {"fallo": f, "receta": res["receta"], "veces": 0, "capa": capa,
                                                     "ignorar": list(ignorar)})
        c["veces"] += 1
        self.cob.fallas[f.get("op", "")] = self.cob.fallas.get(f.get("op", ""), 0) + 1

    def guardar(self):
        guardar_json(self.ruta_avance, self.av)
        self.cob.guardar()
        self.guardado = time.monotonic()

    def correr(self):
        self.info = self.fuente.pedir({"tipo": "catalogo"}, 120)
        self.fuera = set(self.info["fuera_de_cadena"])
        for nombre, segundos in self.tiempos.items():
            capa, inicio = self.capa(nombre), time.monotonic()
            base = capa["seg"]
            if base >= segundos or nombre not in self.ramas:
                continue
            print(f"Capa {nombre}: {segundos - base:.0f} s" + (" (reanudada)" if base else ""), flush=True)

            def queda(base=base, inicio=inicio, segundos=segundos, capa=capa):
                capa["seg"] = base + time.monotonic() - inicio
                if time.monotonic() - self.guardado > GUARDAR_CADA:
                    self.guardar()
                return capa["seg"] < segundos
            self.ramas[nombre](capa, queda)
            self.guardar()
        self.fuente.cerrar()
        return self.cerrar()

    # ------------------------------------------------------------ capas
    def nombres_cadena(self):
        return [h["nombre"] for h in self.info["herramientas"] if h["modifica"] and h["nombre"] not in self.fuera]

    def del_foco(self, nombres=None):
        if not self.foco:
            return None
        palabra = sin_acentos(self.foco)
        if palabra == "pieza_real" or palabra in CADENAS_REALES:
            return None
        por_nombre = {h["nombre"]: h for h in self.info["herramientas"]}
        lista = [n for n in (nombres or por_nombre) if palabra in sin_acentos(f"{n} {por_nombre[n]['descripcion']}")]
        if not lista:
            raise SystemExit(f"Ninguna herramienta habla de «{self.foco}».")
        return lista

    def capa_b(self, capa, queda):
        palabra = sin_acentos(self.foco or "")
        reales = [n for n in CADENAS_REALES if not palabra or palabra == "pieza_real" or palabra in n]
        for i in range(capa.get("reales", 0), len(reales)):
            if not queda():
                return
            nombre = reales[i]
            ped = {"tipo": "cadena", "pieza": nombre, "semilla": f"{self.av['semilla']}-real-{i}",
                   "plan": [], "pesado": self.pesado}
            res = self.fuente.pedir(ped, self.plazo)
            capa["reales"] = i + 1
            capa["hechos"] += 1
            self.cob.anotar(res["avance"])
            if res["fallo"]:
                self.anotar_fallo("B", res)
            print(f"Cadena real {nombre}: " + (firma_de(res["fallo"]) if res["fallo"] else "sin hallazgos"), flush=True)
            for paso in res["avance"]:
                print(f"  {paso['tool']}: {'ok' if paso['ok'] else paso['kind']} · {paso['seg']:.3f} s", flush=True)
        if palabra == "pieza_real" or palabra in CADENAS_REALES:
            return
        nombres = self.nombres_cadena()
        foco = self.del_foco(nombres)
        nucleo = [h["nombre"] for h in self.info["herramientas"] if h["nucleo"] and h["nombre"] in nombres]
        while queda():
            colgadas = {c["fallo"]["op"] for c in self.av["candidatos"].values() if c["fallo"]["kind"].startswith("colgado")}
            nombres = [n for n in nombres if n not in colgadas]     # una espera por herramienta alcanza
            nucleo = [n for n in nucleo if n not in colgadas]
            foco = foco and [n for n in foco if n not in colgadas]
            i = capa["hechos"]
            semilla = f"{self.av['semilla']}-B-{i}"
            rng = random.Random(semilla)
            ped = {"tipo": "cadena", "semilla": semilla, "pieza": PIEZAS[i % len(PIEZAS)], "pesado": self.pesado,
                   "ignorar": [k for k, c in self.av["candidatos"].items() if c["veces"] >= VECES or k in self.conocidos],
                   "plan": self.cob.plan(rng, nombres, foco, nucleo, rng.choice(LARGOS))}
            res = self.fuente.pedir(ped, self.plazo)
            capa["hechos"] += 1
            self.cob.anotar(res["avance"], res.get("sin_contexto", ()))
            if res["fallo"]:
                self.anotar_fallo("B", res, ped["ignorar"])

    def capa_a(self, capa, queda):
        if sin_acentos(self.foco or "") in ("pieza_real", *CADENAS_REALES):
            return
        por_nombre = [h["nombre"] for h in self.info["herramientas"]]
        lista = self.del_foco(por_nombre) or por_nombre
        lista.sort(key=lambda n: self.cob.contratos.get(n, 0))
        seg = max(0.4, self.tiempos["A"] / len(lista))
        for tool in lista:
            if not queda():
                return
            desde = self.cob.contratos.get(tool, 0)
            res = self.fuente.pedir({"tipo": "contratos", "tool": tool, "semilla": f"{self.av['semilla']}-A-{tool}",
                                     "desde": desde, "segundos": seg}, self.plazo)
            capa["hechos"] += 1
            if res.get("caido"):
                self.cob.contratos[tool] = desde + 1        # el caso que tiró el proceso no se repite la próxima
                self.anotar_fallo("A", res)
                continue
            self.cob.contratos[tool] = res["hechos"]
            self.cob.anotar(res["avance"])
            for f in res["fallos"]:
                self.anotar_fallo("A", f)

    def capa_c(self, capa, queda):
        while queda():
            i = capa["hechos"]
            ped = {"tipo": "archivo", "ext": FORMATOS[i % len(FORMATOS)], "semilla": f"{self.av['semilla']}-C-{i}",
                   "carpeta": str(ESTADO / "archivos")}
            res = self.fuente.pedir(ped, self.plazo)
            capa["hechos"] += 1
            self.cob.anotar(res["avance"])
            if res["fallo"]:
                self.anotar_fallo("C", res)

    def capa_d(self, capa, queda):
        ventana = Fuente("ventana.py")
        claves = ventana.pedir({"tipo": "catalogo"}, 180).get("claves", [])
        vistas = self.cob.ventana
        while claves and queda():
            clave = min(claves, key=lambda k: vistas.get(k, 0))
            vistas[clave] = vistas.get(clave, 0) + 1
            ped = {"tipo": "caso", "clave": clave, "semilla": f"{self.av['semilla']}-D-{capa['hechos']}"}
            res = ventana.pedir(ped, self.plazo)
            capa["hechos"] += 1
            if res["fallo"]:
                res.setdefault("receta", [])
                self.anotar_fallo("D", res)
                self.av["candidatos"][firma_de(res["fallo"])]["ped"] = ped
        ventana.cerrar()

    def capa_e(self, capa, queda):
        base = leer_json(ESTADO / "rendimiento.json", {})
        for receta in self.info["recetas_fijas"][capa["hechos"]:]:
            if not queda():
                break
            capa["hechos"] += 1
            self.fuente.cerrar()                       # memoria pico de esta receta sola
            m = self.fuente.pedir({"tipo": "medir", "receta": receta}, 120)
            if m.get("caido"):
                self.anotar_fallo("E", m)
                continue
            b = base.setdefault(receta, m)
            if m["seg"] > 2 * b["seg"] + UMBRAL_SEG or m["mb"] > 2 * b["mb"]:
                self.fuente.cerrar()
                otra = self.fuente.pedir({"tipo": "medir", "receta": receta}, 120)     # sin ruido: tiene que repetirse
                if otra.get("seg", 0) > 2 * b["seg"] + UMBRAL_SEG or otra.get("mb", 0) > 2 * b["mb"]:
                    f = {"juez": "rendimiento", "op": receta, "kind": "lento" if m["seg"] > 2 * b["seg"] else "memoria",
                         "detalle": f"{b['seg']:.2f} s, {b['mb']:.0f} MB → {otra['seg']:.2f} s, {otra['mb']:.0f} MB"}
                    self.anotar_fallo("E", {"fallo": f, "receta": []})
        guardar_json(ESTADO / "rendimiento.json", base)

    # ------------------------------------------------------------ cierre
    def cerrar(self):
        fuente = Fuente()
        nuevos, vistos, pendientes = [], {}, []
        tope = time.monotonic() + (CIERRE_RAPIDA if self.modo != "noche" else 3600)
        # Los cuelgues al final: confirmar cada uno gasta dos veces el plazo entero.
        orden = sorted(self.av["candidatos"].items(), key=lambda kv: (kv[1]["fallo"]["kind"].startswith("colgado"),
                                                                     GRAVEDAD.index(kv[1]["fallo"]["juez"]), -kv[1]["veces"]))
        for firma, c in orden:
            ident = self.conocidos.get(firma)
            if ident:
                vistos[ident] = vistos.get(ident, 0) + c["veces"]
                continue
            colgado = c["fallo"]["kind"].startswith("colgado")
            if len(nuevos) >= MAX_INFORME or time.monotonic() + (2 * self.plazo if colgado else 0) > tope:
                pendientes.append(firma)
                continue
            caso = confirmar(fuente, firma, c, self.pesado, self.plazo)
            if caso:
                nuevos.append(caso)
        ruta = escribir_informe(self, fuente, nuevos, vistos, pendientes)
        fuente.cerrar()
        self.cob.guardar()
        guardar_json(ESTADO / "pendientes.json", {f: self.av["candidatos"][f] for f in pendientes})
        self.ruta_avance.unlink(missing_ok=True)
        print(f"Informe: {ruta}\nNuevos: {len(nuevos)} · conocidos vistos: {vistos or 'ninguno'}", flush=True)
        return 1 if nuevos else 0


def confirmar(fuente, firma, c, pesado, plazo):
    """Sin ruido: lo que no se repite dos veces en un proceso nuevo no se informa. Después, el caso mínimo."""
    if c["capa"] == "E":                    # ya se midió dos veces
        return {"firma": firma, **c}
    lugar = Fuente("ventana.py") if c["capa"] == "D" else fuente
    pedido = c.get("ped") or {"tipo": "repetir", "pasos": c["receta"], "pesado": pesado, "ignorar": c["ignorar"]}
    try:
        lugar.cerrar()                      # proceso limpio: lo que dependa de un caso anterior se cae acá
        for _ in range(2):
            r = lugar.pedir(pedido, plazo)
            if not r["fallo"] or firma_de(r["fallo"]) != firma:
                print(f"No se repite: {firma}", flush=True)
                return None
    finally:
        if lugar is not fuente:
            lugar.cerrar()
    if c["capa"] == "D":
        return {"firma": firma, **c}
    return {"firma": firma, **c, "receta": reducir(fuente, c["receta"], firma, 12, pesado, c["ignorar"])}


REPRO = """# -*- coding: utf-8 -*-
# Repite el caso. Desde clon/: .venv/Scripts/python.exe {ruta}
import json
import sys
from pathlib import Path

sys.path.insert(0, r"{caza}")
import trabajador

pasos = json.loads(Path(__file__).with_name("receta.json").read_text(encoding="utf-8"))["pasos"]
print(trabajador.repetir({{"pasos": pasos}})["fallo"] or "Ya no falla.")
"""


def carpeta_informe():
    return RAIZ / "evidencias" / f"caza_{date.today().isoformat()}"


def escribir_informe(corrida, fuente, nuevos, vistos, pendientes):
    carpeta = carpeta_informe()
    carpeta.mkdir(parents=True, exist_ok=True)
    casos = leer_json(ESTADO / "casos.json", {})
    filas = []
    for n, caso in enumerate(nuevos, 1):
        f = caso["fallo"]
        receta = caso.get("receta") or []
        sub = carpeta / re.sub(r"[^\w-]+", "_", caso["firma"])[:70]
        sub.mkdir(exist_ok=True)
        guardar_json(sub / "receta.json", {"firma": caso["firma"], "pasos": receta, "fallo": f})
        (sub / "repro.py").write_text(REPRO.format(ruta=sub / "repro.py", caza=AQUI), encoding="utf-8")
        if caso["capa"] in ("A", "B") and f["juez"] != "proceso":
            fuente.pedir({"tipo": "imagen", "pasos": receta, "ruta": str(sub / "render.png")}, 60)
        casos[caso["firma"]] = {"pasos": receta, "fallo": f, "ped": caso.get("ped"), "ignorar": caso["ignorar"]}
        detalle = " ".join(f.get("detalle", "").split())[:140]
        filas.append(f"{n}. **{f['juez']}** · `{caso['firma']}` · capa {caso['capa']} · {len(receta)} pasos · "
                     f"{caso['veces']} veces. {detalle} → `{sub.name}/`")
    guardar_json(ESTADO / "casos.json", casos)
    herramientas = corrida.cob.herramientas
    capas = "\n".join(f"| {k} | {v['hechos']} | {v['seg']:.0f} s |" for k, v in corrida.av["capas"].items())
    total = len(corrida.info["herramientas"])
    con_ok = sum(1 for d in herramientas.values() if d["ok"])
    faltan = sorted(h["nombre"] for h in corrida.info["herramientas"] if not herramientas.get(h["nombre"], {}).get("ok"))
    clases = sum(len(v) for v in corrida.cob.clases.values())
    texto = f"""# Caza de errores · {date.today().isoformat()} · {corrida.modo}{' ' + corrida.foco if corrida.foco else ''}

**Resultado: {len(nuevos)} hallazgos nuevos.** Conocidos vistos: {', '.join(f'{k} ×{v}' for k, v in vistos.items()) or 'ninguno'}.

| Capa | Casos | Tiempo |
|---|---|---|
{capas}

**Cobertura acumulada:** {con_ok} de {total} herramientas dieron ok al menos una vez; {len(corrida.cob.pares)} pares de \
operaciones; {clases} clases de valor por herramienta; {sum(corrida.cob.contratos.values())} variantes de contrato. \
Excluidas por seguridad: {len(corrida.info['excluidas'])} (`scripts/caza/generador.py`, `EXCLUIDAS`). Sin ok todavía: \
{len(faltan)}.

## Casos nuevos

{chr(10).join(filas) or 'Ninguno.'}

Sin confirmar por falta de tiempo: {', '.join(f'`{p}`' for p in pendientes) or 'ninguno'}.

Cada caso: `receta.json`, `repro.py` y `render.png` en su carpeta. Lee este informe quien coordina y carga las filas en \
`docs/seguimiento/`; la firma nueva va a `scripts/caza/conocidos.json`.
"""
    ruta = carpeta / "informe.md"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def repetir_firma(firma):
    """¿Sigue fallando? Busca la receta en los casos, en el corpus y en los pendientes sin confirmar y la corre dos veces en procesos limpios."""
    casos = leer_json(ESTADO / "casos.json", {})
    for archivo in sorted(CORPUS.glob("*.json")):
        d = leer_json(archivo, {})
        casos.setdefault(d.get("firma"), d)
    for f, d in leer_json(ESTADO / "pendientes.json", {}).items():       # guardan la receta como «receta», no como «pasos»
        casos.setdefault(f, {**d, "pasos": d.get("receta")})      # la capa D guarda `ped`, sin receta
    if firma not in casos:
        print(f"No hay receta para «{firma}». Firmas: {', '.join(sorted(k for k in casos if k))}")
        return 2
    caso = casos[firma]
    fuente = Fuente("ventana.py" if caso.get("ped") else "trabajador.py")
    pedido = caso.get("ped") or {"tipo": "repetir", "pasos": caso["pasos"], "pesado": True, "ignorar": caso.get("ignorar", ())}
    fallas = 0
    for _ in range(2):
        fuente.cerrar()
        r = fuente.pedir(pedido, 300)
        fallas += bool(r["fallo"]) and firma_de(r["fallo"]) == firma
    fuente.cerrar()
    print("Sigue fallando." if fallas == 2 else "Ya no falla." if not fallas else "Falla a veces.")
    return 0 if not fallas else 1


def en_turno(segundos):
    """Hace fila con turno.py (uno a la vez en toda la PC, 3 GB entre todos los procesos) y vuelve a entrar."""
    if os.environ.get("OMNICAD_CAZA_EN_TURNO"):
        return None
    os.environ["OMNICAD_CAZA_EN_TURNO"] = "1"
    return subprocess.call([sys.executable, str(RAIZ / "scripts" / "turno.py"), "--plazo", str(int(segundos)), "--",
                            sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])


def principal():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Caza automática de errores de OmniCAD (docs/plan_caza_errores.md).")
    sub = ap.add_subparsers(dest="modo", required=True)
    sub.add_parser("rapida")
    sub.add_parser("noche").add_argument("--horas", type=float, default=7.0)
    sub.add_parser("tema").add_argument("palabra")
    sub.add_parser("repetir").add_argument("firma")
    a = ap.parse_args()
    if a.modo == "repetir":
        return repetir_firma(a.firma)
    tiempos = {"rapida": RAPIDA, "tema": TEMA}.get(a.modo) or {k: v * a.horas * 3600 for k, v in REPARTO_NOCHE.items()}
    codigo = en_turno(sum(tiempos.values()) + 300)
    if codigo is not None:
        return codigo
    return Corrida(a.modo, tiempos, getattr(a, "palabra", None)).correr()


if __name__ == "__main__":
    sys.exit(principal())
