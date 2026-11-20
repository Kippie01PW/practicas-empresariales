# language: es
# Traza: CU-10, EAC-03, PA-03, RN-01, RN-02, RN-03, ADR-001, ADR-002, ADR-004, ADR-005, ADR-006, ADR-008, ADR-010
Característica: Aprobar el acta electrónicamente
  Como Docente asesor y Coordinador de prácticas
  Quiero aprobar y firmar electrónicamente en orden secuencial el acta final generada de la práctica verificando su integridad criptográfica
  Para formalizar el aval institucional con trazabilidad y no repudio, culminar la práctica en estado Completada y notificar el documento oficial al estudiante

  Escenario: Aprobación electrónica exitosa del acta final por el Docente asesor asignado (Paso 1)
    Dado que existe una Práctica en estado "Evaluada" perteneciente al Estudiante "EST-001" y asignada al DocenteAsesor con identificador "DOC-001"
    Y la práctica cuenta con un ActaFinal generada con aprobadaPorDocente igual a falso, aprobadaPorCoordinador igual a falso y un hashIntegridadSha256 registrado
    Y el archivo PDF del ActaFinal almacenado conserva una huella criptográfica SHA-256 idéntica al hashIntegridadSha256 registrado
    Y el usuario está autenticado mediante el sistema institucional con rol de "DocenteAsesor" e identificador "DOC-001"
    Cuando el DocenteAsesor aprueba electrónicamente el ActaFinal de la Práctica
    Entonces el sistema recalcula la huella SHA-256 del documento PDF y comprueba que coincide exactamente con el hashIntegridadSha256 del ActaFinal
    Y el sistema actualiza el ActaFinal marcando aprobadaPorDocente igual a verdadero y manteniendo aprobadaPorCoordinador igual a falso
    Y el sistema mantiene la Práctica en estado "Evaluada" a la espera de la aprobación final del Coordinador de prácticas
    Y el sistema registra atómicamente un EventoBitacora inmutable con el identificador "DOC-001", rol "DocenteAsesor", acción de aprobación electrónica de acta por docente, identificador de la práctica, fecha, hora, IP de origen y huellaDigital

  Escenario: Aprobación electrónica final exitosa por el Coordinador de prácticas y transición a estado Completada (Paso 2)
    Dado que existe una Práctica en estado "Evaluada" perteneciente al Estudiante "EST-001" y asignada al DocenteAsesor "DOC-001"
    Y la práctica cuenta con un ActaFinal previamente firmada por el tutor con aprobadaPorDocente igual a verdadero, aprobadaPorCoordinador igual a falso y un hashIntegridadSha256 válido
    Y el archivo PDF del ActaFinal almacenado conserva una huella criptográfica SHA-256 idéntica al hashIntegridadSha256 registrado
    Y el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas aprueba electrónicamente el ActaFinal de la Práctica
    Entonces el sistema verifica la integridad SHA-256 del documento PDF frente al hashIntegridadSha256 del ActaFinal
    Y el sistema actualiza el ActaFinal marcando aprobadaPorCoordinador igual a verdadero quedando el acta oficialmente en firme
    Y el sistema cambia el estadoActual de la Práctica de "Evaluada" a "Completada"
    Y el sistema decrementa automáticamente en 1 el contador practicasActivas del DocenteAsesor "DOC-001" liberando su cupo disponible
    Y el sistema registra atómicamente un EventoBitacora inmutable con el identificador "COORD-001", rol "Coordinador de prácticas", acción de aprobación electrónica final de acta y cierre de práctica, identificador de la práctica, fecha, hora, IP de origen y huellaDigital
    Y el sistema emite de forma asíncrona una notificación por correo electrónico al Estudiante "EST-001" confirmando la culminación de su práctica y adjuntando o enlazando el ActaFinal en PDF

  Escenario: Intento de aprobación por el Coordinador de prácticas sin la firma previa del Docente asesor
    Dado que existe una Práctica en estado "Evaluada" con un ActaFinal cuyo atributo aprobadaPorDocente es igual a falso y aprobadaPorCoordinador es igual a falso
    Y el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas intenta aprobar electrónicamente el ActaFinal antes que el DocenteAsesor
    Entonces el sistema deniega la aprobación por incumplimiento de la secuencia obligatoria de firmas
    Y el sistema mantiene el ActaFinal con aprobadaPorCoordinador igual a falso y la Práctica en estado "Evaluada"
    Y el sistema informa al Coordinador de prácticas que el DocenteAsesor asignado aún no ha firmado electrónicamente el acta

  Escenario: Rechazo de aprobación electrónica por discrepancia en la huella de integridad SHA-256 o alteración del archivo PDF
    Dado que existe una Práctica en estado "Evaluada" con un ActaFinal generada y un hashIntegridadSha256 registrado
    Y el archivo PDF del ActaFinal en el almacenamiento fue alterado, corrompido o no está disponible, de modo que su huella SHA-256 recalculada no coincide con el hashIntegridadSha256 registrado
    Y el usuario está autenticado como el DocenteAsesor asignado "DOC-001" o como "Coordinador de prácticas"
    Cuando el usuario intenta aprobar electrónicamente el ActaFinal
    Entonces el sistema detecta la violación de integridad criptográfica al comparar el hash SHA-256 recalculado contra el hashIntegridadSha256 registrado
    Y el sistema bloquea la aprobación electrónica sin asentar la firma ni transicionar la Práctica a "Completada"
    Y el sistema registra de inmediato un EventoBitacora de alerta de seguridad por fallo de integridad del ActaFinal con identificador del actor, rol, identificador de la práctica, fecha, hora e IP de origen
    Y el sistema informa que el documento del acta presenta una inconsistencia de integridad y no puede ser firmado

  Escenario: Intento de aprobación electrónica sobre una práctica que no cuenta con ActaFinal generada o no está en estado Evaluada
    Dado que existe una Práctica cuyo estadoActual es "Solicitada", "Aprobada", "Asignada" o "EnEjecucion", o que aún no tiene un ActaFinal generada
    Y el usuario está autenticado con rol de "DocenteAsesor" o "Coordinador de prácticas"
    Cuando el usuario intenta registrar una aprobación electrónica de acta sobre dicha Práctica
    Entonces el sistema deniega la operación por violación de la máquina de estados del ciclo de vida de la Práctica
    Y el sistema mantiene el estadoActual de la Práctica sin alteraciones
    Y el sistema informa que solo se puede aprobar electrónicamente un ActaFinal previamente generada sobre una práctica en estado "Evaluada"

  Escenario: Intento de aprobación electrónica duplicada por el Docente asesor o por el Coordinador de prácticas
    Dado que existe una Práctica con un ActaFinal donde aprobadaPorDocente ya es igual a verdadero (o donde la Práctica ya se encuentra en estado "Completada" con ambas firmas asentadas)
    Y el usuario autenticado con rol de "DocenteAsesor" (o "Coordinador de prácticas" cuando aprobadaPorCoordinador ya es verdadero) intenta aprobar nuevamente la misma ActaFinal
    Cuando el sistema procesa la solicitud de aprobación
    Entonces el sistema deniega la operación por tratarse de una firma electrónica ya asentada en firme
    Y el sistema conserva inalterados los datos del ActaFinal, de la Práctica y de los registros previos de EventoBitacora
    Y el sistema informa al usuario que su aprobación electrónica ya fue registrada previamente sobre el acta

  Escenario: Intento de aprobación electrónica de un acta por un Docente asesor no asignado a la práctica
    Dado que existe una Práctica en estado "Evaluada" con un ActaFinal pendiente de firma y asignada al DocenteAsesor con identificador "DOC-002"
    Y el usuario está autenticado con rol de "DocenteAsesor" pero con identificador "DOC-001"
    Cuando el DocenteAsesor "DOC-001" intenta aprobar electrónicamente el ActaFinal de la Práctica asignada a "DOC-002"
    Entonces el sistema deniega la operación aplicando la regla de pertenencia contextual de datos
    Y el sistema mantiene el ActaFinal con aprobadaPorDocente igual a falso y asegura 0 datos expuestos del contenido del acta y del Estudiante
    Y el sistema registra de inmediato un EventoBitacora por intento de acceso y firma sobre recurso ajeno con el identificador "DOC-001", rol "DocenteAsesor", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de aprobación electrónica de un acta por un rol no autorizado
    Dado que existe una Práctica en estado "Evaluada" con un ActaFinal generada
    Y un usuario autenticado con rol de "Estudiante" o "SupervisorEmpresa" intenta aprobar electrónicamente el ActaFinal
    Cuando el mecanismo centralizado de autorización evalúa los permisos del rol bajo la política deny-by-default y la separación estricta de roles
    Entonces el sistema deniega la operación
    Y el sistema mantiene el ActaFinal y la Práctica sin alteraciones asegurando 0 datos expuestos
    Y el sistema registra de inmediato un EventoBitacora por intento de operación por rol no autorizado con el identificador del usuario, rol, identificador de la práctica, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad, no repudio y trazabilidad ante accesos o intentos de firma no válidos
    Dado que en operación normal en producción un usuario sin sesión institucional válida, con un rol no autorizado o un docente ajeno a la práctica intenta acceder o aprobar electrónicamente un ActaFinal
    Cuando el componente de autenticación y el mecanismo centralizado de autorización procesan la solicitud
    Entonces el sistema rechaza el 100% de los accesos o intentos de firma no válidos
    Y el sistema oculta cualquier información del ActaFinal, del Estudiante y de la Práctica logrando 0 datos expuestos
    Y el sistema registra de forma inmediata e inmutable el evento de rechazo en la bitácora de auditoría con IP de origen, fecha y hora en menos de 1 minuto

