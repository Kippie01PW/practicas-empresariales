# language: es
# Traza: CU-11, OB-04, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010
Característica: Consultar estado del trámite
  Como Estudiante titular de una práctica empresarial
  Quiero consultar en modo de autoservicio y estrictamente de solo lectura el estado actual de mi trámite más reciente o activo, los actores asignados, el progreso de mis horas, el estado de realización de mi evaluación de desempeño y el estado de firmas de mi acta final
  Para conocer en qué etapa del ciclo de vida se encuentra mi práctica sin depender de consultas presenciales o por correo electrónico

  Escenario: Consulta exitosa del estado del trámite en etapa inicial de postulación solicitada o pendiente de verificación
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001" en estadoActual "Solicitada" (o "PendienteVerificacion") vinculada a una ReglaPrograma vigente con 320 horasRequeridas
    Y la práctica aún no tiene un DocenteAsesor asignado, cuenta con 0 horasAcumuladasAprobadas, no tiene EvaluacionDesempeno ni ActaFinal
    Y el usuario está autenticado mediante el sistema institucional con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el estado del trámite de su Práctica
    Entonces el sistema presenta el estadoActual "Solicitada" (o "PendienteVerificacion") junto con la fechaPostulacion y las 320 horasRequeridas por su ReglaPrograma vinculada
    Y el sistema indica que la práctica se encuentra pendiente de evaluación administrativa por el Coordinador de prácticas (o pendiente de confirmación de requisitos con el sistema académico) y que aún no cuenta con DocenteAsesor asignado
    Y el sistema mantiene la Práctica sin alteraciones por tratarse de una consulta estrictamente de solo lectura
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite con el identificador "EST-001", rol "Estudiante", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Consulta exitosa del estado del trámite de una práctica aprobada o con docente asesor asignado
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001" en estadoActual "Asignada" vinculada a una ReglaPrograma con 320 horasRequeridas
    Y la práctica tiene asignado al DocenteAsesor "DOC-001" y vinculado al SupervisorEmpresa "SUP-001" de la Empresa receptora
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el estado del trámite de su Práctica
    Entonces el sistema presenta el estadoActual "Asignada", los datos de contacto institucionales del DocenteAsesor asignado "DOC-001" y los datos de identificación del SupervisorEmpresa "SUP-001"
    Y el sistema presenta un avance de 0 horasAcumuladasAprobadas sobre 320 horasRequeridas e indica que el siguiente paso del flujo es el registro de reportes semanales de horas
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite con el identificador "EST-001", rol "Estudiante", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Consulta exitosa del estado del trámite de una práctica en ejecución con avance de horas
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001" en estadoActual "EnEjecucion" vinculada a una ReglaPrograma con 320 horasRequeridas
    Y la práctica tiene asignado al DocenteAsesor "DOC-001" y cuenta con 160 horasAcumuladasAprobadas y 40 horas adicionales en un RegistroHoras con estadoValidacion "Pendiente"
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el estado del trámite de su Práctica
    Entonces el sistema presenta el estadoActual "EnEjecucion", la fechaInicio, el DocenteAsesor "DOC-001", 160 horasAcumuladasAprobadas sobre 320 horasRequeridas (50% de avance) y la existencia de reportes de RegistroHoras pendientes de validación por el SupervisorEmpresa
    Y el sistema indica que aún no se ha registrado la EvaluacionDesempeno ni se ha emitido el ActaFinal
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite

  Escenario: Consulta exitosa del estado del trámite de una práctica evaluada ocultando el detalle de calificación hasta que el acta final esté completada
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001" en estadoActual "Evaluada" con 320 horasAcumuladasAprobadas sobre 320 horasRequeridas
    Y la práctica cuenta con una EvaluacionDesempeno registrada con calificacionCuantitativa de 4.5, respuestasRubrica, observaciones y fechaEvaluacion asentada
    Y la práctica cuenta con un ActaFinal generada con aprobadaPorDocente igual a verdadero y aprobadaPorCoordinador igual a falso
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el estado del trámite de su Práctica
    Entonces el sistema presenta el estadoActual "Evaluada" y el cumplimiento de las 320 horasAcumuladasAprobadas
    Y el sistema informa únicamente que la EvaluacionDesempeno ya fue realizada junto con su fechaEvaluacion, sin exponer la calificacionCuantitativa, las respuestasRubrica ni las observaciones del SupervisorEmpresa mientras la Práctica no haya alcanzado el estado "Completada"
    Y el sistema presenta el estado de firmas del ActaFinal indicando que ya cuenta con la aprobación electrónica del DocenteAsesor (aprobadaPorDocente igual a verdadero) y que se encuentra pendiente de la aprobación electrónica del Coordinador de prácticas (aprobadaPorCoordinador igual a falso)
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite

  Escenario: Consulta exitosa del estado del trámite de una práctica completada con acta final en firme y evaluación visible
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001" en estadoActual "Completada"
    Y la práctica cuenta con 320 horasAcumuladasAprobadas, su EvaluacionDesempeno registrada con calificacionCuantitativa de 4.5 y observaciones, y un ActaFinal con numeroActa, fechaEmision, rutaArchivoPdf, hashIntegridadSha256, aprobadaPorDocente igual a verdadero y aprobadaPorCoordinador igual a verdadero
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el estado del trámite de su Práctica
    Entonces el sistema presenta el estadoActual "Completada", la fechaFin, el cumplimiento del 100% de los hitos de la máquina de estados, la calificacionCuantitativa y las observaciones de la EvaluacionDesempeno, y la confirmación de ambas firmas electrónicas sobre el ActaFinal
    Y el sistema habilita al Estudiante la referencia o descarga del documento PDF oficial del ActaFinal junto con su numeroActa, fechaEmision y hashIntegridadSha256
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite

  Escenario: Consulta exitosa del estado del trámite de una práctica rechazada con causal o justificación
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001" en estadoActual "Rechazada"
    Y la práctica tiene registrado el detalle del incumplimiento de requisitos en IntentoValidacion o la justificación administrativa de rechazo asentada por el Coordinador de prácticas
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el estado del trámite de su Práctica
    Entonces el sistema presenta el estadoActual "Rechazada" junto con la causal académica o la justificación administrativa del rechazo registrada en la práctica
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite

  Escenario: Consulta del estado del trámite retornando únicamente la práctica activa o más reciente cuando el estudiante tiene antecedentes previos
    Dado que el Estudiante con identificador "EST-001" tuvo una postulación anterior en estadoActual "Rechazada" y posteriormente registró una nueva Práctica que se encuentra activa en estadoActual "EnEjecucion"
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante "EST-001" consulta el estado de su trámite de práctica sin especificar un identificador de práctica
    Entonces el sistema selecciona y presenta únicamente el estado del trámite de su Práctica activa o más reciente en estado "EnEjecucion"
    Y el sistema registra un único EventoBitacora de consulta de estado del trámite

  Escenario: Consulta del estado del trámite cuando el estudiante aún no registra ninguna postulación de práctica
    Dado que el Estudiante con identificador "EST-003" no tiene ninguna Práctica registrada en el sistema
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-003"
    Cuando el Estudiante "EST-003" consulta el estado de su trámite de práctica
    Entonces el sistema informa al Estudiante que no cuenta con ninguna postulación o práctica registrada en el sistema

  Escenario: Intento de consulta del estado del trámite de una práctica ajena por otro estudiante no titular
    Dado que existe una Práctica perteneciente al Estudiante con identificador "EST-001"
    Y el usuario está autenticado con rol de "Estudiante" pero con identificador "EST-002"
    Cuando el Estudiante "EST-002" intenta consultar el estado del trámite de la Práctica perteneciente a "EST-001"
    Entonces el sistema deniega la operación aplicando la regla de pertenencia contextual de datos
    Y el sistema asegura 0 datos expuestos del Estudiante "EST-001", de su Práctica, de su EvaluacionDesempeno y de su ActaFinal
    Y el sistema registra de inmediato un único EventoBitacora por intento de acceso a recurso ajeno con el identificador "EST-002", rol "Estudiante", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de consulta en CU-11 por un rol distinto a Estudiante o sin sesión válida
    Dado que existe una Práctica perteneciente al Estudiante "EST-001"
    Y un usuario sin sesión activa o autenticado con rol de "DocenteAsesor", "Coordinador de prácticas" o "SupervisorEmpresa" intenta consultar el estado del trámite mediante CU-11 (el cual es de uso exclusivo para el rol "Estudiante")
    Cuando el mecanismo centralizado de autorización evalúa la solicitud bajo la política deny-by-default
    Entonces el sistema deniega la operación por tratarse de un caso de uso exclusivo para el rol "Estudiante"
    Y el sistema asegura 0 datos expuestos de la Práctica y del Estudiante
    Y el sistema registra de inmediato un único EventoBitacora por intento de acceso por rol no autorizado con el identificador del usuario, rol, identificador de la práctica, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante accesos no válidos a la consulta de estado del trámite
    Dado que en operación normal en producción un usuario no autorizado, sin sesión institucional válida o un estudiante ajeno a la práctica intenta consultar el estado del trámite de un practicante
    Cuando el componente de autenticación y el mecanismo centralizado de autorización interceptan la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema oculta cualquier información del Estudiante, de la Empresa, de la EvaluacionDesempeno y del ActaFinal logrando 0 datos expuestos
    Y el sistema registra de forma inmediata el evento de rechazo en la bitácora de auditoría con IP de origen, fecha y hora en menos de 1 minuto

  Escenario: EAC-01 - Inmutabilidad de las condiciones normativas reportadas en el estado del trámite frente a nuevas versiones de la regla de programa
    Dado que existe una Práctica en estadoActual "EnEjecucion" perteneciente al Estudiante "EST-001" vinculada al iniciar a la versión 1 de la ReglaPrograma con 320 horasRequeridas
    Y la práctica acumula 160 horasAcumuladasAprobadas
    Y posteriormente el Coordinador de prácticas publica una versión 2 de la ReglaPrograma para el mismo programa académico exigiendo 400 horasRequeridas
    Cuando el Estudiante "EST-001" consulta el estado del trámite de su Práctica
    Entonces el sistema informa el progreso del trámite tomando como referencia las 320 horasRequeridas de la versión 1 de la ReglaPrograma vinculada a la Práctica (50% de avance)
    Y el sistema garantiza un 0% de alteración en las condiciones normativas vigentes de la práctica activa

  Escenario: RT-01 - Consulta concurrente del estado del trámite en autoservicio bajo carga de 500 estudiantes simultáneos
    Dado que hasta 500 estudiantes autenticados consultan de forma simultánea el estado del trámite de sus respectivas prácticas durante los picos de inicio o cierre de semestre
    Cuando el sistema procesa las solicitudes concurrentes de solo lectura
    Entonces el sistema retorna a cada Estudiante el estado exacto y actualizado de su propia Práctica activa o más reciente según la máquina de estados finitos sin bloqueos ni exposición cruzada de información entre estudiantes
