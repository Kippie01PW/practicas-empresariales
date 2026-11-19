# Plan: 005 Validar horas registradas

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`.
  - La capa de dominio define la entidad `TokenEvaluacion` y extiende `RegistroHoras` y `Practica` sin dependencias externas ni acoplamiento a frameworks.
  - La capa de aplicación define el caso de uso `ValidarHorasRegistradasCasoUso` (dentro del Módulo Seguimiento y Evaluación según `03-desarrollo.md`), sus DTOs inmutables de entrada y salida, y los puertos requeridos.
  - La capa de infraestructura provee `InMemoryRepositorioTokenEvaluacion` y el componente `InterceptorIdentidad` para la autenticación criptográfica de enlaces efímeros, extendiendo los repositorios en memoria existentes.
  - `main.py` actúa como único punto de composición e inyección de dependencias.
- **ADR-004 (Esquema de autenticación híbrida con enlaces criptográficos efímeros):**
  - Los supervisores de empresa externos acceden a la validación de horas a través de enlaces con tokens seguros (Magic Links con firma HMAC), sin requerir cuentas en el directorio activo universitario (RN-04, SUP-02).
  - Los enlaces cuentan con expiración a 15 días calendario y carácter de un solo uso para asentar validaciones en firme.
  - Todo intento de acceso con token manipulado, expirado (> 15 días) o previamente utilizado es denegado por el interceptor de seguridad sin exponer datos del estudiante ni de la práctica (**EAC-03**).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política centralizada *deny-by-default*.
  - La operación `validar_horas` está restringida a actores con rol `SupervisorEmpresa` (`RolUsuario.SUPERVISOR_EMPRESA` o `RolUsuario.SUPERVISOR`). Intentos por otros roles (e.g. `Estudiante`, `DocenteAsesor`) son denegados de inmediato.
  - Validación de pertenencia contextual de datos (*Context-Based Access Control*, RN-01): el supervisor solo puede validar reportes de la práctica que le fue asignada formalmente. El intento de validar horas de prácticas ajenas es bloqueado sin exponer datos.
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Registro inmutable de auditoría mediante `EventoBitacora` para cada acción de validación (aprobación de horas con acumulación, o rechazo de horas con observaciones registradas).
  - Registro de seguridad inmediato (< 1 minuto) para cualquier acceso no válido: enlaces expirados, firmas HMAC corruptas, tokens ya utilizados, accesos por roles no autorizados o violaciones de pertenencia contextual, registrando IP, fecha y hora (**EAC-03**).
- **ADR-007 (Configuración declarativa de reglas de negocio y plantillas versionadas por programa):**
  - La práctica mantiene la referencia inmutable a la `ReglaPrograma` vigente al momento de su postulación, la cual define las `horasRequeridas` de referencia institucional.
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La validación de horas requiere que la práctica se encuentre en estado formal `EnEjecucion`.
  - Intentos de validar reportes sobre prácticas en estados no permitidos (`PendienteVerificacion`, `Solicitada`, `Rechazada`, `Aprobada`, `Evaluada`, `Completada`) son rechazados por la máquina de estados con `EstadoPracticaInvalidoParaValidarHorasError` o `TransicionEstadoInvalidaError` (RN-02).
  - La entidad `RegistroHoras` controla las transiciones de su estado de validación (`Pendiente → Aprobado` o `Pendiente → Rechazado`), denegando reevaluaciones si ya cuenta con una decisión en firme.

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/token_evaluacion.py` *(Nuevo)*:
  - Entidad `TokenEvaluacion`: modela la credencial efímera para supervisores externos según `01-logica.puml` y ADR-004.
  - Atributos: `id: str`, `token: str`, `practica_id: str`, `supervisor_id: str`, `fecha_emision: datetime`, `fecha_expiracion: datetime`, `usado: bool`, `fecha_uso: Optional[datetime]`.
  - Invariantes y métodos de dominio:
    - `es_valido(ahora: datetime) -> bool`: verifica que `not self._usado` y `ahora <= self._fecha_expiracion` (dentro de los 15 días calendario, Escenarios 7 y 8).
    - `marcar_usado(fecha_uso: Optional[datetime]) -> None`: marca el token como consumido tras asentar una validación (Escenario 9). Lanza `TokenEvaluacionYaUsadoError` si ya fue utilizado.
- `dominio/modelos/registro_horas.py` *(Modificar)*:
  - Atributos adicionales: `_observaciones_rechazo: Optional[str] = None`.
  - Propiedad de lectura: `observaciones_rechazo -> Optional[str]`.
  - Método `aprobar() -> None`:
    - Valida que `estado_validacion == EstadoValidacionHoras.PENDIENTE`. Si ya está resuelto, lanza `ReporteHorasYaEvaluadoError` (Escenario 4).
    - Asigna `_estado_validacion = EstadoValidacionHoras.APROBADO` (Escenario 1).
  - Método `rechazar(motivo: str) -> None`:
    - Valida que `estado_validacion == EstadoValidacionHoras.PENDIENTE`. Si ya está resuelto, lanza `ReporteHorasYaEvaluadoError` (Escenario 4).
    - Valida que `motivo` sea una cadena no vacía; si es vacía o en blanco, lanza `MotivoRechazoHorasRequeridoError` (Escenario 3).
    - Asigna `_observaciones_rechazo = motivo.strip()` y `_estado_validacion = EstadoValidacionHoras.RECHAZADO` (Escenario 2).
- `dominio/modelos/practica.py` *(Modificar)*:
  - Atributo y propiedad: `_supervisor_empresa_id: Optional[str]` (identificador del supervisor vinculado a la práctica).
  - Método `acumular_horas_aprobadas(cantidad_horas: int) -> None`:
    - Valida que la práctica se encuentre en estado `EstadoPractica.EN_EJECUCION`; de lo contrario, lanza `EstadoPracticaInvalidoParaValidarHorasError` (Escenario 5).
    - Valida que `cantidad_horas > 0`.
    - Incrementa `_horas_acumuladas_aprobadas += cantidad_horas` (Escenario 1).
  - Método de consulta: `puede_validar_horas() -> bool` (retorna `True` si `_estado_actual == EstadoPractica.EN_EJECUCION`).
- `dominio/modelos/evento_bitacora.py` *(Existente)*:
  - Entidad `EventoBitacora`: modela los eventos append-only de auditoría para decisiones sobre horas y rechazos de seguridad.
- `dominio/errores.py` *(Modificar)*:
  - Excepciones de dominio específicas:
    - `TokenEvaluacionInvalidoError`: lanzada cuando un token presenta firma inválida, parámetros adulterados o formato erróneo (Escenario 8).
    - `TokenEvaluacionExpiradoError`: lanzada cuando el enlace o token supera los 15 días de emisión (Escenario 7).
    - `TokenEvaluacionYaUsadoError`: lanzada al intentar reutilizar un enlace de un solo uso consumido (Escenario 9).
    - `ReporteHorasYaEvaluadoError`: lanzada cuando se intenta evaluar un reporte de horas que ya fue aprobado o rechazado previamente (Escenario 4).
    - `MotivoRechazoHorasRequeridoError`: lanzada cuando se intenta rechazar un reporte de horas sin observaciones descriptivas (Escenario 3).
    - `EstadoPracticaInvalidoParaValidarHorasError`: lanzada cuando la práctica se encuentra en un estado que no admite validación de horas (Escenario 5).
    - `RegistroHorasNoEncontradoError`: lanzada cuando el identificador del reporte de horas no existe.
    - `SupervisorNoAsignadoAPracticaError`: lanzada ante violación de pertenencia contextual del supervisor a la práctica (Escenario 6).

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/validacion_horas_dto.py` *(Nuevo)*:
  - `ValidarHorasComando`: DTO inmutable de entrada con:
    - `practica_id: str`
    - `registro_horas_id: str`
    - `decision: str` (valores: `"Aprobar"` o `"Rechazar"`)
    - `observaciones: Optional[str] = None`
    - `token_acceso: Optional[str] = None`
    - `supervisor_id: Optional[str] = None`
    - `ip_origen: str = "127.0.0.1"`
  - `ValidacionHorasRespuestaDTO`: DTO inmutable de salida con:
    - `registro_horas_id: str`
    - `practica_id: str`
    - `semana: int`
    - `cantidad_horas: int`
    - `estado_validacion: str`
    - `horas_acumuladas_practica: int`
    - `observaciones: Optional[str]`
    - `fecha_decision: datetime`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_token_evaluacion.py` *(Nuevo)*:
  - Protocol `RepositorioTokenEvaluacionPort`:
    - `guardar(token: TokenEvaluacion) -> None`
    - `buscar_por_token(token: str) -> Optional[TokenEvaluacion]`
    - `buscar_por_id(token_id: str) -> Optional[TokenEvaluacion]`
- `aplicacion/puertos/repositorio_registro_horas.py` *(Existente)*:
  - Protocol `RepositorioRegistroHorasPort`: `buscar_por_id`, `guardar`, `listar_por_practica`.
- `aplicacion/puertos/repositorio_practica.py` *(Existente)*:
  - Protocol `RepositorioPracticaPort`: `buscar_por_id`, `guardar`.
- `aplicacion/puertos/repositorio_bitacora.py` *(Existente)*:
  - Protocol `RepositorioBitacoraPort`: `registrar_evento(evento: EventoBitacora)`.
- `aplicacion/puertos/servicio_correo.py` *(Existente)*:
  - Protocol `ServicioCorreoPort`: `enviar_correo(destinatario, asunto, cuerpo)` para notificar al estudiante sobre la decisión del supervisor.
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Operación canónica: `"validar_horas": {RolUsuario.SUPERVISOR.value, RolUsuario.SUPERVISOR_EMPRESA.value}`.
  - Método `validar_pertenencia_supervisor(contexto: ContextoUsuario, supervisor_asignado_id: str, operacion: Optional[str])`: valida que el supervisor opere exclusivamente sobre su propia práctica (Escenario 6, RN-01).
- `aplicacion/casos_uso/validar_horas_registradas.py` *(Nuevo)*:
  - Caso de uso `ValidarHorasRegistradasCasoUso` (Módulo Seguimiento y Evaluación):
    - Orquesta la autenticación por token efímero o contexto RBAC:
      - Si se provee `token_acceso`, verifica su validez y caducidad mediante `InterceptorIdentidad` y `RepositorioTokenEvaluacionPort`. Si el token es inválido, expirado o ya usado, asienta inmediatamente `EventoBitacora` de seguridad (< 1 min) y deniega con 0 datos expuestos (**EAC-03**, Escenarios 7, 8, 9 y 11).
      - Si se provee `ContextoUsuario`, valida la operación mediante `AutorizadorRBAC.validar_operacion` bajo política *deny-by-default* (Escenario 10).
    - Recupera la práctica desde `RepositorioPracticaPort` (o lanza `PracticaNoEncontradaError`).
    - Valida que la práctica se encuentre en estado `EnEjecucion` (Escenario 5).
    - Valida pertenencia: que el supervisor coincida con el supervisor asignado a la práctica (Escenario 6).
    - Recupera el `RegistroHoras` desde `RepositorioRegistroHorasPort` (o lanza `RegistroHorasNoEncontradoError`).
    - Valida que el `RegistroHoras` pertenezca a la práctica indicada.
    - Procesa la decisión:
      - Si la decisión es `"Aprobar"`: invoca `registro.aprobar()` y `practica.acumular_horas_aprobadas(registro.cantidad_horas)` (Escenario 1).
      - Si la decisión es `"Rechazar"`: invoca `registro.rechazar(comando.observaciones)` (Escenarios 2 y 3).
    - Persiste atómicamente el `RegistroHoras` y la `Practica` actualizada.
    - Si se utilizó un `TokenEvaluacion`, invoca `token.marcar_usado()` y persiste en `RepositorioTokenEvaluacionPort`.
    - Asienta un `EventoBitacora` inmutable (`APROBACION_HORAS_SEMANALES` o `RECHAZO_HORAS_SEMANALES`) con identificador del supervisor, práctica, reporte, fecha, hora e IP (ADR-006).
    - Emite una notificación al estudiante titular mediante `ServicioCorreoPort`.
    - Retorna `ValidacionHorasRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/seguridad/interceptor_identidad.py` *(Nuevo)*:
  - Componente `InterceptorIdentidad`:
    - Genera y valida tokens criptográficos efímeros con firma HMAC (ADR-004).
    - Valida integridad de firma, fecha de expiración `<= 15 días` y estado de no uso.
    - Emite un `ContextoUsuario` autenticado con rol `SupervisorEmpresa`.
- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - `InMemoryRepositorioTokenEvaluacion`: almacén determinista en memoria para tokens efímeros con búsquedas por token y por identificador.
  - Actualización de `InMemoryRepositorioPractica` e `InMemoryRepositorioRegistroHoras` para soportar actualizaciones de acumulados y estados de validación.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Instanciar `InMemoryRepositorioTokenEvaluacion`.
  - Instanciar `InterceptorIdentidad`.
  - Instanciar `ValidarHorasRegistradasCasoUso` inyectando repositorios, bitácora, servicio de correo, autorizador RBAC e interceptor de identidad.

---

## Flujo

Secuencia operativa para la validación de horas registradas (adaptada del diagrama de secuencia ESC-02 `docs/diagramas/secuencias/cu07-evaluar-desempeno.puml` y CU-05):

1. **Recepción de la solicitud y verificación de enlace efímero (ADR-004):**
   - El supervisor accede a través de un Magic Link que contiene un token HMAC.
   - El `InterceptorIdentidad` valida la firma criptográfica HMAC y consulta el `TokenEvaluacion` en `RepositorioTokenEvaluacionPort`.
   - **Guarda de rechazo temprano (EAC-03):** Si el token está alterado, expiró (> 15 días) o ya fue utilizado:
     - Se registra inmediatamente un `EventoBitacora` (`AccesoRechazadoTokenInvalido`, `AccesoRechazadoTokenExpirado` o `AccesoRechazadoTokenYaUsado`) con IP, fecha y hora en menos de 1 minuto.
     - Se interrumpe la ejecución rechazando el acceso con 0 datos expuestos de la práctica y del estudiante.
2. **Autorización RBAC centralizada y pertenencia (ADR-005, RN-01):**
   - El `AutorizadorRBAC` valida que el actor tenga rol `SupervisorEmpresa` bajo política *deny-by-default*.
   - Se consulta la práctica en `RepositorioPracticaPort`. Si no existe, se arroja `PracticaNoEncontradaError`.
   - Se valida la pertenencia contextual: si el supervisor que invoca la operación no coincide con el supervisor registrado en la práctica, se deniega la petición y se registra el intento en bitácora sin exponer datos.
3. **Validación del estado de la práctica en la máquina de estados (ADR-010):**
   - Se verifica que la práctica esté en estado formal `EstadoPractica.EN_EJECUCION`. Si la práctica está en `Solicitada`, `Rechazada`, etc., se rechaza lanzando `EstadoPracticaInvalidoParaValidarHorasError`.
4. **Recuperación y validación del reporte semanal de horas:**
   - Se consulta el `RegistroHoras` mediante `RepositorioRegistroHorasPort.buscar_por_id(registro_horas_id)`.
   - Se valida que pertenezca a la práctica indicada.
   - Se verifica que `registro.estado_validacion == EstadoValidacionHoras.PENDIENTE`. Si ya está en `Aprobado` o `Rechazado`, se interrumpe lanzando `ReporteHorasYaEvaluadoError`.
5. **Ejecución de la decisión en el dominio:**
   - **Caso Aprobación:**
     - `registro.aprobar()` transiciona el reporte a `EstadoValidacionHoras.APROBADO`.
     - `practica.acumular_horas_aprobadas(registro.cantidad_horas)` suma las horas reportadas al acumulado de horas aprobadas de la práctica.
   - **Caso Rechazo:**
     - Si la observación o motivo es vacía, se lanza `MotivoRechazoHorasRequeridoError`.
     - `registro.rechazar(observaciones)` almacena las observaciones y transiciona a `EstadoValidacionHoras.RECHAZADO`. El acumulado de horas de la práctica permanece inalterado.
6. **Persistencia atómica y consumo de token:**
   - Se persisten los cambios de `RegistroHoras` en `RepositorioRegistroHorasPort`.
   - Se persiste la `Practica` actualizada en `RepositorioPracticaPort`.
   - Si se utilizó `TokenEvaluacion`, se marca como consumido (`token.marcar_usado()`) y se guarda en `RepositorioTokenEvaluacionPort`.
7. **Trazabilidad inmutable en bitácora (ADR-006):**
   - Se asienta un `EventoBitacora` inmutable con la acción (`APROBACION_HORAS_SEMANALES` o `RECHAZO_HORAS_SEMANALES`), identificador del supervisor, práctica, reporte de horas, fecha, hora e IP.
8. **Notificación al estudiante:**
   - Se invoca `ServicioCorreoPort.enviar_correo` notificando al estudiante sobre el estado de la validación (aprobada o rechazada con observaciones).
9. **Respuesta:**
   - Se retorna `ValidacionHorasRespuestaDTO` con el resumen formal de la validación.

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md`):

- `RegistroHoras`: reporte semanal de horas evaluado; almacena `id`, `practica_id`, `semana`, `cantidad_horas`, `descripcion_actividades`, `estado_validacion` (`Pendiente`, `Aprobado`, `Rechazado`), `observaciones_rechazo` y `fecha_registro`.
- `Practica`: entidad agregada raíz; almacena `id`, `estudiante_id`, `supervisor_empresa_id`, `estadoActual` (`EnEjecucion`), `horasAcumuladasAprobadas` y `regla_programa_id`.
- `TokenEvaluacion`: credencial criptográfica efímera; almacena `id`, `token`, `practica_id`, `supervisor_id`, `fecha_emision`, `fecha_expiracion` (15 días) y `usado`.
- `SupervisorEmpresa`: jefe inmediato externo responsable de validar las horas del practicante.
- `Estudiante`: titular de la práctica que recibe las notificaciones de aprobación o rechazo.
- `ReglaPrograma`: regla vigente que define las `horasRequeridas` de referencia institucional.
- `EventoBitacora`: registro transaccional inmutable de solo inserción con `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada`.

---

## Fuera de alcance

- Diligenciamiento y calificación de la rúbrica de evaluación de desempeño por el supervisor (CU-07).
- Consulta y visualización de avances acumulados por parte del docente asesor (CU-06).
- Envío de alertas y recordatorios programados por vencimiento de plazos (CU-08).
- Generación de acta final de práctica en PDF y cálculo de hash SHA-256 (CU-09).
- Aprobación y firma electrónica del acta por docente y coordinador (CU-10).
- Registro inicial de horas por parte del estudiante (CU-04).

---

## Decisiones pendientes

Ninguna. La estructura modular en capas, el mecanismo de autenticación híbrida por tokens HMAC efímeros con expiración de 15 días, el control de acceso contextual RBAC *deny-by-default*, la bitácora transaccional *append-only* y el gobierno del ciclo de vida mediante máquina de estados finitos están formalmente respaldados por los **ADR-002, ADR-004, ADR-005, ADR-006, ADR-007 y ADR-010**.
