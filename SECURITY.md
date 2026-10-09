# Seguridad

## Reportar una vulnerabilidad

No abras un issue público. Usá **Security → Report a vulnerability** en
[GitHub](https://github.com/JerryblackVe/OmniCAD/security) (aviso privado), con los pasos para reproducirla.

## Puntos sensibles conocidos

- **Puente en vivo** (`clon/omnicad/ui/puente.py`): deja que un agente maneje la ventana abierta. Viene **apagado**,
  escucha solo en `127.0.0.1`, exige un token aleatorio que se guarda en un archivo del usuario y muestra «Agente IA
  conectado» mientras hay alguien conectado.
- **`execute_code`**: corre Python dentro de la sesión del agente. En el modo en vivo está apagado salvo que el usuario
  lo active en Preferencias.
- **Proyectos `.omnicad`**: son ZIP con una receta JSON; no ejecutan código al abrirse.

Detalle del puente: [docs/agentes/puente.md](docs/agentes/puente.md).
