# language: es
# Traza: CU-13, OB-01, OB-02, EAC-01, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010
Característica: Monitorear estado general de prácticas
  Como Coordinador de prácticas
  Quiero consultar en un tablero de control centralizado y estrictamente de solo lectura los indicadores consolidados por estado del ciclo de vida, la ocupación de cupos de los docentes asesores y el listado de prácticas restringido automáticamente a mi programa académico y filtrable por documento del Estudiante, estadoActual o DocenteAsesor
  Para supervisar globalmente la cohorte de mi programa sin depender de hojas de cálculo manuales e identificar el avance de horas, evaluación de desempeño y estado de firmas del acta final

  Escenario: Consulta exitosa del tablero de monitoreo general restringido al programa académico del coordinador autenticado
    Dado que existen en el sistema 5 prácticas pertenecientes al programaAcademico "Ingeniería de Sistemas" distribuidas en distintos estados del ciclo de vida: 1 en "PendienteVerificacion", 1 en "Solicitada", 1 en "Asignada", 1 en "EnEjecucion" vinculada a una ReglaPrograma con 320 horasRequeridas y 160 horasAcumuladasAprobadas, y 1 en "Completada" con ActaFinal firmada por docente y coordinador
    Y existe además 1 práctica perteneciente a otro programaAcademico "Ingeniería Industrial" en estadoActual "EnEjecucion"
    Y existen 2 registros de DocenteAsesor donde "DOC-001" tiene cupoMaximoPracticas de 10 y 4 practicasActivas, y "DOC-002" tiene cupoMaximoPracticas de 10 y 10 practicasActivas
    Y el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas", identificador "COORD-001" y adscrito al programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas consulta el tablero de monitoreo del estado general de prácticas de su programa académico
    Entonces el sistema restringe automáticamente el monitoreo a las prácticas del programaAcademico "Ingeniería de Sistemas" al que pertenece el coordinador autenticado y omite cualquier práctica de "Ingeniería Industrial"
    Y el sistema presenta el resumen cuantitativo de las 5 prácticas del programa agrupadas por cada valor de estadoActual ("PendienteVerificacion": 1, "Solicitada": 1, "Aprobada": 0, "Asignada": 1, "EnEjecucion": 1, "Evaluada": 0, "Completada": 1, "Rechazada": 0)
    Y el sistema presenta el indicador consolidado de carga docente mostrando para "DOC-001" 4 practicasActivas de 10 (6 cupos disponibles) y para "DOC-002" 10 practicasActivas de 10 (0 cupos disponibles)
    Y el sistema presenta el listado de las 5 prácticas de "Ingeniería de Sistemas" indicando para cada una el identificador o documento del Estudiante, el nombreCompleto del DocenteAsesor asignado (si aplica), el estadoActual, las horasAcumuladasAprobadas frente a las horasRequeridas de su ReglaPrograma vinculada, el estado de la EvaluacionDesempeno y el estado de firmas del ActaFinal (aprobadaPorDocente y aprobadaPorCoordinador)
    Y el sistema mantiene todas las entidades sin alteraciones por tratarse de una operación estrictamente de solo lectura
    Y el sistema registra un único EventoBitacora de consulta del monitoreo general con el identificador "COORD-001", rol "Coordinador de prácticas", programaAcademico "Ingeniería de Sistemas", fecha, hora e IP de origen

  Escenario: Filtrado del monitoreo general de prácticas por documento del Estudiante dentro del programa académico del coordinador
    Dado que existen en el sistema 3 prácticas del programaAcademico "Ingeniería de Sistemas": 1 perteneciente al Estudiante con documento "1053800001" en estadoActual "EnEjecucion" con 160 horasAcumuladasAprobadas sobre 320 horasRequeridas, 1 perteneciente al Estudiante con documento "1053800002" en estadoActual "Solicitada" y 1 perteneciente al Estudiante con documento "1053800003" en estadoActual "Evaluada"
    Y el usuario está autenticado con rol de "Coordinador de prácticas", identificador "COORD-001" y programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas consulta el monitoreo filtrando por el documento del Estudiante "1053800001"
    Entonces el sistema presenta únicamente la práctica correspondiente al Estudiante con documento "1053800001" con su estadoActual "EnEjecucion", 160 horasAcumuladasAprobadas sobre 320 horasRequeridas (50% de avance) y su tutor asignado
    Y el sistema omite del listado las prácticas de los demás estudiantes
    Y el sistema registra un único EventoBitacora de consulta filtrada del monitoreo general

  Escenario: Filtrado del monitoreo general de prácticas por estado del ciclo de vida y docente asesor asignado
    Dado que en el programaAcademico "Ingeniería de Sistemas" el DocenteAsesor "DOC-001" tiene asignadas 2 prácticas en estadoActual "EnEjecucion" y 1 en estadoActual "Evaluada", y el DocenteAsesor "DOC-002" tiene asignada 1 práctica en estadoActual "EnEjecucion"
    Y el usuario está autenticado con rol de "Coordinador de prácticas", identificador "COORD-001" y programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas consulta el monitoreo filtrando por estadoActual "EnEjecucion" y DocenteAsesor "DOC-001"
    Entonces el sistema presenta únicamente las 2 prácticas del programa "Ingeniería de Sistemas" que se encuentran en estadoActual "EnEjecucion" y asesoradas por "DOC-001"
    Y el sistema registra un único EventoBitacora de consulta del monitoreo general

  Escenario: Consulta del detalle consolidado de una práctica específica del programa académico del coordinador desde el tablero de monitoreo
    Dado que existe una Práctica en estadoActual "Evaluada" vinculada a una ReglaPrograma del programaAcademico "Ingeniería de Sistemas" con 320 horasRequeridas, perteneciente al Estudiante con documento "1053800001", supervisada por el SupervisorEmpresa "SUP-001" y asesorada por el DocenteAsesor "DOC-001"
    Y la práctica cuenta con 320 horasAcumuladasAprobadas, una EvaluacionDesempeno con calificacionCuantitativa de 4.6 y fechaEvaluacion registrada, y un ActaFinal con numeroActa "ACTA-2026-0015", aprobadaPorDocente igual a verdadero y aprobadaPorCoordinador igual a falso
    Y el usuario está autenticado con rol de "Coordinador de prácticas", identificador "COORD-001" y programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas consulta el detalle de dicha Práctica en el monitoreo general
    Entonces el sistema presenta la trazabilidad completa de la Práctica incluyendo fechaPostulacion, fechaInicio, fechaFin, el documento del Estudiante, el SupervisorEmpresa y el DocenteAsesor, el cumplimiento de 320 sobre 320 horasRequeridas, la calificacionCuantitativa de la EvaluacionDesempeno, el estado de firmas del ActaFinal y el último IntentoValidacion registrado
    Y el sistema registra un único EventoBitacora de consulta de detalle de práctica en monitoreo con el identificador "COORD-001", rol "Coordinador de prácticas", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de consulta en el monitoreo de una práctica perteneciente a un programa académico distinto al del coordinador autenticado
    Dado que existe una Práctica perteneciente al Estudiante con documento "1053999999" vinculada a una ReglaPrograma del programaAcademico "Ingeniería Industrial"
    Y el usuario está autenticado con rol de "Coordinador de prácticas", identificador "COORD-001" pero adscrito al programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas "COORD-001" intenta consultar el detalle de la Práctica de "Ingeniería Industrial" o filtrar prácticas de otro programa académico
    Entonces el sistema deniega el acceso a la práctica ajena al programa académico del coordinador aplicando la regla de pertenencia contextual por programa
    Y el sistema asegura 0 datos expuestos de las prácticas pertenecientes a "Ingeniería Industrial"
    Y el sistema registra un único EventoBitacora por intento de acceso fuera del programa académico asignado con el identificador "COORD-001", rol "Coordinador de prácticas", fecha, hora e IP de origen

  Escenario: Consulta del tablero de monitoreo cuando no existen prácticas registradas para el documento del Estudiante o criterio consultado
    Dado que el usuario está autenticado con rol de "Coordinador de prácticas", identificador "COORD-001" y programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas consulta el monitoreo filtrando por un documento del Estudiante para el cual no existen prácticas coincidentes en su programa académico
    Entonces el sistema presenta los contadores del resumen en 0 para los estados filtrados y retorna una lista vacía de prácticas
    Y el sistema informa que no se encontraron prácticas registradas para los criterios consultados en el programa académico
    Y el sistema registra un único EventoBitacora de consulta del monitoreo general

  Escenario: Intento de acceso al monitoreo del estado general de prácticas por un rol no autorizado o usuario sin sesión válida
    Dado que existen prácticas registradas en el sistema
    Y un usuario sin sesión institucional activa o autenticado con rol de "Estudiante", "DocenteAsesor" o "SupervisorEmpresa" intenta consultar el tablero de monitoreo del estado general de prácticas de CU-13
    Cuando el mecanismo centralizado de autorización evalúa la solicitud bajo la política deny-by-default y la separación estricta de roles
    Entonces el sistema deniega la operación por tratarse de una funcionalidad exclusiva para el rol "Coordinador de prácticas"
    Y el sistema asegura 0 datos expuestos del consolidado de prácticas, de los estudiantes, de las empresas y de la carga de los docentes asesores
    Y el sistema registra de inmediato un único EventoBitacora por intento de acceso no autorizado con el identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante accesos no válidos al monitoreo general de prácticas
    Dado que en operación normal en producción un usuario no autorizado, sin sesión institucional válida, con un rol distinto a "Coordinador de prácticas" o un coordinador de un programa académico distinto intenta acceder a los datos de prácticas en el monitoreo general
    Cuando el componente de autenticación y el mecanismo centralizado de autorización interceptan la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema oculta toda información de los estudiantes, empresas, docentes asesores, evaluaciones y actas logrando 0 datos expuestos
    Y el sistema registra de forma inmediata el evento de rechazo en la bitácora de auditoría con IP de origen, fecha y hora en menos de 1 minuto

  Escenario: EAC-01 - Exactitud e inmutabilidad de las horas requeridas en el monitoreo cuando coexisten prácticas del mismo programa bajo distintas versiones de regla
    Dado que en el programaAcademico "Ingeniería de Sistemas" existe una Práctica activa "PRAC-V1" en estadoActual "EnEjecucion" con 160 horasAcumuladasAprobadas vinculada al iniciar a la versión 1 de la ReglaPrograma con 320 horasRequeridas
    Y posteriormente se publica una versión 2 de la ReglaPrograma para "Ingeniería de Sistemas" con 400 horasRequeridas y se registra una nueva Práctica "PRAC-V2" en estadoActual "EnEjecucion" con 160 horasAcumuladasAprobadas vinculada a la versión 2
    Y el usuario está autenticado con rol de "Coordinador de prácticas", identificador "COORD-001" y programaAcademico "Ingeniería de Sistemas"
    Cuando el Coordinador de prácticas consulta el tablero de monitoreo general de prácticas de "Ingeniería de Sistemas"
    Entonces el sistema calcula y presenta para "PRAC-V1" un progreso del 50% (160 sobre 320 horasRequeridas según la versión 1) y para "PRAC-V2" un progreso del 40% (160 sobre 400 horasRequeridas según la versión 2)
    Y el sistema garantiza un 0% de alteración sobre las condiciones normativas vigentes de las prácticas iniciadas con versiones previas

  Escenario: RT-01 - Consulta del monitoreo general sobre el volumen completo de la cohorte activa de 500 estudiantes y 50 tutores en concurrencia
    Dado que se encuentran operando simultáneamente en el sistema hasta 500 estudiantes con prácticas activas y 50 docentes asesores mientras el Coordinador de prácticas consulta el tablero de monitoreo general de su programa académico
    Cuando el sistema procesa la consulta consolidada de solo lectura sobre la cohorte
    Entonces el sistema calcula y retorna de forma consistente los totales por estadoActual, la disponibilidad de cupo de los 50 docentes asesores y los registros de las prácticas del programa sin bloqueos transaccionales ni pérdida de integridad en la información
