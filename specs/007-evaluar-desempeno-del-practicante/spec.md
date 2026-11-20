# language: es
# Traza: CU-07, EAC-01, EAC-03, RN-01, RN-02, RN-03, RN-04, ADR-001, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010
Característica: Evaluar desempeño del practicante
  Como Supervisor de empresa externo
  Quiero consultar y diligenciar la evaluación de desempeño del practicante mediante un enlace criptográfico efímero conforme a la rúbrica vigente de su programa
  Para asentar formalmente la calificación cualitativa y cuantitativa del estudiante, transicionar la práctica al estado evaluada y habilitar la generación del acta final

  Escenario: Consulta exitosa de la rúbrica de evaluación mediante TokenEvaluacion válido y vigente
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al Estudiante "EST-001" y vinculada a una ReglaPrograma con criteriosRubrica definidos
    Y la práctica tiene asignado como jefe inmediato externo al SupervisorEmpresa "SUP-001"
    Y existe un TokenEvaluacion emitido hace menos de 15 días calendario, con usado igual a falso, vinculado a dicha Práctica y al SupervisorEmpresa "SUP-001"
    Cuando el SupervisorEmpresa abre el enlace de evaluación presentando el TokenEvaluacion válido
    Entonces el sistema verifica la firma criptográfica del TokenEvaluacion y confirma su vigencia y disponibilidad de uso
    Y el sistema presenta los datos de identificación del Estudiante titular y los criteriosRubrica de la ReglaPrograma vinculada a la Práctica
    Y el sistema mantiene el TokenEvaluacion con usado igual a falso hasta que se envíe la evaluación en firme

  Escenario: Registro exitoso de la evaluación de desempeño aprobatoria y transición de la práctica a estado Evaluada
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma con criteriosRubrica "dominio_tecnico", "habilidades_blandas" y "cumplimiento_objetivos"
    Y la práctica tiene asignado al DocenteAsesor "DOC-001" y al SupervisorEmpresa "SUP-001"
    Y el SupervisorEmpresa "SUP-001" accede mediante un TokenEvaluacion válido, con menos de 15 días de emisión y con usado igual a falso
    Cuando el SupervisorEmpresa envía la evaluación diligenciando en respuestasRubrica una nota entre 0.0 y 5.0 para cada uno de los criteriosRubrica, una calificacionCuantitativa de 4.5 (dentro de la escala 0.0 a 5.0) y las observaciones "Excelente desempeño técnico, cumplimiento de objetivos y trabajo en equipo"
    Entonces el sistema registra una nueva EvaluacionDesempeno asociada a la Práctica con la calificacionCuantitativa de 4.5, las observaciones, las respuestasRubrica y la fechaEvaluacion actual
    Y el sistema marca el TokenEvaluacion con usado igual a verdadero y registra su fecha de uso
    Y el sistema cambia el estadoActual de la Práctica de "EnEjecucion" a "Evaluada"
    Y el sistema registra atómicamente un EventoBitacora con el identificador "SUP-001", rol "SupervisorEmpresa", acción de evaluación de desempeño registrada, identificador de la práctica, fecha, hora e IP de origen
    Y el sistema emite una notificación por correo electrónico al DocenteAsesor "DOC-001" informando que la práctica fue evaluada y se encuentra lista para generar el ActaFinal

  Escenario: Registro exitoso de la evaluación de desempeño en estado EnEjecucion con horas acumuladas parciales (validación de total de horas diferida a CU-09)
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma que exige 320 horasRequeridas
    Y la Práctica cuenta con 200 horasAcumuladasAprobadas y tiene asignado al DocenteAsesor "DOC-001" y al SupervisorEmpresa "SUP-001"
    Y el SupervisorEmpresa "SUP-001" accede mediante un TokenEvaluacion válido, vigente y con usado igual a falso
    Cuando el SupervisorEmpresa envía la EvaluacionDesempeno con respuestasRubrica completas y una calificacionCuantitativa aprobatoria de 4.2 (o sin observaciones, dado que no es reprobatoria)
    Entonces el sistema permite y registra la EvaluacionDesempeno asociada a la Práctica
    Y el sistema marca el TokenEvaluacion con usado igual a verdadero
    Y el sistema cambia el estadoActual de la Práctica de "EnEjecucion" a "Evaluada", difiriendo la validación del cumplimiento total de las 320 horasRequeridas al momento de generar el ActaFinal en CU-09
    Y el sistema registra un EventoBitacora con el registro de la evaluación y cambio de estado

  Escenario: Registro exitoso de evaluación con calificación reprobatoria acompañada de observaciones obligatorias
    Dado que existe una Práctica en estado "EnEjecucion" supervisada por el SupervisorEmpresa "SUP-001"
    Y el SupervisorEmpresa "SUP-001" accede mediante un TokenEvaluacion válido y vigente
    Cuando el SupervisorEmpresa envía la evaluación diligenciando la totalidad de respuestasRubrica, una calificacionCuantitativa reprobatoria de 2.4 (menor a 3.0 en la escala 0.0 a 5.0) y las observaciones "Incumplimiento reiterado de los entregables técnicos asignados"
    Entonces el sistema registra la EvaluacionDesempeno con la calificacionCuantitativa de 2.4 y las observaciones justificativas
    Y el sistema marca el TokenEvaluacion con usado igual a verdadero
    Y el sistema cambia el estadoActual de la Práctica de "EnEjecucion" a "Evaluada"
    Y el sistema registra un EventoBitacora con la evaluación asentada

  Escenario: Rechazo de evaluación reprobatoria por ausencia de observaciones obligatorias
    Dado que existe una Práctica en estado "EnEjecucion" supervisada por el SupervisorEmpresa "SUP-001"
    Y el SupervisorEmpresa "SUP-001" accede mediante un TokenEvaluacion válido y vigente
    Cuando el SupervisorEmpresa intenta enviar una evaluación con una calificacionCuantitativa reprobatoria de 2.5 (menor a 3.0) dejando el campo observaciones vacío o en blanco
    Entonces el sistema rechaza el registro de la EvaluacionDesempeno
    Y el sistema mantiene la Práctica en estado "EnEjecucion" y el TokenEvaluacion con usado igual a falso
    Y el sistema informa al SupervisorEmpresa que las observaciones son obligatorias cuando la calificación cuantitativa es reprobatoria (inferior a 3.0)

  Escenario: Rechazo de evaluación por calificación cuantitativa fuera de la escala permitida de 0.0 a 5.0
    Dado que existe una Práctica en estado "EnEjecucion" supervisada por el SupervisorEmpresa "SUP-001"
    Y el SupervisorEmpresa "SUP-001" accede mediante un TokenEvaluacion válido y vigente
    Cuando el SupervisorEmpresa intenta enviar una evaluación con una calificacionCuantitativa de 5.5 o de -0.5 (fuera del rango permitido de 0.0 a 5.0)
    Entonces el sistema rechaza el registro de la EvaluacionDesempeno
    Y el sistema mantiene la Práctica en estado "EnEjecucion" y el TokenEvaluacion con usado igual a falso
    Y el sistema informa al SupervisorEmpresa que la calificación cuantitativa debe encontrarse en la escala de 0.0 a 5.0

  Escenario: Rechazo de evaluación por respuestas incompletas o inválidas respecto a los criterios de la rúbrica del programa
    Dado que existe una Práctica en estado "EnEjecucion" vinculada a una ReglaPrograma que exige los criteriosRubrica "dominio_tecnico", "habilidades_blandas" y "cumplimiento_objetivos"
    Y el SupervisorEmpresa "SUP-001" accede con un TokenEvaluacion válido y vigente
    Cuando el SupervisorEmpresa intenta enviar la evaluación omitiendo en respuestasRubrica alguno de los criteriosRubrica exigidos o asignando a un criterio un valor fuera de la escala de 0.0 a 5.0
    Entonces el sistema rechaza el registro de la EvaluacionDesempeno
    Y el sistema mantiene la Práctica en estado "EnEjecucion" sin crear la EvaluacionDesempeno
    Y el sistema mantiene el TokenEvaluacion con usado igual a falso para permitir al supervisor corregir y enviar la evaluación dentro de su vigencia
    Y el sistema informa detalladamente cuáles criteriosRubrica faltan o presentan valores fuera del rango permitido

  Escenario: Intento de acceso o evaluación mediante TokenEvaluacion con más de 15 días de emisión
    Dado que existe un TokenEvaluacion cuya fecha de emisión supera los 15 días calendario
    Cuando el SupervisorEmpresa o un tercero intenta consultar el formulario o enviar la evaluación presentando dicho enlace expirado
    Entonces el sistema deniega el acceso a la operación
    Y el sistema oculta cualquier información del Estudiante, de la Empresa y de la Práctica garantizando 0 datos expuestos
    Y el sistema registra de inmediato un EventoBitacora con la acción de acceso rechazado por token expirado, IP de origen, fecha y hora en menos de 1 minuto
    Y el sistema informa al usuario que el enlace de evaluación ha expirado

  Escenario: Intento de acceso o evaluación mediante enlace criptográfico alterado o con firma HMAC inválida
    Dado que un usuario o tercero ajeno intenta acceder a la evaluación modificando los parámetros del enlace o presentando una firma criptográfica HMAC inválida
    Cuando el sistema verifica la autenticidad del TokenEvaluacion presentado
    Entonces el sistema deniega el acceso de forma inmediata
    Y el sistema no expone ningún dato del Estudiante, de la Práctica ni de la ReglaPrograma garantizando 0 datos expuestos
    Y el sistema registra de inmediato un EventoBitacora con la acción de acceso rechazado por token inválido o adulterado, IP de origen, fecha y hora en menos de 1 minuto
    Y el sistema informa que el enlace de evaluación es inválido

  Escenario: Intento de reutilización de un TokenEvaluacion de un solo uso previamente utilizado
    Dado que existe un TokenEvaluacion que ya fue utilizado previamente para registrar una EvaluacionDesempeno y se encuentra marcado con usado igual a verdadero
    Cuando el SupervisorEmpresa u otro usuario intenta abrir nuevamente el enlace o enviar otra evaluación con dicho TokenEvaluacion
    Entonces el sistema deniega el acceso
    Y el sistema mantiene inalterada la EvaluacionDesempeno previamente registrada y la Práctica en estado "Evaluada"
    Y el sistema garantiza 0 datos expuestos del Estudiante y de la Práctica
    Y el sistema registra de inmediato un EventoBitacora por intento de acceso con token ya utilizado con IP de origen, fecha y hora en menos de 1 minuto
    Y el sistema informa al usuario que el enlace de evaluación ya fue utilizado

  Escenario: Intento de evaluar desempeño sobre una práctica en estado distinto a EnEjecucion
    Dado que existe una Práctica cuyo estadoActual es "Solicitada", "Aprobada", "Asignada", "Evaluada", "Completada" o "Rechazada"
    Y se presenta un TokenEvaluacion para intentar asentar una evaluación sobre dicha Práctica
    Cuando se intenta registrar la EvaluacionDesempeno
    Entonces el sistema deniega la operación por violación de la máquina de estados del ciclo de vida de la Práctica
    Y el sistema no crea ninguna EvaluacionDesempeno ni consume el TokenEvaluacion
    Y el sistema informa que solo se puede evaluar el desempeño de prácticas que se encuentren formalmente en estado "EnEjecucion"

  Escenario: Intento de evaluar una práctica que ya cuenta con una EvaluacionDesempeno registrada
    Dado que existe una Práctica que ya tiene asociada una EvaluacionDesempeno en firme
    Cuando se intenta registrar una segunda EvaluacionDesempeno para la misma Práctica
    Entonces el sistema deniega la operación garantizando que cada Práctica reciba como máximo una única EvaluacionDesempeno
    Y el sistema conserva intacta la EvaluacionDesempeno original

  Escenario: Intento de evaluar una práctica ajena al supervisor de empresa vinculado
    Dado que existe una Práctica supervisada por el SupervisorEmpresa "SUP-002" de la empresa "Empresa Beta"
    Y el SupervisorEmpresa "SUP-001" de la empresa "Empresa Alfa" intenta evaluar dicha Práctica utilizando una credencial que no corresponde al supervisor asignado a esa Práctica
    Cuando el mecanismo de autorización verifica la pertenencia contextual entre el SupervisorEmpresa y la Práctica
    Entonces el sistema deniega la operación bajo la regla de pertenencia contextual de datos
    Y el sistema garantiza 0 datos expuestos del Estudiante y de la Práctica de "Empresa Beta"
    Y el sistema registra un EventoBitacora por intento de acceso a recurso ajeno con el identificador "SUP-001", rol "SupervisorEmpresa", identificador de la práctica, fecha, hora e IP de origen

  Escenario: Intento de registrar evaluación de desempeño por un rol interno no autorizado
    Dado que existe una Práctica en estado "EnEjecucion"
    Y un usuario autenticado con rol de "Estudiante", "DocenteAsesor" o "Coordinador de prácticas" intenta enviar o registrar la EvaluacionDesempeno del practicante
    Cuando el mecanismo centralizado de autorización evalúa los permisos del rol para el caso de uso
    Entonces el sistema deniega la operación aplicando la política de autorización deny-by-default y la separación estricta de roles
    Y el sistema mantiene la Práctica en estado "EnEjecucion" sin crear ninguna EvaluacionDesempeno
    Y el sistema registra un EventoBitacora por intento de operación por rol no autorizado con identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante accesos no válidos al formulario de evaluación
    Dado que en operación normal en producción un usuario no autorizado o tercero ajeno a la empresa evaluadora intenta acceder al formulario de evaluación mediante un enlace alterado, reenviado tras su consumo o con más de 15 días de emisión
    Cuando el componente de autenticación tokenizada procesa la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema oculta cualquier información del Estudiante y de la Práctica logrando 0 datos expuestos
    Y el sistema registra de inmediato el evento en la bitácora de auditoría con IP de origen, fecha y hora en menos de 1 minuto

  Escenario: EAC-01 - Inmutabilidad de la rúbrica de evaluación frente a cambios normativos posteriores en la regla de programa
    Dado que existe una Práctica en estado "EnEjecucion" que al momento de su postulación quedó vinculada a la versión 1 de la ReglaPrograma con los criteriosRubrica originales del programa académico
    Y posteriormente el Coordinador de prácticas publica una versión 2 de la ReglaPrograma modificando los criteriosRubrica para nuevas cohortes
    Cuando el SupervisorEmpresa accede con su TokenEvaluacion válido y registra la EvaluacionDesempeno de dicha Práctica
    Entonces el sistema presenta y valida la evaluación estrictamente contra los criteriosRubrica de la versión 1 de la ReglaPrograma vinculada a la Práctica
    Y el sistema garantiza un 0% de alteración en las condiciones y criterios de evaluación de la práctica en curso
