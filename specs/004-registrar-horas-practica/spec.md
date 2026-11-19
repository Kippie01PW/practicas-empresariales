# language: es
# Traza: CU-04, EAC-03, RT-01, RN-01, RN-02, RN-03, ADR-005, ADR-006, ADR-010
Característica: Registrar horas de práctica semanales
  Como Estudiante titular de una práctica empresarial
  Quiero registrar periódicamente las horas ejecutadas y las actividades desarrolladas en cada semana
  Para acumular mi avance de horas y someterlas a validación por parte del supervisor de empresa

  Escenario: Registro exitoso de horas semanales en una práctica en ejecución
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al estudiante autenticado con rol de "Estudiante"
    Y la práctica está vinculada a una ReglaPrograma vigente con 320 horas requeridas
    Y no existe un RegistroHoras previo para la semana 1 en dicha práctica
    Cuando el estudiante registra las horas de la semana 1 indicando 40 horas y la descripción de actividades "Configuración de entorno de desarrollo y diseño de componentes"
    Entonces el sistema registra un nuevo RegistroHoras asociado a la Práctica
    Y el sistema asigna al RegistroHoras la semana 1, la cantidad de 40 horas, la descripción "Configuración de entorno de desarrollo y diseño de componentes" y el estado de validación "Pendiente"
    Y el sistema registra la fecha y hora actual del registro
    Y el sistema mantiene la Práctica en estado "EnEjecucion"
    Y el estudiante recibe confirmación de que su reporte de horas de la semana 1 quedó registrado en estado "Pendiente" de validación

  Escenario: Transición automática de Asignada a EnEjecucion con el primer reporte semanal de horas
    Dado que existe una Práctica en estado "Asignada" con docente asesor ya asignado y perteneciente al estudiante autenticado con rol de "Estudiante"
    Y la práctica no cuenta con registros de horas previos
    Cuando el estudiante registra las horas de la semana 1 indicando 40 horas y la descripción de actividades "Inducción institucional e inicio de actividades técnicas"
    Entonces el sistema cambia el estado de la Práctica a "EnEjecucion"
    Y el sistema registra un nuevo RegistroHoras para la semana 1 con 40 horas en estado de validación "Pendiente"
    Y el sistema registra un EventoBitacora con el cambio de estado de la Práctica de "Asignada" a "EnEjecucion", identificador del estudiante, fecha, hora e IP de origen
    Y el estudiante recibe confirmación informando que la práctica inició su fase de ejecución formal y sus horas quedaron registradas

  Escenario: Intento de registro de horas en una práctica en estado no permitido por la máquina de estados
    Dado que existe una Práctica en estado "Solicitada" perteneciente al estudiante autenticado con rol de "Estudiante"
    Cuando el estudiante intenta registrar horas semanales para la semana 1
    Entonces el sistema deniega el registro de horas
    Y el sistema mantiene la Práctica en estado "Solicitada" sin crear ningún RegistroHoras
    Y el sistema informa al estudiante que solo se pueden registrar horas cuando la práctica se encuentra formalizada en estado "Asignada" o "EnEjecucion"

  Escenario: Intento de registro con cantidad de horas no permitida o no positiva
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al estudiante autenticado con rol de "Estudiante"
    Cuando el estudiante intenta registrar horas para la semana 2 indicando 0 horas
    Entonces el sistema deniega el registro de horas
    Y el sistema no crea ningún RegistroHoras asociado a la práctica
    Y el sistema informa al estudiante que la cantidad de horas reportada debe ser un valor positivo mayor a 0

  Escenario: Intento de registro con exceso sobre el límite máximo de horas semanales permitido
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al estudiante autenticado con rol de "Estudiante"
    Cuando el estudiante intenta registrar horas para la semana 2 indicando 70 horas
    Entonces el sistema deniega el registro de horas
    Y el sistema no crea ningún RegistroHoras asociado a la práctica
    Y el sistema informa al estudiante que la cantidad de horas semanales no puede superar el límite reglamentario de 60 horas

  Escenario: Intento de registro con descripción de actividades vacía o en blanco
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al estudiante autenticado con rol de "Estudiante"
    Cuando el estudiante intenta registrar horas para la semana 2 indicando 40 horas y dejando la descripción de actividades en blanco
    Entonces el sistema deniega el registro de horas
    Y el sistema no crea ningún RegistroHoras asociado a la práctica
    Y el sistema informa al estudiante que la descripción de actividades realizadas es obligatoria

  Escenario: Intento de registro con número de semana inválido menor o igual a cero
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al estudiante autenticado con rol de "Estudiante"
    Cuando el estudiante intenta registrar horas indicando la semana 0 con 40 horas y descripción válida
    Entonces el sistema deniega el registro de horas
    Y el sistema no crea ningún RegistroHoras asociado a la práctica
    Y el sistema informa al estudiante que el número de semana debe ser un entero positivo mayor o igual a 1

  Escenario: Intento de registro duplicado para una misma semana ya reportada
    Dado que existe una Práctica en estado "EnEjecucion" perteneciente al estudiante autenticado con rol de "Estudiante"
    Y la práctica ya cuenta con un RegistroHoras registrado para la semana 1 en estado de validación "Pendiente"
    Cuando el estudiante intenta registrar nuevamente horas para la semana 1
    Entonces el sistema deniega el registro duplicado
    Y el sistema mantiene el RegistroHoras original de la semana 1 sin alteraciones
    Y el sistema informa al estudiante que la semana 1 ya cuenta con un reporte de horas registrado

  Escenario: Intento de registro de horas sobre una práctica ajena por estudiante no titular
    Dado que existe una Práctica perteneciente al estudiante con identificador "EST-001"
    Y el usuario está autenticado con rol de "Estudiante" pero con identificador "EST-002"
    Cuando el estudiante con identificador "EST-002" intenta registrar horas en la práctica de "EST-001"
    Entonces el sistema deniega la operación bajo la regla de pertenencia contextual de datos
    Y el sistema no altera ni expone la información de la práctica de "EST-001"
    Y el sistema registra un EventoBitacora por intento de acceso a recurso ajeno con identificador "EST-002", fecha, hora e IP de origen

  Escenario: Intento de registro de horas por un rol de usuario no autorizado
    Dado que existe una Práctica en estado "EnEjecucion"
    Y el usuario está autenticado con rol de "DocenteAsesor" o "Coordinador de prácticas"
    Cuando el usuario intenta registrar horas semanales en la práctica
    Entonces el sistema deniega la operación aplicando la política de autorización deny-by-default
    Y el sistema mantiene la práctica sin alteraciones
    Y el sistema registra un EventoBitacora por intento de operación no autorizada con el identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad ante accesos no válidos
    Dado que en operación normal un usuario sin rol de Estudiante o con credenciales inválidas intenta registrar horas semanales
    Cuando el mecanismo centralizado de autorización intercepta la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema asegura 0 datos expuestos de la práctica, del estudiante y de los registros de horas
    Y el sistema registra de forma inmediata el intento no autorizado en la bitácora de auditoría con IP, fecha y hora en un tiempo menor a 1 minuto

  Escenario: RT-01 - Consistencia y ausencia de pérdidas bajo alta concurrencia transaccional
    Dado que hasta 500 estudiantes concurrentes envían sus registros semanales de horas de manera simultánea
    Cuando el sistema procesa los reportes de horas
    Entonces el sistema garantiza 0% de registros de horas perdidos o sobreescritos
    Y cada reporte válido queda persistido atómicamente vinculado a la práctica de su respectivo estudiante

## Preguntas abiertas

1. ¿El sistema debe realizar la transición automática de la práctica de "Asignada" a "EnEjecucion" al momento en que el estudiante registra su primer reporte semanal de horas, o dicha transición requiere un evento administrativo o fecha formal previa (e.g. fecha de inicio pactada o confirmación del tutor/empresa)?
2. ¿Cuál es el límite formal reglamentario de horas permitidas por semana para un practicante (e.g. 40 horas como jornada estándar, 48 horas como jornada máxima legal o un tope configurable)?
3. ¿Puede el estudiante editar o corregir un RegistroHoras mientras se encuentra en estado "Pendiente" de validación, o toda modificación exige que el supervisor de empresa primero lo rechace en CU-05 con observaciones?
4. Si las horas acumuladas aprobadas sumadas a las nuevas horas reportadas exceden las `horasRequeridas` de la `ReglaPrograma` (ej. 320 horas), ¿el sistema debe permitir registrar horas adicionales para seguimiento, alertar al estudiante o bloquear reportes adicionales?
5. ¿Los reportes de semanas deben ingresarse de manera estrictamente consecutiva (semana 1, luego semana 2, etc.), o se permite registrar semanas en desorden temporal ante contingencias del estudiante?
