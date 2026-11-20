# language: es
# Traza: CU-14, EAC-03, OB-02, PA-03, RN-01, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-008
Característica: Generar consolidados para auditoría
  Como Coordinador de prácticas
  Quiero consultar y exportar en formato PDF consolidados históricos de prácticas empresariales y su ActaFinal
  Para respaldar los procesos de acreditación académica con trazabilidad verificable e inmutable y sin pérdida de información

  Escenario: Generación y exportación exitosa de consolidado histórico en PDF para auditoría y acreditación por el Coordinador de prácticas
    Dado que el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Y existen registros históricos de prácticas en estado "Completada" y "EnEjecucion" para el programa académico "Ingeniería de Sistemas" en el período "2026-1" con sus respectivos Estudiante, DocenteAsesor, SupervisorEmpresa, EvaluacionDesempeno y ActaFinal (con número oficial, fecha de emisión, firmas electrónicas y huella SHA-256)
    Cuando el Coordinador de prácticas solicita generar y exportar el consolidado para auditoría indicando como filtros obligatorios el programa académico "Ingeniería de Sistemas" y el período "2026-1"
    Entonces el sistema recopila exclusivamente el resumen histórico de las prácticas coincidentes y la información de su ActaFinal asociada (número de acta, fecha de emisión, estado de firmas y huella de integridad SHA-256)
    Y el sistema genera el documento exportable en formato PDF sellado con huella SHA-256 junto con los totales resumidos de prácticas consultadas sin alterar ni eliminar ningún registro histórico
    Y el sistema registra atómicamente un EventoBitacora inmutable con actorIdentificador "COORD-001", rolActor "Coordinador de prácticas", accionRealizada de generación de consolidado de auditoría, fechaHora, ipOrigen y huellaDigital

  Escenario: Generación exitosa de consolidado en PDF aplicando filtros opcionales de rango de fechas y estado de la práctica
    Dado que el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Y existen prácticas registradas para el programa académico "Ingeniería de Sistemas" en el período "2026-1" en estados "Completada" y "EnEjecucion" con fechas de postulación dentro y fuera del rango "2026-01-01" a "2026-06-30"
    Cuando el Coordinador de prácticas solicita generar el consolidado indicando programa académico "Ingeniería de Sistemas", período "2026-1" y los filtros opcionales de rango de fechas "2026-01-01" a "2026-06-30" y estado de práctica "Completada"
    Entonces el sistema incluye en el PDF exportado únicamente las prácticas del programa "Ingeniería de Sistemas" y período "2026-1" que además se encuentren en estado "Completada" dentro del rango de fechas indicado, junto con su ActaFinal asociada
    Y el sistema registra un EventoBitacora inmutable de la consulta ejecutada por "COORD-001" con fechaHora, ipOrigen y huellaDigital

  Escenario: Generación exitosa de consolidado filtrado sin registros coincidentes en el programa o período consultado
    Dado que el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Y no existen prácticas empresariales registradas para el programa académico "Ingeniería de Alimentos" en el período "2025-1"
    Cuando el Coordinador de prácticas solicita generar el consolidado para auditoría indicando programa académico "Ingeniería de Alimentos" y período "2025-1"
    Entonces el sistema genera el documento PDF del consolidado con total de registros igual a 0 e informa explícitamente que no se encontraron registros históricos para los criterios indicados
    Y el sistema registra un EventoBitacora inmutable de la consulta ejecutada por "COORD-001" con fechaHora, ipOrigen y huellaDigital

  Escenario: Preservación de la inmutabilidad e integridad de los registros históricos y huellas de ActaFinal en el consolidado
    Dado que existen prácticas con ActaFinal aprobada electrónicamente y sellada con huella SHA-256 para el programa académico "Ingeniería de Sistemas" en el período "2026-1"
    Y el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas genera el consolidado para auditoría sobre dichas prácticas
    Entonces el sistema incluye en el consolidado PDF las huellas de integridad SHA-256, fechas, firmas y responsables exactos de cada práctica y su ActaFinal sin permitir la edición ni el borrado de ningún registro histórico
    Y el conteo y contenido de las prácticas, ActaFinal y EventoBitacora almacenados permanecen 100% íntegros antes y después de la exportación

  Escenario: Rechazo de generación de consolidado por ausencia de filtros obligatorios o rango de fechas inválido
    Dado que el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas solicita generar un consolidado para auditoría omitiendo el programa académico o el período, o indicando una fecha de inicio "2026-12-01" posterior a la fecha de fin "2026-06-01"
    Entonces el sistema rechaza la solicitud informando el filtro obligatorio faltante o que el rango de fechas indicado es inválido
    Y no genera ningún archivo PDF de exportación

  Escenario: EAC-03 - Rechazo de generación o exportación de consolidados de auditoría por rol no autorizado o sin sesión válida
    Dado que un usuario autenticado con rol de "Estudiante", "DocenteAsesor" o "SupervisorEmpresa", o una solicitud sin sesión institucional válida, intenta generar o exportar un consolidado para auditoría
    Cuando el mecanismo centralizado de autorización evalúa los permisos del actor bajo la política deny-by-default y la separación estricta de roles
    Entonces el sistema deniega el 100% de los intentos no autorizados
    Y el sistema asegura 0 datos expuestos de estudiantes, evaluaciones, actas finales o prácticas
    Y el sistema registra de inmediato un EventoBitacora inmutable por intento de acceso no autorizado a consolidados de auditoría con actorIdentificador, rolActor, fechaHora e ipOrigen en menos de 1 minuto
