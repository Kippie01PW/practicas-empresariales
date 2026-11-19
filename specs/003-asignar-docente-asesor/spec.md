# language: es
# Traza: CU-03, EAC-03, RT-01, RN-02, RN-03, ADR-005, ADR-006, ADR-010
Característica: Asignar docente asesor o tutor
  Como Coordinador de prácticas
  Quiero asignar un docente asesor a una práctica en estado Aprobada consultando la disponibilidad de cupos de los tutores
  Para vincular al tutor académico responsable del seguimiento del practicante y avanzar la práctica al estado Asignada

  Escenario: Asignación exitosa de docente asesor con cupo disponible
    Dado que existe una Práctica registrada en estado "Aprobada"
    Y existe un DocenteAsesor registrado con cupo máximo de 10 prácticas y 3 prácticas activas asignadas
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas asigna al DocenteAsesor a la Práctica
    Entonces el sistema cambia el estado de la Práctica a "Asignada"
    Y el sistema asocia al DocenteAsesor como tutor responsable de la Práctica
    Y el sistema incrementa a 4 las prácticas activas asignadas a dicho DocenteAsesor
    Y el sistema registra un EventoBitacora con el identificador del coordinador, rol "Coordinador de prácticas", acción de asignación de tutor, identificador de la práctica, identificador del docente asesor, fecha, hora e IP de origen
    Y el sistema emite una notificación al estudiante titular informando la asignación de su docente asesor
    Y el sistema emite una notificación al docente asesor informando la nueva práctica asignada bajo su tutoría

  Escenario: Intento de asignación a docente asesor que alcanzó su cupo máximo de prácticas
    Dado que existe una Práctica registrada en estado "Aprobada"
    Y existe un DocenteAsesor registrado con cupo máximo de 10 prácticas y 10 prácticas activas asignadas
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta asignar al DocenteAsesor a la Práctica
    Entonces el sistema deniega la asignación
    Y el sistema mantiene la Práctica en estado "Aprobada" sin modificar su ciclo de vida
    Y el sistema no incrementa la carga de prácticas activas del DocenteAsesor
    Y el sistema informa al coordinador que el docente asesor ha alcanzado el límite máximo de su cupo disponible

  Escenario: Intento de asignación a docente asesor inexistente o inactivo
    Dado que existe una Práctica registrada en estado "Aprobada"
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta asignar un docente asesor con un identificador inexistente o inactivo en el sistema
    Entonces el sistema deniega la asignación
    Y el sistema mantiene la Práctica en estado "Aprobada" sin alteraciones
    Y el sistema informa al coordinador que el docente asesor especificado no existe o no se encuentra habilitado para asignación

  Escenario: Intento de asignación sobre práctica en estado no permitido por la máquina de estados
    Dado que existe una Práctica registrada en estado "Solicitada"
    Y existe un DocenteAsesor registrado con cupo disponible
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta asignar el docente asesor a la Práctica
    Entonces el sistema deniega la transición de estado
    Y el sistema mantiene la Práctica en estado "Solicitada"
    Y el sistema informa al coordinador que solo se puede asignar un docente asesor a prácticas que se encuentren en estado "Aprobada"

  Escenario: Intento de asignación sobre práctica que ya cuenta con docente asesor asignado
    Dado que existe una Práctica registrada en estado "Asignada" con un DocenteAsesor previamente vinculado
    Y existe un DocenteAsesor con cupo disponible
    Y el usuario está autenticado con rol de "Coordinador de prácticas"
    Cuando el Coordinador de prácticas intenta asignar un nuevo docente asesor a la Práctica
    Entonces el sistema deniega la operación
    Y el sistema mantiene la Práctica en estado "Asignada" con su docente asesor original sin alteraciones
    Y el sistema informa al coordinador que la práctica ya cuenta con un docente asesor asignado en firme

  Escenario: Intento de asignación por rol no autorizado
    Dado que existe una Práctica registrada en estado "Aprobada"
    Y existe un DocenteAsesor con cupo disponible
    Y el usuario está autenticado con rol de "DocenteAsesor" o "Estudiante"
    Cuando el usuario intenta asignar un docente asesor a la Práctica
    Entonces el sistema deniega la operación aplicando la política de autorización deny-by-default
    Y el sistema mantiene la Práctica en estado "Aprobada" sin alteraciones
    Y el sistema registra un EventoBitacora de intento de acceso no autorizado con identificador del usuario, rol, fecha, hora e IP de origen

  Escenario: EAC-03 - Seguridad, confidencialidad y trazabilidad de accesos no autorizados
    Dado que en operación normal un usuario sin rol de Coordinador de prácticas intenta forzar la asignación de un docente asesor
    Cuando el mecanismo centralizado de autorización intercepta la solicitud
    Entonces el sistema rechaza el 100% de los accesos no válidos
    Y el sistema asegura 0 datos expuestos de la práctica, del estudiante y del docente asesor
    Y el sistema registra de forma inmediata el intento no autorizado en la bitácora de auditoría con IP, fecha y hora en un tiempo menor a 1 minuto

## Preguntas abiertas

1. ¿El docente asesor debe pertenecer obligatoriamente al mismo programa académico del estudiante o de la práctica para poder ser asignado (validación de pertenencia por programa en RBAC contextual), o la asignación es interdisciplinaria/libre entre los 50 tutores institucionales?
2. ¿Se contempla la reasignación o sustitución de un docente asesor (por ejemplo, ante incapacidad médica prolongada, retiro o fuerza mayor) una vez que la práctica se encuentra en estado "Asignada" o "EnEjecucion"? De ser así, ¿cuál es el procedimiento formal y la transición de estados correspondiente?
3. ¿El límite de cupo máximo de prácticas activas por docente asesor es un valor estándar fijo institucional (por ejemplo, 10 estudiantes por tutor según RT-01) o debe ser un parámetro configurable individualmente por cada docente asesor en la base de datos?
4. ¿El Coordinador de prácticas realiza la asignación únicamente de forma individual (práctica por práctica), o se requiere un mecanismo de asignación masiva o sugerencia automática basada en menor carga actual de tutorías?
