# Integración del gateway público — Catálogo (CATA08, 3.3)

**Alcance:** añadir al gateway Nginx las rutas públicas ya implementadas en
Catálogo. No se altera la autenticación de Identidad, los endpoints de
Circulación ni las rutas internas. **Coordinar este cambio con el responsable
del issue de integración del gateway** antes del push, porque
`infra/nginx/default.conf` es un archivo compartido.

## Mapeo (sin reescritura de URL)

| Ruta externa | Destino Docker | Uso |
| --- | --- | --- |
| `/api/libros/` y `/api/libros/{id}/` | `http://ms-catalogo:8000` | Administración, bibliotecario |
| `/api/autores/` y `/api/autores/{id}/` | `http://ms-catalogo:8000` | Administración, bibliotecario |
| `/api/categorias/` y `/api/categorias/{id}/` | `http://ms-catalogo:8000` | Administración, bibliotecario |
| `/api/catalogo/`, `/api/catalogo/filtros/`, `/api/catalogo/{id}/` | `http://ms-catalogo:8000` | Lectura con Bearer |
| `/api/internal/*` | **404 en Nginx** | Solo accesible entre contenedores por la red interna |

La URL entrante debe conservarse íntegra (por eso `proxy_pass` **no** lleva
una barra final). Los cuatro prefijos usan `location ^~` para prevalecer
sobre el enrutamiento genérico a Identidad sin perturbarlo. La ruta exacta
sin `/` final responde `308` y conserva los parámetros de búsqueda.

El gateway NO debe transmitir una clave de servicio enviada desde el navegador:
se limpia `X-Internal-Service-Key` al reenviar rutas públicas de Catálogo.
La autorización de usuarios depende de `Authorization: Bearer ...`, que se
reenvía sin modificación, y se valida en Catálogo llamando a Identidad.

## Procedimiento reproducible (Git Bash, raíz del repositorio)

El parche CATA08 contiene el configurador y sus pruebas, **pero no modifica
`infra/nginx/default.conf` inmediatamente**: el archivo puede haber cambiado
por trabajo simultáneo de otros integrantes.

1. Con el parche aplicado y sin archivos ajenos modificados, ejecutar pruebas:

   ```bash
   docker compose exec -T ms-catalogo \
     python scripts/test_configurar_gateway_catalogo.py
   ```

2. Revisar el diff propuesto, sin escribir nada:

   ```bash
   MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -T \
     -v "./infra/nginx:/gateway" \
     ms-catalogo python scripts/configurar_gateway_catalogo.py \
     --config /gateway/default.conf --diff
   ```

3. Si no hay conflictos con el issue de gateway y las rutas propuestas son
   apropiadas, aplicar una sola vez:

   ```bash
   MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -T \
     -v "./infra/nginx:/gateway" \
     ms-catalogo python scripts/configurar_gateway_catalogo.py \
     --config /gateway/default.conf --write
   ```

   El configurador solo acepta un `server` público con rutas `/api/` y exige
   que **ya exista** un `location` literal para `/api/internal/` con `return 404`.
   También se niega a duplicar rutas de Catálogo presentes sin sus marcadores.
   Si el archivo no cumple, revisar con el responsable del gateway; no
   deshabilitar esas comprobaciones para hacerlo pasar.

4. Verificar Nginx y reiniciarlo para incorporar cambios:

   ```bash
   docker compose config --quiet
   docker compose up -d --no-deps ms-catalogo
   docker compose exec -T api_gateway nginx -t
   docker compose restart api_gateway
   docker compose ps api_gateway ms-catalogo
   ```

5. En la raíz del repositorio, revisar el diff real de Nginx:

   ```bash
   git diff -- infra/nginx/default.conf
   git diff --check
   ```

## Pruebas HTTP desde el host

La URL de ejemplo usa el gateway en `http://127.0.0.1:8000`. Consultar
`docker compose ps api_gateway` para confirmar el puerto expuesto en tu equipo.

```bash
# Debe ser 404 (la API interna JAMÁS es pública):
curl -i http://127.0.0.1:8000/api/internal/libros/1/

# Debe ser 401 sin token: la solicitud llegó al backend de Catálogo.
curl -i http://127.0.0.1:8000/api/catalogo/filtros/
curl -i http://127.0.0.1:8000/api/libros/

# Con un token real de Identidad y permisos adecuados:
curl -i -H 'Authorization: Bearer TOKEN_VALIDO' \
  http://127.0.0.1:8000/api/catalogo/filtros/
```

Un `200` en filtros requiere Identidad operativo y bibliografía en la base.
El listado `/api/catalogo/` también requiere Circulación: **antes de que esta
publique existencias puede devolver 503**, y eso es el comportamiento correcto;
no confundirlo con un error de enrutamiento ni reemplazar el stock por 0.

## Restricciones pendientes para la integración completa

- Probar contra la versión real del frontend Angular los parámetros/filtros
  y el JSON; este cambio no edita Angular.
- Comprobar el flujo real Identidad → Catálogo con un token válido.
- Ejecutar pruebas reales de Catálogo ↔ Circulación cuando ese servicio
  implemente `POST /api/internal/existencias/consultar/`.
- Evitar que otros commits modifiquen el mismo bloque del gateway sin resolver
  los cambios mediante revisión o pull request.

La suite de `catalogo.tests` de CATA07 no se modifica en CATA08 (93 pruebas
esperadas); el configurador tiene 14 pruebas independientes, que no requieren
Nginx ni Django. `nginx -t` y las pruebas HTTP reales deben ejecutarse en
la instalación de cada equipo.
