# ADR-004: Esquema de autenticación híbrida con enlaces criptográficos efímeros

## Estado

Aceptado

## Contexto

Se deben gestionar permisos (PA-02) para usuarios institucionales y para supervisores de empresas externas (CU-05, CU-07). Exigir a los supervisores la creación de una cuenta formal genera fricción, arriesgando los tiempos del proceso (RN-04, SUP-02, RI-02). Sin embargo, EAC-03 exige denegar el 100% de accesos alterados o expirados en 15 días sin comprometer datos (RN-01).

## Alternativas consideradas

- **A) Cuentas locales con usuario y contraseña para todos:**
  - *Ventaja:* Flujo único de seguridad.
  - *Desventaja:* Viola explícitamente RN-04, disuade a los tutores empresariales (RI-02) y traslada la carga de recuperación de contraseñas al sistema.
- **B) SSO Institucional para todos vía cuentas de invitado:**
  - *Ventaja:* Identidad centralizada.
  - *Desventaja:* El trámite administrativo previo recae en el tutor o el área de TI, perpetuando las demoras de OB-01 e incumpliendo RN-04.
- **C) SSO para usuarios internos + Enlaces criptográficos efímeros (Magic Links) para externos:** Los supervisores reciben un enlace con un token seguro (HMAC) de un solo uso y expiración a 15 días.
  - *Ventaja:* Fricción cero para el evaluador (SUP-02), cumpliendo RN-04 y bloqueando intentos fraudulentos (EAC-03).
  - *Desventaja:* Hay que mantener dos mecanismos de autenticación separados en la capa de seguridad.

## Decisión

Se elige la opción C porque elimina la barrera tecnológica para el actor crítico externo, asegurando la adopción y agilidad (RI-02, RN-04), garantizando a la vez la trazabilidad y expiración forzosa (EAC-03).

## Consecuencias

### Positivas

- El supervisor evalúa con un solo clic desde su correo, favoreciendo OB-02.
- Cumplimiento de EAC-03 frente a enlaces vencidos o manipulados.

### Negativas y costos aceptados

- Incrementa la lógica en la capa de exposición web (interceptores para dos métodos).
- Un enlace comprometido en la bandeja de correo del supervisor es un riesgo de delegación de identidad temporal.

### Riesgos asumidos y sus respectivas mitigaciones

- **El correo con el enlace es reenviado a un tercero:** Mitigación mediante el diseño del enlace como de un solo uso por práctica; adicionalmente, la evaluación queda sujeta a la aprobación final del docente asesor institucional (CU-10).


## Vistas arquitectónicas afectadas

* [Contexto del Sistema](../contexto.md) (`../diagramas/contexto.puml`): Interacción del `Supervisor de empresa`, `SSO Institucional` y `Servicio de correo`.
* [Vista Lógica](../vistas/01-logica.md) (`../diagramas/01-logica.puml`): Entidad `TokenEvaluacion`.
* [Vista de Procesos](../vistas/02-procesos.md) (`../diagramas/02-procesos.puml`): Validación contra `SSO Institucional` y envío por `Servicio de correo`.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): Componente `Interceptor de Identidad`.
* [Escenario ESC-02](../diagramas/secuencias/cu07-evaluar-desempeno.puml): Validación y caducidad del Magic Link a los 15 días.
