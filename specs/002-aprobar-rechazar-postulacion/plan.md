# Plan: 002 Aprobar o rechazar postulación

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas: `dominio/`, `aplicacion/` e `infraestructura/`.
  - La capa de dominio no depende de ningún framework ni de capas externas.
  - La capa de aplicación define el caso de uso `EvaluarPostulacionCasoUso` (dentro del Módulo Postulaciones), sus DTOs inmutables de entrada y salida, y los puertos necesarios.
  - La infraestructura provee adaptadores en memoria (`InMemory...`) para repositorios y servicio de correo.
  - `main.py` actúa como único punto de composición e inyección de dependencias.
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política *deny-by-default*.
  - Solo los usuarios autenticados con rol `Coordinador` o `CoordinadorPracticas` están autorizados para ejecutar la aprobación o rechazo.
  - Solicitudes de roles no autorizados (e.g. `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`) son denegadas inmediatamente, registrando la alerta en bitácora de auditoría sin exponer datos de la postulación.
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada cambio de estado de la práctica hacia `Aprobada` o `Rechazada` se asienta de forma inmutable mediante `EventoBitacora` con identificador de usuario, rol, acción, fecha, hora e IP de origen.
  - Cumplimiento de **EAC-03**: los accesos denegados por RBAC se registran de inmediato en la bitácora en menos de 1 minuto con IP, fecha y hora.
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La entidad `Practica` encapsula el ciclo de vida y valida las transiciones válidas declaradas:
    - `Solicitada → Aprobada`: transición permitida ante aprobación administrativa.
    - `Solicitada → Rechazada`: transición permitida ante rechazo administrativo con justificación.
  - Cualquier intento de evaluar una práctica en un estado distinto a `Solicitada` (e.g. `PendienteVerificacion`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`, `Rechazada`) es denegado por la máquina de estados lanzando `TransicionEstadoInvalidaError`.

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/practica.py`:
  - Métodos en `Practica`:
    - `aprobar()`: transiciona el estado de `Solicitada` a `Aprobada`.
    - `rechazar(motivo: str)`: valida que el motivo no sea vacío y transiciona de `Solicitada` a `Rechazada` almacenando el `motivo_rechazo`.
  - Atributo de la entidad: `motivo_rechazo: Optional[str]`.
- `dominio/modelos/evento_bitacora.py`:
  - Entidad `EventoBitacora` (existente): modela los registros inmutables de auditoría para aprobaciones, rechazos y accesos denegados.
- `dominio/errores.py`:
  - Excepciones de dominio:
    - `TransicionEstadoInvalidaError` (existente): lanzada cuando la práctica no está en estado `Solicitada`.
    - `MotivoRechazoRequeridoError`: lanzada cuando se intenta rechazar sin justificación.
    - `PracticaNoEncontradaError`: lanzada cuando el identificador de la práctica no existe en el sistema.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/evaluacion_postulacion_dto.py`:
  - `EvaluarPostulacionComando`: DTO inmutable de entrada con `practica_id: str`, `decision: str` ("APROBAR" o "RECHAZAR"), `motivo_rechazo: Optional[str] = None`.
  - `EvaluacionPostulacionRespuestaDTO`: DTO inmutable de respuesta con `practica_id: str`, `nuevo_estado: str`, `mensaje: str`, `fecha_evaluacion: datetime`.
- `aplicacion/puertos/repositorio_practica.py`:
  - Protocol `RepositorioPracticaPort`: utilización de `buscar_por_id(practica_id: str)` y `guardar(practica: Practica)`.
- `aplicacion/puertos/repositorio_bitacora.py`:
  - Protocol `RepositorioBitacoraPort`: `registrar_evento(evento: EventoBitacora)`.
- `aplicacion/puertos/servicio_correo.py`:
  - Protocol `ServicioCorreoPort`: `enviar_notificacion(destinatario: str, asunto: str, cuerpo: str)`.
- `aplicacion/seguridad/autorizador_rbac.py`:
  - Configuración del permiso para CU-02 asignado exclusivamente a los roles de Coordinador (`RolUsuario.COORDINADOR`, `RolUsuario.COORDINADOR_PRACTICAS`).
- `aplicacion/casos_uso/evaluar_postulacion.py`:
  - Caso de uso `EvaluarPostulacionCasoUso` (Módulo Postulaciones):
    - Orquesta la validación de autorización RBAC (*deny-by-default*).
    - Recupera la práctica o lanza `PracticaNoEncontradaError`.
    - Ejecuta la transición de dominio (`aprobar()` o `rechazar(motivo)`).
    - Persiste el estado actualizado en el repositorio.
    - Registra el `EventoBitacora` de auditoría.
    - Notifica al estudiante mediante `ServicioCorreoPort`.
    - Retorna `EvaluacionPostulacionRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py`:
  - Soporte en `InMemoryRepositorioPractica` para actualización de estado y almacenamiento de `EventoBitacora`.
- `infraestructura/adaptadores/servicio_correo_simulado.py`:
  - `AdaptadorCorreoSimulado`: emulación determinista de envío de notificaciones al estudiante titular.

### Composición (`main.py`)

- `main.py`:
  - Instanciación del caso de uso `EvaluarPostulacionCasoUso` inyectando los adaptadores en memoria y el autorizador RBAC.

## Flujo

Secuencia operativa de evaluación administrativa:

1. **Autorización previa (RBAC - ADR-005):**
   - El `AutorizadorRBAC` valida que el actor en `ContextoUsuario` tenga rol `Coordinador` o `CoordinadorPracticas`.
   - Si no está autorizado, se registra de inmediato un `EventoBitacora` de acceso no autorizado y se deniega la petición (EAC-03) con 0 datos expuestos.
2. **Búsqueda de la práctica:**
   - Se consulta `RepositorioPracticaPort.buscar_por_id(practica_id)`. Si no existe, se arroja `PracticaNoEncontradaError`.
3. **Validación de la decisión y datos requeridos:**
   - Si la decisión es rechazar y el motivo es nulo o vacío, se interrumpe el flujo arrojando `MotivoRechazoRequeridoError`.
4. **Ejecución de transición en el dominio (ADR-010):**
   - Si `practica.estadoActual != EstadoPractica.SOLICITADA`, la entidad arroja `TransicionEstadoInvalidaError`.
   - Si es aprobación: la entidad cambia su estado a `EstadoPractica.APROBADA`.
   - Si es rechazo: la entidad cambia su estado a `EstadoPractica.RECHAZADA` y guarda `motivo_rechazo`.
5. **Persistencia transaccional y auditoría (ADR-006):**
   - Se guarda la práctica modificada en `RepositorioPracticaPort`.
   - Se registra el `EventoBitacora` inmutable con la acción ejecutada (`APROBACION_POSTULACION` o `RECHAZO_POSTULACION`), coordinador actor, fecha/hora e IP.
6. **Notificación al estudiante titular:**
   - Se invoca `ServicioCorreoPort.enviar_notificacion` comunicando la decisión y el motivo en caso de rechazo.
7. **Respuesta:**
   - Se retorna `EvaluacionPostulacionRespuestaDTO` confirmando el nuevo estado.

## Datos

Entidades del modelo de dominio involucradas [docs/vistas/01-logica.md]:

- `Practica`: entidad raíz que almacena `id`, `estudiante_id`, `regla_programa_id`, `estadoActual` (`Solicitada`, `Aprobada`, `Rechazada`) y `motivo_rechazo`.
- `Estudiante`: titular de la práctica referenciado para obtener correo institucional y datos para la notificación.
- `EventoBitacora`: registro append-only de auditoría con `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada`.

## Fuera de alcance

- Asignación de docente asesor / tutor a la práctica aprobada (CU-03).
- Registro y validación semanal de horas de práctica (CU-04, CU-05, CU-06).
- Calificación y evaluación de desempeño por la empresa receptora (CU-07).
- Generación y aprobación de actas finales en PDF (CU-09, CU-10).
- Monitoreo general del estado de las prácticas en tablero de control (CU-13).
- Configuración y versionamiento de reglas de programas académicos (CU-12).

## Decisiones pendientes

Ninguna. Todas las transiciones, esquemas de autorización, auditoría y persistencia están formalmente cubiertos por los ADR-002, ADR-005, ADR-006 y ADR-010.
