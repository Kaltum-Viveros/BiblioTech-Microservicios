# BiblioTech — Sistema de gestión de biblioteca

Proyecto académico de **Arquitectura de Software** para la gestión de usuarios, catálogo bibliográfico y circulación de ejemplares. El sistema original se desarrolló con Angular, Django REST Framework y MySQL; la rama `dev` está en proceso de migración a una **arquitectura de microservicios con bases de datos independientes y comunicación REST**.

> **Estado de esta etapa:** el **microservicio de Identidad** y su enrutamiento público mediante Nginx están implementados. **Catálogo y Circulación todavía no están desplegados como microservicios**. Por tanto, las pantallas de Angular relacionadas con esos módulos pueden mostrar errores de carga (HTTP 404) hasta que se complete su migración. El frontend original se mantiene sin cambios.

## 1. Alcance y estado de implementación

| Componente | Estado en `dev` | Responsabilidad |
|---|---|---|
| `ms-identidad` | **Implementado** | Autenticación, sesiones, roles, usuarios y consultas REST internas |
| `db-identidad` | **Implementado** | Base MySQL exclusiva de Identidad (`db_identidad`) |
| `api_gateway` | **Implementado para Identidad** | Punto de entrada Nginx, enrutamiento público y protección de rutas internas |
| `frontend` | **Conservado** | Interfaz Angular original, sin reescribir sus servicios HTTP |
| `ms-catalogo` | **Pendiente** | Libros, autores, categorías, ejemplares y consultas de catálogo |
| `ms-circulacion` | **Pendiente** | Préstamos, devoluciones, sanciones, pagos y reglas relacionadas |

**Funcionalidades disponibles en esta etapa:** inicio y cierre de sesión; token Bearer opaco; consulta de la sesión; permisos para estudiante, docente y bibliotecario; listado, registro y modificación de usuarios; consulta de roles; validación de tokens y resolución de usuarios mediante una API interna protegida.

**Dependencia todavía pendiente:** promover a bibliotecario a un usuario existente requiere consultar a Circulación para comprobar que no tenga préstamos activos. Como Circulación aún no está disponible, Identidad responde `503` para ese cambio cuando no puede efectuar la verificación, sin guardar la actualización. Las demás operaciones admitidas de gestión de usuarios continúan disponibles.

## 2. Arquitectura

```text
                    Navegador / Angular
                    http://localhost:4200
                             |
                             | HTTP / JSON / Bearer
                             v
                    Nginx API Gateway
                    http://localhost:8000
                             |
                             | Rutas públicas de Identidad
                             v
                    ms-identidad (Django)
                    Puerto interno: 8000
                             |
                             | Django ORM
                             v
                    db-identidad (MySQL 8.4)
                    Volumen: identidad_mysql_data

       Próximos microservicios: ms-catalogo y ms-circulacion
       Consultarán Identidad por REST en la red Docker `api`.
       Cada uno tendrá su propia base de datos.
```

El código del **monolito de referencia** permanece en `backend/`, pero **no se ejecuta en el `compose.yaml` actual**. No se deben compartir tablas, relaciones ORM ni claves foráneas entre bases de diferentes microservicios. La comunicación entre servicios se realiza mediante contratos HTTP REST.

La red Docker `api` conecta los servicios HTTP. La red `datos_identidad` es interna y conecta únicamente Identidad con su base MySQL.

## 3. Tecnologías

| Área | Tecnología en el repositorio |
|---|---|
| Frontend | Angular 21.2, TypeScript 5.9, Node.js 24 |
| Microservicio | Python 3.12, Django 5.2, Django REST Framework 3.16 |
| Persistencia | MySQL 8.4 y `mysqlclient` |
| Gateway | Nginx 1.28 Alpine |
| Infraestructura | Docker y Docker Compose v2 |
| Pruebas | Django Test Runner, pruebas HTTP con Python y Postman; pruebas Angular mediante el proyecto frontend |

Las dependencias de Identidad se declaran en `backend/ms-identidad/requirements.txt`; las del frontend, en `frontend/package.json` y `frontend/package-lock.json`.

## 4. Organización del repositorio

```text
BiblioTech-Microservicios/
├── compose.yaml
├── .env.example
├── backend/
│   ├── ms-identidad/          # Microservicio independiente en ejecución
│   │   ├── config/
│   │   ├── identidad/
│   │   ├── scripts/verificar_gateway.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── biblioteca/            # Código heredado del monolito; referencia
├── frontend/                  # Angular original
├── infra/nginx/default.conf   # Enrutamiento y seguridad del gateway
└── Documentacion/
    ├── API/                    # Contratos externos, internos y gateway
    ├── Postman/                # Colección unificada de Identidad
    └── ...                     # Diagramas, prototipos y reglas de negocio
```

## 5. Requisitos y puertos

Se necesita **Git**, **Docker Desktop** (o Docker Engine con Compose v2) y acceso a Internet para construir o descargar imágenes. No hace falta instalar Python, MySQL o Angular CLI en el equipo si se trabaja mediante contenedores.

| Recurso | URL o puerto local | Observación |
|---|---|---|
| Frontend Angular | `http://localhost:4200/` | Servidor Angular de desarrollo |
| Login | `http://localhost:4200/login` | Entrada de los tres perfiles |
| API Gateway | `http://localhost:8000/` | Entrada pública del backend |
| API pública de Identidad | `http://localhost:8000/api/` | Requiere ruta concreta |
| Health de Identidad | `http://localhost:8000/health/ready/` | Responde `200` si MySQL está disponible |
| Identidad directa | `http://localhost:18081/` | Solo `127.0.0.1`, para depuración local |
| MySQL Identidad | Puerto `3306` **solo dentro de Docker** | No se publica en el equipo anfitrión |

Los puertos locales **4200, 8000 y 18081** deben estar disponibles. La raíz `/api/` no es una página web y puede devolver `404`; utiliza un endpoint específico.

## 6. Instalación desde cero (rama `dev`)

Todos los comandos siguientes se ejecutan desde la **raíz del repositorio**, donde está `compose.yaml`.

### 6.1 Clonar la rama

```bash
git clone --branch dev https://github.com/Kaltum-Viveros/BiblioTech-Microservicios.git
cd BiblioTech-Microservicios
```

### 6.2 Preparar variables locales

En **PowerShell**:

```powershell
Copy-Item .env.example .env
```

En **Git Bash** o Linux:

```bash
cp .env.example .env
```

Edita `.env` para configurar las variables ya previstas:

```dotenv
# Identidad — valores ilustrativos de desarrollo (sustituir localmente)
IDENTIDAD_DB_NAME=db_identidad
IDENTIDAD_DB_USER=identidad_app
IDENTIDAD_DB_PASSWORD=CAMBIAR_CLAVE_MYSQL_APP
IDENTIDAD_DB_ROOT_PASSWORD=CAMBIAR_CLAVE_MYSQL_ROOT
IDENTIDAD_DJANGO_SECRET_KEY=CAMBIAR_SECRETO_DJANGO
IDENTIDAD_INTERNAL_API_KEY=CAMBIAR_CLAVE_SERVICIO_INTERNA
AUTH_TOKEN_TTL_HOURS=8
DJANGO_TIME_ZONE=America/Mexico_City
```

Se pueden utilizar valores **fijos** para desarrollo; no es necesario regenerarlos al iniciar. La clave de servicio debe cumplir la validación mínima configurada en Identidad (**16 caracteres** en el entorno de desarrollo). **No publiques `.env`**, contraseñas ni tokens: son credenciales aunque el entorno sea académico.

> Cambiar las variables de contraseña de MySQL **no modifica automáticamente** las credenciales de un volumen que ya fue inicializado. Si tienes datos existentes, consérvalos y actualiza la configuración de forma compatible; no borres el volumen para resolver un problema de conexión.

### 6.3 Construir y levantar los servicios

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Los servicios definidos actualmente son `db-identidad`, `ms-identidad`, `api_gateway` y `frontend`. `db-identidad` y `ms-identidad` incluyen comprobaciones de salud. El arranque de Angular puede requerir tiempo para compilar.

### 6.4 Aplicar migraciones de Identidad

```powershell
docker compose exec ms-identidad python manage.py migrate
```

Las migraciones pertenecen únicamente a `db_identidad` y no requieren ejecutar el monolito. Para consultar el esquema aplicado:

```powershell
docker compose exec ms-identidad python manage.py showmigrations identidad
```

### 6.5 Cargar usuarios y roles de demostración

El seed requiere la variable `IDENTIDAD_SEED_PASSWORD` (al menos 12 caracteres). Se puede proporcionar solo a la ejecución del comando:

```powershell
docker compose exec -e "IDENTIDAD_SEED_PASSWORD=Biblioteca123*" ms-identidad python manage.py seed_identidad_demo
```

Cuentas de demostración:

| Correo | Rol |
|---|---|
| `esme@bibliotech.com` | Estudiante |
| `saul@bibliotech.com` | Docente |
| `kalt@bibliotech.com` | Bibliotecario |

Para una instalación nueva, las tres cuentas reciben la contraseña indicada al ejecutar el seed. Si las cuentas ya existían, el seed **no sustituye sus contraseñas** por defecto. Para restablecerlas explícitamente:

```powershell
docker compose exec -e "IDENTIDAD_SEED_PASSWORD=Biblioteca123*" ms-identidad python manage.py seed_identidad_demo --reset-passwords
```

**Atención:** `--reset-passwords` revoca los tokens activos de esas cuentas; úsalo solamente cuando sea necesario.

### 6.6 Comprobar disponibilidad

```powershell
docker compose ps
curl.exe -i http://localhost:8000/health/live/
curl.exe -i http://localhost:8000/health/ready/
curl.exe -I http://localhost:4200/
```

Cuando el frontend esté disponible, abre `http://localhost:4200/login`. Si el navegador muestra `ERR_CONNECTION_REFUSED`, verifica primero que el contenedor `frontend` esté en ejecución y revisa sus logs; no es necesariamente un problema de la API.

## 7. API pública del microservicio de Identidad

El frontend consume las siguientes rutas a través del gateway (`http://localhost:8000`):

| Método | Ruta | Acceso |
|---|---|---|
| `POST` | `/api/auth/login/` | Público; credenciales válidas |
| `POST` | `/api/auth/logout/` | Bearer |
| `GET` | `/api/auth/me/` | Bearer |
| `GET` | `/api/auth/access/lector/` | Estudiante o docente |
| `GET` | `/api/auth/access/bibliotecario/` | Bibliotecario |
| `GET` | `/api/usuarios/` | Bibliotecario; paginación |
| `POST` | `/api/usuarios/` | Bibliotecario |
| `GET` | `/api/usuarios/{usuario_id}/` | Bibliotecario |
| `PATCH` | `/api/usuarios/{usuario_id}/` | Bibliotecario |
| `GET` | `/api/roles/` | Bibliotecario |
| `GET` | `/health/live/` | Público |
| `GET` | `/health/ready/` | Público |

La autenticación utiliza **tokens Bearer opacos** que se almacenan mediante hash SHA-256 en Identidad. Las contraseñas se almacenan mediante el sistema de hashing de Django. La autorización se verifica en el backend, no solo mediante los guards de Angular.

Ejemplo de login:

```http
POST http://localhost:8000/api/auth/login/
Content-Type: application/json
```

```json
{
  "email": "esme@bibliotech.com",
  "password": "<contrasena_del_seed>"
}
```

El contrato completo de campos, códigos y reglas de negocio está en [API externa de Identidad](Documentacion/API/ms_identidad_externa.md).

## 8. API interna y comunicación REST

Los futuros microservicios que necesiten verificar un token o consultar usuarios utilizarán la dirección interna de Docker:

`http://ms-identidad:8000/api/internal/`

| Método | Ruta | Función |
|---|---|---|
| `POST` | `/api/internal/auth/validar/` | Validar un token opaco y devolver usuario y rol |
| `GET` | `/api/internal/usuarios/{usuario_id}/` | Consultar identidad por ID |
| `POST` | `/api/internal/usuarios/resolver/` | Resolver hasta 100 IDs por solicitud |

Todas estas operaciones requieren la cabecera `X-Internal-Service-Key`, distinta del Bearer del usuario. El consumidor debe comprobar `valido: true` y el rol antes de autorizar una operación. **Nginx rechaza públicamente `/api/internal/`**; en desarrollo puede probarse directamente desde `http://localhost:18081`.

Consulta [API interna de Identidad](Documentacion/API/ms_identidad_interna.md) y [API Gateway](Documentacion/API/gateway.md).

## 9. Compatibilidad con Angular y limitaciones actuales

El frontend original permanece sin cambios y su `API_BASE_URL` sigue apuntando a `http://localhost:8000/api`. Las rutas y estructuras de login, sesión, roles y usuarios se conservaron para permitir su funcionamiento sin reescribir los servicios Angular.

**Disponible para comprobar:** login por los tres perfiles, restauración y cierre de sesión, navegación por rol, listado/registro/edición de usuarios y consulta de roles.

**Todavía no disponible en los microservicios:** catálogo, libros, ejemplares, autores, categorías, préstamos, devoluciones, sanciones y bloqueos. Las pantallas de esos módulos permanecen en Angular, pero sus solicitudes pueden devolver `404` del gateway hasta implementar los servicios correspondientes. Esto es un estado esperado de la migración, no una indicación de que el frontend deba volver a conectarse al monolito.

## 10. Pruebas y verificación

### 10.1 Suite Django de Identidad

```powershell
docker compose exec ms-identidad python manage.py check
docker compose exec ms-identidad python manage.py makemigrations --check --dry-run identidad
docker compose exec ms-identidad python manage.py test identidad.tests -v 2
```

**Última ejecución compartida durante la etapa C07:** **86 pruebas aprobadas**. Estas pruebas incluyen modelos, seed, autenticación, permisos, usuarios, contratos internos y salud del servicio. Django crea y destruye una base temporal `test_db_identidad`.

Si MySQL impide crear esa base temporal, revisa los permisos del usuario `identidad_app` sobre `test_db_identidad`; no reemplaces la base de aplicación ni elimines el volumen persistente.

### 10.2 Integración HTTP del gateway

```powershell
docker compose exec api_gateway nginx -t
docker compose exec -e "GATEWAY_TEST_PASSWORD=Biblioteca123*" ms-identidad python scripts/verificar_gateway.py
```

**Última ejecución compartida durante la etapa C07:** **19 pruebas HTTP aprobadas**. Validan enrutamiento, autenticación por rol, CORS, rechazo de rutas internas, errores esperados y revocación de sesiones.

### 10.3 Colección única Postman de Identidad

Importa [BiblioTech_MS_Identidad.postman_collection.json](Documentacion/Postman/BiblioTech_MS_Identidad.postman_collection.json). Contiene **82 peticiones** para la API externa, la API interna y las comprobaciones del gateway, con casos de éxito y error intencional.

Configura las variables `password_demo`, `password_nuevo` y `internal_key` en Postman; no deben almacenarse en el archivo versionado. Ejecuta la colección en orden con una sola iteración. **La ejecución completa de esta colección sigue pendiente de confirmación**.

### 10.4 Comprobaciones del frontend

```powershell
docker compose up -d --build frontend
docker compose ps -a
docker compose logs --tail=100 frontend
docker compose exec frontend npm run build
```

Comprueba visualmente el login, el perfil mostrado, los permisos, el listado, registro y edición de usuarios y el logout. **La validación visual completa todavía está pendiente**, incluso si las pruebas Django y de gateway han pasado.

## 11. Operación y diagnóstico

```powershell
# Arrancar todos los servicios
docker compose up -d

# Estado de contenedores
docker compose ps -a

# Logs de infraestructura y frontend
docker compose logs --tail=100 db-identidad ms-identidad api_gateway frontend

# Comprobación de Nginx
docker compose exec api_gateway nginx -t

# Reiniciar únicamente Angular
docker compose restart frontend

# Detener sin borrar los datos de MySQL
docker compose down
```

| Síntoma | Qué verificar |
|---|---|
| `localhost:4200` rechaza la conexión | `docker compose ps -a` y `docker compose logs frontend`; levantar `frontend` |
| Angular abre pero no inicia sesión | `health/ready/`, seed, contraseña usada, respuesta de `/api/auth/login/` |
| Login funciona pero Catálogo muestra `404` | Catálogo aún no está migrado: el gateway no lo enruta al monolito |
| Una ruta pública responde `503` | Estado de `ms-identidad`, logs del gateway y dependencia consultada |
| Cambiar lector a bibliotecario responde `503` | Circulación aún no responde al contrato de préstamos activos |
| Fallo de autenticación tras resetear el seed | El reset revoca sesiones; iniciar sesión nuevamente |
| Error de creación de `test_db_identidad` | Privilegios MySQL para la base temporal de pruebas |
| Problemas de Docker por OneDrive | Considerar clonar en una carpeta local no sincronizada |

**No uses `docker compose down -v`** si necesitas conservar `db_identidad`; esa opción elimina también el volumen persistente.

## 12. Documentación del proyecto

- [Índice de contratos REST](Documentacion/API/README.md).
- [API externa de Identidad](Documentacion/API/ms_identidad_externa.md).
- [API interna de Identidad](Documentacion/API/ms_identidad_interna.md).
- [Contrato del API Gateway](Documentacion/API/gateway.md).
- [Colección unificada de Identidad](Documentacion/Postman/BiblioTech_MS_Identidad.postman_collection.json).
- [Contratos históricos de préstamos](Documentacion/API/prestamos.md) y [catálogo](Documentacion/API_catalogo.md).
- [Documentación y diagramas de microservicios](Documentacion/Documentacion%20microservicios/).
- [Diagramas de flujo](Documentacion/DiagramasDeFlujo/).
- [Diagramas de navegación](Documentacion/DiagramasDeNavegacion/).
- [Prototipos de interfaz](Documentacion/PrototipoUI/).

Los contratos de las funciones aún no migradas describen el **sistema original** y se conservarán como referencia para implementar Catálogo y Circulación.

## 13. Alcance del despliegue

El Compose actual está orientado a **desarrollo y demostración académica**: utiliza el servidor de desarrollo de Django, `ng serve`, `DJANGO_DEBUG=1` y credenciales locales. No representa un despliegue de producción. Antes de exponerlo públicamente serían necesarios servidores de producción, HTTPS, gestión segura y rotación de secretos, controles de red, respaldos y políticas de observabilidad.

**Estado de cierre de Identidad:** backend y gateway implementados, con **86 pruebas Django y 19 pruebas HTTP del gateway aprobadas** en las ejecuciones compartidas. La aceptación visual del frontend y la ejecución total de Postman deben registrarse por separado antes de afirmar que el ciclo integral de pruebas está completo.
