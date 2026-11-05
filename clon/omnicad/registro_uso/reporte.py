"""Borrador de un issue público: solo texto elegido por la persona y entorno sin datos privados."""
from urllib.parse import urlencode


def url_issue(tipo: str, titulo: str, nota: str, version: str, so: str, captura: str | None = None) -> str:
    """Arma una URL de GitHub de hasta 7000 caracteres; no lee archivos ni abre conexiones o Qt."""
    if not titulo.strip():
        raise ValueError("El título es obligatorio para abrir un issue en GitHub.")
    etiquetas = {"Problema": "bug", "Sugerencia": "enhancement"}
    if tipo not in etiquetas:
        raise ValueError("El tipo debe ser Problema o Sugerencia.")
    pie = f"\n\nVersión de OmniCAD: {version}\nSistema operativo: {so}"
    if captura:
        pie += f"\nSi marcaste captura, arrastrala acá: {captura}"

    def armar(texto):
        return "https://github.com/JerryblackVe/OmniCAD/issues/new?" + urlencode({
            "title": titulo, "body": texto + pie, "labels": etiquetas[tipo]})

    url = armar(nota)
    if len(url) <= 7000:
        return url
    aviso = "\n\n[Nota recortada para respetar el límite de la URL.]"
    if len(armar(aviso)) > 7000:
        raise ValueError("El título o los datos del entorno son demasiado largos para la URL de GitHub.")
    # Medir el texto ya codificado: una tilde o un emoji ocupan más que un carácter ASCII.
    desde, hasta = 0, min(len(nota), 7000)
    while desde < hasta:
        medio = (desde + hasta + 1) // 2
        if len(armar(nota[:medio] + aviso)) <= 7000:
            desde = medio
        else:
            hasta = medio - 1
    return armar(nota[:desde] + aviso)
