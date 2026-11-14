"""B-418: dónde se corta la respuesta del trabajador de previas en Windows. Deja un informe de texto.

Uso, desde clon/ (en Windows, la consola del venv):
  .venv\\Scripts\\python.exe ..\\scripts\\diagnostico_b418.py
  .venv\\Scripts\\python.exe ..\\scripts\\diagnostico_b418.py --hijo .venv\\Scripts\\pythonw.exe
El segundo usa para el trabajador el mismo pythonw.exe que la app. Cada paso espera como mucho `--plazo` segundos; si no
contesta, copia al informe lo que dejó el trabajador: las marcas, errores.txt y pila.txt (las pilas de sus hilos).
"""
import argparse
import platform
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clon"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hijo", help="ejecutable de Python para el trabajador (por defecto, el mismo que corre esto)")
    parser.add_argument("--plazo", type=float, default=40.0,
                        help="segundos por paso (por defecto 40; el trabajador deja sus pilas a los 20)")
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

    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 30, "width": 20, "height": 10})["ok"]
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 20, "x": 15, "y": 10})["ok"]
    receta = s.doc.a_dict()
    vacia = api.Sesion().doc.a_dict()

    paso("1. arranca el trabajador", despertar)
    paso("2. pedido mínimo (documento vacío)", lambda: pedir("recalcular_documento", {"receta": vacia}))
    paso("3. recalcular dos cuerpos", lambda: pedir("recalcular_documento", {"receta": receta}))
    paso("4. otra vez, con el trabajador caliente", lambda: pedir("recalcular_documento", {"receta": receta}))
    paso("5. previa sin esperar (CalculoPendiente)", lambda: esperar_pendiente(
        aislado.CalculoPendiente("recalcular_documento", {"receta": receta})))
    if carpeta():
        volcar("estado final del trabajador", marca="·")
    aislado.cerrar_trabajador()
    aislado.TRABAJADOR = False
    paso("6. lo mismo en un hijo de una sola tarea (sin tubería)", lambda: pedir("recalcular_documento", {"receta": receta}))
    anotar(f"\nInforme: {args.informe}")
    print(args.informe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
