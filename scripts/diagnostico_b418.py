"""B-418: dónde se corta la respuesta del trabajador de previas en Windows. Deja un informe de texto.

Uso, desde clon/ (en Windows, la consola del venv):
  .venv\\Scripts\\python.exe ..\\scripts\\diagnostico_b418.py
  .venv\\Scripts\\python.exe ..\\scripts\\diagnostico_b418.py --hijo .venv\\Scripts\\pythonw.exe
El segundo usa para el trabajador el mismo pythonw.exe que la app. `--qt` abre antes la ventana de OmniCAD en este proceso
(como la app): sirve para ver si lo que traba al trabajador es tener Qt en el padre. Cada paso espera como mucho `--plazo` segundos; si no
contesta, copia al informe lo que dejó el trabajador: las marcas, errores.txt y pila.txt (las pilas de sus hilos).
"""
import argparse
import platform
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clon"))


def previa_en_panel(ventana, app, sesion, plazo=40.0):
    """El camino real: la ventana precalienta el trabajador con el boceto y el panel de Extruir pide la previa aparte."""
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui import comando
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    comando.PREVIA_APARTE = True
    doc = sesion.doc
    del doc.operaciones[-1]                 # sin la extrusión de los pasos de antes: solo el boceto
    doc.marcador = len(doc.operaciones)
    doc.recalcular(0)
    ventana.set_documento(doc)
    app.processEvents()
    p = ventana.ejecutar_comando(CATALOGO["extruir"]())
    est, boceto = doc.estado_final, doc.operaciones[-1].id
    ref = OpExtrusion.referencia_perfil(est.bocetos[boceto].perfiles[0])
    p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **ref}, est))
    p.set_valor("distancia", "15 mm")
    limite = time.monotonic() + plazo
    while time.monotonic() < limite and not (p._previa_ok and p._hijo_previa is None):
        app.processEvents()
        time.sleep(0.02)
    if not (p._previa_ok and p._hijo_previa is None):
        raise TimeoutError(f"la previa del panel no llegó: {p.mensaje.text()!r}, aparte={p._previa_aparte}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hijo", help="ejecutable de Python para el trabajador (por defecto, el mismo que corre esto)")
    parser.add_argument("--plazo", type=float, default=40.0,
                        help="segundos por paso (por defecto 40; el trabajador deja sus pilas a los 20)")
    parser.add_argument("--qt", action="store_true", help="abrir antes la ventana de OmniCAD en este proceso, como la app")
    parser.add_argument("--informe", type=Path, default=Path.cwd() / f"diagnostico_b418_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    args = parser.parse_args()
    lineas = []

    def anotar(texto):
        lineas.append(texto)
        args.informe.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    from omnicad import api
    from omnicad.nucleo import aislado
    aislado.TRABAJADOR = True               # lo que se diagnostica es el trabajador, apagado en Windows por B-418
    if args.hijo:
        sys.executable = str(Path(args.hijo).resolve())
    anotar(f"diagnóstico B-418 · {time.strftime('%Y-%m-%d %H:%M:%S')} · {platform.platform()} · Python {sys.version.split()[0]}")
    anotar(f"hijo: {sys.executable} · plazo {args.plazo:g} s")

    def carpeta():
        t = aislado._trabajador
        return None if t is None else t.carpeta

    def volcar(motivo, marca="✗"):
        c = carpeta()
        anotar(f"  {marca} {motivo}")
        if c is None:
            anotar("    (no hay trabajador)")
            return
        vivo = aislado._trabajador.proceso.poll() is None
        anotar(f"    trabajador vivo: {vivo} · carpeta: {c}")
        anotar("    archivos: " + ", ".join(f"{p.name} ({p.stat().st_size} B)" for p in sorted(c.iterdir())))
        for nombre in ("errores.txt", "pila.txt"):
            texto = (c / nombre).read_text(encoding="utf-8", errors="replace").strip() if (c / nombre).exists() else ""
            anotar(f"    --- {nombre} ---\n{texto or '(vacío)'}")

    def paso(nombre, hacer):
        anotar(f"\n== {nombre}")
        inicio = time.monotonic()
        try:
            resultado = hacer()
        except Exception as e:  # noqa: BLE001 — el informe dice qué falló y sigue con el próximo paso
            volcar(f"{type(e).__name__}: {e} ({time.monotonic() - inicio:.1f} s)")
            anotar(traceback.format_exc())
            return None
        anotar(f"  ✓ {time.monotonic() - inicio:.1f} s")
        return resultado

    def despertar():
        t = aislado._trabajador_vivo()
        limite = time.monotonic() + args.plazo
        while not (t.carpeta / "despierto").exists():
            if t.proceso.poll() is not None or time.monotonic() > limite:
                raise RuntimeError("el trabajador no despertó (no llegó a importar OCP y el timeline)")
            time.sleep(0.05)

    def esperar_pendiente(calculo):
        limite = time.monotonic() + args.plazo
        while time.monotonic() < limite:
            salida = calculo.sondear()
            if salida is not None:
                return salida
            time.sleep(0.05)
        raise TimeoutError("la previa no volvió")

    def pedir(tarea, datos):
        """Como `correr_json`, pero sin cerrar al trabajador al vencer: su carpeta queda para el informe."""
        if not aislado.TRABAJADOR:
            return aislado.correr_json(tarea, datos, args.plazo)
        t = aislado._trabajador_vivo()
        t.enviar(tarea, dict(datos, _cwd=str(Path.cwd()), _marca=aislado.marca_recibida,
                             _tope_mb=aislado.TOPE_MEMORIA_TRABAJADOR))
        limite = time.monotonic() + args.plazo
        while not t.termino():
            if time.monotonic() > limite:
                recibido = (t.carpeta / "recibido").exists()
                raise TimeoutError(f"no contestó en {args.plazo:g} s ({'recibió' if recibido else 'NO recibió'} el pedido)")
            time.sleep(0.05)
        return t.recoger()

    if args.qt:
        from omnicad.ui.ventana import VentanaPrincipal
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        ventana = VentanaPrincipal()
        ventana.show()
        app.processEvents()
        anotar("con Qt: ventana de OmniCAD abierta en este proceso")
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 30, "width": 20, "height": 10})["ok"]
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 20, "x": 15, "y": 10})["ok"]
    receta = s.doc.a_dict()
    vacia = api.Sesion().doc.a_dict()
    # La previa de Extruir como la pide el panel (`PanelComando._iniciar_previa`): la que se trabó en Windows.
    e = api.Sesion()
    assert api.llamar(e, "sketch_from_spec", {"plane": "XY", "entities": [
        {"type": "rectangle", "corner1": [0, 0], "corner2": [30, 20]}]})["ok"]
    previa = {"receta": e.doc.a_dict(), "indice": len(e.doc.operaciones), "deflexion": None, "angular": 0.3, "formas": True}
    assert api.llamar(e, "extrude", {"sketch": e.doc.operaciones[-1].id, "distance": 15})["ok"]
    previa["operacion"] = e.doc.operaciones[-1].a_dict()

    aislado.cerrar_trabajador()       # el precalentado de la ventana (FL-9): sus respuestas no son de estos pasos
    paso("1. arranca el trabajador", despertar)
    paso("2. pedido mínimo (documento vacío)", lambda: pedir("recalcular_documento", {"receta": vacia}))
    paso("3. recalcular dos cuerpos", lambda: pedir("recalcular_documento", {"receta": receta}))
    paso("4. otra vez, con el trabajador caliente", lambda: pedir("recalcular_documento", {"receta": receta}))
    paso("5. previa sin esperar (CalculoPendiente)", lambda: esperar_pendiente(
        aislado.CalculoPendiente("recalcular_documento", {"receta": receta})))
    paso("6. previa de Extruir en el trabajador (previa_visual, como el panel)", lambda: pedir("previa_visual", previa))
    paso("7. otra vez, sin esperar (CalculoPendiente)", lambda: esperar_pendiente(
        aislado.CalculoPendiente("previa_visual", previa)))
    if carpeta():
        volcar("estado final del trabajador", marca="·")
    if args.qt:
        paso("8. previa de Extruir desde el panel de la ventana (precalentado, como la app)",
             lambda: previa_en_panel(ventana, app, e))
    aislado.cerrar_trabajador()
    aislado.TRABAJADOR = False
    paso("9. recalcular en un hijo de una sola tarea (sin tubería)", lambda: pedir("recalcular_documento", {"receta": receta}))
    paso("10. previa de Extruir en un hijo de una sola tarea", lambda: pedir("previa_visual", previa))
    anotar(f"\nInforme: {args.informe}")
    print(args.informe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
