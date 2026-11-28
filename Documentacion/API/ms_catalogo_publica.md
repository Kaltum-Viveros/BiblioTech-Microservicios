# Contrato público REST — Catálogo Bibliográfico (CATA07, 3.3)

**Estado:** implementado en Catálogo y verificable con mocks; **la integración
real con Circulación queda pendiente** hasta que el equipo publique su API.
Rutas accesibles directamente en desarrollo: `http://127.0.0.1:18082`.
El gateway se configurará en CATA08. Todas las rutas requieren
`Authorization: Bearer <token>`; Identidad admite los roles estudiante,
docente y bibliotecario para lectura.

## GET `/api/catalogo/`

Devuelve paginación de Django REST Framework: `count`, `next`, `previous`,
`results`. Parámetros:

- `page` (1 en adelante), `page_size` (10 por defecto, máximo 100).
- `q` / `buscar`: título, ISBN o nombre de autor, búsqueda parcial.
- `titulo`, `isbn`: búsqueda parcial específica.
- `autor_id` / `autor`: filtro por ID positivo de autor.
- `categoria_id` / `categoria`: filtro por ID positivo de categoría.
- `orden`: `titulo_asc` (por defecto), `titulo_desc`, `titulo`, `-titulo`, `id`, `recientes`.
- `solo_disponibles=true|false` (o `1|0`), alias `disponible`: si es true,
  únicamente libros con al menos un ejemplar disponible.

Ejemplo de `results[0]`:

```json
{
  "libro_id": 7,
  "titulo": "Ingeniería de software",
  "isbn": "9780000000007",
  "fecha_publicacion": "2024-05-12",
  "autores": [{"autor_id": 3, "nombre": "Ada Lovelace"}],
  "categorias": [{"categoria_id": 2, "nombre_categoria": "Computación"}],
  "stock_total": 4,
  "stock_disponible": 2
}
```

Los valores de existencias son solo un ejemplo, no registros precargados.
Una página normal hace una consulta REST por lote a Circulación (no una
por libro). `solo_disponibles=true` requiere conocer existencias de todos los
candidatos antes de calcular `count` y paginar; la implementación envía lotes
de 100, lo cual puede ser costoso sobre catálogos grandes.

## GET `/api/catalogo/{libro_id}/`

Devuelve el objeto anterior sin envoltura de paginación. `404` si no existe.

## GET `/api/catalogo/filtros/`

Respuesta bibliográfica independiente de las existencias:

```json
{
  "autores": [{"autor_id": 3, "nombre": "Ada Lovelace"}],
  "categorias": [{"categoria_id": 2, "nombre_categoria": "Computación"}]
}
```

## Errores

- `400`: filtro o `orden` inválidos.
- `401`: falta token o es inválido.
- `403`: token válido con rol no autorizado.
- `404`: libro o página inexistente.
- `405`: método distinto de GET.
- `503`: Identidad o Circulación no disponible, o respuesta de existencias
  incompleta/inconsistente. **No se transforma un error en stock 0**.

## Contrato de Circulación que debe acordarse con su equipo

**Ruta propuesta** (aún no implementada por este commit):

`POST http://ms-circulacion:8000/api/internal/existencias/consultar/`

Cabecera: `X-Internal-Service-Key: <CIRCULACION_INTERNAL_API_KEY>`.

Solicitud (hasta 100 IDs únicos por llamada):

```json
{"libros_ids": [7, 8]}
```

Respuesta HTTP 200:

```json
{
  "existencias": [
    {"libro_id": 7, "stock_total": 4, "stock_disponible": 2},
    {"libro_id": 8, "stock_total": 0, "stock_disponible": 0}
  ]
}
```

Se requiere una entrada por cada ID solicitado, incluso cuando el libro tiene
cero ejemplares. No se permiten IDs extra ni duplicados, valores negativos,
`stock_disponible > stock_total` ni campos numéricos booleanos. Respuestas
incompletas o errores de red se traducen en `503`.

Variables en entorno de `ms-catalogo`:
`CIRCULACION_INTERNAL_BASE_URL=http://ms-circulacion:8000`,
`CIRCULACION_INTERNAL_API_KEY=` ,
`CIRCULACION_HTTP_TIMEOUT_SECONDS=3`. **No compartir credenciales con Angular**.

## Verificación

```bash
docker compose exec -T ms-catalogo python manage.py check
docker compose exec -T ms-catalogo python manage.py test catalogo.tests --verbosity 2
```

La prueba de contrato en este commit simula Circulación. La prueba real
entre contenedores sigue pendiente hasta acordar y publicar la ruta por
el equipo responsable. Antes de CATA08, contrastar el JSON con los clientes
Angular reales para confirmar nombres exactos de parámetros y campos.
