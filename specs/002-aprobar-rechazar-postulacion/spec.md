# language: es
# Traza: CU-02, EAC-03, RN-02, RN-03, ADR-005, ADR-006, ADR-010
Característica: Aprobar o rechazar postulación
  Como Coordinador de prácticas
  Quiero evaluar administrativamente las postulaciones de práctica en estado Solicitada para aprobarlas o rechazarlas
  Para habilitar la asignación de tutor a las postulaciones procedentes o finalizar tempranamente las no procedentes

  Escenario: Aprobación exitosa de postulación solicitada
    Dado que existe una Práctica registrada en estado "Solicitada"
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas aprueba la postulación
    Entonces el sistema cambia el estado de la Práctica a "Aprobada"
    Y el sistema registra un EventoBitacora con el identificador del coordinador, rol "Coordinador de prácticas", acción de aprobación, identificador de la práctica, fecha, hora e IP de origen
    Y el sistema emite una notificación de aprobación al estudiante titular de la práctica

  Escenario: Rechazo administrativo de postulación solicitada con justificación
    Dado que existe una Práctica registrada en estado "Solicitada"
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas rechaza la postulación indicando como justificación "No cumple con el perfil empresarial del programa"
    Entonces el sistema cambia el estado de la Práctica a "Rechazada"
    Y el sistema asocia la justificación de rechazo a la Práctica
    Y el sistema registra un EventoBitacora con el identificador del coordinador, rol "Coordinador de prácticas", acción de rechazo, justificación, fecha, hora e IP de origen
    Y el sistema emite una notificación al estudiante titular informando el rechazo junto con la justificación registrada

  Escenario: Rechazo fallido por ausencia de justificación obligatoria
    Dado que existe una Práctica registrada en estado "Solicitada"
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta rechazar la postulación sin proporcionar una justificación
    Entonces el sistema deniega el registro del rechazo
    Y el sistema mantiene la Práctica en estado "Solicitada" sin alterar sus datos
    Y el sistema informa al coordinador que la justificación de rechazo es un dato obligatorio

  Escenario: Intento de evaluar postulación en estado no permitido por la máquina de estados
    Dado que existe una Práctica registrada en estado "PendienteVerificacion"
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta aprobar o rechazar la postulación
    Entonces el sistema deniega la transición de estado
    Y el sistema mantiene la Práctica en estado "PendienteVerificacion"
    Y el sistema informa al coordinador que la postulación solo puede ser evaluada cuando se encuentra en estado "Solicitada"

  Escenario: Intento de evaluar postulación con decisión previa ya asentada
    Dado que existe una Práctica registrada en estado "Aprobada"
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta aprobar o rechazar nuevamente la postulación
    Entonces el sistema deniega la operación
    Y el sistema mantiene la Práctica en estado "Aprobada" sin modificar su ciclo de vida
    Y el sistema informa al coordinador que la postulación ya cuenta con una decisión administrativa en firme

  Escenario: Intento de aprobación o rechazo por rol no autorizado
    Dado que existe una Práctica registrada en estado "Solicitada"
    Y el usuario está autenticado con rol de "DocenteAsesor" o "Estudiante"
    Cuando el usuario intenta aprobar o rechazar la postulación
    Entonces el sistema deniega la operación aplicando la política de autorización deny-by-default
    Y el sistema mantiene la Práctica en estado "Solicitada" sin alteraciones
    Y el sistema registra un EventoBitacora de intento de acceso no autorizado con identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad de accesos no autorizados
    Dado que en operación normal un usuario sin rol de Coordinador de prácticas intenta forzar la aprobación o rechazo de una postulación
    Cuando el mecanismo centralizado de autorización intercepta la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema asegura 0 datos expuestos de la postulación y del estudiante
    Y el sistema registra de forma inmediata el intento no autorizado en la bitácora de auditoría con IP, fecha y hora en un tiempo menor a 1 minuto

## Preguntas abiertas

1. ¿El Coordinador de prácticas debe pertenecer al mismo programa académico del estudiante postulante para evaluar la postulación (validación de pertenencia por programa en RBAC contextual), o cualquier usuario con rol de Coordinador puede evaluar postulaciones de todos los programas?
2. Ante un rechazo administrativo en CU-02, ¿el estudiante puede volver a enviar una postulación (CU-01) en el mismo semestre académico o queda inhabilitado temporalmente?
3. ¿Existe un plazo formal límite de días hábiles para que la Coordinación evalúe una postulación en estado "Solicitada" antes de que el sistema genere alertas o recordatorios automáticos?
