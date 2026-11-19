# language: es
# Traza: CU-05, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-002, ADR-004, ADR-005, ADR-006, ADR-010
Característica: Validar horas registradas
  Como Supervisor de empresa
  Quiero revisar y validar los reportes de horas semanales registrados por el practicante bajo mi supervisión
  Para aprobar las horas efectivamente ejecutadas o rechazarlas con observaciones, manteniendo el avance fidedigno de la práctica

  Escenario: Aprobación exitosa de un reporte semanal de horas pendiente
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma de 320 horas requeridas
    Y la práctica cuenta con un acumulado previo de 40 horas aprobadas
    Y existe un RegistroHoras para la semana 2 con 40 horas en estado "Pendiente"
    Y el supervisor de empresa accede mediante un enlace criptográfico válido y vigente vinculado a dicha práctica
    Cuando el supervisor de empresa aprueba el reporte de horas de la semana 2
    Entonces el sistema cambia el estado de validación del RegistroHoras a "Aprobado"
    Y el sistema incrementa el acumulado de horas aprobadas de la Práctica a 80 horas
    Y el sistema registra un EventoBitacora con el identificador del supervisor, rol "SupervisorEmpresa", acción de aprobación de horas, identificador de la práctica, identificador del reporte de horas, fecha, hora e IP de origen
    Y el sistema emite una notificación al estudiante titular informando que su reporte de horas de la semana 2 fue aprobado

  Escenario: Rechazo de un reporte semanal de horas con observaciones descriptivas
    Dado que existe una Práctica en estado "EnEjecucion"
    Y la práctica cuenta con un acumulado previo de 40 horas aprobadas
    Y existe un RegistroHoras para la semana 2 con 40 horas en estado "Pendiente"
    Y el supervisor de empresa accede mediante un enlace criptográfico válido y vigente vinculado a dicha práctica
    Cuando el supervisor de empresa rechaza el reporte de horas indicando como motivo "Las 8 horas del día viernes no corresponden a actividades del proyecto asignado"
    Entonces el sistema cambia el estado de validación del RegistroHoras a "Rechazado"
    Y el sistema asocia las observaciones de rechazo al RegistroHoras
    Y el sistema mantiene el acumulado de horas aprobadas de la Práctica en 40 horas sin incremento
    Y el sistema registra un EventoBitacora con el identificador del supervisor, rol "SupervisorEmpresa", acción de rechazo de horas, motivo registrado, identificador de la práctica, identificador del reporte de horas, fecha, hora e IP de origen
    Y el sistema emite una notificación al estudiante titular informando el rechazo del reporte junto con las observaciones registradas

  Escenario: Rechazo fallido por ausencia de justificación u observaciones obligatorias
    Dado que existe una Práctica en estado "EnEjecucion" con un RegistroHoras en estado "Pendiente"
    Y el supervisor de empresa accede mediante un enlace criptográfico válido y vigente vinculado a dicha práctica
    Cuando el supervisor de empresa intenta rechazar el reporte de horas dejando el motivo u observaciones en blanco
    Entonces el sistema deniega el registro del rechazo
    Y el sistema mantiene el RegistroHoras en estado "Pendiente"
    Y el sistema informa al supervisor que la justificación u observación de rechazo es obligatoria

  Escenario: Intento de validación sobre un reporte de horas que ya fue evaluado previamente
    Dado que existe una Práctica en estado "EnEjecucion" con un RegistroHoras para la semana 1 en estado "Aprobado"
    Y el supervisor de empresa accede mediante un enlace criptográfico válido vinculado a la práctica
    Cuando el supervisor de empresa intenta evaluar nuevamente dicho reporte de horas
    Entonces el sistema deniega la operación
    Y el sistema mantiene el RegistroHoras en estado "Aprobado" sin modificaciones
    Y el sistema informa al supervisor que el reporte de horas de la semana 1 ya cuenta con una validación en firme

  Escenario: Intento de validación sobre una práctica en estado no permitido por la máquina de estados
    Dado que existe una Práctica en estado "Solicitada" o "Rechazada"
    Cuando se intenta validar un reporte de horas sobre dicha práctica
    Entonces el sistema deniega la operación
    Y el sistema informa que solo se pueden validar reportes de horas en prácticas formalizadas en estado "EnEjecucion"

  Escenario: Intento de validación sobre un reporte de horas de una práctica ajena al supervisor
    Dado que existe una Práctica perteneciente a la empresa "Empresa Alfa" con supervisor vinculado "SUP-001"
    Y existe un RegistroHoras perteneciente a una práctica distinta de la empresa "Empresa Beta" con supervisor "SUP-002"
    Y el usuario intenta operar con las credenciales o enlace del supervisor "SUP-001" sobre el reporte de "Empresa Beta"
    Cuando el mecanismo de autorización intercepta la solicitud
    Entonces el sistema deniega la operación bajo la regla de pertenencia contextual de datos
    Y el sistema asegura 0 datos expuestos de la práctica y del estudiante de "Empresa Beta"
    Y el sistema registra un EventoBitacora de intento de acceso a recurso ajeno con identificador "SUP-001", fecha, hora e IP de origen

  Escenario: Intento de acceso mediante enlace criptográfico con más de 15 días de emisión
    Dado que en operación normal un supervisor de empresa intenta acceder al formulario de validación de horas
    Cuando el supervisor presenta un enlace criptográfico cuya fecha de emisión supera los 15 días calendario
    Entonces el sistema deniega el acceso al formulario
    Y el sistema oculta cualquier información del estudiante y de la práctica asegurando 0 datos expuestos
    Y el sistema registra de inmediato un EventoBitacora por intento de acceso con enlace expirado con IP, fecha y hora en menos de 1 minuto
    Y el sistema muestra al supervisor un mensaje informando que el enlace ha expirado

  Escenario: Intento de acceso mediante enlace criptográfico alterado o con firma HMAC inválida
    Dado que un tercero ajeno intenta acceder al formulario de validación de horas modificando los parámetros del enlace o su firma criptográfica
    Cuando el componente de autenticación tokenizada verifica la firma HMAC
    Entonces el sistema deniega el acceso al formulario
    Y el sistema no expone ningún dato del estudiante, de la empresa ni de los registros de horas
    Y el sistema registra de forma inmediata el intento de acceso alterado en la bitácora de auditoría con IP, fecha y hora en un tiempo menor a 1 minuto

  Escenario: Intento de acceso mediante enlace criptográfico de un solo uso previamente utilizado
    Dado que existe un enlace criptográfico de un solo uso que ya fue utilizado para asentar una validación de horas previa
    Cuando el supervisor u otro usuario intenta ingresar nuevamente utilizando dicho enlace
    Entonces el sistema deniega el acceso
    Y el sistema asegura 0 datos expuestos
    Y el sistema informa al usuario que el enlace ya ha sido utilizado

  Escenario: Intento de validación por rol de usuario no autorizado
    Dado que existe una Práctica con un RegistroHoras en estado "Pendiente"
    Y el usuario está autenticado con rol de "Estudiante" o "DocenteAsesor"
    Cuando el usuario intenta validar (aprobar o rechazar) el reporte de horas
    Entonces el sistema deniega la operación aplicando la política de autorización deny-by-default
    Y el sistema mantiene el RegistroHoras en estado "Pendiente" sin alteraciones
    Y el sistema registra un EventoBitacora por intento de operación no autorizada con identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante accesos no válidos
    Dado que en operación normal un usuario no autorizado o tercero ajeno intenta acceder a un formulario de validación mediante un enlace alterado, reenviado o con más de 15 días de emisión
    Cuando el componente de autenticación tokenizada procesa la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema garantiza 0 datos expuestos del estudiante y de la práctica
    Y el sistema registra de forma inmediata el evento en la bitácora de auditoría con IP, fecha y hora en menos de 1 minuto

## Preguntas abiertas

1. ¿El enlace criptográfico efímero (Magic Link) se emite por cada reporte semanal que envía el estudiante o es un enlace de sesión temporal de 15 días que da acceso a una consola donde el supervisor visualiza todos los reportes pendientes de su practicante?
2. Cuando el supervisor rechaza un reporte de horas con observaciones, ¿el estudiante edita y reenvía el mismo reporte (reabriendo su estado a "Pendiente"), o el reporte rechazado queda inmutable y el estudiante debe enviar un nuevo reporte para esa semana?
3. ¿Puede el supervisor de empresa realizar una aprobación parcial de horas (e.g. aprobar 30 de las 40 horas reportadas directamente) o el sistema solo admite la decisión binaria de aprobar la totalidad o rechazar con observaciones?
4. Si la aprobación de un reporte de horas hace que la práctica alcance o supere las horas requeridas por la `ReglaPrograma` (e.g. 320 horas), ¿el sistema emite una notificación especial al docente asesor y/o genera el disparador para la evaluación de desempeño (CU-07)?
5. ¿El docente asesor recibe una notificación por correo cada vez que el supervisor aprueba o rechaza horas semanales, o el docente solo consulta los avances consolidados a demanda (CU-06)?
