# Plan: 001 Postulación de estudiante a la práctica

## Decisiones que aplican

- **ADR-001 (Resiliencia e integración asíncrona con Registro Académico):**
  - La consulta de requisitos académicos al SIA se instrumenta con timeout de 5 segundos y patrón *Circuit Breaker*.
  - Ante caída o timeout del SIA, la postulación se preserva de inmediato en estado `PendienteVerificacion` (0% pérdida de datos) y se encola una tarea asíncrona en el bróker de mensajes.
  - La respuesta al estudiante se entrega en menos de 3 segundos informando el estado "Pendiente de verificación".
  - Un worker asíncrono reintenta la validación contra el SIA (máximo 5 reintentos con espera exponencial). Al restablecerse el SIA (< 30 min), culmina la verificación, actualiza a `Solicitada` y notifica por correo. Si se agotan los reintentos, el mensaje pasa a una Dead-Letter Queue (DLQ) y se emite alerta a TI.
- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas: `dominio/`, `aplicacion/` e `infraestructura/`.
  - La capa de dominio no depende de ningún framework ni de capas externas.
  - La capa de aplicación define los puertos de entrada (casos de uso) y puertos de salida (`Protocol` / clases abstractas).
  - En esta fase de desarrollo y validación sin dependencias externas pesadas, la infraestructura provee adaptadores en memoria (`InMemory...`) y simuladores deterministas para SIA, mensajería y correo.
  - `main.py` actúa como único punto de composición e inyección de dependencias.
- **ADR-004 (Autenticación híbrida):**
  - La identidad del estudiante se valida mediante token institucional (SSO/OIDC) verificado por el componente de interceptor de identidad.
- **ADR-005 (Autorización RBAC centralizada en la capa de Aplicación):**
  - El `AutorizadorRBAC` aplica política *deny-by-default*, validando que el actor autenticado tenga el rol `Estudiante` y que la solicitud pertenezca al propio estudiante autenticado.
- **ADR-006 (Bitácora de auditoría Append-Only):**
  - Registro inmutable de transiciones de estado de la práctica y eventos del proceso mediante la entidad `EventoBitacora`.
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - Cada nueva postulación se vincula obligatoriamente al identificador de la `ReglaPrograma` activa vigente para el programa del estudiante, garantizando inmutabilidad normativa.
- **ADR-010 (Máquina de estados finitos en la entidad Práctica):**
  - `Practica.estadoActual` gobierna las transiciones permitidas (`PendienteVerificacion`, `Solicitada`, `Rechazada`).
  - Se valida como regla de dominio que el estudiante no posea una práctica activa en curso (`Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`).

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y las convenciones de Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/practica.py`:
  - Entidad `Practica`: encapsula el identificador, estudiante, regla vinculada, máquina de estados finitos (`estadoActual`) y métodos de transición (`solicitar()`, `marcar_pendiente_verificacion()`, `rechazar()`).
  - Enum `EstadoPractica`: define los estados formales del ciclo de vida.
- `dominio/modelos/estudiante.py`:
  - Entidad `Estudiante`: modela los datos del estudiante (identificador, documento, nombre, correo, programa académico).
- `dominio/modelos/regla_programa.py`:
  - Entidad `ReglaPrograma`: define el programa académico, versión y estado activo.
- `dominio/modelos/intento_validacion.py`:
  - Entidad `IntentoValidacion`: modela la trazabilidad de cada intento de validación frente al SIA (fecha, exitoso, causal_falla).
- `dominio/modelos/evento_bitacora.py`:
  - Entidad `EventoBitacora`: registro append-only de cambios de estado y auditoría.
- `dominio/errores.py`:
  - Excepciones de dominio: `PracticaActivaExistenteError`, `ReglaProgramaNoConfiguradaError`, `TransicionEstadoInvalidaError`.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/postulacion_dto.py`:
  - `PostularEstudianteComando`: DTO inmutable con datos de entrada para la postulación.
  - `PostulacionRespuestaDTO`: DTO inmutable de respuesta al usuario.
- `aplicacion/puertos/repositorio_practica.py`:
  - Protocol `RepositorioPracticaPort`: guardar, actualizar, buscar_activa_por_estudiante, buscar_por_id.
- `aplicacion/puertos/repositorio_regla.py`:
  - Protocol `RepositorioReglaProgramaPort`: buscar_activa_por_programa.
- `aplicacion/puertos/servicio_registro_academico.py`:
  - Protocol `ServicioRegistroAcademicoPort`: consultar_requisitos_academicos(documento_estudiante).
- `aplicacion/puertos/publicador_eventos.py`:
  - Protocol `PublicadorEventosPort`: publicar_tarea_validacion_sia(datos_tarea).
- `aplicacion/puertos/servicio_correo.py`:
  - Protocol `ServicioCorreoPort`: enviar_notificacion(destinatario, asunto, cuerpo).
- `aplicacion/seguridad/autorizador_rbac.py`:
  - Componente `AutorizadorRBAC`: validación de rol `Estudiante` y contexto de identidad.
- `aplicacion/casos_uso/postular_estudiante.py`:
  - Caso de uso `PostularEstudianteCasoUso` (Módulo Postulaciones): orquesta validación RBAC, reglas de dominio, consulta síncrona/circuit breaker al SIA, persistencia inicial y encolamiento si aplica.
- `aplicacion/casos_uso/reintentar_validacion_sia.py`:
  - Caso de uso `ReintentarValidacionSiaCasoUso` (Worker de integración): orquesta los reintentos asíncronos, persistencia de intentos, transición final y notificación por correo.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py`:
  - `InMemoryRepositorioPractica`: implementación en memoria del repositorio de prácticas y bitácora.
  - `InMemoryRepositorioReglaPrograma`: almacén en memoria de reglas versionadas.
- `infraestructura/adaptadores/cliente_sia_simulado.py`:
  - `AdaptadorSiaSimulado`: implementación de `ServicioRegistroAcademicoPort` con simulación determinista de latencia, timeout (> 5 s) y fallos, integrando lógica de Circuit Breaker.
- `infraestructura/adaptadores/broker_memoria.py`:
  - `InMemoryBrokerMensajes`: implementación de `PublicadorEventosPort` con despacho de tareas simulado para ejecución en segundo plano y manejo de DLQ.
- `infraestructura/adaptadores/servicio_correo_simulado.py`:
  - `AdaptadorCorreoSimulado`: implementación de `ServicioCorreoPort` para registrar envíos en memoria.
- `infraestructura/seguridad/proveedor_identidad_simulado.py`:
  - Proveedor de contexto de autenticación para simular sesiones OIDC.

### Composición (`main.py`)

- `main.py`:
  - Cablea los adaptadores en memoria con los puertos e instancia los casos de uso disponibles.

## Flujo

Sigue fielmente el diagrama de secuencia [ESC-01 (cu01-postularse.puml)]:

1. **Identificación y autorización:** El `AutorizadorRBAC` valida el rol `Estudiante` y la correspondencia del usuario autenticado.
2. **Validación de precondiciones de dominio:**
   - Se verifica que el estudiante no cuente con una práctica activa en curso (`Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`).
   - Se consulta la `ReglaPrograma` activa vigente para el programa del estudiante. Si no existe, se bloquea la solicitud informando al estudiante.
3. **Consulta síncrona al SIA (timeout = 5 s):**
   - **Caso 3.1 (SIA responde < 5 s y cumple requisitos):** Se registra la `Practica` en estado `Solicitada`, se asocia el `IntentoValidacion` exitoso y se retorna confirmación al estudiante (< 3 s).
   - **Caso 3.2 (SIA responde < 5 s y no cumple requisitos):** Se registra la `Practica` en estado `Rechazada`, se guarda el `IntentoValidacion` y se responde con la causal de rechazo (< 3 s).
   - **Caso 3.3 (Timeout > 5 s o error de SIA - EAC-02):** Se activa el Circuit Breaker, se persiste la `Practica` en estado `PendienteVerificacion`, se guarda el `IntentoValidacion` con estado fallido, se publica la tarea en el bróker de mensajes y se retorna confirmación al estudiante en < 3 s ("Pendiente de verificación").
4. **Procesamiento asíncrono (EAC-02):**
   - El worker consume el mensaje y reintenta la validación frente al SIA (hasta 5 reintentos con espera exponencial).
   - Al recuperarse el servicio (< 30 min): actualiza la `Practica` a `Solicitada`, registra el `EventoBitacora` y envía la notificación por correo al estudiante.
   - Si se agotan los 5 reintentos sin éxito: el mensaje pasa a la Dead-Letter Queue (DLQ) y se emite alerta operativa a TI sin descartar la postulación.

## Datos

Entidades del modelo de dominio involucradas [docs/vistas/01-logica.md]:

- `Practica`: entidad raíz con identificador, referencia a estudiante, identificador de regla vinculada, fechas y máquina de estados (`PendienteVerificacion`, `Solicitada`, `Rechazada`).
- `Estudiante`: titular solicitante (documento, nombre, correo, programa).
- `ReglaPrograma`: regla vigente del programa que define horas mínimas y rúbrica asignada.
- `IntentoValidacion`: registro inmutable del resultado de cada verificación con el SIA.
- `EventoBitacora`: registro append-only de auditoría ante transiciones de estado.

## Fuera de alcance

- Evaluación administrativa y aprobación/rechazo de la postulación por el Coordinador de prácticas (CU-02).
- Asignación de docente asesor / tutor (CU-03).
- Vinculación o registro de supervisor y datos de la empresa receptora (se gestiona tras la aprobación de la práctica).
- Registro y aprobación semanal de horas de práctica (CU-04, CU-05, CU-06).
- Calificación de desempeño del estudiante por la empresa (CU-07).
- Generación y aprobación de actas finales (CU-09, CU-10).
- Configuración de nuevas reglas de programas académicos (CU-12).

## Decisiones pendientes

Ninguna. La totalidad de los requerimientos, restricciones y escenarios de calidad están respaldados por los ADR-001 al ADR-010 y las respuestas de negocio ya provistas.
