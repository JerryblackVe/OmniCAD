"""Telemetría local optativa, compartida por la app, MCP y CLI."""
from .. import registro_uso
from .registro import herramienta


@herramienta("set_usage_logging", "avanzado", "Prende o apaga el registro LOCAL de uso. No envía datos; "
             "solo números, claves y longitudes. Apagado de fábrica. No entra en deshacer.",
             modifica=False)
def set_usage_logging(sesion, enabled: bool):
    """
    enabled: true activa la sesión local; false la drena y apaga.
    """
    configurar = getattr(sesion, "configurar_registro", None)
    if configurar:
        return configurar(enabled)
    return registro_uso.configurar(enabled, {"proyecto": sesion.doc.nombre})
