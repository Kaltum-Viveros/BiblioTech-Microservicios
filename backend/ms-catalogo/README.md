# Microservicio de Catálogo — datos bibliográficos (3.1)

Catálogo es propietario de libros, autores, categorías y sus asociaciones. Su base
`db_catalogo` **no** almacena usuarios, ejemplares, préstamos ni sanciones.

## Datos de demostración (solo ambiente de desarrollo)

Con `ms-catalogo` y `db-catalogo` activos, y después de `migrate`:

```bash
docker compose exec -T ms-catalogo python manage.py seed_catalogo_demo
```

El comando crea 15 libros ficticios, cinco autores y cinco categorías, con
asociaciones reproducibles. Es idempotente: no duplica registros al repetirlo.
Se niega a ejecutarse si encuentra bibliografía distinta de la del seed.
**No lo ejecutes en una base destinada a recibir datos históricos.**

El seed antiguo del monolito también creaba usuarios, ejemplares y préstamos;
estas operaciones se excluyen intencionalmente.

## Importación histórica preservando identificadores

No hay un volcado real de datos del monolito dentro de este repositorio.
Para preservar los `libro_id` que usarán los ejemplares de Circulación, primero
hay que exportar **los datos reales** de la base antigua.

En una instalación operativa del backend monolítico, apuntando a su base original:

```bash
python manage.py dumpdata \
  biblioteca.Autor biblioteca.Categoria biblioteca.Libro \
  biblioteca.LibroAutor biblioteca.CategoriaLibro \
  --indent 2 --output bibliografia_monolito.json
```

Este archivo contiene datos del proyecto y **no debe agregarse a Git**.
Antes de exportar, confirmar que el monolito esté conectado a la base histórica
correcta y no a una base vacía o a la nueva base de Catálogo.
Transferirlo de forma controlada a la máquina que ejecuta Catálogo. Para
importarlo desde Git Bash, en la raíz de `BiblioTech-Microservicios`, usar:

```bash
docker compose exec -T ms-catalogo \
  python manage.py importar_bibliografia - --solo-validar \
  < bibliografia_monolito.json

# Si la validación pasa y la base destino es la correcta:
docker compose exec -T ms-catalogo \
  python manage.py importar_bibliografia - \
  < bibliografia_monolito.json
```

El argumento `-` lee desde la entrada estándar del contenedor y evita
problemas de conversión de rutas en Git Bash. La opción `--solo-validar`
comprueba los datos dentro de una transacción que **se revierte**; no guarda
registros. En MySQL, una validación que realiza inserciones dentro de una
transacción revertida puede avanzar contadores `AUTO_INCREMENT`. Esto no altera
los identificadores explícitos del fixture, pero conviene usar una base de
validación independiente cuando se migren datos reales.

El importador acepta únicamente fixtures Django de los cinco modelos
bibliográficos, conserva sus PK y las referencias entre tablas, y ordena los
registros para respetar las claves foráneas. La operación es atómica: ante un
ID conflictivo, ISBN duplicado, categoría duplicada o referencia inválida,
no se aplica **ninguna** parte del lote. Repetir el mismo archivo no duplica datos.

**Orden recomendado:** importar los datos originales sobre una base de Catálogo
recién migrada, **sin ejecutar antes** `seed_catalogo_demo`. Si el seed ya se
usó para probar, conviene utilizar otra base limpia para la importación real;
no borrar el volumen actual sin respaldo y autorización explícita.

Tras importar, comprobar IDs y cantidades con Django ORM. El hecho de que se
importen los libros no significa que se hayan importado sus ejemplares:
Circulación gestionará esa información separadamente, referenciando `libro_id`.

## Pruebas

```bash
docker compose exec -T ms-catalogo \
  python manage.py test catalogo.tests --verbosity 2
```

La primera ejecución de pruebas en MySQL puede requerir permisos del usuario de
Catálogo sobre la base temporal `test_db_catalogo`; no se requieren permisos
sobre bases de Identidad ni Circulación.

## Integración con Identidad (3.2 — CATA04)

Catálogo no almacena sesiones ni usuarios BiblioTech. Para autorizar una ruta
protegida recibe `Authorization: Bearer <token>` y realiza una solicitud HTTP
interna al proveedor de Identidad:

- `POST http://ms-identidad:8000/api/internal/auth/validar/`
- Cabecera interna: `X-Internal-Service-Key` (solo entre contenedores).
- JSON de solicitud: `{"token": "<token_Bearer>"}`.
- `HTTP 200` con `valido: true`: se construye un usuario remoto de solo lectura
  con rol; el permiso de cada vista decide si puede acceder.
- `HTTP 200` con `valido: false`: `401` público.
- Rol sin autorización: `403` público.
- Identidad inaccesible, timeout, clave interna rechazada o contrato incorrecto:
  `503` público; nunca se concede acceso por un fallo del proveedor.

El servicio utiliza las variables `IDENTIDAD_INTERNAL_API_KEY`,
`IDENTIDAD_INTERNAL_BASE_URL` y `IDENTIDAD_HTTP_TIMEOUT_SECONDS`, inyectadas
por Compose. La clave no debe colocarse en Angular, en los logs ni en Git.

Las vistas administrativas de libros, autores y categorías utilizarán
`IsAuthenticated` e `IsBibliotecario`; las vistas de consulta del catálogo
utilizarán `IsAuthenticated` y `PuedeConsultarCatalogo` (estudiante, docente o
bibliotecario). CATA04 incorpora la infraestructura de autenticación y las
pruebas con un proveedor HTTP simulado; **todavía no expone endpoints públicos**.

Para verificarla sin necesitar que Identidad esté ejecutándose:

```bash
docker compose exec -T ms-catalogo \
  python manage.py test catalogo.tests.test_autenticacion --verbosity 2
```

El contrato de respuesta de Identidad se describe en
`Documentacion/API/ms_identidad_interna.md`.

## Administración bibliográfica (3.2 — CATA05)

Se preservan los endpoints públicos del monolito (`/api/libros/`,
`/api/autores/`, `/api/categorias/` y sus detalles), con los mismos métodos,
serializadores, reglas de negocio y paginación. Solo el rol bibliotecario
puede utilizarlos. El gateway aún no los enruta; se prueban temporalmente
mediante `http://127.0.0.1:18082/api/` (puerto de depuración).

Antes de ejecutar `check`, se extraen las capas **desde el monolito incluido
en este mismo repositorio** sin sobrescribir los archivos originales:

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -T \
  -v "./backend/biblioteca:/fuentes:ro" \
  ms-catalogo python scripts/extraer_administracion.py --origen /fuentes
```

El extractor copia las 12 piezas originales de presentación, servicios y
repositorios. Actualiza `biblioteca.` por `catalogo.`, recupera la validación
estricta de campos permitidos y elimina la **dependencia de eliminación** de
libros con ejemplares: no hay endpoint público DELETE, y las existencias
pertenecen a Circulación. Los métodos de escritura existentes conservan
sus restricciones. No se copian los modelos ni los datos de otros servicios.

```bash
docker compose exec -T ms-catalogo python manage.py check
docker compose exec -T ms-catalogo python manage.py test catalogo.tests --verbosity 2
```

Nota: sin conexión a Identidad los endpoints protegidos devuelven `503`;
la suite usa un doble de su cliente HTTP para verificar lógica y permisos.
No ejecutar `seed_catalogo_demo` si la base se reservará para importar
registros reales del monolito.
