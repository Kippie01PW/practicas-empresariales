# language: es
# Traza: CU-09, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, RN-03, ADR-002, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010
Característica: Generar acta final de la práctica
  Como Docente asesor asignado a la práctica empresarial
  Quiero generar el acta final oficial en formato PDF a partir de la plantilla configurada en la regla del programa vinculada y sellarla con una huella criptográfica SHA-256 una vez verificados el estado de evaluación y el cumplimiento de las horas requeridas
  Para formalizar el documento oficial e inmutable de culminación de la práctica empresarial y dejarlo disponible para las firmas electrónicas del docente asesor y del coordinador de prácticas

  Escenario: Generación exitosa del acta final en PDF con sellado criptográfico SHA-256 por el docente asesor asignado
    Dado que existe una Práctica cuyo estadoActual es "Evaluada" perteneciente al Estudiante "EST-001", supervisada por el SupervisorEmpresa "SUP-001" de la Empresa "EMP-001" y asesorada por el DocenteAsesor "DOC-001"
    Y la Práctica se encuentra vinculada a una ReglaPrograma con 320 horasRequeridas y una plantillaActa configurada
    Y la Práctica cuenta con 320 horasAcumuladasAprobadas a partir de sus registros de RegistroHoras en estadoValidacion "Aprobado"
    Y la Práctica cuenta con una EvaluacionDesempeno registrada con calificacionCuantitativa de 4.5, respuestasRubrica completas y observaciones
    Y la Práctica aún no tiene un ActaFinal asociada
    Y el usuario está autenticado mediante sesión institucional con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal de la Práctica
    Entonces el sistema verifica que el DocenteAsesor "DOC-001" es el tutor asignado a la Práctica
    Y el sistema comprueba que la Práctica se encuentra en estadoActual "Evaluada", que las horasAcumuladasAprobadas (320) son mayores o iguales a las horasRequeridas (320) de su ReglaPrograma vinculada y que existe la EvaluacionDesempeno
    Y el sistema renderiza el documento en formato PDF inyectando en la plantillaActa de la ReglaPrograma vinculada los datos del Estudiante, Empresa, SupervisorEmpresa, DocenteAsesor, horasAcumuladasAprobadas y EvaluacionDesempeno
    Y el sistema calcula la huella criptográfica hashIntegridadSha256 de 64 caracteres hexadecimales sobre el contenido binario del PDF generado
    Y el sistema almacena el archivo binario del acta en el repositorio de actas PDF confirmando su rutaArchivoPdf
    Y el sistema registra el ActaFinal asociada a la Práctica asignándole su numeroActa con formato consecutivo anual "ACTA-2026-0001" ("ACTA-<AÑO>-<NNNN>"), fechaEmision actual, rutaArchivoPdf, hashIntegridadSha256, aprobadaPorDocente igual a falso y aprobadaPorCoordinador igual a falso
    Y el sistema mantiene la Práctica en estadoActual "Evaluada" a la espera de las aprobaciones electrónicas de CU-10
    Y el sistema registra atómicamente un EventoBitacora con actorIdentificador "DOC-001", rolActor "DocenteAsesor", accionRealizada de generación de acta final, entidadAfectada correspondiente a la Práctica y al ActaFinal, huellaDigital hashIntegridadSha256, fechaHora e ipOrigen
    Y el sistema presenta al DocenteAsesor los datos del ActaFinal generada junto con su hashIntegridadSha256 y la previsualización del PDF lista para aprobación electrónica

  Escenario: Rechazo de generación del acta final cuando la práctica no se encuentra en estado Evaluada
    Dado que existe una Práctica asesorada por el DocenteAsesor "DOC-001" cuyo estadoActual es "PendienteVerificacion", "Solicitada", "Aprobada", "Asignada", "EnEjecucion", "Completada" o "Rechazada"
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal de dicha Práctica
    Entonces el sistema rechaza la operación por bloqueo de la máquina de estados del ciclo de vida de la Práctica
    Y el sistema no renderiza ningún archivo PDF ni registra ningún ActaFinal
    Y el sistema informa al DocenteAsesor que el acta final solo puede generarse cuando la Práctica se encuentra formalmente en estado "Evaluada"

  Escenario: Rechazo de generación del acta final cuando las horas acumuladas aprobadas son inferiores a las horas requeridas por la regla del programa
    Dado que existe una Práctica en estadoActual "Evaluada" asesorada por el DocenteAsesor "DOC-001" y vinculada a una ReglaPrograma que exige 320 horasRequeridas
    Y la Práctica cuenta con una EvaluacionDesempeno registrada pero solo acumula 280 horasAcumuladasAprobadas (menos de las 320 horasRequeridas)
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal de la Práctica
    Entonces el sistema rechaza la generación del ActaFinal por incumplimiento del requisito de horas mínimas exigidas
    Y el sistema no almacena ningún archivo PDF ni crea registro de ActaFinal
    Y el sistema mantiene la Práctica en estadoActual "Evaluada"
    Y el sistema informa al DocenteAsesor que el estudiante cuenta con 280 horasAcumuladasAprobadas de las 320 horasRequeridas y que faltan 40 horas aprobadas para poder emitir el acta final

  Escenario: Rechazo de generación del acta final cuando la práctica carece de evaluación de desempeño registrada
    Dado que existe una Práctica asesorada por el DocenteAsesor "DOC-001" vinculada a una ReglaPrograma con 320 horasRequeridas y que cuenta con 320 horasAcumuladasAprobadas
    Y la Práctica no tiene una EvaluacionDesempeno registrada por el SupervisorEmpresa
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal de la Práctica
    Entonces el sistema rechaza la operación indicando que falta la Evaluación de Desempeño del Supervisor de Empresa
    Y el sistema no genera ningún archivo PDF ni crea registro de ActaFinal

  Escenario: Intento de generar nuevamente el acta final cuando la práctica ya cuenta con un ActaFinal emitida
    Dado que existe una Práctica en estadoActual "Evaluada" asesorada por el DocenteAsesor "DOC-001" que ya tiene asociada un ActaFinal previamente generada con su numeroActa, rutaArchivoPdf y hashIntegridadSha256
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal para la misma Práctica
    Entonces el sistema rechaza la creación de un ActaFinal duplicada garantizando que cada Práctica tenga una única ActaFinal (relación 0..1)
    Y el sistema conserva inalterados el archivo PDF, el hashIntegridadSha256 y el registro de ActaFinal original
    Y el sistema informa al DocenteAsesor que la Práctica ya cuenta con un ActaFinal generada

  Escenario: Generación exitosa de acta final para una práctica con calificación cuantitativa reprobatoria en la evaluación de desempeño
    Dado que existe una Práctica en estadoActual "Evaluada" asesorada por el DocenteAsesor "DOC-001", vinculada a una ReglaPrograma con 320 horasRequeridas y con 320 horasAcumuladasAprobadas
    Y la Práctica tiene registrada una EvaluacionDesempeno con calificacionCuantitativa reprobatoria de 2.4 (menor a 3.0) y sus observaciones justificativas "Incumplimiento reiterado de los entregables técnicos asignados"
    Y la Práctica aún no tiene un ActaFinal asociada
    Y el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal de la Práctica
    Entonces el sistema permite la generación y renderiza el documento en formato PDF dejando constancia de la calificacionCuantitativa reprobatoria de 2.4 y las observaciones justificativas en la plantillaActa de la ReglaPrograma vinculada
    Y el sistema calcula el hashIntegridadSha256 del PDF, almacena el archivo binario en el repositorio de actas PDF y registra la única ActaFinal de la Práctica con aprobadaPorDocente igual a falso y aprobadaPorCoordinador igual a falso
    Y el sistema registra atómicamente el EventoBitacora con el hashIntegridadSha256 del ActaFinal emitida

  Escenario: Intento de generar el acta final de una práctica asignada a otro docente asesor
    Dado que existe una Práctica en estadoActual "Evaluada" con 320 horasAcumuladasAprobadas y EvaluacionDesempeno registrada, cuyo tutor asignado es el DocenteAsesor "DOC-002"
    Y el usuario está autenticado con rol de "DocenteAsesor" pero con identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" intenta generar el ActaFinal de la Práctica asignada a "DOC-002"
    Entonces el sistema deniega la operación aplicando la regla de pertenencia contextual de datos
    Y el sistema garantiza 0 datos expuestos del Estudiante, de la EvaluacionDesempeno y de la Práctica
    Y el sistema no genera ningún archivo PDF ni crea registro de ActaFinal
    Y el sistema registra de inmediato un EventoBitacora por intento de acceso a recurso ajeno con actorIdentificador "DOC-001", rolActor "DocenteAsesor", entidadAfectada correspondiente a la Práctica, fechaHora e ipOrigen en menos de 1 minuto

  Escenario: Intento de generar el acta final por un rol no autorizado
    Dado que existe una Práctica en estadoActual "Evaluada" con 320 horasAcumuladasAprobadas y EvaluacionDesempeno registrada, asesorada por el DocenteAsesor "DOC-001"
    Y un usuario autenticado con rol de "Estudiante", "SupervisorEmpresa" o "Coordinador de prácticas" intenta ejecutar la generación del ActaFinal (dado que exclusivamente el DocenteAsesor asignado está autorizado para invocar la generación del acta en CU-09)
    Cuando el mecanismo centralizado de autorización evalúa los permisos del rol para la operación de generar acta bajo la política deny-by-default
    Entonces el sistema deniega la operación por separación estricta de roles
    Y el sistema garantiza 0 datos expuestos y no genera ningún archivo PDF ni registro de ActaFinal
    Y el sistema registra de inmediato un EventoBitacora por intento de operación por rol no autorizado con actorIdentificador, rolActor, fechaHora e ipOrigen en menos de 1 minuto

  Escenario: Intento de generar el acta final sobre una práctica inexistente
    Dado que el usuario está autenticado con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal para un identificador de práctica que no existe en el sistema
    Entonces el sistema rechaza la solicitud informando que la práctica especificada no existe
    Y el sistema no genera ningún archivo PDF ni registro de ActaFinal

  Escenario: Preservación de consistencia atómica si falla el almacenamiento del PDF o el registro del acta
    Dado que existe una Práctica en estadoActual "Evaluada" con 320 horasAcumuladasAprobadas sobre 320 horasRequeridas y EvaluacionDesempeno registrada, asesorada por el DocenteAsesor "DOC-001"
    Y el DocenteAsesor "DOC-001" solicita generar el ActaFinal de la Práctica
    Cuando ocurre un error al escribir el archivo binario en el repositorio de actas PDF o al persistir el registro de ActaFinal
    Entonces el sistema revierte la operación evitando dejar un registro de ActaFinal sin su archivo PDF correspondiente o un archivo PDF huérfano sin su huella hashIntegridadSha256 registrada
    Y el sistema mantiene la Práctica en estadoActual "Evaluada" sin ActaFinal asociada e informa el error al DocenteAsesor

  Escenario: EAC-01 - Uso de la plantilla versión original vinculada a la práctica e inmutabilidad frente a cambios normativos o de formato posteriores
    Dado que existe una Práctica en estadoActual "Evaluada" asesorada por el DocenteAsesor "DOC-001" que al momento de su postulación quedó vinculada a la versión 1 de la ReglaPrograma con 320 horasRequeridas y la plantillaActa "plantilla_acta_v1.html"
    Y posteriormente el Coordinador de prácticas actualiza y publica una versión 2 de la ReglaPrograma para el mismo programa académico cambiando las horasRequeridas a 400 y el formato visual a "plantilla_acta_v2.html" (modificación completada en menos de 16 horas-hombre afectando como máximo 2 componentes)
    Cuando el DocenteAsesor "DOC-001" solicita generar el ActaFinal de dicha Práctica que cuenta con 320 horasAcumuladasAprobadas
    Entonces el sistema valida el requisito de horas y renderiza el PDF utilizando estrictamente las 320 horasRequeridas y la plantillaActa "plantilla_acta_v1.html" de la versión 1 de la ReglaPrograma vinculada a la Práctica
    Y el sistema garantiza un 0% de alteración en las condiciones normativas de la práctica en curso y un 0% de alteración en las actas emitidas previamente

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante intentos no autorizados de generación de acta final
    Dado que en operación normal en producción un usuario sin rol de DocenteAsesor o un DocenteAsesor no asignado a la Práctica intenta generar o acceder al ActaFinal de un practicante
    Cuando el mecanismo centralizado de autorización procesa la solicitud bajo la política deny-by-default
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema oculta cualquier información del Estudiante, de la EvaluacionDesempeno y de la Práctica logrando 0 datos expuestos
    Y el sistema registra de inmediato el evento de rechazo en la bitácora de auditoría con ipOrigen, fechaHora, actorIdentificador y rolActor en menos de 1 minuto
