# language: es
# Traza: CU-15, OB-02, RT-02, RN-01, RN-02, RN-03, PA-05, R-03, R-04, DT-04, ADR-005, ADR-006, ADR-007, ADR-009, ADR-010
Característica: Migrar prácticas en curso desde Excel
  Como Administrador DBA
  Quiero ejecutar un proceso único de validación e importación desde una plantilla normalizada de Excel (con columnas de identificación del Estudiante, programaAcademico, Empresa, SupervisorEmpresa, DocenteAsesor, horas acumuladas, estado o hitos y fechas)
  Para incorporar las prácticas en curso (y opcionalmente históricas si incluyen todos sus hitos) al sistema aplicando las reglas de dominio vigentes sin corromper la información ni depender de hojas de cálculo manuales

  Escenario: Migración exitosa de prácticas en curso válidas desde la plantilla normalizada de Excel
    Dado que existe una plantilla normalizada de Excel con 3 registros de prácticas en curso que incluyen identificación del Estudiante, programaAcademico "Ingeniería de Sistemas", Empresa, SupervisorEmpresa, DocenteAsesor, horas acumuladas, estado o hitos y fechas consistentes
    Y existe una ReglaPrograma vigente para "Ingeniería de Sistemas" con 320 horasRequeridas
    Y los DocenteAsesor referenciados ("DOC-001" y "DOC-002") tienen menos de 10 prácticas activas asignadas
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración en modo de carga definitiva sobre la plantilla normalizada de Excel
    Entonces el sistema valida cada registro aplicando las reglas de dominio de negocio y crea las 3 entidades Práctica vinculadas a su Estudiante, Empresa, SupervisorEmpresa, DocenteAsesor y la ReglaPrograma vigente de "Ingeniería de Sistemas"
    Y el sistema asigna a cada Práctica el estadoActual correspondiente en la máquina de estados según los hitos completados en la plantilla
    Y el sistema actualiza la cantidad de prácticas activas asignadas a cada DocenteAsesor
    Y el sistema registra un EventoBitacora de auditoría por la ejecución de la migración con el identificador del Administrador DBA, fecha, hora y resumen de registros importados

  Escenario: Ejecución previa en modo de solo validación (dry-run) sin persistir cambios
    Dado que existe una plantilla normalizada de Excel con 4 registros: 2 registros válidos y 2 registros con inconsistencias de formato o datos faltantes
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración en modo de solo validación (dry-run)
    Entonces el sistema procesa y valida los 4 registros de la plantilla contra las reglas de dominio
    Y el sistema genera un reporte detallando los 2 registros válidos y las advertencias e inconsistencias específicas encontradas en los 2 registros inválidos
    Y el sistema mantiene 0 registros nuevos persistidos en el almacenamiento (ninguna Práctica, Estudiante, DocenteAsesor ni SupervisorEmpresa es creada o modificada)

  Escenario: Importación parcial de registros válidos y rechazo únicamente de registros con datos inconsistentes o formatos corruptos
    Dado que existe una plantilla normalizada de Excel con 3 registros: 2 registros válidos y 1 registro al que le falta la identificación del Estudiante o tiene un formato de fecha o número de horas inválido
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración en modo de carga definitiva sobre dicha plantilla
    Entonces el sistema importa los 2 registros válidos y rechaza únicamente el registro inconsistente sin incorporarlo en estado corrupto
    Y el sistema reporta el número de fila y el motivo exacto de la inconsistencia del registro rechazado para su corrección previa en la plantilla

  Escenario: Omisión y reporte de registros duplicados en la plantilla o ya existentes en el sistema
    Dado que en la plantilla normalizada de Excel existen 2 filas para el mismo Estudiante con documento "1053800001" en la misma práctica o ya existe una Práctica registrada para ese Estudiante en el sistema
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración sobre dicha plantilla
    Entonces el sistema detecta la duplicidad, omite el registro duplicado sin sobrescribir los datos existentes e impide crear una segunda Práctica para el mismo Estudiante
    Y el sistema reporta la omisión en el informe de migración sin corromper los datos existentes

  Escenario: Asignación de estado formal a una práctica importada que carece de fecha de inicio formal
    Dado que existe en la plantilla normalizada de Excel un registro de Práctica para el Estudiante con documento "1053800002" que no tiene fechaInicio registrada
    Y el registro indica que la postulación fue aprobada, tiene un DocenteAsesor "DOC-001" asignado y reporta 120 horas acumuladas aprobadas
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración sobre dicha plantilla
    Entonces el sistema asigna a la Práctica el estadoActual "EnEjecucion" de acuerdo con la regla determinista de hitos (sin aprobación -> "Solicitada"; aprobada sin tutor -> "Aprobada"; con tutor sin fechaInicio ni horas -> "Asignada"; con tutor y fechaInicio o horas acumuladas > 0 -> "EnEjecucion"; con evaluación registrada -> "Evaluada"; con acta firmada -> "Completada")
    Y el sistema evita dejar la Práctica en un estado ambiguo o inválido dentro de la máquina de estados

  Escenario: Rechazo de asignación cuando un DocenteAsesor supera el límite de 10 prácticas activas durante la migración
    Dado que el DocenteAsesor "DOC-001" ya tiene 9 prácticas activas asignadas en el sistema
    Y la plantilla normalizada de Excel incluye 2 nuevas prácticas en curso asignadas al mismo DocenteAsesor "DOC-001"
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración sobre dicha plantilla
    Entonces el sistema permite asignar e importar la primera práctica alcanzando el límite máximo de 10 prácticas activas para "DOC-001"
    Y el sistema rechaza la segunda práctica reportando que el DocenteAsesor "DOC-001" superaría el cupo máximo de 10 prácticas activas

  Escenario: Rechazo de migración cuando no existe una ReglaPrograma configurada para el programa académico del registro
    Dado que la plantilla normalizada de Excel contiene un registro de Práctica para el programaAcademico "Ingeniería Mecatrónica"
    Y no existe ninguna ReglaPrograma vigente registrada en el sistema para "Ingeniería Mecatrónica"
    Y el operador está autenticado con el rol de "Administrador DBA"
    Cuando el Administrador DBA ejecuta la migración sobre dicha plantilla
    Entonces el sistema rechaza ese registro reportando la ausencia de una ReglaPrograma vigente para "Ingeniería Mecatrónica"
    Y no crea ninguna Práctica huérfana sin regla normativa asociada

  Escenario: Intento de ejecución del proceso de migración por un rol distinto a Administrador DBA
    Dado que un usuario autenticado con rol de "Estudiante", "DocenteAsesor", "SupervisorEmpresa" o "Coordinador de prácticas", o sin autorización de "Administrador DBA", intenta ejecutar la migración desde Excel
    Cuando el mecanismo centralizado de autorización evalúa la solicitud bajo la política deny-by-default
    Entonces el sistema rechaza el 100% de los intentos no autorizados
    Y el sistema mantiene 0 registros modificados o importados en el almacenamiento
    Y el sistema registra un EventoBitacora por intento de acceso no autorizado con el identificador del usuario, rol, fecha, hora e IP u origen en menos de 1 minuto
