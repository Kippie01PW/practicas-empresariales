# AGENTS.md: Sistema de gestión de prácticas empresariales

Reglas permanentes del proyecto. Se le entregan al agente al inicio de cada sesión junto con la documentación en `docs/`. Es corto: enlaza a `docs/` en lugar de duplicar su contenido.

## Fuentes de verdad

- `docs/arquitectura.md`: mapa general de arquitectura (arc42), síntesis de drivers, vistas 4+1, ADRs y glosario.
- `docs/contexto.md`: visión global, objetivos y alcance del sistema.
- `docs/drivers.md`, sección 1: catálogo de casos de uso (CU-01 a CU-15). Es la lista canónica de funcionalidades del sistema.
- `docs/drivers.md`, secciones 2 a 5: escenarios de atributos de calidad (EAC), restricciones (RT/RN), preocupaciones arquitectónicas (PA) y matriz de priorización.
- `docs/vistas/`: vistas arquitectónicas bajo el modelo 4+1 (`01-logica.md`, `02-procesos.md`, `03-desarrollo.md`, `04-fisica.md`).
- `docs/adr/`: decisiones arquitectónicas registradas (ADR-001 al ADR-010). Los ADR no se editan: una decisión nueva se formaliza como un ADR nuevo que reemplaza o amplía al anterior.
- `specs/`: una carpeta por cada caso de uso del catálogo (`specs/001-postulacion-estudiante/`, ..., `specs/015-migrar-practicas-excel/`), conteniendo sus artefactos de ciclo de vida (`spec.md`, `plan.md`, `tasks.md` y `validacion.md`).
- Si el código contradice una especificación, gana la especificación. Si la especificación parece incorrecta o ambigua, detenerse y consultar antes de proceder.

## Arquitectura

- **Monolito modular con Clean Architecture** (ADR-002): organizado en `dominio/`, `aplicacion/` e `infraestructura/`, con `main.py` como único punto de composición e inyección de dependencias.
- **Regla de dependencias estricta**: `dominio/` no importa nada de `aplicacion/` ni de `infraestructura/`. `aplicacion/` no importa de `infraestructura/`.
- **Puertos y adaptadores**: puertos definidos como `Protocol` (o clases base abstractas) en `aplicacion/puertos/` (los define el caso de uso; los implementan los adaptadores en `infraestructura/`).
- **Resiliencia e integración asíncrona** (ADR-001): la verificación con SIA instrumentada con timeout de 5s y circuit breaker; si falla, la postulación queda en `PendienteVerificacion`, se encola en el broker y solo el worker asíncrono reintenta la verificación y emite notificaciones.
- **Persistencia transaccional** (ADR-003): arquitectura diseñada para PostgreSQL; en fases iniciales de desarrollo y pruebas se usan adaptadores en memoria o repositorios simulados.
- **Autenticación híbrida** (ADR-004): SSO institucional (OIDC) para usuarios internos y enlaces criptográficos efímeros (Magic Links firmados con token HMAC de un solo uso y expiración de 15 días) para supervisores de empresa externos.
- **Autorización RBAC centralizada** (ADR-005): vive en la capa de `aplicacion/` con política *deny-by-default*, validando rol y contexto (un tutor solo accede a sus practicantes asignados).
- **Bitácora de auditoría Append-Only** (ADR-006): cada cambio de estado, aprobación de acta y acceso rechazado se registra de forma inmutable y atómica con timestamp, usuario e IP.
- **Reglas declarativas versionadas por programa** (ADR-007): horas requeridas, rúbricas y plantillas asociadas a cada práctica al momento de iniciar; 0% alteración a prácticas activas o pasadas ante cambios normativos (EAC-01).
- **Generación y preservación de actas** (ADR-008): renderizado de acta en PDF desde plantilla HTML/CSS e inmutabilidad garantizada con sellado hash SHA-256 en base de datos y volumen de almacenamiento.
- **Máquina de estados finitos** (ADR-010): el ciclo de vida de la entidad `Practica` encapsula transiciones formales y estrictas; ninguna práctica se puede marcar como completada sin horas validadas, evaluación registrada y firmas asentadas.

## Convenciones de código

- Python 3.12; tipado estático (`typing`); una clase o componente principal por archivo.
- Uso de DTOs (`dataclass` o esquemas pydantic) inmutables para la entrada y la salida de los casos de uso.
- Vocabulario de clases y métodos alineado rigurosamente con los términos del glosario y entidades del modelo de dominio (`Practica`, `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`, `ReglaPrograma`, `RegistroHoras`, `EvaluacionDesempeno`, `TokenEvaluacion`, `ActaFinal`, `EventoBitacora`, etc.).
- Sin base de datos real ni servicios externos reales en esta etapa: usar adaptadores en memoria (`InMemory...`) o simulaciones deterministas.
- Sin framework de pruebas pesadas en esta etapa inicial: la validación se realiza escenario por escenario según `validacion.md`, documentando entradas, salidas y evidencia reproducible.

## Forma de trabajar

- Ejecutar estrictamente **una tarea de `tasks.md` a la vez**.
- Al terminar cada tarea: marcarla como completada (`[X]`), reportar los archivos creados o modificados y detenerse para revisión.
- No inventar reglas de negocio ni requisitos no documentados: lo que no esté en `docs/` o las especificaciones se marca en `spec.md` con `# [NECESITA ACLARACIÓN: <pregunta>]` o se pregunta al usuario.
- No agregar dependencias ni bibliotecas que no hayan sido contempladas y justificadas por los ADR.
- Un commit o entrega atómica por tarea, incluyendo el ID de la tarea en el mensaje de cambio.
