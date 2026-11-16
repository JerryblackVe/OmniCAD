#!/usr/bin/env bash
# PreToolUse de start_session: recuerda reusar sesiones (HOOKS-1116).
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"Protocolo: ¿hay una sesión para reusar? clear_session + SendMessage; start_session solo si no queda ninguna."}}'
