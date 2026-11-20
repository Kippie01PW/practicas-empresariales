# language: es
# Traza: CU-08, EAC-02, EAC-03, RT-01, RN-01, RN-02, RN-03, RN-04, ADR-001, ADR-002, ADR-004, ADR-005, ADR-006, ADR-010
Característica: Enviar recordatorios de plazos
  Como Sistema mediante una tarea programada automatizada de ejecución diaria o Coordinador de prácticas mediante disparo manual autorizado
  Quiero identificar en días calendario las prácticas empresariales con validaciones de horas, evaluaciones de desempeño o trámites internos pendientes o vencidos y despachar notificaciones por correo electrónico junto con la renovación de enlaces criptográficos efímeros y el escalamiento tras 3 recordatorios sin respuesta
  Para mitigar retrasos de actores externos e internos, reducir el tiempo total de gestión a un máximo de 10 días calendario y evitar bloqueos en la generación y aprobación del acta final

  Escenario: Envío automático diario de recordatorio a supervisor de empresa por evaluación de desempeño pendiente con enlace vigente
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al Estudiante "EST-001" y vinculada a una ReglaPrograma con 320 horasRequeridas
    Y la práctica cuenta con 320 horasAcumuladasAprobadas, no tiene una EvaluacionDesempeno registrada y tiene asignado al SupervisorEmpresa "SUP-001" y al DocenteAsesor "DOC-001"
    Y existe un TokenEvaluacion para evaluación de desempeño con usado igual a falso cuya fecha de emisión se encuentra dentro del plazo de vigencia de 15 días calendario pero supera el umbral de días calendario sin respuesta del supervisor
    Cuando se ejecuta la tarea programada diaria de envío de recordatorios de plazos
    Entonces el sistema identifica la Práctica con evaluación de desempeño pendiente
    Y el sistema despacha un recordatorio por correo electrónico al SupervisorEmpresa "SUP-001" incluyendo el enlace de acceso con su TokenEvaluacion vigente
    Y el sistema registra atómicamente un EventoBitacora con el actor "SISTEMA", acción de envío de recordatorio de evaluación de desempeño, identificador de la práctica, destinatario "SUP-001", fecha y hora

  Escenario: Renovación y emisión de nuevo TokenEvaluacion al supervisor de empresa cuando el enlace anterior expiró tras 15 días calendario
    Dado que existe una Práctica en estado "EnEjecucion" supervisada por el SupervisorEmpresa "SUP-001" y asesorada por el DocenteAsesor "DOC-001"
    Y la práctica tiene pendiente el registro de la EvaluacionDesempeno
    Y el TokenEvaluacion previamente emitido para dicha Práctica ha superado los 15 días calendario de vigencia sin haber sido utilizado y se han enviado menos de 3 recordatorios previos
    Cuando se ejecuta la tarea programada diaria de envío de recordatorios de plazos
    Entonces el sistema invalida el TokenEvaluacion expirado y emite un nuevo TokenEvaluacion de un solo uso con vigencia de 15 días calendario vinculado a la Práctica y al SupervisorEmpresa "SUP-001"
    Y el sistema despacha por correo electrónico al SupervisorEmpresa "SUP-001" el recordatorio con el nuevo enlace criptográfico efímero
    Y el sistema registra un EventoBitacora dejando trazabilidad de la invalidación del token expirado, la emisión del nuevo TokenEvaluacion y el despacho del recordatorio

  Escenario: Escalamiento y envío de alerta al DocenteAsesor tras alcanzar 3 recordatorios o emisiones de token sin respuesta del supervisor de empresa
    Dado que existe una Práctica en estado "EnEjecucion" supervisada por el SupervisorEmpresa "SUP-001" y asesorada por el DocenteAsesor "DOC-001"
    Y la práctica tiene pendiente la EvaluacionDesempeno o la validación de RegistroHoras
    Y el sistema ya ha emitido 3 recordatorios o renovaciones de TokenEvaluacion al SupervisorEmpresa "SUP-001" sin obtener respuesta
    Cuando se ejecuta la tarea diaria de envío de recordatorios de plazos
    Entonces el sistema detecta que se ha superado el límite de 3 recordatorios sin respuesta del SupervisorEmpresa
    Y el sistema despacha una notificación de alerta de escalamiento por correo electrónico al DocenteAsesor "DOC-001" informando la falta de respuesta del SupervisorEmpresa "SUP-001" sobre la Práctica
    Y el sistema registra un EventoBitacora con la acción de escalamiento de alerta al DocenteAsesor "DOC-001", identificador de la práctica, fecha y hora

  Escenario: Envío automático de recordatorio a supervisor de empresa por reportes semanales de horas pendientes de validación
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al Estudiante "EST-001" y supervisada por el SupervisorEmpresa "SUP-001"
    Y la práctica tiene uno o más registros de RegistroHoras en estadoValidacion "Pendiente" que han superado el umbral de días calendario sin revisión por parte del supervisor
    Cuando se ejecuta la tarea programada diaria de envío de recordatorios de plazos
    Entonces el sistema agrupa los registros de RegistroHoras en estado "Pendiente" de la Práctica y despacha un correo electrónico de recordatorio al SupervisorEmpresa "SUP-001"
    Y el sistema registra un EventoBitacora con el actor "SISTEMA", acción de envío de recordatorio de validación de horas, identificador de la práctica, destinatario "SUP-001", fecha y hora

  Escenario: Envío automático de recordatorio a actores internos por trámites pendientes en días calendario
    Dado que existen prácticas activas con acciones pendientes por parte de actores internos que superan el umbral de días calendario para cumplir el objetivo de gestión de máximo 10 días calendario:
    Y una Práctica en estado "Solicitada" o "Aprobada" pendiente de aprobación o asignación de tutor por el Coordinador de prácticas, o en estado "EnEjecucion" sin reporte semanal reciente del Estudiante "EST-001", o en estado "Evaluada" pendiente de generación o firma de ActaFinal por el DocenteAsesor "DOC-001" o el Coordinador de prácticas
    Cuando se ejecuta la tarea programada diaria de envío de recordatorios de plazos
    Entonces el sistema despacha un recordatorio por correo electrónico al actor interno responsable (Estudiante, DocenteAsesor o Coordinador de prácticas) detallando la acción pendiente sobre la Práctica
    Y el sistema registra un EventoBitacora por cada recordatorio enviado indicando el actor "SISTEMA", el destinatario interno, la acción pendiente recordada, el identificador de la práctica, fecha y hora

  Escenario: Disparo manual exitoso del envío de recordatorios por el Coordinador de prácticas
    Dado que existe una Práctica en estado "EnEjecucion" con evaluación o validación pendiente por parte del SupervisorEmpresa "SUP-001" fuera del período de enfriamiento de 1 hora
    Y el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas dispara manualmente la ejecución de recordatorios de plazos
    Entonces el sistema autoriza la operación para el rol "Coordinador de prácticas"
    Y el sistema procesa y despacha el recordatorio por correo electrónico al destinatario correspondiente renovando el TokenEvaluacion si se encontraba expirado
    Y el sistema registra un EventoBitacora con el identificador "COORD-001", rol "Coordinador de prácticas", acción de disparo manual de recordatorios, identificador de la práctica, fecha, hora e IP de origen

  Escenario: Prevención de envío duplicado de recordatorios dentro del período de enfriamiento de 1 hora
    Dado que existe una Práctica en estado "EnEjecucion" con evaluación de desempeño pendiente por parte del SupervisorEmpresa "SUP-001"
    Y el sistema ya despachó un recordatorio exitoso para dicha Práctica y acción pendiente hace menos de 1 hora
    Cuando la tarea programada o un disparo manual intenta ejecutar nuevamente el envío de recordatorios dentro de la ventana de enfriamiento de 1 hora
    Entonces el sistema detecta en el historial de bitácora que existe un recordatorio enviado hace menos de 1 hora para la misma Práctica y acción
    Y el sistema omite el despacho de un correo duplicado al SupervisorEmpresa "SUP-001" garantizando la idempotencia del proceso

  Escenario: Omisión de envío de recordatorios para prácticas al día o en estados terminales
    Dado que existen en el sistema prácticas cuyo estadoActual es "Completada" o "Rechazada"
    Y existen prácticas activas cuyos trámites se encuentran dentro del plazo en días calendario sin acciones vencidas
    Cuando se ejecuta la tarea de envío de recordatorios de plazos
    Entonces el sistema excluye dichas prácticas del lote de notificación
    Y el sistema no emite correos electrónicos ni genera nuevos registros de TokenEvaluacion para ellas

  Escenario: Intento de disparo manual del envío de recordatorios por un rol no autorizado
    Dado que un usuario autenticado con rol de "Estudiante", "DocenteAsesor" o "SupervisorEmpresa" intenta disparar manualmente la ejecución de la tarea de envío de recordatorios de plazos
    Cuando el mecanismo centralizado de autorización evalúa los permisos del rol bajo la política deny-by-default
    Entonces el sistema deniega la operación por falta de privilegios para ejecutar o disparar recordatorios
    Y el sistema no despacha ningún correo electrónico ni altera ningún TokenEvaluacion
    Y el sistema registra de inmediato un EventoBitacora por intento de operación por rol no autorizado con el identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-02 - Tolerancia a fallos y reintentos asíncronos ante indisponibilidad del servicio de correo institucional
    Dado que la tarea de recordatorios identifica un lote de prácticas activas que requieren el envío de recordatorios de plazos en una cohorte de hasta 500 estudiantes y 50 tutores
    Y el servicio de correo externo no responde o presenta error de conexión al momento del despacho
    Cuando el proceso intenta entregar las notificaciones de recordatorio
    Entonces el sistema conserva la totalidad de las tareas de notificación en la cola persistente garantizando 0% de pérdida de recordatorios
    Y el sistema aplica reintentos automáticos con retroceso exponencial hasta que el servicio de correo se restablece o deriva el mensaje a la cola de fallidos para alerta operativa tras agotar los reintentos
    Y el sistema registra en la bitácora el resultado del intento de despacho sin abortar el procesamiento de las demás prácticas del lote

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad en el envío de recordatorios y renovación de enlaces criptográficos
    Dado que el sistema genera o reenvía enlaces criptográficos efímeros dentro de los recordatorios dirigidos a supervisores de empresa externos e invalida los tokens anteriores expirados
    Cuando un usuario no autorizado o tercero intenta utilizar un TokenEvaluacion anterior que fue reemplazado o que supera los 15 días calendario de emisión, o intenta disparar recordatorios sin autorización
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema oculta cualquier información del Estudiante, de la Empresa y de la Práctica garantizando 0 datos expuestos
    Y el sistema registra de inmediato el evento en la bitácora de auditoría con IP de origen, fecha y hora en menos de 1 minuto
