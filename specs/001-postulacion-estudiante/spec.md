# language: es
# Traza: CU-01, EAC-02, RT-01, RT-03, ADR-001, ADR-007, ADR-010
Característica: Postulación de estudiante a la práctica
  Como estudiante activo de un programa académico
  Quiero enviar mi solicitud de inscripción general a la práctica empresarial con verificación de requisitos
  Para iniciar formalmente el trámite de práctica y quedar a la espera de aprobación

  Escenario: Postulación exitosa con verificación inmediata de requisitos
    Dado que el estudiante está autenticado con rol de Estudiante
    Y el estudiante no cuenta con una práctica activa en curso
    Y el estudiante pertenece a un programa académico con una ReglaPrograma activa vigente
    Y el estudiante cumple con los requisitos académicos exigidos en Registro Académico
    Cuando el estudiante envía su formulario de inscripción general de postulación
    Y el servicio de Registro Académico responde en menos de 5 segundos confirmando el cumplimiento
    Entonces el sistema registra una nueva Práctica en estado "Solicitada" vinculada a la ReglaPrograma activa
    Y el sistema registra un IntentoValidacion exitoso asociado a la postulación
    Y el estudiante recibe confirmación en pantalla en un tiempo menor a 3 segundos indicando que su postulación fue registrada en estado "Solicitada"

  Escenario: Rechazo de postulación por incumplimiento de requisitos académicos
    Dado que el estudiante está autenticado con rol de Estudiante
    Y el estudiante no cuenta con una práctica activa en curso
    Y el estudiante pertenece a un programa académico con una ReglaPrograma activa vigente
    Y el estudiante no cumple con los requisitos académicos exigidos en Registro Académico
    Cuando el estudiante envía su formulario de inscripción general de postulación
    Y el servicio de Registro Académico responde en menos de 5 segundos indicando el incumplimiento
    Entonces el sistema registra la Práctica en estado "Rechazada"
    Y el sistema registra un IntentoValidacion con el detalle del incumplimiento
    Y el estudiante recibe una respuesta en pantalla en un tiempo menor a 3 segundos detallando la causal académica del rechazo

  Escenario: Bloqueo de postulación por práctica activa en curso
    Dado que el estudiante está autenticado con rol de Estudiante
    Y el estudiante ya cuenta con una Práctica activa en estado "Aprobada", "Asignada", "EnEjecucion" o "Evaluada"
    Cuando el estudiante intenta enviar un formulario de postulación a la práctica
    Entonces el sistema deniega el registro de la nueva postulación
    Y el sistema no realiza consultas al servicio de Registro Académico
    Y el estudiante recibe una notificación indicando que no puede postularse mientras tenga una práctica activa en curso

  Escenario: Bloqueo de postulación por inexistencia de ReglaPrograma activa
    Dado que el estudiante está autenticado con rol de Estudiante
    Y el estudiante no cuenta con una práctica activa en curso
    Y el programa académico del estudiante no tiene configurada una ReglaPrograma activa vigente
    Cuando el estudiante intenta enviar su formulario de postulación a la práctica
    Entonces el sistema deniega el registro de la postulación
    Y el sistema no realiza consultas al servicio de Registro Académico
    Y el estudiante recibe un mensaje indicando que su programa académico no tiene reglas activas configuradas y debe consultar con la Coordinación de prácticas

  Escenario: EAC-02 - Tolerancia a fallos por indisponibilidad o timeout de Registro Académico
    Dado que hasta 500 estudiantes concurrentes envían solicitudes al inicio del semestre
    Y el estudiante está autenticado con rol de Estudiante y no tiene práctica activa en curso
    Y el estudiante pertenece a un programa académico con ReglaPrograma activa vigente
    Cuando el estudiante envía su formulario de postulación a la práctica
    Y el servicio de Registro Académico no responde tras un tiempo de espera de 5 segundos o responde con error de servicio
    Entonces el sistema asegura un 0% de postulaciones perdidas
    Y el sistema registra la Práctica en estado "PendienteVerificacion"
    Y el sistema registra un IntentoValidacion indicando el fallo de comunicación
    Y el estudiante recibe confirmación en pantalla en un tiempo menor a 3 segundos (en al menos el 95% de los casos) informando que su solicitud fue recibida y quedó en estado "Pendiente de verificación"
    Y el sistema programa la verificación asíncrona de requisitos en segundo plano

  Escenario: EAC-02 - Verificación asíncrona exitosa tras recuperación del servicio de Registro Académico
    Dado que existe una postulación de práctica en estado "PendienteVerificacion"
    Y el servicio de Registro Académico se restablece tras una caída previa
    Cuando el proceso en segundo plano reintenta la verificación de requisitos académicos
    Entonces el sistema finaliza la verificación de requisitos en menos de 30 minutos tras el restablecimiento del servicio
    Y el sistema actualiza el estado de la Práctica a "Solicitada"
    Y el sistema registra un EventoBitacora con el cambio de estado
    Y el estudiante recibe una notificación por correo electrónico confirmando la validación exitosa de su postulación

  Escenario: Agotamiento de reintentos asíncronos ante indisponibilidad persistente de Registro Académico
    Dado que existe una postulación de práctica en estado "PendienteVerificacion"
    Y el servicio de Registro Académico permanece no disponible de manera persistente
    Cuando el proceso en segundo plano ejecuta 5 reintentos consecutivos con espera exponencial sin obtener respuesta
    Entonces el sistema mantiene la Práctica en estado "PendienteVerificacion" garantizando 0% de pérdida de la información
    Y el sistema registra cada IntentoValidacion fallido
    Y el sistema genera una alerta operativa al equipo de soporte técnico para gestión administrativa sin rechazar al estudiante
