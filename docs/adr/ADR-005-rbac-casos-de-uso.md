# ADR-005: Control de acceso basado en roles (RBAC) centralizado a nivel de Casos de Uso

## Estado

Aceptado

## Contexto

El sistema tiene roles definidos (Estudiante, Docente, Coordinador, Supervisor) con separación estricta de funciones (RN-03). Por la Ley 1581 (RN-01), se debe asegurar que un docente solo vea a sus practicantes y no a los de otros. La aprobación final de actas debe estar restringida exclusivamente a Docente y Coordinador (CU-10).

## Alternativas consideradas

- **A) Validación de roles por anotaciones en los controladores HTTP:**
  - *Ventaja:* Rápido de programar.
  - *Desventaja:* Si se expone el caso de uso por otra vía (ej. CLI o evento asíncrono), se pierde la validación; propenso a omitir verificaciones de pertenencia de datos, arriesgando RN-01.
- **B) Control RBAC contextual en la capa de Aplicación (Casos de Uso):** Se inyecta la identidad en el orquestador de dominio, validando en un solo punto tanto el rol como la pertenencia (Context-based access control). Todo caso de uso niega el acceso por defecto.
  - *Ventaja:* Centraliza la política (PA-02) y protege los datos independientemente de la interfaz.
  - *Desventaja:* Exige pasar el objeto de identidad del usuario en cada invocación interna.
- **C) Motor de políticas (ABAC/XACML):**
  - *Ventaja:* Extremadamente granular.
  - *Desventaja:* Introduce sobrecarga tecnológica para un escenario de roles y flujos ya limitados (RN-03).

## Decisión

Se elige la opción B porque garantiza que la política de privacidad y autorización (RN-01, RN-03) rija integralmente a nivel de dominio, mitigando las fugas de información.

## Consecuencias

### Positivas

- Garantía estructural de que las operaciones sensibles (CU-10) solo sean ejecutables por actores autorizados.
- Cualquier revisor encuentra los permisos en un solo lugar.

### Negativas y costos aceptados

- Los desarrolladores deben actualizar manualmente la matriz de roles por cada nuevo caso de uso integrado.

### Riesgos asumidos y sus respectivas mitigaciones

- **Olvidar asignar permisos a un caso de uso nuevo:** Mitigación mediante la adopción de una política deny-by-default, de modo que una ruta o caso de uso sin rol configurado explícitamente arroje siempre error de autorización (HTTP 403).
