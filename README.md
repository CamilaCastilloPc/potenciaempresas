# Potencia Empresas — Integración GoHighLevel

Cliente de la API v2 de GoHighLevel (LeadConnector) para vincular una subcuenta.
Sólo biblioteca estándar de Python 3.11+: no hay dependencias que instalar.

## Configuración

1. En GoHighLevel: **Settings → Private Integrations → Create new integration**.
   Asigná sólo los scopes que necesites (para las verificaciones de este repo:
   `locations.readonly`, `contacts.readonly`, `opportunities.readonly`).
   El token generado empieza con `pit-`.
2. Copiá el Location ID de la subcuenta (**Settings → Business Profile**).
3. Configurá las variables:

   ```bash
   cp .env.example .env    # completar y NO commitear
   export GHL_PRIVATE_TOKEN='pit-...'
   export GHL_LOCATION_ID='...'
   ```

   El token y el Location ID se confunden fácil. El token es el que empieza con
   `pit-`; el client valida esto y falla temprano con un mensaje claro.

## Verificar el vínculo

```bash
python3 scripts/verificar_conexion.py
```

Códigos de salida:

| Código | Significado |
|---|---|
| 0 | Vínculo funcionando |
| 1 | Se alcanzó la API pero alguna verificación falló (típicamente falta un scope) |
| 2 | Falta configuración o las credenciales están invertidas |
| 3 | No hay conectividad hacia la API |

## Uso

```python
from ghl import GHLClient

client = GHLClient()                       # lee las variables de entorno
print(client.get_location()["location"]["name"])

for contacto in client.iter_contacts():    # pagina automáticamente
    print(contacto["id"], contacto.get("email"))

client.upsert_contact(email="cliente@ejemplo.cl", firstName="Ana")
```

## Requisito de red

La API vive en `services.leadconnectorhq.com`. En entornos con proxy de egreso
restringido (por ejemplo las sesiones remotas de Claude Code) ese dominio debe
estar permitido en la política de red del entorno, o toda llamada falla con
`403 Forbidden` en el CONNECT antes del handshake TLS. Ver la
[documentación de entornos](https://code.claude.com/docs/en/claude-code-on-the-web).

## Alternativa sin código: MCP oficial

HighLevel expone un servidor MCP en `https://services.leadconnectorhq.com/mcp/`
que se puede agregar como conector personalizado en claude.ai, autenticando con
el mismo Private Integration Token más el Location ID en los headers. Eso permite
consultar la subcuenta desde una conversación, sin pasar por este cliente.

## Seguridad

- El token `pit-` da acceso de lectura/escritura a la subcuenta según sus scopes.
- Nunca lo pegues en el chat, en código, ni en un commit: va en `.env` (ignorado)
  o en el gestor de secretos del entorno.
- Si un token queda expuesto, revocalo en Private Integrations y generá otro.
