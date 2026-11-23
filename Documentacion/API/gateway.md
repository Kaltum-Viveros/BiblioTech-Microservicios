# Contrato de integración — API Gateway de BiblioTech

## 1. Información general

- **Componente:** `api_gateway`.
- **Implementación:** C07 — Integración del gateway con las rutas públicas de Identidad.
- **Tecnología:** Nginx 1.28 Alpine, ejecutado mediante Docker Compose.
- **Archivo de configuración:** `infra/nginx/default.conf`.
- **URL pública local:** `http://localhost:8000`.
- **Frontend consumidor:** Angular en `http://localhost:4200`.
- **Microservicio conectado actualmente:** `ms-identidad` (`http://ms-identidad:8000` dentro de Docker).
- **Objetivo:** centralizar el acceso público al backend y enviar cada ruta al microservicio propietario, sin exponer contratos internos ni compartir bases de datos.

El gateway **no implementa reglas de negocio, autenticación de usuarios ni permisos por rol**. Su responsabilidad es el **enrutamiento HTTP y la protección de rutas**. Django REST Framework valida credenciales, tokens, datos y permisos.

## 2. Topología y redes

```text
Angular / Postman
      |
      | http://localhost:8000
      v
  api_gateway (Nginx)
      |
      | HTTP REST, red Docker `api`
      v
  ms-identidad:8000
      |
      | ORM, red `datos_identidad`
      v
  db-identidad (MySQL)
```

El servicio Nginx escucha en el **puerto 80 del contenedor**, publicado como `127.0.0.1:8000` en el equipo anfitrión. El puerto directo `127.0.0.1:18081` corresponde a Identidad y **no pasa por el gateway**; existe únicamente para depuración y pruebas locales.

La red Docker `api` permite que Nginx se comunique con Identidad. La base MySQL no se expone al gateway ni al navegador.

## 3. Contratos públicos enrutados a Identidad

El gateway conserva el método HTTP, la ruta y la cadena de consulta; no altera el cuerpo JSON. El proveedor decide qué métodos admite cada endpoint.

| Método admitido por Django | Ruta pública | Servicio destino | Función |
|---|---|---|---|
| `POST` | `/api/auth/login/` | Identidad | Autenticar usuario |
| `POST` | `/api/auth/logout/` | Identidad | Revocar sesión |
| `GET` | `/api/auth/me/` | Identidad | Consultar sesión actual |
| `GET` | `/api/auth/access/lector/` | Identidad | Verificar acceso de estudiante o docente |
| `GET` | `/api/auth/access/bibliotecario/` | Identidad | Verificar acceso administrativo |
| `GET` | `/api/usuarios/` | Identidad | Listar usuarios y paginarlos |
| `POST` | `/api/usuarios/` | Identidad | Registrar usuario |
| `GET` | `/api/usuarios/{usuario_id}/` | Identidad | Obtener usuario |
| `PATCH` | `/api/usuarios/{usuario_id}/` | Identidad | Actualizar usuario parcialmente |
| `GET` | `/api/roles/` | Identidad | Consultar roles |
| `GET` | `/health/live/` | Identidad | Comprobar que Django responde |
| `GET` | `/health/ready/` | Identidad | Comprobar disponibilidad de MySQL |

La expresión regular de `infra/nginx/default.conf` acepta **estas rutas exactas**, incluido el formato `/api/usuarios/{id}/` con un identificador numérico. Una ruta con nombre desconocido o sin la barra final no coincide con la ruta pública declarada y se trata como ruta no asignada.

El gateway no restringe por método: una solicitud con método no permitido que coincida con una ruta configurada llegará a Django, que puede responder `405 Method Not Allowed`.

Los endpoints de salud están fuera de `/api/`, y ambos permiten consultar el estado del microservicio sin token.

## 4. Bloqueo de la API interna

Las siguientes rutas están **bloqueadas intencionalmente** por Nginx:

- `/api/internal`
- `/api/internal/` y cualquier subruta, por ejemplo `/api/internal/usuarios/1/`
- `/internal`
- `/internal/` y cualquier subruta

**Resultado esperado:** `HTTP 404 Not Found` generado por el gateway, incluso si la petición intenta incluir un token Bearer o una clave de servicio correcta.

Ejemplo de verificación pública:

```powershell
curl.exe -i http://localhost:8000/api/internal/usuarios/1/
```

El resultado debe ser `404`, **no `200` ni `403` del backend**.

La API interna de Identidad sí está disponible para futuros microservicios dentro de Docker en:

`http://ms-identidad:8000/api/internal/`

En desarrollo se puede probar directamente desde el anfitrión:

`http://localhost:18081/api/internal/`

Dichas solicitudes requieren `X-Internal-Service-Key`. El puerto directo `18081` no debe publicarse como entrada general en producción. Consulta [ms_identidad_interna.md](ms_identidad_interna.md) para los contratos internos completos.

## 5. Cabeceras y autenticación

Para las rutas públicas enrutadas, Nginx configura o conserva:

| Cabecera | Tratamiento |
|---|---|
| `Host` | Se envía al upstream a partir de `$host` |
| `X-Real-IP` | Dirección del cliente (`$remote_addr`) |
| `X-Forwarded-For` | Cadena de direcciones de proxy (`$proxy_add_x_forwarded_for`) |
| `X-Forwarded-Proto` | Esquema HTTP/HTTPS recibido por Nginx |
| `Authorization` | Se reenvía el valor recibido, incluido `Bearer <token>` |
| `X-Internal-Service-Key` | **Se elimina** en las rutas públicas (`""`) |

Identidad autentica al usuario usando su token Bearer opaco, comprueba su vigencia y revocación y aplica las reglas de permisos del backend. En particular:

- `POST /api/auth/login/` no requiere sesión previa.
- `GET /api/auth/me/` y `POST /api/auth/logout/` requieren token válido.
- Las operaciones de `/api/usuarios/` y `/api/roles/` requieren rol bibliotecario.
- Los endpoints de control de acceso requieren el rol correspondiente.

**El gateway no considera que un usuario esté autorizado por el simple hecho de que envíe una cabecera `Authorization`.**

## 6. CORS y comunicación con Angular

Angular utiliza `API_BASE_URL = 'http://localhost:8000/api'`, conservado sin cambios. El origen local permitido por Django es `http://localhost:4200`.

Las peticiones a las rutas públicas de Identidad atraviesan Nginx y llegan a Django, donde `django-cors-headers` gestiona CORS, incluidas las solicitudes preflight `OPTIONS` y las respuestas de error autorizadas para el origen permitido.

Nginx añade `Access-Control-Allow-Origin: http://localhost:4200` y `Vary: Origin` a sus respuestas JSON de **ruta no asignada** y **servicio no disponible**, para que Angular pueda recibir el error correspondiente.

**Nota:** esta configuración está pensada para el origen local indicado. No debe interpretarse como una autorización de cualquier origen ni como una política de CORS de producción.

### Prueba preflight

```powershell
curl.exe -i -X OPTIONS `
  -H "Origin: http://localhost:4200" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: authorization,content-type" `
  http://localhost:8000/api/auth/login/
```

Para esta ruta pública, se espera una respuesta preflight satisfactoria con `Access-Control-Allow-Origin: http://localhost:4200`.

## 7. Rutas sin microservicio asignado

En la fase actual solo Identidad tiene rutas públicas registradas en Nginx. Las llamadas que no coinciden con esas rutas se responden directamente desde el gateway:

**HTTP 404 Not Found**

```json
{
  "detail": "Ruta no disponible en el gateway."
}
```

Ejemplos:

- `GET /api/catalogo/`
- `GET /api/libros/`
- `GET /api/ejemplares/`
- `GET /api/prestamos/`
- `GET /api/sanciones/`
- `GET /api/`

Esta respuesta es **esperada mientras `ms-catalogo` y `ms-circulacion` no estén implementados**. No significa que el monolito deba volver a ejecutarse. Las pantallas Angular correspondientes conservarán sus llamadas, que serán atendidas cuando los nuevos microservicios se incorporen al gateway.

## 8. Errores HTTP y disponibilidad

| Código | Origen habitual | Interpretación |
|---|---|---|
| `200` | Identidad | Consulta, login o comprobación exitosa |
| `201` | Identidad | Usuario creado |
| `204` | Identidad | Logout exitoso, sin cuerpo |
| `400` | Identidad | Datos de entrada inválidos |
| `401` | Identidad | Falta una sesión válida o las credenciales son incorrectas |
| `403` | Identidad | Usuario autenticado sin el rol necesario |
| `404` | Nginx | Ruta no asignada o acceso público a `/api/internal/` bloqueado |
| `404` | Identidad | Usuario inexistente o consulta no encontrada en una ruta válida |
| `405` | Identidad | Método HTTP no permitido para un endpoint válido |
| `503` | Identidad | Dependencia de negocio no disponible, por ejemplo Circulación durante una promoción de rol |
| `503` | Gateway | Indisponibilidad o timeout del upstream, convertidos desde errores Nginx `502/504` |

Para fallos de conexión o timeout del upstream, el gateway responde con:

```json
{
  "detail": "El servicio requerido no esta disponible temporalmente."
}
```

El archivo Nginx configura `proxy_intercept_errors off`: una respuesta `503` generada por Django, por ejemplo ante la indisponibilidad de Circulación, **se conserva con su propio cuerpo**. El gateway no debe sustituir el mensaje de negocio por otro genérico.

## 9. Resolución del upstream y tiempos

La configuración utiliza un upstream llamado `identidad_publica`, con resolución de DNS de Docker:

```nginx
upstream identidad_publica {
    zone identidad_publica 64k;
    resolver 127.0.0.11 valid=10s ipv6=off;
    server ms-identidad:8000 resolve;
}
```

Esto permite actualizar la dirección IP del contenedor `ms-identidad` cuando Docker lo recrea, sin fijar manualmente su IP.

Los tiempos configurados para las rutas de Identidad son:

- `proxy_connect_timeout 3s`
- `proxy_send_timeout 30s`
- `proxy_read_timeout 30s`

La resolución y la recuperación tras recrear un contenedor pueden presentar un fallo temporal durante la transición.

## 10. Pruebas de integración

### 10.1 Validación de sintaxis

```powershell
docker compose config --quiet
docker compose exec api_gateway nginx -t
```

Cuando se modifica `infra/nginx/default.conf` y la sintaxis es correcta, se puede recargar sin reconstruir la imagen:

```powershell
docker compose exec api_gateway nginx -s reload
```

### 10.2 Pruebas manuales básicas

```powershell
# Identidad operativa
curl.exe -i http://localhost:8000/health/live/
curl.exe -i http://localhost:8000/health/ready/

# API interna inaccesible públicamente
curl.exe -i http://localhost:8000/api/internal/usuarios/1/

# Ruta sin servicio asignado
curl.exe -i http://localhost:8000/api/catalogo/

# Un recurso público protegido sin Bearer
curl.exe -i http://localhost:8000/api/roles/
```

Se esperan respectivamente `200`, `200`, `404`, `404` y `401` cuando todos los servicios necesarios están disponibles.

### 10.3 Pruebas HTTP automatizadas del gateway

**Script:** `backend/ms-identidad/scripts/verificar_gateway.py`.

```powershell
docker compose exec -e "GATEWAY_TEST_PASSWORD=Biblioteca123*" ms-identidad python scripts/verificar_gateway.py
```

La suite **verifica 19 escenarios**: salud, login correcto e incorrecto, sesión, permisos de los tres roles, listado y edición de usuarios, CORS, bloqueo de rutas internas, rutas sin implementar, conservación de un `503` del backend y revocación tras logout.

**Último resultado compartido de C07:** **19/19 pruebas aprobadas**. Este resultado corresponde a la ejecución comunicada durante esa fase; debe volver a comprobarse tras cambios posteriores.

### 10.4 Suite de Identidad

```powershell
docker compose exec ms-identidad python manage.py test identidad.tests -v 2
```

**Último resultado compartido de C07:** **86/86 pruebas aprobadas**. Estas pruebas no sustituyen las comprobaciones HTTP reales del gateway.

### 10.5 Postman

La colección **unificada** [BiblioTech_MS_Identidad.postman_collection.json](../Postman/BiblioTech_MS_Identidad.postman_collection.json) incluye pruebas de:

- API pública de Identidad por rol.
- API interna de Identidad mediante acceso directo de desarrollo.
- Seguridad y errores intencionales del gateway.

La colección contiene **82 peticiones**, organizadas en seis carpetas. Requiere configurar localmente las variables `password_demo`, `password_nuevo` e `internal_key`; **su ejecución completa sigue pendiente de confirmación**.

## 11. Evolución del gateway

Cuando se implementen `ms-catalogo` y `ms-circulacion`, se añadirán upstreams y reglas de enrutamiento específicas manteniendo:

1. Las URL públicas ya utilizadas por Angular.
2. La propiedad de cada ruta en su microservicio correspondiente.
3. La protección de todas las rutas `/api/internal/` frente al tráfico público.
4. La comunicación privada entre microservicios mediante REST, no mediante bases compartidas.
5. Las respuestas de error y las verificaciones CORS y Bearer.
6. Las pruebas de regresión del gateway.

**El monolito no forma parte del enrutamiento actual y no debe utilizarse como fallback.**

## 12. Referencias internas

- [Índice de contratos REST](README.md).
- [API externa de Identidad](ms_identidad_externa.md).
- [API interna de Identidad](ms_identidad_interna.md).
- [Colección Postman unificada](../Postman/BiblioTech_MS_Identidad.postman_collection.json).
- Configuración ejecutable: `infra/nginx/default.conf` (ruta desde la raíz del repositorio).

Esta documentación describe el gateway de la rama `dev` tras C07, orientado a pruebas y demostración local. Para producción se requieren HTTPS, controles adicionales de red, manejo seguro de secretos y servidores adecuados para los microservicios.
