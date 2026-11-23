# Contrato de API — Microservicio de Identidad (API externa)

## Información general

- **Módulos de origen:** 3.1 Autenticación y permisos; 3.2 Gestión de usuarios y roles.
- **Arquitectura:** microservicio `ms-identidad`, independiente del monolito.
- **Entregable:** contratos HTTP para el frontend Angular y consumidores públicos de BiblioTech.
- **Implementación:** C04 (autenticación) y C05 (usuarios y roles).
- **URL base de desarrollo:** `http://localhost:8000/api/`, a través de Nginx API Gateway.
- **Tecnología:** Django REST Framework; JSON; fechas-hora ISO 8601 con zona horaria.
- **Autenticación:** `Authorization: Bearer <token>`; no requerida para iniciar sesión.
- **Roles:** `estudiante`, `docente` y `bibliotecario`.
- **Compatibilidad:** se conservan las rutas, métodos y estructuras utilizados por el frontend Angular original; no se modificó su código.

Esta API es propiedad de Identidad y utiliza exclusivamente `db_identidad`. No consulta tablas del monolito ni utiliza claves foráneas entre microservicios.

## Endpoints implementados

| Método | Ruta | Autenticación | Roles autorizados | Descripción |
|---|---|---|---|---|
| `POST` | `/api/auth/login/` | No | Credenciales válidas | Iniciar sesión y emitir un token |
| `POST` | `/api/auth/logout/` | Bearer | Cualquier usuario autenticado | Revocar la sesión actual |
| `GET` | `/api/auth/me/` | Bearer | Cualquier usuario autenticado | Obtener la identidad de la sesión |
| `GET` | `/api/auth/access/bibliotecario/` | Bearer | `bibliotecario` | Comprobar acceso administrativo |
| `GET` | `/api/auth/access/lector/` | Bearer | `estudiante`, `docente` | Comprobar acceso de lector |
| `GET` | `/api/usuarios/` | Bearer | `bibliotecario` | Listar usuarios con paginación |
| `POST` | `/api/usuarios/` | Bearer | `bibliotecario` | Registrar un usuario |
| `GET` | `/api/usuarios/{usuario_id}/` | Bearer | `bibliotecario` | Consultar un usuario |
| `PATCH` | `/api/usuarios/{usuario_id}/` | Bearer | `bibliotecario` | Modificar campos permitidos |
| `GET` | `/api/roles/` | Bearer | `bibliotecario` | Listar roles disponibles |

Las rutas terminan con `/`. Los identificadores son numéricos y se generan en MySQL; nunca debe suponerse que un rol tiene un identificador fijo.

## 1. `POST /api/auth/login/`

**Propósito:** verificar correo y contraseña; emitir un token opaco para el usuario autenticado.

**Solicitud JSON:**

```json
{
  "email": "lector@example.com",
  "password": "<contrasena_de_ejemplo>"
}
```

| Campo | Requerido | Validación |
|---|---|---|
| `email` | Sí | Correo válido, máximo 50 caracteres; se eliminan espacios exteriores y se normaliza a minúsculas |
| `password` | Sí | Cadena no vacía; no se recortan espacios de la contraseña |

**HTTP 200 OK:**

```json
{
  "token": "<token_opaco_ilustrativo>",
  "tipo_token": "Bearer",
  "expira_en": "2026-11-23T04:00:00+00:00",
  "usuario": {
    "usuario_id": 7,
    "nombre": "Lector de ejemplo",
    "email": "lector@example.com",
    "rol": {
      "rol_id": 1,
      "nombre": "estudiante",
      "limite_prestamos_activos": 5
    }
  }
}
```

La fecha y los identificadores son ilustrativos. `expira_en` indica un instante absoluto. El frontend conserva la sesión en `sessionStorage` o `localStorage` según la opción «Recordar sesión»; esto no cambia el tiempo de expiración del servidor.

**Errores:** `400` cuando faltan campos o su formato es inválido; `401` para correo inexistente o contraseña incorrecta. Ambos errores de credenciales devuelven el mismo mensaje:

```json
{"detail": "Credenciales incorrectas."}
```

## 2. `POST /api/auth/logout/`

**Autorización:** `Authorization: Bearer <token>`.

**Solicitud:** cuerpo opcional `{}`. **Respuesta:** `204 No Content`, sin cuerpo JSON.

Revoca únicamente el token enviado; otras sesiones del mismo usuario permanecen activas. Un intento posterior de utilizar ese token produce `401 Unauthorized`. Sin token válido, también devuelve `401`.

## 3. `GET /api/auth/me/`

**Autorización:** cualquier token Bearer vigente. Sin parámetros ni cuerpo.

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

El identificador proviene del token verificado, no de un parámetro enviado por el cliente. El frontend invoca esta ruta para restaurar la sesión al recargar la aplicación.

**Error:** `401` si falta el token, es inválido, expiró o fue revocado.

## 4. Verificación de permisos por rol

### `GET /api/auth/access/bibliotecario/`

Requiere token Bearer y rol `bibliotecario`.

**HTTP 200:**

```json
{"detail": "Acceso autorizado para bibliotecario."}
```

### `GET /api/auth/access/lector/`

Requiere token Bearer y rol `estudiante` o `docente`.

**HTTP 200:**

```json
{"detail": "Acceso autorizado para estudiante o docente."}
```

Para ambos endpoints: `401` sin autenticación válida y `403` con token válido cuyo rol no está permitido. La autorización se comprueba en el backend, independientemente de los *guards* de Angular.

## 5. Representación pública administrativa de usuario

Las operaciones de gestión emplean la siguiente estructura:

```json
{
  "usuario_id": 7,
  "nombre": "Ana Martínez",
  "email": "ana@example.com",
  "direccion": "Puebla",
  "telefono": "2221234567",
  "rol": {
    "rol_id": 1,
    "nombre": "estudiante",
    "limite_prestamos_activos": 5
  }
}
```

`direccion` y `telefono` pueden ser `null`. Nunca se envían `password`, `contrasena_hash`, `token_hash` ni otros secretos. Los nombres y datos de los ejemplos son ilustrativos.

## 6. `GET /api/usuarios/`

**Rol autorizado:** `bibliotecario`.

**Parámetros de consulta:**

| Parámetro | Valor predeterminado | Restricción |
|---|---|---|
| `page` | `1` | Página solicitada, desde 1 |
| `page_size` | `10` | Hasta 100 registros |

Ejemplo: `GET /api/usuarios/?page=1&page_size=10`.

**HTTP 200 OK:**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "usuario_id": 7,
      "nombre": "Ana Martínez",
      "email": "ana@example.com",
      "direccion": null,
      "telefono": null,
      "rol": {
        "rol_id": 1,
        "nombre": "estudiante",
        "limite_prestamos_activos": 5
      }
    }
  ]
}
```

Los registros se ordenan por `usuario_id`. La ruta no implementa búsqueda por texto ni filtros de rol. Una página fuera del rango disponible puede devolver `404`, según el paginador de Django REST Framework.

## 7. `POST /api/usuarios/`

**Rol autorizado:** `bibliotecario`.

**Solicitud JSON:**

```json
{
  "nombre": "Ana Martínez",
  "email": "ana@example.com",
  "direccion": "Puebla",
  "telefono": "2221234567",
  "rol_id": 1,
  "password": "<contrasena_inicial>"
}
```

| Campo | Requerido | Restricción |
|---|---|---|
| `nombre` | Sí | Texto no vacío de máximo 100 caracteres |
| `email` | Sí | Correo válido, máximo 50 caracteres; único sin distinguir mayúsculas |
| `direccion` | No | Cadena de hasta 255 caracteres, vacía o `null` |
| `telefono` | No | Cadena de hasta 15 caracteres, vacía o `null` |
| `rol_id` | Sí | Entero positivo que corresponde a `estudiante`, `docente` o `bibliotecario` |
| `password` | Sí | Contraseña validada mediante los validadores de Django |

**HTTP 201 Created:** cuerpo con la representación pública administrativa del usuario creado. La contraseña se guarda mediante hashing de Django y no se devuelve.

**HTTP 400:** campo desconocido, correo duplicado, rol inexistente o no permitido, contraseña inválida u otro error de validación.

Ejemplo de error:

```json
{"email": ["Este correo ya está registrado."]}
```

## 8. `GET /api/usuarios/{usuario_id}/`

**Rol autorizado:** `bibliotecario`.

**HTTP 200:** representación pública administrativa del usuario. **HTTP 404:**

```json
{"detail": "Usuario no encontrado."}
```

## 9. `PATCH /api/usuarios/{usuario_id}/`

**Rol autorizado:** `bibliotecario`.

Admite modificaciones parciales de `nombre`, `email`, `direccion`, `telefono` y `rol_id`. No admite cambiar la contraseña ni el hash mediante este endpoint.

**Solicitud JSON ilustrativa:**

```json
{
  "nombre": "Ana Martínez López",
  "telefono": "2229876543"
}
```

**HTTP 200:** devuelve el usuario actualizado. `400` por correo duplicado, rol inexistente, campo prohibido o violación de reglas de negocio. `404` si no existe el usuario.

**Restricción de préstamos activos:** el sistema base prohíbe convertir en bibliotecario a un usuario que mantiene préstamos activos. En la arquitectura actual, Identidad solicita la comprobación a Circulación por REST únicamente si el rol cambia a `bibliotecario`:

- Si Circulación confirma préstamos activos: **HTTP 400**, error en `rol_id`.
- Si Circulación confirma que no existen préstamos activos: se permite el cambio.
- Si Circulación no está disponible o su respuesta no puede verificarse: **HTTP 503**, sin guardar los cambios de esa solicitud.

Respuesta de indisponibilidad:

```json
{
  "detail": "No es posible verificar los préstamos activos porque Circulación no está disponible. No se guardaron cambios."
}
```

La integración con Circulación todavía está pendiente. Editar los demás datos de un usuario y cambiar de `estudiante` a `docente` no requiere esa comprobación.

## 10. `GET /api/roles/`

**Rol autorizado:** `bibliotecario`. **HTTP 200:** arreglo JSON con los roles permitidos:

```json
[
  {"rol_id": 1, "nombre": "estudiante", "limite_prestamos_activos": 5},
  {"rol_id": 2, "nombre": "docente", "limite_prestamos_activos": 5},
  {"rol_id": 3, "nombre": "bibliotecario", "limite_prestamos_activos": 0}
]
```

Los IDs son ilustrativos. No se exponen roles ajenos a estos tres.

## 11. Salud del microservicio

Estas rutas están fuera del prefijo `/api/` y no requieren token:

| Método | Ruta | Resultado |
|---|---|---|
| `GET` | `/health/live/` | `200` si el proceso Django responde |
| `GET` | `/health/ready/` | `200` si Django puede consultar MySQL; `503` cuando la base no está disponible |

## 12. Códigos HTTP y seguridad

| Código | Uso |
|---|---|
| `200` | Inicio de sesión, consultas y modificaciones exitosas |
| `201` | Usuario registrado |
| `204` | Sesión revocada; sin cuerpo |
| `400` | Datos inválidos o regla de negocio incumplida |
| `401` | Credenciales incorrectas o sesión ausente, expirada, inválida o revocada |
| `403` | Usuario autenticado sin el rol necesario |
| `404` | Usuario o página inexistente |
| `405` | Método no implementado |
| `503` | Dependencia Circulación indisponible durante una comprobación obligatoria |

- Token de sesión opaco, no JWT; se almacena solo su hash SHA-256.
- La duración se controla con `AUTH_TOKEN_TTL_HOURS` (desarrollo: 8 horas).
- Cada login crea un token independiente; logout revoca únicamente el presentado.
- El frontend envía automáticamente `Authorization: Bearer <token>` mediante su interceptor.
- No hay endpoints de borrado de usuarios ni de cambio de contraseña a través de `PATCH /api/usuarios/`.
- Las rutas internas `/api/internal/` no forman parte de esta API; su contrato está en [ms_identidad_interna.md](ms_identidad_interna.md).

## 13. Implementación, pruebas y dependencias

**Código:**

- Rutas: `backend/ms-identidad/identidad/urls.py`.
- Vistas: `identidad/presentation/auth_views.py` y `identidad/presentation/usuarios_views.py`.
- Serializadores: `identidad/presentation/auth_serializers.py` y `identidad/presentation/usuarios_serializers.py`.
- Servicios: `identidad/services/auth_service.py` y `identidad/services/usuarios_service.py`.
- Repositorios: `identidad/repositories/auth_repository.py` y `identidad/repositories/usuarios_repository.py`.
- Autenticación y permisos: `identidad/authentication.py` y `identidad/permissions.py`.
- Frontend: `frontend/src/app/core/auth/` y `frontend/src/app/features/usuarios/`.

**Pruebas Django:** `test_health.py`, `test_auth.py`, `test_usuarios.py`, `test_models.py` y `test_seed.py` bajo `backend/ms-identidad/identidad/tests/`.

```powershell
docker compose exec ms-identidad python manage.py test identidad.tests -v 2
```

En la ejecución compartida durante C06 se aprobaron **85 de 85 pruebas encontradas** en la suite completa de Identidad. Las validaciones manuales confirmaron el login, la autorización interna y la revocación del token; no se atribuyen resultados de Postman o de las pantallas Angular que no se hayan reportado.

**Pendiente:** implementación de Circulación para verificar préstamos activos al promover usuarios existentes a bibliotecario; implementación independiente de Catálogo y Circulación para las demás funcionalidades del frontend.
