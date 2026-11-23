# Contratos de API — Sistema de Gestión de Biblioteca

## Objetivo

Este directorio centraliza los contratos HTTP de comunicación entre el frontend Angular, el API Gateway y los microservicios desarrollados con Django REST Framework.

Corresponde al entregable 2.4 del proyecto BiblioTech.

Los contratos documentan los endpoints, sus restricciones de autenticación, permisos, validaciones, respuestas y reglas de negocio.

La arquitectura actual separa las responsabilidades en microservicios independientes. Cada microservicio administra su propia base de datos y puede comunicarse con otros servicios mediante contratos REST internos.

Actualmente, el microservicio de Identidad está implementado. Los contratos de Catálogo y Circulación se conservan como referencia funcional hasta completar su migración.

## Convenciones generales

- URL base pública local: `http://localhost:8000/api/`.
- API Gateway: Nginx.
- Formato de intercambio: JSON.
- Fechas: `YYYY-MM-DD`.
- Fechas y horas: ISO 8601.
- Autenticación pública: `Authorization: Bearer <token>`.
- Excepción: `POST /api/auth/login/`, que no requiere autenticación previa.
- Autenticación entre microservicios: `X-Internal-Service-Key`.
- Identificadores: generados por MySQL y administrados por el microservicio propietario.
- Permisos: verificados en el backend.
- Las rutas públicas se consumen a través del API Gateway.
- Las rutas internas no se exponen mediante el gateway público.

### Comunicación entre microservicios

Los microservicios utilizan HTTP REST para intercambiar información sin compartir directamente sus bases de datos.

En el entorno Docker, los servicios se comunican mediante sus nombres de servicio y la red interna correspondiente.

Por ejemplo, otros microservicios podrán consultar Identidad mediante:

`http://ms-identidad:8000/api/internal/`

Durante el desarrollo, sus endpoints internos también pueden probarse localmente mediante:

`http://localhost:18081/api/internal/`

Este último acceso se utiliza exclusivamente para desarrollo y pruebas.

## Códigos HTTP generales

| Código | Significado |
|---|---|
| 200 | Consulta u operación exitosa |
| 201 | Recurso creado |
| 204 | Operación exitosa sin cuerpo |
| 400 | Parámetros o datos inválidos |
| 401 | Autenticación requerida o inválida |
| 403 | Usuario sin autorización o clave interna incorrecta |
| 404 | Recurso, página o ruta inexistente o no disponible |
| 405 | Método HTTP no permitido |
| 409 | Conflicto con reglas de negocio, cuando corresponda al contrato |
| 503 | Servicio o dependencia temporalmente no disponible |

Los códigos pueden variar según el contrato de cada operación.

En la validación interna de tokens, una respuesta HTTP 200 no garantiza que el token sea válido. El servicio consumidor debe comprobar el campo `valido`.

## Índice de contratos

| Módulo | Operaciones | Documento |
|---|---|---|
| MS Identidad — API externa | Login, logout, sesiones, permisos, usuarios y roles | [ms_identidad_externa.md](ms_identidad_externa.md) |
| MS Identidad — API interna (C06) | Validación de tokens y consultas REST entre microservicios | [ms_identidad_interna.md](ms_identidad_interna.md) |
| API Gateway (C07) | Enrutamiento público, CORS, seguridad y control de acceso | [gateway.md](gateway.md) |
| 3.3 Libros y ejemplares | Administración bibliográfica | [libros_ejemplares.md](libros_ejemplares.md) |
| 3.4 Catálogo | Búsqueda y disponibilidad | [API_catalogo.md](../API_catalogo.md) |
| 3.5 Préstamos | Registro, elegibilidad y listado administrativo | [prestamos.md](prestamos.md) |
| 3.6 Devoluciones | Registro y multas por retraso | [devoluciones.md](devoluciones.md) |
| 3.7 Bloqueos | Restricciones por atrasos prolongados | [prestamos.md](prestamos.md), [mis_prestamos.md](mis_prestamos.md) |
| 3.8 Sanciones y pagos | Consulta, detalle y registro de pagos | [sanciones.md](sanciones.md) |
| 3.9 Mis préstamos | Historial y estado de cuenta del lector | [mis_prestamos.md](mis_prestamos.md) |
| 3.9 Mis sanciones | Multas y bloqueos propios | [mis_sanciones.md](mis_sanciones.md) |

**Nota:** Los contratos de Libros, Catálogo, Préstamos, Devoluciones, Bloqueos y Sanciones documentan las funcionalidades del sistema original. Permanecen como referencia durante la migración y no implican que sus endpoints ya estén disponibles en los nuevos microservicios.

## Microservicio de Identidad

El microservicio de Identidad administra usuarios, roles, credenciales y sesiones de acceso.

Su API externa permite al frontend autenticarse, consultar la sesión actual y administrar usuarios según los permisos del rol correspondiente.

Su API interna permite que otros microservicios validen tokens y consulten información de usuarios mediante REST, sin conectarse directamente a `db_identidad`.

Las operaciones públicas se encuentran bajo `/api/` y son atendidas mediante el API Gateway.

Las operaciones internas se encuentran bajo `/api/internal/` y requieren autenticación entre servicios.

Los contratos correspondientes se encuentran en:

- [API externa de Identidad](ms_identidad_externa.md).
- [API interna de Identidad](ms_identidad_interna.md).

## API Gateway

El API Gateway funciona como punto de entrada para las solicitudes HTTP del frontend.

En la implementación actual, Nginx dirige las rutas públicas de autenticación, usuarios y roles al microservicio de Identidad.

También se encarga de:

- Conservar las cabeceras necesarias para la autenticación Bearer.
- Permitir las solicitudes CORS configuradas para Angular.
- Rechazar el acceso público a `/api/internal/`.
- Responder con HTTP 404 para rutas que todavía no tienen un microservicio asignado.
- Gestionar errores de disponibilidad de los servicios backend.

Las rutas de Catálogo y Circulación se incorporarán cuando sus respectivos microservicios estén implementados.

La configuración de Nginx se encuentra en `infra/nginx/default.conf`.

El contrato y las reglas de enrutamiento se documentan en [gateway.md](gateway.md).

## Préstamos administrativos

El contrato funcional de préstamos contempla dos operaciones principales sobre `/api/prestamos/`:

- `GET`: listado administrativo con búsqueda, filtros por estado y paginación.
- `POST`: registro de préstamos.

Ambas requieren rol `bibliotecario`.

La consulta personal permanece separada en `GET /api/prestamos/mios/`, exclusiva para estudiantes y docentes.

Estas operaciones forman parte de los contratos del sistema original y deberán implementarse en el microservicio correspondiente durante la migración a la nueva arquitectura.

## Mantenimiento de los contratos

Cada contrato debe documentar:

1. Ruta y método HTTP.
2. Roles o servicios autorizados.
3. Parámetros de entrada.
4. Reglas de validación.
5. Respuestas de éxito.
6. Errores HTTP.
7. Reglas de negocio aplicadas.
8. Pruebas y dependencias.

Los contratos deben actualizarse cuando cambien las rutas, las respuestas, las restricciones del backend o la distribución de responsabilidades entre microservicios.

Las operaciones internas y externas deben documentarse de forma separada.

No deben incluirse tokens activos, contraseñas reales, claves de servicio ni información personal sensible.

## Postman

Las colecciones se encuentran en `Documentacion/Postman/`.

### Microservicio de Identidad

La colección unificada de Identidad se denomina:

`BiblioTech_MS_Identidad.postman_collection.json`

[Consultar colección Postman de Identidad](../Postman/BiblioTech_MS_Identidad.postman_collection.json)

Incluye pruebas de:

- Disponibilidad y salud del microservicio.
- Autenticación y cierre de sesión.
- Permisos de estudiante, docente y bibliotecario.
- Registro, consulta y modificación de usuarios.
- Consulta de roles.
- Validación de tokens mediante la API interna.
- Consulta individual y múltiple de usuarios entre microservicios.
- Seguridad del API Gateway y bloqueo de rutas internas.
- CORS, respuestas HTTP y errores intencionales.
- Revocación de sesiones.

La colección utiliza variables propias para las URL, tokens, identificadores y credenciales de desarrollo. No requiere un archivo adicional de entorno.

Las credenciales deben configurarse localmente en Postman antes de ejecutar las pruebas.

### Otros módulos

Las colecciones históricas de Préstamos, Catálogo y las demás funcionalidades se conservan como referencia de sus respectivos contratos.

Se actualizarán conforme los endpoints sean migrados a los microservicios correspondientes.

## Pruebas automatizadas

El microservicio de Identidad cuenta con pruebas automatizadas de modelos, autenticación, sesiones, permisos, usuarios, roles y contratos REST internos.

Las pruebas se ejecutan mediante:

```bash
docker compose exec ms-identidad python manage.py test identidad.tests -v 2
```

**Último resultado verificado:** 86 pruebas aprobadas.

El API Gateway también cuenta con pruebas de integración HTTP:

```bash
docker compose exec -e GATEWAY_TEST_PASSWORD="Biblioteca123*" ms-identidad python scripts/verificar_gateway.py
```

**Último resultado verificado:** 19 pruebas aprobadas.

Estas pruebas verifican el funcionamiento del enrutamiento público, autenticación, permisos, seguridad, CORS y respuestas del gateway.

La colección Postman complementa las pruebas automatizadas y permite comprobar manualmente los contratos externos e internos.

## Estado de implementación

| Componente | Estado |
|---|---|
| Microservicio de Identidad | Implementado |
| API externa de Identidad | Implementada |
| API interna de Identidad | Implementada |
| API Gateway para Identidad | Implementado |
| Pruebas automatizadas de Identidad | 86 aprobadas |
| Pruebas de integración del Gateway | 19 aprobadas |
| Microservicio de Catálogo | Pendiente de implementación |
| Microservicio de Circulación | Pendiente de implementación |

La integración visual completa con Angular y la ejecución de la colección Postman unificada deben verificarse antes de considerar finalizado el ciclo completo de pruebas del microservicio.

Los contratos se mantendrán actualizados durante la incorporación de los siguientes microservicios de BiblioTech.
