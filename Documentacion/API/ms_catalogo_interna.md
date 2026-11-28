# Contrato interno REST — Catálogo Bibliográfico (CATA06, 3.3)

**Estado:** implementado en el código de Catálogo; **pendiente de integración con Circulación** (servicio aún no disponible). El proveedor es `ms-catalogo`.

- Base interna Docker: `http://ms-catalogo:8000/api/internal/`.
- Acceso de depuración: `http://127.0.0.1:18082/api/internal/`.
- Autenticación: `X-Internal-Service-Key: <CATALOGO_INTERNAL_API_KEY>`.
- La clave pertenece a **Catálogo** y se configura por entorno, con al menos 16 caracteres.
- El Bearer de usuarios no reemplaza la clave de servicio.
- Nginx devuelve `404` para `/api/internal/`; nunca debe reenviar estas rutas públicas.

## GET `/api/internal/libros/{libro_id}/`

Consulta un libro existente utilizando su `libro_id` original. Respuesta `200`:

```json
{
  "libro_id": 7,
  "titulo": "Arquitectura de software",
  "isbn": "9780000000007",
  "fecha_publicacion": "2021-03-04"
}
```

La fecha de publicación puede ser `null`. Devuelve `404` y `{"detail":"Libro no encontrado."}` cuando no existe. No expone autores, categorías ni información de ejemplares; Circulación utiliza estos campos para validar y describir sus referencias a libros.

## POST `/api/internal/libros/resolver/`

Permite resolver hasta 100 referencias bibliográficas en una sola solicitud.

```json
{"libros_ids":[7,8,7,999999]}
```

Respuesta `200`:

```json
{
  "libros": [
    {"libro_id":7,"titulo":"Arquitectura de software","isbn":"9780000000007","fecha_publicacion":"2021-03-04"},
    {"libro_id":8,"titulo":"Bases de datos","isbn":"9780000000008","fecha_publicacion":null}
  ],
  "no_encontrados":[999999]
}
```

`libros_ids` es obligatorio, debe ser una lista de 1 a 100 enteros positivos. Los duplicados se eliminan conservando el primer orden de aparición. Los no encontrados se informan por separado; no se crean registros.

## Respuestas de error

| HTTP | Situación |
|---|---|
| `400` | Falta la lista, está vacía, contiene IDs inválidos o supera 100 elementos |
| `403` | Clave interna inexistente, incorrecta o configurada con longitud insuficiente |
| `404` | Libro individual no encontrado |
| `405` | Método no permitido |
| `500` | Error inesperado de Catálogo |

Si Catálogo está inaccesible o hay timeout, **el consumidor** debe tratarlo como una dependencia indisponible (`503` en su propia API pública) y no asumir que el libro existe.

## Integración y verificación

Este contrato es **nuevo**. No sustituye los endpoints públicos de Angular. Se ejecuta únicamente en la red `api` de Compose o en el puerto local de depuración para pruebas.

```bash
docker compose exec -T ms-catalogo python manage.py test catalogo.tests.test_internal --verbosity 2
```

Pruebas de integración reales desde Circulación: **pendientes** hasta que exista el consumidor.
