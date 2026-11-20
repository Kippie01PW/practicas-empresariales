# Plan: 008 Enviar recordatorios de plazos

## Decisiones que aplican

- **ADR-001 (Resiliencia e integración asíncrona):**
  - El despacho de recordatorios de plazos (ejecutado diariamente por el `Worker de integración` o disparado manualmente por el `Coordinador de prácticas`) utiliza el servicio de correo (`ServicioCorreoPort`) y la cola persistente del bróker de mensajería (`PublicadorEventosPort` / `InMemoryBrokerMensajes`) para garantizar tolerancia a fallos (**PA-04**, **EAC-02**, **DT-03**).
  - Si el servicio de correo externo falla durante el envío de un recordatorio, el sistema captura la excepción `ErrorServicioCorreo`, encola la notificación pendiente con reintentos exponenciales (o la enruta a la *Dead-Letter Queue* con alerta operativa tras agotar reintentos), registra el intento en bitácora y continúa procesando el resto de las prácticas del lote sin pérdida de información (`0% de pérdida de recordatorios`, Escenario 10).
- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas concéntricas (`dominio/`, `aplicacion/`, `infraestructura/`) con `main.py` como único punto de composición e inyección de dependencias.
  - El caso de uso `EnviarRecordatoriosPlazosCasoUso` reside en el `Módulo Seguimiento y Evaluación` de la capa `aplicacion/`, operando exclusivamente a través de puertos (`RepositorioPracticaPort`, `RepositorioRegistroHorasPort`, `RepositorioTokenEvaluacionPort`, `RepositorioDocentePort`, `RepositorioReglaProgramaPort`, `ServicioCorreoPort`, `PublicadorEventosPort`) sin acoplarse a detalles de infraestructura.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - Las operaciones de emisión/invalidación de `TokenEvaluacion` y escritura de `EventoBitacora` se ejecutan de forma determinista y transaccional sobre los repositorios en memoria.
- **ADR-004 (Esquema de autenticación híbrida con enlaces criptográficos efímeros):**
  - Mitiga el riesgo **R-02** (*Supervisor de empresa no responde la evaluación en los plazos fijados*):
    - Si el `TokenEvaluacion` vinculado a una práctica en `EnEjecucion` sigue vigente (`<= 15 días calendario` y `usado == False`), el recordatorio incluye el enlace criptográfico actual (Escenario 1).
    - Si el `TokenEvaluacion` anterior superó los `15 días calendario` sin uso (`!es_valido(ahora)`), la tarea invalida el token expirado y emite un nuevo `TokenEvaluacion` firmado con HMAC-SHA256 con nueva vigencia de 15 días calendario y `usado = False` (Escenario 2).
    - Cualquier intento posterior de usar un `TokenEvaluacion` expirado o reemplazado es rechazado con `0 datos expuestos` y registro inmediato en bitácora (**EAC-03**, Escenario 11).
  - Tras alcanzar **3 recordatorios o emisiones de token** sin respuesta del `SupervisorEmpresa`, el sistema escala automáticamente una alerta por correo electrónico al `DocenteAsesor` asignado a la práctica (Escenario 3).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/autorizador_rbac.py` gobierna quién puede invocar `enviar_recordatorios` bajo política *deny-by-default* (**RN-03**):
    - Autorizado únicamente para el actor técnico `"SISTEMA"` (tarea programada diaria) y para el rol `"Coordinador de prácticas"` (`RolUsuario.COORDINADOR` / `RolUsuario.COORDINADOR_PRACTICAS`) en disparo manual (Escenario 6).
    - Cualquier intento de disparo manual por `"Estudiante"`, `"DocenteAsesor"` o `"SupervisorEmpresa"` es denegado de inmediato con registro en `EventoBitacora` y `0 datos expuestos` (Escenarios 9 y 11).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada recordatorio despachado, cada renovación de `TokenEvaluacion`, cada alerta de escalamiento al `DocenteAsesor` tras 3 recordatorios, cada fallo de correo encolado y cada intento de disparo manual no autorizado inserta atómicamente un `EventoBitacora` inmutable sellado con SHA-256.
  - La bitácora permite verificar determinísticamente la ventana de enfriamiento (*cooldown*) de **1 hora** entre recordatorios consecutivos para una misma práctica y acción pendiente, así como el conteo acumulado de recordatorios enviados al supervisor para activar el escalamiento al tercer intento (Escenarios 3 y 7).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - La evaluación de si una práctica en `EnEjecucion` o `Evaluada` ya alcanzó las horas exigidas consulta estrictamente `horas_requeridas` de la versión de `ReglaPrograma` vinculada a la `Practica` (`practica.regla_programa_id`).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La elegibilidad de cada práctica para recibir recordatorios depende estrictamente de su `estadoActual` en la máquina de estados (**RN-02**, **OB-01**):
    - `Solicitada`: recordatorio al `Coordinador de prácticas` por aprobación/rechazo pendiente (CU-02).
    - `Aprobada`: recordatorio al `Coordinador de prácticas` por asignación de `DocenteAsesor` pendiente (CU-03).
    - `Asignada` / `EnEjecucion`:
      - Recordatorio al `Estudiante` si no ha registrado reportes de `RegistroHoras` dentro del umbral en días calendario (CU-04).
      - Recordatorio al `SupervisorEmpresa` si existen reportes de `RegistroHoras` en estado `Pendiente` que superan el umbral en días calendario (CU-05, Escenario 4).
      - Recordatorio al `SupervisorEmpresa` si la práctica requiere `EvaluacionDesempeno` y el enlace lleva días calendario sin respuesta o expiró tras 15 días calendario, con escalamiento al `DocenteAsesor` tras 3 recordatorios (CU-07, Escenarios 1, 2 y 3).
    - `Evaluada`: recordatorio al `DocenteAsesor` o al `Coordinador de prácticas` por generación o firma pendiente de `ActaFinal` para cumplir el objetivo de máximo 10 días calendario (**OB-01**, CU-09, CU-10, Escenario 5).
    - `Completada` y `Rechazada`: estados terminales excluidos del lote de recordatorios (Escenario 8).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/token_evaluacion.py` *(Modificar)*:
  - Agregar método de dominio `invalidar(fecha_invalidacion: Optional[datetime] = None) -> None` (o marcar consumo/reemplazo por expiración) para que cuando CU-08 renueve un `TokenEvaluacion` expirado tras 15 días calendario y emita uno nuevo, el token anterior quede explícitamente invalidado/consumido y no pueda utilizarse si alguien intenta abrir el enlace antiguo (Escenarios 2 y 11, **ADR-004**, **EAC-03**).
- `dominio/errores.py` *(Modificar)*:
  - Agregar excepción de dominio `RecordatorioEnEnfriamientoError(ErrorDominio)` (opcional para invocaciones directas sobre una práctica específica dentro de la ventana de *cooldown* de 1 hora).

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/recordatorio_plazos_dto.py` *(Nuevo)*:
  - `EjecutarRecordatoriosComando`: DTO inmutable de entrada para disparar la tarea programada diaria o la ejecución manual por el Coordinador:
    - `actor_id: str = "SISTEMA"`
    - `rol_actor: str = "SISTEMA"`
    - `ip_origen: str = "127.0.0.1"`
    - `practica_id_filtro: Optional[str] = None` (permite procesar todo el lote o filtrar una práctica específica en disparo manual)
    - `fecha_referencia: Optional[datetime] = None` (instante de evaluación en días calendario; por defecto `datetime.now(timezone.utc)`)
    - `umbral_dias_calendario: int = 3` (días naturales de inactividad/retraso para considerar un trámite pendiente vencido dentro de la meta de 10 días de **OB-01**)
    - `cooldown_minutos: int = 60` (ventana de enfriamiento de 1 hora para idempotencia, Escenario 7)
    - `max_recordatorios_antes_escalamiento: int = 3` (umbral de 3 recordatorios antes de alertar al `DocenteAsesor`, Escenario 3)
  - `DetalleRecordatorioEnviadoDTO`: DTO inmutable con el resultado unitario de cada recordatorio, renovación o escalamiento procesado:
    - `practica_id: str`
    - `tipo_recordatorio: str` (`"EVALUACION_DESEMPENO"`, `"VALIDACION_HORAS"`, `"REPORTE_HORAS_ESTUDIANTE"`, `"TRAMITE_COORDINACION"`, `"CIERRE_ACTA_INTERNO"`, `"ESCALAMIENTO_DOCENTE_ASESOR"`)
    - `destinatario_id: str`
    - `correo_destinatario: str`
    - `rol_destinatario: str`
    - `token_emitido: Optional[str] = None`
    - `token_renovado: bool = False`
    - `escalado_a_docente: bool = False`
    - `encolado_por_fallo_correo: bool = False`
    - `mensaje: str = ""`
  - `ResultadoEnvioRecordatoriosDTO`: DTO inmutable de salida del caso de uso:
    - `total_practicas_evaluadas: int`
    - `total_recordatorios_enviados: int`
    - `total_tokens_renovados: int`
    - `total_escalamientos_docente: int`
    - `total_omitidos_por_cooldown: int`
    - `total_omitidos_al_dia_o_terminales: int`
    - `total_encolados_por_fallo_correo: int`
    - `detalles: tuple[DetalleRecordatorioEnviadoDTO, ...]`
    - `fecha_ejecucion: datetime`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_token_evaluacion.py` *(Modificar)*:
  - Agregar firma `listar_por_practica(practica_id: str) -> list[TokenEvaluacion]` al protocolo `RepositorioTokenEvaluacionPort` para consultar los tokens emitidos para una práctica, verificar su expiración en 15 días calendario y contabilizar las emisiones/renovaciones previas.
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Agregar `RolUsuario.SISTEMA = "SISTEMA"` (y alias `"sistema"`) para identificar formalmente la tarea programada automatizada.
  - Registrar la operación `"enviar_recordatorios"` en `_MATRIZ_PERMISOS` permitida exclusivamente para `{RolUsuario.SISTEMA.value, RolUsuario.COORDINADOR.value, RolUsuario.COORDINADOR_PRACTICAS.value}`.
  - Agregar método `validar_envio_recordatorios(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "enviar_recordatorios") -> None` bajo política *deny-by-default* (Escenarios 6 y 9, **ADR-005**).
- `aplicacion/casos_uso/enviar_recordatorios_plazos.py` *(Nuevo)*:
  - Clase `EnviarRecordatoriosPlazosCasoUso` (Módulo Seguimiento y Evaluación, `docs/vistas/03-desarrollo.md`):
    - Inyecta `RepositorioPracticaPort`, `RepositorioRegistroHorasPort`, `RepositorioTokenEvaluacionPort`, `RepositorioDocentePort`, `RepositorioReglaProgramaPort`, `ServicioCorreoPort`, `PublicadorEventosPort`, `AutorizadorRBAC`, `InterceptorIdentidad` y `RepositorioEvaluacionDesempenoPort` (opcional, si está disponible en composición).
    - Método `ejecutar(comando: EjecutarRecordatoriosComando) -> ResultadoEnvioRecordatoriosDTO` (y `__call__`):
      1. **Autorización RBAC (ADR-005, EAC-03):**
         - Invoca `autorizador_rbac.validar_envio_recordatorios(comando.rol_actor, comando.actor_id)`.
         - Si un `Estudiante`, `DocenteAsesor` o `SupervisorEmpresa` intenta disparar manualmente la tarea, registra de inmediato un `EventoBitacora` de acceso denegado en `< 1 min` y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenarios 9 y 11).
      2. **Selección de prácticas candidatas (ADR-010):**
         - Recupera todas las prácticas (o la indicada en `practica_id_filtro`).
         - Excluye inmediatamente prácticas en estados terminales `Completada` o `Rechazada` (Escenario 8).
      3. **Verificación de ventana de enfriamiento (*cooldown* de 1 hora, Escenario 7):**
         - Antes de despachar un recordatorio para una práctica y tipo de acción pendiente, inspecciona los `EventoBitacora` de la práctica (`buscar_eventos_por_entidad(f"Practica:{practica.id}")`).
         - Si ya existe un recordatorio enviado para esa misma acción hace menos de `comando.cooldown_minutos` (60 minutos / 1 hora), omite el envío e incrementa `total_omitidos_por_cooldown`.
      4. **Evaluación de plazos en días naturales (días calendario) por estado y actor:**
         - **A) Supervisores de empresa externos (`EstadoPractica.EN_EJECUCION`, ADR-004, R-02):**
           - *Validación de horas pendientes (Escenario 4):* Si existen registros de `RegistroHoras` en estado `Pendiente` cuya antigüedad en días calendario (`(ahora - registro.fecha_registro).days >= umbral_dias_calendario`), agrupa los reportes pendientes y envía recordatorio al `SupervisorEmpresa` con enlace criptográfico vigente (o renovado si expiró).
           - *Evaluación de desempeño pendiente (Escenarios 1, 2 y 3):* Si la práctica está pendiente de evaluación (tiene token de evaluación emitido o alcanzó las `horasRequeridas` de su `ReglaPrograma` sin evaluación asentada):
             - Si el `TokenEvaluacion` actual está vigente (`<= 15 días calendario`) y su antigüedad en días calendario supera `umbral_dias_calendario`, envía recordatorio al `SupervisorEmpresa` con el token vigente (Escenario 1).
             - Si el `TokenEvaluacion` actual superó los `15 días calendario` de emisión (`!token.es_valido(ahora)`), invalida el token expirado y genera un nuevo `TokenEvaluacion` HMAC-SHA256 con 15 días calendario de vigencia mediante `InterceptorIdentidad.generar_token()`, enviando el nuevo enlace al `SupervisorEmpresa` (Escenario 2).
           - *Escalamiento al DocenteAsesor tras 3 recordatorios (Escenario 3):* Contabiliza los recordatorios previos enviados al `SupervisorEmpresa` sobre la práctica. Si ya se alcanzaron `>= 3` recordatorios/emisiones sin respuesta, despacha correo de alerta de escalamiento al `DocenteAsesor` asignado (`practica.docente_asesor_id`) y registra el `EventoBitacora` de escalamiento.
         - **B) Actores internos en días calendario (Escenario 5, OB-01):**
           - `Solicitada` o `Aprobada` con antigüedad `>= umbral_dias_calendario`: envía recordatorio al `Coordinador de prácticas` para aprobar/rechazar postulación (CU-02) o asignar `DocenteAsesor` (CU-03).
           - `Asignada` o `EnEjecucion` sin reportes de `RegistroHoras` recientes por `>= umbral_dias_calendario`: envía recordatorio al `Estudiante` titular para registrar sus horas semanales (CU-04).
           - `Evaluada` con antigüedad `>= umbral_dias_calendario`: envía recordatorio al `DocenteAsesor` asignado y/o al `Coordinador de prácticas` para generar y aprobar electrónicamente el `ActaFinal` (CU-09, CU-10).
      5. **Despacho resiliente de correo y auditoría Append-Only (ADR-001, ADR-006, EAC-02):**
         - Invoca `servicio_correo.enviar_notificacion(destinatario, asunto, cuerpo)`.
         - Si el correo se envía con éxito, inserta un `EventoBitacora` con `actorIdentificador` (`"SISTEMA"` o el ID del Coordinador en disparo manual), `rolActor`, `accionRealizada`, `entidadAfectada = f"Practica:{practica.id}"`, fecha, hora e IP.
         - Si `servicio_correo` lanza `ErrorServicioCorreo` (Escenario 10, **EAC-02**), encola la alerta/tarea en `publicador_eventos`, registra el `EventoBitacora` del fallo transitorio encolado e incrementa `total_encolados_por_fallo_correo` sin abortar el lote.
      6. **Retorno:**
         - Retorna `ResultadoEnvioRecordatoriosDTO` con las métricas consolidadas y la tupla inmutable de `DetalleRecordatorioEnviadoDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - En `InMemoryRepositorioTokenEvaluacion`, agregar el método `listar_por_practica(practica_id: str) -> list[TokenEvaluacion]` que retorna los tokens asociados a una práctica ordenados cronológicamente por `fecha_emision`.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `EnviarRecordatoriosPlazosCasoUso`, `EjecutarRecordatoriosComando` y `ResultadoEnvioRecordatoriosDTO`.
  - Agregar `caso_uso_enviar_recordatorios: EnviarRecordatoriosPlazosCasoUso` al contenedor `SistemaPracticasEmpresariales`.
  - Instanciar e inyectar `EnviarRecordatoriosPlazosCasoUso` en `inicializar_sistema()`.
  - Agregar demostración CLI de CU-08 en `main()`.

---

## Flujo

Aunque CU-08 no es uno de los 5 escenarios primarios diagramados individualmente en `docs/diagramas/secuencias/`, sigue la arquitectura de procesos de `docs/vistas/02-procesos.md` (`Worker de integración`, `Broker de mensajes`, `Servicio de correo`, `PostgreSQL`) y se articula con `docs/diagramas/secuencias/cu07-evaluar-desempeno.puml` (ESC-02):

1. **Activación (Diaria programada o Disparo manual):**
   - El `Worker de integración` (con identidad `"SISTEMA"`) ejecuta diariamente la tarea programada, o el `Coordinador de prácticas` invoca manualmente el caso de uso desde la `API de prácticas`.
2. **Validación RBAC (*deny-by-default*, ADR-005):**
   - `AutorizadorRBAC` verifica que el invocador sea `"SISTEMA"` o `"Coordinador de prácticas"`. Si es otro rol (`Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`), registra `EventoBitacora` inmediato y rechaza la solicitud (Escenario 9).
3. **Inspección de prácticas activas y control de *cooldown* (1 hora):**
   - El caso de uso consulta las prácticas no terminales (`Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`) y calcula en **días naturales (días calendario)** el tiempo transcurrido desde el último hito o reporte.
   - Verifica en la bitácora si ya se envió un recordatorio del mismo tipo para la práctica en los últimos **60 minutos (1 hora)**; de ser así, lo omite (Escenario 7).
4. **Gestión de enlaces criptográficos efímeros y escalamiento (ADR-004, R-02):**
   - Para recordatorios al `SupervisorEmpresa`:
     - Si el `TokenEvaluacion` está vigente (`<= 15 días calendario`), reenvía el enlace actual (Escenario 1).
     - Si el `TokenEvaluacion` superó los `15 días calendario`, invalida el token anterior y emite un nuevo `TokenEvaluacion` firmado con HMAC-SHA256 con 15 días de vigencia (Escenario 2).
     - Si ya se acumulan **3 recordatorios** sin respuesta del supervisor, envía una alerta de escalamiento por correo al `DocenteAsesor` asignado (Escenario 3).
5. **Despacho resiliente por correo y registro en bitácora (ADR-001, ADR-006, EAC-02):**
   - Despacha cada notificación a través de `ServicioCorreoPort` (hacia supervisores externos o actores internos: `Estudiante`, `DocenteAsesor`, `Coordinador de prácticas`) y asienta atómicamente el `EventoBitacora`.
   - Ante caída o error del servidor de correo, encola la notificación en el `Broker de mensajes` para reintento asíncrono sin detener el procesamiento de las demás prácticas del lote (`0% de pérdida`, Escenario 10).

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `Practica`: agregado raíz cuyo `estadoActual`, `fechaPostulacion`, `fechaInicio`, `fechaFin`, `horasAcumuladasAprobadas`, `estudiante_id`, `docente_asesor_id` y `supervisor_empresa_id` determinan las acciones pendientes y sus destinatarios.
- `TokenEvaluacion`: credencial criptográfica efímera (Magic Link HMAC-SHA256) con vigencia de 15 días calendario y un solo uso; se adjunta si está vigente o se invalida y reemite si expiró (**ADR-004**, **EAC-03**).
- `RegistroHoras`: reportes semanales de horas cuyos registros en estado `Pendiente` (o su ausencia en prácticas en curso) disparan recordatorios al `SupervisorEmpresa` o al `Estudiante`.
- `ReglaPrograma`: regla versionada vinculada a la práctica de la cual se consulta `horasRequeridas` (**ADR-007**).
- `DocenteAsesor`: tutor académico asignado a la práctica; recibe recordatorios de cierre de acta en estado `Evaluada` y alertas de escalamiento cuando el `SupervisorEmpresa` acumula 3 recordatorios sin respuesta.
- `Estudiante`: practicante titular; recibe recordatorios cuando no reporta horas semanales dentro del umbral en días calendario.
- `SupervisorEmpresa`: jefe inmediato externo; recibe recordatorios con enlaces criptográficos efímeros para validar horas (CU-05) o evaluar desempeño (CU-07).
- `EventoBitacora`: registro inmutable *Append-Only* que audita cada recordatorio enviado, renovación de token, escalamiento al docente, ventana de *cooldown* de 1 hora, fallo de correo encolado y rechazo de disparo manual no autorizado (**ADR-006**).

---

## Fuera de alcance

- Diligenciamiento o asentamiento de la validación de horas por el supervisor (cubierto en CU-05).
- Diligenciamiento o asentamiento de la evaluación de desempeño por el supervisor (cubierto en CU-07).
- Generación del archivo PDF del `ActaFinal` y sellado SHA-256 (cubierto en CU-09).
- Firma y aprobación electrónica del `ActaFinal` por docente y coordinador (cubierto en CU-10).
- Modificación de estados del ciclo de vida de la `Practica` (CU-08 solo notifica, renueva tokens efímeros expirados y escala alertas sin alterar el `estadoActual` de la práctica).

---

## Decisiones pendientes

Ninguna. Las cinco aclaraciones de negocio proporcionadas por el usuario (1. ejecución diaria en días naturales/calendario; 2. emisión automática de nuevo token al expirar y alerta de escalamiento al `DocenteAsesor` después de 3 recordatorios; 3. cobertura tanto de `SupervisorEmpresa` como de actores internos; 4. período de enfriamiento/*cooldown* de 1 hora; 5. permiso de disparo manual para el `Coordinador de prácticas`) han sido integradas en `specs/008-enviar-recordatorios-plazos/spec.md` y están completamente respaldadas por los **ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007 y ADR-010**.

