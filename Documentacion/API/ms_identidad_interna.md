# Contrato de API — Microservicio de Identidad (API interna REST)

## Información general

- **Microservicio proveedor:** `ms-identidad`.
- **Implementación:** C06 — Contratos REST internos para otros microservicios.
- **Consumidores previstos:** `ms-catalogo` y `ms-circulacion`.
- **Objetivo:** validar sesiones y resolver datos de usuarios y roles sin compartir la base `db_identidad`.
- **Transporte:** HTTP REST; solicitudes y respuestas JSON.
- **URL dentro de Docker Compose:** `http://ms-identidad:8000/api/internal/`.
- **Acceso directo de desarrollo desde el anfitrión:** `http://localhost:18081/api/internal/`.
- **Autenticación entre servicios:** `X-Internal-Service-Key: <clave_de_servicio>`.

Esta API **no está destinada al navegador ni al frontend Angular**. El Nginx API Gateway devuelve **404** para el prefijo público `/api/internal/`. El puerto `18081` solo está expuesto en `127.0.0.1` para pruebas locales.

## Endpoints implementados

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/internal/auth/validar/` | Determinar si un token de usuario está vigente y obtener su identidad |
| `GET` | `/api/internal/usuarios/{usuario_id}/` | Consultar la identidad mínima de un usuario |
| `POST` | `/api/internal/usuarios/resolver/` | Resolver hasta 100 identificadores en una solicitud |

Todos requieren una **clave de servicio válida**. No utilizan el token Bearer del usuario para autenticar al consumidor.

## 1. Seguridad y autenticación del consumidor

En cada petición debe incluirse:

```http
X-Internal-Service-Key: <clave_de_servicio>
Accept: application/json
```

Para peticiones `POST` también se envía:

```http
Content-Type: application/json
```

El proveedor compara la cabecera con `IDENTIDAD_INTERNAL_API_KEY`, recibida por variable de entorno. La versión de desarrollo exige una clave configurada de al menos 16 caracteres y la comparación se realiza con `constant_time_compare`.

**HTTP 403 Forbidden**, si no existe la cabecera, es incorrecta o la configuración de seguridad es inválida:

```json
{"detail": "Acceso interno no autorizado."}
```

Una clave válida identifica al **servicio consumidor**, no al usuario final. Para autorizar una acción de un usuario, el consumidor debe además validar el token mediante el endpoint de autenticación y comprobar el rol devuelto.

## 2. `POST /api/internal/auth/validar/`

**Propósito:** validar en tiempo real un token de sesión opaco emitido por el endpoint público `/api/auth/login/`.

**Solicitud:**

```json
{
  "token": "<token_opaco_del_usuario>"
}
```

El campo `token` es obligatorio, no admite cadena vacía y tiene un máximo de 512 caracteres. La cadena se procesa sin recortar sus espacios.

### Respuesta de token válido — HTTP 200

```json
{
  "valido": true,
  "usuario": {
    "usuario_id": 7,
    "nombre": "Lector de ejemplo",
    "email": "lector@example.com",
    "rol": {
      "rol_id": 1,
      "nombre": "estudiante",
      "limite_prestamos_activos": 5
    }
  },
  "expira_en": "2026-11-23T04:00:00+00:00"
}
```

### Respuesta de token inválido — HTTP 200

```json
{
  "valido": false,
  "usuario": null,
  "expira_en": null
}
```

Esta última estructura se devuelve si el token no existe, ha sido revocado o expiró. Cuando se detecta un token expirado todavía no revocado, Identidad registra su revocación.

**Importante:** HTTP `200` significa que el servicio interno procesó la solicitud. **No significa que el usuario esté autorizado.** El consumidor debe verificar explícitamente `valido === true` y el rol correspondiente. Nunca debe permitir el acceso basándose solo en el código HTTP.

**Otros resultados:** `400` si falta el token o supera la longitud permitida; `403` por clave de servicio incorrecta; `405` si se usa `GET` en lugar de `POST`.

## 3. `GET /api/internal/usuarios/{usuario_id}/`

**Propósito:** obtener el identificador, nombre, correo y rol de un usuario de Identidad. Esta ruta se utiliza para referencias por ID en otros microservicios.

| Parámetro | Ubicación | Tipo | Restricción |
|---|---|---|---|
| `usuario_id` | Ruta | Entero | Identificador existente en `db_identidad` |

**HTTP 200 OK:**

```json
{
  "usuario_id": 7,
  "nombre": "Lector de ejemplo",
  "email": "lector@example.com",
  "rol": {
    "rol_id": 1,
    "nombre": "estudiante",
    "limite_prestamos_activos": 5
  }
}
```

**HTTP 404**, si no existe:

```json
{"detail": "Usuario no encontrado."}
```

No incluye `password`, `contrasena_hash`, `token_hash`, dirección ni teléfono.

**Nota de autorización:** la existencia de un usuario no demuestra que el consumidor tenga una sesión válida de ese usuario. Cuando la operación depende del usuario autenticado, se debe utilizar el contrato de validación de token.

## 4. `POST /api/internal/usuarios/resolver/`

**Propósito:** consultar en un solo viaje REST varios usuarios, evitando una petición por registro al mostrar relaciones de préstamos, sanciones u otros recursos.

**Solicitud JSON:**

```json
{
  "usuarios_ids": [7, 8, 7, 999999]
}
```

`usuarios_ids` es obligatorio; debe contener entre 1 y 100 identificadores enteros positivos. No se admiten cadenas no numéricas.

**HTTP 200 OK:**

```json
{
  "usuarios": [
    {
      "usuario_id": 7,
      "nombre": "Lector de ejemplo",
      "email": "lector@example.com",
      "rol": {
        "rol_id": 1,
        "nombre": "estudiante",
        "limite_prestamos_activos": 5
      }
    },
    {
      "usuario_id": 8,
      "nombre": "Docente de ejemplo",
      "email": "docente@example.com",
      "rol": {
        "rol_id": 2,
        "nombre": "docente",
        "limite_prestamos_activos": 5
      }
    }
  ],
  "no_encontrados": [999999]
}
```

Los identificadores duplicados se eliminan y los usuarios encontrados conservan el orden de la solicitud. Los no encontrados aparecen solamente en `no_encontrados`. La operación no crea ni modifica usuarios.

**Errores:** `400` si la lista falta, está vacía, contiene IDs inválidos o supera 100 entradas; `403` si falla la autenticación del servicio; `405` ante un método no admitido.

## 5. Códigos HTTP

| Código | Significado |
|---|---|
| `200` | Petición interna procesada; verificar además `valido` en la validación de token |
| `400` | Datos o parámetros inválidos |
| `403` | Clave de servicio ausente, inválida o no configurada correctamente |
| `404` | Usuario individual inexistente; también es el bloqueo intencional de Nginx para rutas internas públicas |
| `405` | Método HTTP no permitido |
| `500` | Error inesperado del proveedor |

Si Identidad no responde o hay un error de red, los consumidores **no deben suponer que la sesión es válida ni que un usuario cumple los permisos**. Deben rechazar o posponer las operaciones protegidas y gestionar la indisponibilidad de la dependencia.

## 6. Flujo de integración entre microservicios

1. El frontend realiza login mediante el gateway público y obtiene un token Bearer.
2. El frontend solicita una operación a Catálogo o Circulación adjuntando `Authorization: Bearer <token>`.
3. El microservicio consumidor extrae el token y llama a `POST /api/internal/auth/validar/` de Identidad, autenticándose con su propia clave de servicio.
4. Identidad comprueba el hash, expiración y revocación del token en `db_identidad` y devuelve la identidad y el rol.
5. El consumidor comprueba `valido` y aplica sus permisos de negocio. Si necesita datos de otros usuarios referenciados por ID, utiliza la consulta individual o múltiple.
6. El consumidor responde al frontend sin exponer la clave interna.

En C06 solo se implementa el proveedor REST en Identidad. Los clientes efectivos de Catálogo y Circulación se incorporarán cuando se construyan esos microservicios.

## 7. Dependencia futura: consulta de préstamos activos

Desde C05, Identidad prepara un cliente REST hacia Circulación para proteger el cambio de rol a bibliotecario:

```http
GET /internal/prestamos/activos/?usuario_id=7
X-Internal-Service-Key: <clave_configurada_para_circulacion>
```

Respuesta prevista:

```json
{"tiene_prestamos_activos": false}
```

**Este endpoint todavía no está implementado en Circulación.** Su dirección y clave se configurarán cuando exista `ms-circulacion`. Hasta entonces, Identidad responde `503` ante un cambio de rol que exija verificar esa condición, sin persistir los cambios. No debe reemplazarse por una consulta directa a la base de Circulación.

## 8. Configuración y límites de exposición

| Elemento | Dirección / variable | Uso |
|---|---|---|
| DNS interno de Identidad | `ms-identidad:8000` | Llamadas desde contenedores en la red `api` |
| API interna | `/api/internal/` | Rutas de este contrato |
| API pública | `localhost:8000/api/` | Tráfico de Angular mediante Nginx |
| Depuración local | `localhost:18081/api/internal/` | Pruebas directas desde el equipo |
| Clave de servicio | `IDENTIDAD_INTERNAL_API_KEY` | Autenticación entre servicios |
| Base de datos | `db_identidad` | Accesible solamente por el servicio propietario |

La clave de servicio es un secreto de desarrollo aunque su valor sea fijo. No debe incluirse en frontend, ejemplos versionados, capturas ni logs. Para producción se requieren credenciales robustas, HTTPS o una red confiable con controles adicionales, y rotación de credenciales.

## 9. Código relacionado

- Rutas: `backend/ms-identidad/identidad/urls.py`.
- Permiso interno: `identidad/internal_permissions.py` (`IsInternalService`).
- Vistas: `identidad/presentation/internal_views.py`.
- Serializadores: `identidad/presentation/internal_serializers.py`.
- Servicio: `identidad/services/internal_service.py`.
- Repositorio de token: `identidad/repositories/auth_repository.py`.
- Modelos propios: `identidad/models.py`.
- Contrato público: [ms_identidad_externa.md](ms_identidad_externa.md).

## 10. Pruebas verificadas

**Pruebas automatizadas:** `backend/ms-identidad/identidad/tests/test_internal.py`.

```powershell
docker compose exec ms-identidad python manage.py test identidad.tests -v 2
```

La ejecución comunicada para C06 reportó **85 pruebas encontradas, 85 aprobadas** en toda la suite, incluidas las de contratos internos. Es un resultado real, no la meta inicial de 86.

**Pruebas HTTP verificadas:**

| Prueba | Resultado observado |
|---|---|
| `GET localhost:8000/api/internal/usuarios/1/` | `404` de Nginx, acceso público bloqueado |
| `GET localhost:18081/api/internal/usuarios/1/` sin clave | `403` |
| Misma solicitud con clave configurada | `200`, usuario y rol |
| Misma solicitud con clave incorrecta | `403` |
| Validación de token emitido por login | `200`, `valido: true` |
| Logout público con ese token | `204` |
| Nueva validación interna del token revocado | `200`, `valido: false` |

**Pendientes de verificación:** ejecución completa de la colección Postman C06 y consumo real desde los futuros microservicios.

## 11. Criterios de mantenimiento

Cuando cambie una ruta, parámetro, estructura JSON, regla de permisos o código HTTP, actualizar este documento y sus pruebas de contrato. Mantener separadas la documentación de API pública y la API interna; ningún consumidor debe compartir tablas de Identidad ni comunicarse con el backend del monolito en tiempo de ejecución.
