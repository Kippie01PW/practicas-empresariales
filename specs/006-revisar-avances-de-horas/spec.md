# language: es
# Traza: CU-06, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010
Característica: Revisar avances de horas
  Como Docente asesor o Estudiante titular
  Quiero consultar de forma estrictamente de solo lectura los reportes semanales de horas y el acumulado de horas aprobadas de la práctica
  Para realizar el seguimiento del progreso frente a las horas exigidas por la regla del programa y verificar el cumplimiento del requisito previo a la generación del acta final

  Escenario: Consulta exitosa del avance de horas de una práctica en ejecución por su docente asesor asignado
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma vigente con 320 horas requeridas
    Y la práctica tiene asignado como tutor al DocenteAsesor con identificador "DOC-001"
    Y la práctica cuenta con un RegistroHoras para la semana 1 con 40 horas en estado "Aprobado"
    Y la práctica cuenta con un RegistroHoras para la semana 2 con 40 horas en estado "Aprobado"
    Y la práctica cuenta con un RegistroHoras para la semana 3 con 35 horas en estado "Pendiente"
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor consulta el avance de horas de dicha Práctica
    Entonces el sistema presenta el resumen de progreso de la Práctica con 80 horasAcumuladasAprobadas sobre 320 horasRequeridas, equivalentes a un 25% de avance y 240 horas restantes por aprobar
    Y el sistema presenta el desglose cronológico de los 3 registros de RegistroHoras indicando para cada uno la semana, cantidadHoras, descripcionActividades, estadoValidacion y fechaRegistro
    Y el sistema discrimina que existen 80 horas en estado "Aprobado" y 35 horas en estado "Pendiente" de validación por el SupervisorEmpresa
    Y el sistema mantiene el estado de la Práctica y sus registros de RegistroHoras sin alteraciones por ser una operación estrictamente de solo lectura
    Y el sistema registra un único EventoBitacora de consulta de avance de horas con el identificador "DOC-001", rol "DocenteAsesor", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Consulta exitosa del avance de horas por el estudiante titular de la práctica
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al Estudiante con identificador "EST-001" y vinculada a una ReglaPrograma con 320 horas requeridas
    Y la práctica cuenta con 2 registros de RegistroHoras de 40 horas cada uno en estado "Aprobado", totalizando 80 horasAcumuladasAprobadas
    Y el usuario está autenticado con rol de "Estudiante" e identificador "EST-001"
    Cuando el Estudiante titular consulta el avance de horas de su Práctica
    Entonces el sistema presenta el resumen de progreso con 80 horasAcumuladasAprobadas sobre 320 horasRequeridas, equivalentes a un 25% de avance y 240 horas restantes
    Y el sistema presenta el listado detallado de los 2 registros de RegistroHoras sin alterar la Práctica ni sus reportes
    Y el sistema registra un único EventoBitacora de consulta de avance de horas con el identificador "EST-001", rol "Estudiante", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Consulta de avance de horas cuando el practicante alcanza el total de horas requeridas por la regla del programa
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma con 320 horas requeridas
    Y la práctica tiene asignado como tutor al DocenteAsesor con identificador "DOC-001"
    Y la práctica cuenta con 8 registros semanales de RegistroHoras de 40 horas cada uno en estado "Aprobado", totalizando 320 horasAcumuladasAprobadas
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor consulta el avance de horas de la Práctica
    Entonces el sistema presenta 320 horasAcumuladasAprobadas sobre 320 horasRequeridas, equivalentes a un 100% de avance y 0 horas restantes
    Y el sistema indica que la Práctica cumple la totalidad de horas exigidas por su ReglaPrograma vinculada
    Y el sistema registra un único EventoBitacora de consulta de avance de horas

  Escenario: Consulta de avance de horas de una práctica recién asignada sin reportes semanales registrados
    Dado que existe una Práctica en estado "Asignada" vinculada a una ReglaPrograma con 320 horas requeridas
    Y la práctica tiene asignado como tutor al DocenteAsesor con identificador "DOC-001"
    Y la práctica no cuenta con ningún RegistroHoras registrado
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor consulta el avance de horas de la Práctica
    Entonces el sistema presenta 0 horasAcumuladasAprobadas sobre 320 horasRequeridas, equivalentes a un 0% de avance y 320 horas restantes por aprobar
    Y el sistema presenta la lista de reportes semanales vacía e informa que el Estudiante titular aún no ha registrado reportes de horas
    Y el sistema registra un único EventoBitacora de consulta de avance de horas

  Escenario: Consulta de avance de horas con visualización de reportes rechazados y sus observaciones en modo solo lectura
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma con 320 horas requeridas
    Y la práctica tiene asignado como tutor al DocenteAsesor con identificador "DOC-001"
    Y la práctica cuenta con un RegistroHoras para la semana 1 con 40 horas en estado "Aprobado"
    Y la práctica cuenta con un RegistroHoras para la semana 2 con 40 horas en estado "Rechazado" y la observación "Las actividades descritas el día jueves no corresponden al alcance de la práctica"
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor consulta el avance de horas de la Práctica
    Entonces el sistema presenta 40 horasAcumuladasAprobadas sobre 320 horasRequeridas sin contabilizar en el acumulado aprobado las 40 horas en estado "Rechazado"
    Y el sistema muestra en el detalle de la semana 2 el estado "Rechazado" junto con la observación registrada por el SupervisorEmpresa en modo estrictamente de solo lectura
    Y el sistema registra un único EventoBitacora de consulta de avance de horas

  Escenario: Consulta consolidada del avance de horas de todas las prácticas asignadas al docente asesor
    Dado que el DocenteAsesor con identificador "DOC-001" tiene asignadas 3 prácticas activas bajo su tutoría dentro de su cupo máximo de 10 prácticas
    Y existe una cuarta Práctica activa en el sistema asignada a un DocenteAsesor distinto con identificador "DOC-002"
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor consulta el listado de avances de horas de sus practicantes asignados
    Entonces el sistema presenta únicamente el resumen de las 3 prácticas asignadas a "DOC-001" indicando para cada una el Estudiante titular, estadoActual, horasAcumuladasAprobadas, horasRequeridas y cantidad de reportes en estado "Pendiente"
    Y el sistema omite y no expone ningún dato de la práctica asignada a "DOC-002"
    Y el sistema registra un único EventoBitacora por la consulta consolidada del docente asesor

  Escenario: Intento de consulta de avance de horas de una práctica asignada a otro docente asesor
    Dado que existe una Práctica en estado "EnEjecucion" asignada al DocenteAsesor con identificador "DOC-002"
    Y el usuario está autenticado con rol de "DocenteAsesor" pero con identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" intenta consultar el avance de horas de la Práctica asignada a "DOC-002"
    Entonces el sistema deniega la operación aplicando la regla de pertenencia contextual de datos
    Y el sistema asegura 0 datos expuestos del Estudiante, de la Práctica y de sus registros de RegistroHoras
    Y el sistema registra un único EventoBitacora por intento de acceso a recurso ajeno con el identificador "DOC-001", rol "DocenteAsesor", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de consulta de avance de horas de una práctica ajena por un estudiante no titular
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al Estudiante con identificador "EST-001"
    Y el usuario está autenticado con rol de "Estudiante" pero con identificador "EST-002"
    Cuando el Estudiante "EST-002" intenta consultar el avance de horas de la Práctica de "EST-001"
    Entonces el sistema deniega la operación aplicando la regla de pertenencia contextual de datos
    Y el sistema asegura 0 datos expuestos del Estudiante "EST-001", de la Práctica y de sus registros de RegistroHoras
    Y el sistema registra un único EventoBitacora por intento de acceso a recurso ajeno con el identificador "EST-002", rol "Estudiante", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de consulta de avance de horas sobre una práctica sin docente asesor asignado
    Dado que existe una Práctica en estado "Solicitada" o "Aprobada" que aún no tiene un DocenteAsesor asignado
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" intenta consultar el avance de horas de dicha Práctica
    Entonces el sistema deniega la consulta por no existir asignación de tutoría vigente sobre la Práctica
    Y el sistema asegura 0 datos expuestos de la Práctica y del Estudiante
    Y el sistema registra un único EventoBitacora por intento de acceso no autorizado con identificador "DOC-001", rol "DocenteAsesor", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de consulta de avance de horas sobre una práctica inexistente
    Dado que el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor intenta consultar el avance de horas de una práctica con un identificador inexistente en el sistema
    Entonces el sistema rechaza la consulta
    Y el sistema informa al DocenteAsesor que la práctica consultada no existe

  Escenario: Intento de consulta de avance de horas en CU-06 por Coordinador de prácticas u otro rol no autorizado
    Dado que existe una Práctica en estado "EnEjecucion" asignada al DocenteAsesor "DOC-001"
    Y el usuario está autenticado con rol de "Coordinador de prácticas" (quien utiliza exclusivamente CU-13) o "SupervisorEmpresa"
    Cuando el usuario intenta ejecutar la revisión de avances de horas de CU-06 sobre la Práctica
    Entonces el sistema deniega la operación aplicando la política de autorización deny-by-default
    Y el sistema asegura 0 datos expuestos de la Práctica, del Estudiante y de los registros de RegistroHoras
    Y el sistema registra un único EventoBitacora por intento de acceso por rol no autorizado con el identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante accesos no válidos a avances de horas
    Dado que en operación normal un usuario con rol no autorizado o sin pertenencia contextual sobre la práctica intenta consultar el avance y los reportes semanales de horas de un practicante
    Cuando el mecanismo centralizado de autorización intercepta la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema garantiza 0 datos expuestos del Estudiante, de la Práctica y de sus registros de RegistroHoras
    Y el sistema registra de forma inmediata un único EventoBitacora con el rechazo en la bitácora de auditoría con IP, fecha y hora en un tiempo menor a 1 minuto

  Escenario: EAC-01 - Inmutabilidad del cálculo de avance frente a nuevas versiones de la regla de programa
    Dado que existe una Práctica en estado "EnEjecucion" asignada al DocenteAsesor "DOC-001" y vinculada al iniciar a la versión 1 de la ReglaPrograma con 320 horasRequeridas
    Y la práctica acumula 160 horasAcumuladasAprobadas
    Y posteriormente se publica una versión 2 de la ReglaPrograma para el mismo programa académico exigiendo 400 horasRequeridas
    Cuando el DocenteAsesor "DOC-001" consulta el avance de horas de la Práctica
    Entonces el sistema calcula el porcentaje de avance sobre las 320 horasRequeridas de la versión 1 vinculada a la Práctica reportando un 50% de avance y 160 horas restantes
    Y el sistema garantiza 0% de alteración sobre las condiciones normativas de la práctica activa

  Escenario: RT-01 - Consulta concurrente de avances de horas bajo carga de 50 tutores y 500 estudiantes
    Dado que hasta 50 docentes asesores y 500 estudiantes consultan simultáneamente los avances de horas de sus respectivas prácticas en el sistema
    Cuando el sistema procesa las consultas de solo lectura sobre los acumulados de horas
    Entonces el sistema retorna para cada consulta los valores exactos y consistentes de horasAcumuladasAprobadas y el listado íntegro de RegistroHoras sin bloqueos ni exposición cruzada de datos entre actores
