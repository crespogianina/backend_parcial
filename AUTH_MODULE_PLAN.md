# Plan de implementación - Auth dentro de `usuarios`

## Objetivo

Adaptar el módulo existente `app/modules/usuarios/` para cumplir la especificación de Auth sin crear una carpeta `auth/` separada, manteniendo la arquitectura por capas del proyecto y evitando romper el resto de los módulos.

La idea es que el sistema quede consistente con el código que ya existe: usuarios, roles, permisos, direcciones, pedidos, productos y categorías siguen usando la misma base de autenticación, pero el flujo público de autenticación pasa a ser el definido por la spec.

## Decisión de arquitectura

- Se mantiene un solo módulo funcional: `usuarios`.
- Los endpoints públicos de autenticación se exponen bajo `/api/v1/auth`.
- Las rutas administrativas de usuarios, si se conservan, quedan bajo `/api/v1/usuario`.
- No se crea un módulo separado `auth/`.
- Se respeta la estructura por capas:
  - `router`
  - `service`
  - `repository`
  - `schemas`
  - `unit_of_work`
  - `model`

## Estado actual del proyecto

Hoy el auth existente está basado en:

- `username` como identificador de login.
- JWT transportado por cookie `access_token`.
- `OAuth2PasswordRequestForm` para login.
- Un solo token de acceso, sin refresh tokens.
- `get_current_user` y `require_role` apoyados en el esquema viejo.
- `UserPublic` como esquema público de usuario, con campos que ya no encajan con la spec nueva.

Además, ya existe un rate limiting local en `app/core/rate_limit.py`, y eso permite implementar la limitación de login sin introducir una dependencia externa obligatoria.

## Qué se quiere lograr

### Auth público

| Método | Endpoint | Body / Params | Response | Auth requerida |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | `{ nombre, apellido, email, password }` | `201 UserResponse` | No |
| POST | `/api/v1/auth/login` | `{ email, password }` | `200 TokenResponse` | No, con rate limit `5/15min` |
| POST | `/api/v1/auth/refresh` | `{ refresh_token }` | `200 TokenResponse` | No |
| POST | `/api/v1/auth/logout` | `{ refresh_token }` | `204 No Content` | Bearer token |
| GET | `/api/v1/auth/me` | - | `200 UserResponse` | Bearer token |

### Esquemas principales

| Schema | Campos | Validaciones |
|---|---|---|
| `RegisterRequest` | `nombre`, `apellido`, `email`, `password` | `nombre/apellido` 2-80, `email` válido, `password` mínimo 8 |
| `LoginRequest` | `email`, `password` | `password` mínimo 8 |
| `RefreshRequest` | `refresh_token` | string no vacía |
| `TokenResponse` | `access_token`, `refresh_token`, `token_type`, `expires_in` | `token_type = "bearer"`, `expires_in` en segundos |
| `UserResponse` | `id`, `nombre`, `apellido`, `email`, `roles`, `created_at` | nunca incluye `password_hash` |

### Modelo de datos esperado

| Entidad | Campo clave | Restricción | Nota |
|---|---|---|---|
| `Usuario` | `id` | PK | soft delete con `deleted_at` |
| `Usuario` | `email` | UQ, NN | identificador único |
| `Usuario` | `password_hash` | NN | bcrypt, nunca plaintext |
| `Rol` | `codigo` | PK semántica | `ADMIN`, `STOCK`, `PEDIDOS`, `CLIENT` |
| `UsuarioRol` | `(usuario_id, rol_codigo)` | PK compuesta | relación N:M |
| `RefreshToken` | `token_hash` | UQ, NN | SHA-256 del token real |
| `RefreshToken` | `expires_at` | NN | vencimiento, por ejemplo 7 días |
| `RefreshToken` | `revoked_at` | nullable | `NULL` significa activo |

## Criterios de diseño

### 1. Email como identificador

- `username` deja de existir en el dominio principal.
- El login, el registro y el payload del JWT usan `email`.
- El campo `email` pasa a ser la identidad funcional del usuario.

### 2. Tokens

- El access token sigue siendo JWT.
- El refresh token debe ser opaco y aleatorio.
- En base de datos nunca se guarda el refresh token en claro.
- Se guarda únicamente el hash SHA-256 del refresh token.
- El refresh token debe poder rotarse al refrescar sesión.

### 3. Seguridad

- bcrypt con costo 12.
- JWT con `sub` basado en email.
- `type = "access"` en el access token.
- Los helpers de seguridad deben separar claramente:
  - hash de password
  - verificación de password
  - creación de access token
  - creación de refresh token
  - hash de refresh token
  - validación de token

### 4. Compatibilidad con el resto del proyecto

- Los módulos externos que usan `require_role` no deben romperse.
- Las dependencias de usuario actual deben seguir pudiendo devolver un objeto con `roles`.
- La migración de `UserPublic` debe hacerse con cuidado para no romper routers o services de otros módulos.
- `pedidos` merece una revisión específica porque concentra reglas de autorización por rol, validación de pertenencia del pedido y websocket de seguimiento.
- El refactor de auth no debe cambiar la semántica de permisos en pedidos: un cliente sigue viendo y cancelando sus pedidos, mientras que `ADMIN` y `PEDIDOS` conservan el acceso operativo.
- El websocket de pedidos hoy acepta token por query o cookie; si se migra a Bearer puro, ese cambio debe planearse aparte y validarse sin romper la suscripción de pedidos.

## Alcance exacto por archivo

### `app/modules/usuarios/model.py`

Cambios previstos:

- Eliminar `username` de `Usuario`.
- Mantener `nombre`, `apellido`, `email`, `password_hash`, timestamps y `deleted_at`.
- Agregar la entidad `RefreshToken`.
- Revisar que las relaciones de `Usuario` con `UsuarioRol`, `Rol`, direcciones y pedidos sigan coherentes.
- Verificar que `UsuarioRol` siga representando correctamente la relación de roles.

### `app/modules/usuarios/schemas.py`

Cambios previstos:

- Reemplazar los schemas viejos de auth.
- Crear:
  - `RegisterRequest`
  - `LoginRequest`
  - `RefreshRequest`
  - `TokenResponse`
  - `UserResponse`
- Mantener un esquema interno si hace falta para compatibilidad con dependencias de permisos.
- Usar validaciones de Pydantic v2 con `Field`.

### `app/modules/usuarios/repository.py`

Cambios previstos:

- Eliminar `get_by_username`.
- Dejar `get_by_email` como método principal de lookup.
- Mantener el alta de roles y el listado de usuarios.
- Agregar repositorio para refresh tokens.

### `app/modules/usuarios/unit_of_work.py`

Cambios previstos:

- Agregar `refresh_tokens` al UoW.
- Mantener la unidad de trabajo como orquestador de repositorios.

### `app/modules/usuarios/service.py`

Cambios previstos:

- Implementar `register`.
- Implementar `login`.
- Implementar `refresh`.
- Implementar `logout`.
- Implementar `get_me`.
- Corregir `autenticar_websocket`.
- Eliminar toda lógica dependiente de `username`.

### `app/modules/usuarios/router.py`

Cambios previstos:

- Exponer los endpoints de auth bajo `/auth`.
- Cambiar login a body JSON.
- Quitar el login por formulario OAuth2.
- Quitar la lógica de cookie para autenticación.
- Aplicar rate limit al login.

### `app/modules/pedido/router.py` y `app/modules/pedido/service.py`

Cambios o impactos a revisar:

- Verificar que los checks de `require_role(["ADMIN", "CLIENT", "PEDIDOS"])` sigan funcionando con la nueva identidad por email.
- Confirmar que `usuario.id` y `usuario.roles` sigan disponibles donde pedidos los usa para decidir acceso y pertenencia.
- Revisar el websocket de pedidos, porque hoy extrae token de `query_params` o cookie y llama a `UsuarioService.autenticar_websocket`.
- Mantener las reglas actuales:
  - `CLIENT` crea y cancela solo sus pedidos.
  - `ADMIN` y `PEDIDOS` pueden gestionar estados operativos.
  - La lógica de historial y transición no cambia por la migración de auth.

### `app/core/deps.py`

Cambios previstos:

- Cambiar a `OAuth2PasswordBearer` estándar.
- Leer `Authorization: Bearer`.
- Resolver el usuario actual por email desde el JWT.
- Seguir validando `deleted_at` en `get_current_active_user`.
- Mantener `require_role` funcionando sin cambiar la lógica de negocio de los demás módulos.

### `app/core/security.py`

Cambios previstos:

- Configurar bcrypt con 12 rondas.
- Asegurar que el JWT de acceso lleve el tipo correcto.
- Agregar helpers para refresh token.
- Agregar hash SHA-256 para refresh token.

### `app/core/config.py`

Cambios previstos:

- Agregar `REFRESH_TOKEN_EXPIRE_DAYS`.
- Revisar duplicados o valores inconsistentes de configuración.

### `app/core/database.py`

Cambios previstos:

- Importar explícitamente todos los modelos necesarios para `create_all`.
- Asegurar que `RefreshToken` se cree junto con el resto del esquema.
- Evitar tablas faltantes por imports incompletos.

### `app/main.py`

Cambios previstos:

- Montar el router de auth en `/api/v1/auth`.
- Mantener el router administrativo, si se separa, en `/api/v1/usuario`.
- Integrar el rate limiting local si hace falta centralizarlo.

### `app/db/seed.py`

Cambios previstos:

- Quitar `username` de los datos semilla.
- Sembrar usuarios por email.
- Asegurar que los roles queden asignados correctamente.

### `app/core/rate_limit.py`

Estado esperado:

- Se usa como implementación local del rate limiting.
- Se aplica solo al login.
- Limita por IP y ventana temporal.
- Devuelve `429` cuando se supera el máximo de intentos.

## Orden de implementación recomendado

Este orden reduce roturas y hace más fácil validar cada paso:

### Fase 1 - Contrato público

1. Definir los schemas nuevos.
2. Ajustar respuestas públicas.
3. Preparar el router nuevo de auth.

### Fase 2 - Seguridad y persistencia

4. Actualizar `security.py`.
5. Agregar `RefreshToken` al modelo.
6. Agregar el repositorio de refresh tokens.
7. Ampliar el UoW.

### Fase 3 - Lógica de negocio

8. Reescribir `register`.
9. Reescribir `login`.
10. Implementar `refresh`.
11. Implementar `logout`.
12. Implementar `get_me`.

### Fase 4 - Integración del sistema

13. Cambiar `deps.py` a Bearer.
14. Ajustar `main.py`.
15. Ajustar `database.py`.
16. Actualizar `seed.py`.

### Fase 5 - Verificación

17. Probar register.
18. Probar login.
19. Probar me.
20. Probar refresh.
21. Probar logout.
22. Probar rate limiting.
23. Probar compatibilidad con permisos y módulos existentes.

## Riesgos técnicos a tener presentes

- Eliminar `username` demasiado pronto puede romper dependencias internas si no se migra toda la ruta de auth a la vez.
- Cambiar cookies por Bearer impacta a cualquier dependencia que siga leyendo `access_token` desde cookie.
- El refresh token en memoria no sirve; tiene que persistirse en DB con hash.
- El rate limiting local no es distribuido; sirve para este TP, pero no para un despliegue con varios workers.
- Si `UserPublic` se redefine sin cuidado, se puede romper `require_role` o cualquier módulo que espere `roles`.

## Verificación mínima esperada

Cuando termine la implementación, esto debería funcionar:

- `POST /api/v1/auth/register`
  - crea un usuario nuevo
  - devuelve `UserResponse`
  - no expone `password_hash`

- `POST /api/v1/auth/login`
  - autentica con email y password
  - devuelve access token y refresh token
  - aplica rate limit

- `GET /api/v1/auth/me`
  - funciona con `Authorization: Bearer <token>`
  - devuelve usuario y roles

- `POST /api/v1/auth/refresh`
  - valida el refresh token
  - rota el token
  - invalida el anterior

- `POST /api/v1/auth/logout`
  - revoca el refresh token
  - deja de ser utilizable

- Los módulos existentes siguen funcionando con `get_current_active_user` y `require_role`.

## Criterio de finalización

El trabajo se considera terminado cuando:

- El auth usa email y no username.
- Los endpoints pedidos existen bajo `/api/v1/auth`.
- Se usan schemas separados para request y response.
- El refresh token se persiste con hash.
- El access token se envía por Bearer.
- El login está rate-limited.
- El resto del proyecto sigue funcionando.
- El módulo `pedidos` mantiene sus permisos, filtros y websocket de seguimiento sin regresiones.

## Nota de implementación

Si aparece una contradicción entre la spec y la estructura actual del proyecto, la prioridad práctica es:

1. No romper módulos existentes.
2. Cumplir la spec del auth.
3. Mantener la arquitectura por capas.
4. Evitar una migración más grande de la necesaria.
