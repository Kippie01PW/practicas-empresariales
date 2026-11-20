# language: es
# Traza: CU-12, EAC-01, EAC-03, OB-05, PA-01, RN-01, RN-02, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008
Característica: Configurar reglas y plantillas por programa
  Como Coordinador de prácticas
  Quiero crear en borrador, editar mientras permanezca en borrador, simular con vista previa y activar oficialmente nuevas versiones de reglas normativas y plantillas de acta final por programa académico
  Para ajustar dinámicamente las horas requeridas, los criterios de rúbrica y el formato del acta final sin modificar el código fuente y garantizando un 0% de alteración en prácticas en curso y en actas emitidas previamente

  Escenario: Creación exitosa de una nueva versión de regla de programa en estado Borrador por el Coordinador de prácticas
    Dado que el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Y existe para el programa académico "Ingeniería de Sistemas" una ReglaPrograma con version "2026-1", estadoVigencia "Activa", 320 horasRequeridas, criteriosRubrica definidos y plantillaActa "plantilla_acta_sistemas_v1.html"
    Cuando el Coordinador de prácticas registra una nueva configuración para el programa académico "Ingeniería de Sistemas" con version "2026-2", 360 horasRequeridas (entero positivo mayor a 0), criteriosRubrica válidos (como diccionario de criterios con pesos positivos o lista simple no vacía de nombres de criterios sin peso) y plantillaActa "plantilla_acta_sistemas_v2.html"
    Entonces el sistema crea y persiste una nueva ReglaPrograma para "Ingeniería de Sistemas" con version "2026-2" y estadoVigencia igual a "Borrador"
    Y el sistema mantiene la ReglaPrograma con version "2026-1" en estadoVigencia "Activa" para las postulaciones vigentes hasta que el nuevo borrador sea activado oficialmente
    Y el sistema registra atómicamente un EventoBitacora inmutable con actorIdentificador "COORD-001", rolActor "Coordinador de prácticas", accionRealizada de creación de borrador de ReglaPrograma, entidadAfectada correspondiente a la nueva ReglaPrograma, fechaHora, ipOrigen y huellaDigital

  Escenario: Edición exitosa de los atributos de una regla de programa mientras permanece en estado Borrador
    Dado que existe una ReglaPrograma en estadoVigencia "Borrador" para el programa académico "Ingeniería de Sistemas" con version "2026-2", 360 horasRequeridas, criteriosRubrica iniciales y plantillaActa "plantilla_acta_sistemas_v2.html"
    Y el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas edita la ReglaPrograma en estado "Borrador" actualizando las horasRequeridas a 380, los criteriosRubrica a la lista simple de criterios ["dominio_tecnico", "trabajo_en_equipo", "cumplimiento_objetivos", "innovacion"] y la plantillaActa a "plantilla_acta_sistemas_v2_rev1.html"
    Entonces el sistema actualiza los atributos horasRequeridas, criteriosRubrica y plantillaActa de la ReglaPrograma con version "2026-2" manteniéndola en estadoVigencia "Borrador"
    Y el sistema conserva inalterada la ReglaPrograma con version "2026-1" en estadoVigencia "Activa" y las prácticas vinculadas a ella
    Y el sistema registra atómicamente un EventoBitacora inmutable con actorIdentificador "COORD-001", rolActor "Coordinador de prácticas", accionRealizada de actualización de borrador de ReglaPrograma, entidadAfectada, fechaHora, ipOrigen y huellaDigital

  Escenario: Simulación y previsualización exitosa del acta final y rúbrica sobre una regla de programa en estado Borrador antes de activarla
    Dado que existe una ReglaPrograma en estadoVigencia "Borrador" para el programa académico "Ingeniería de Sistemas" con version "2026-2", 380 horasRequeridas, criteriosRubrica configurados y plantillaActa "plantilla_acta_sistemas_v2_rev1.html"
    Y el usuario está autenticado mediante el sistema institucional con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas solicita simular y previsualizar el ActaFinal con datos de prueba para dicha ReglaPrograma en estado "Borrador"
    Entonces el sistema genera en memoria una vista previa del documento PDF del ActaFinal aplicando la plantillaActa "plantilla_acta_sistemas_v2_rev1.html", las 380 horasRequeridas y los criteriosRubrica de la versión "2026-2"
    Y el sistema presenta al Coordinador de prácticas la previsualización del acta y de la rúbrica sin almacenar un ActaFinal oficial ni alterar ninguna Práctica existente
    Y el sistema mantiene la ReglaPrograma con version "2026-2" en estadoVigencia "Borrador"

  Escenario: Activación oficial exitosa de una nueva versión de regla de programa en estado Borrador y transición de la versión anterior
    Dado que para el programa académico "Ingeniería de Sistemas" existe una ReglaPrograma con version "2026-1" en estadoVigencia "Activa"
    Y existen prácticas empresariales en curso en estado "Solicitada", "Aprobada", "Asignada", "EnEjecucion" o "Evaluada" vinculadas a la ReglaPrograma version "2026-1"
    Y existe para el mismo programa académico "Ingeniería de Sistemas" una nueva ReglaPrograma con version "2026-2" en estadoVigencia "Borrador"
    Y el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas publica y activa oficialmente la ReglaPrograma con version "2026-2"
    Entonces el sistema cambia atómicamente el estadoVigencia de la ReglaPrograma version "2026-1" a "Inactiva" (histórica) y cambia el estadoVigencia de la ReglaPrograma version "2026-2" a "Activa" con su fechaVigencia actualizada
    Y el sistema garantiza que haya como máximo una única ReglaPrograma en estadoVigencia "Activa" para el programa académico "Ingeniería de Sistemas"
    Y el sistema conserva intacto el vínculo de todas las prácticas en curso y completadas con la ReglaPrograma version "2026-1" asegurando un 0% de alteración sobre sus condiciones normativas
    Y el sistema vincula toda nueva Práctica que se postule a partir de ese momento en "Ingeniería de Sistemas" a la ReglaPrograma version "2026-2"
    Y el sistema registra atómicamente un EventoBitacora inmutable con actorIdentificador "COORD-001", rolActor "Coordinador de prácticas", accionRealizada de activación oficial de ReglaPrograma, entidadAfectada, fechaHora, ipOrigen y huellaDigital

  Escenario: Rechazo de configuración de regla de programa por datos obligatorios vacíos o cantidad de horas requeridas no válida
    Dado que el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas intenta registrar o actualizar una ReglaPrograma con programaAcademico vacío, version vacía, plantillaActa vacía o con horasRequeridas que no sea un número entero positivo mayor a 0 (menor o igual a 0)
    Entonces el sistema rechaza el registro o edición de la ReglaPrograma por incumplimiento de las invariantes de validación normativa
    Y el sistema no modifica la ReglaPrograma activa vigente del programa académico
    Y el sistema informa al Coordinador de prácticas el detalle del campo obligatorio faltante o que horasRequeridas debe ser un número entero positivo mayor a 0

  Escenario: Rechazo de configuración de regla de programa por criterios de rúbrica vacíos o inválidos
    Dado que el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas intenta registrar o editar una ReglaPrograma con criteriosRubrica vacíos (lista vacía o diccionario vacío), con nombres de criterio en blanco o, en caso de proporcionar diccionario con pesos, con ponderaciones menores o iguales a 0
    Entonces el sistema rechaza la creación o edición de la ReglaPrograma
    Y el sistema informa al Coordinador de prácticas que los criteriosRubrica deben contener al menos un criterio válido (como lista simple de criterios sin peso o como diccionario con ponderaciones válidas)

  Escenario: Rechazo de creación de regla de programa por identificador de versión duplicado para el mismo programa académico
    Dado que ya existe una ReglaPrograma registrada para el programa académico "Ingeniería de Sistemas" con la version "2026-1"
    Y el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas intenta crear otra ReglaPrograma para "Ingeniería de Sistemas" con la misma version "2026-1"
    Entonces el sistema rechaza la operación por duplicidad de versión dentro del mismo programa académico
    Y el sistema conserva inalterada la ReglaPrograma existente con version "2026-1"
    Y el sistema informa al Coordinador de prácticas que ya existe una versión "2026-1" para el programa académico "Ingeniería de Sistemas"

  Escenario: Intento de edición o eliminación directa de una regla de programa activa o histórica vinculada a prácticas existentes
    Dado que existe una ReglaPrograma con version "2026-1" cuyo estadoVigencia es "Activa" o "Inactiva" (histórica)
    Y el usuario está autenticado con rol de "Coordinador de prácticas" e identificador "COORD-001"
    Cuando el Coordinador de prácticas intenta editar directamente los atributos normativos (horasRequeridas, criteriosRubrica o plantillaActa) o eliminar dicha ReglaPrograma que ya no se encuentra en estadoVigencia "Borrador"
    Entonces el sistema deniega la modificación o eliminación directa porque solo se permite editar los atributos de una ReglaPrograma mientras permanezca en estadoVigencia "Borrador"
    Y el sistema mantiene intactos los datos de la ReglaPrograma version "2026-1" garantizando un 0% de alteración en las prácticas y actas asociadas
    Y el sistema informa que una regla en estado "Activa" o "Inactiva" es inmutable y que cualquier cambio normativo debe registrarse como una nueva versión en estado "Borrador"

  Escenario: Intento de configurar, editar, simular o activar una regla de programa por un rol no autorizado
    Dado que un usuario autenticado con rol de "Estudiante", "DocenteAsesor" o "SupervisorEmpresa", o una solicitud sin sesión institucional válida, intenta crear, editar, simular o activar una ReglaPrograma
    Cuando el mecanismo centralizado de autorización evalúa los permisos del rol bajo la política deny-by-default y la separación estricta de roles
    Entonces el sistema deniega el 100% de los intentos no autorizados
    Y el sistema mantiene las configuraciones de ReglaPrograma sin alteraciones asegurando 0 datos expuestos
    Y el sistema registra de inmediato un EventoBitacora inmutable por intento de configuración de reglas por rol no autorizado con actorIdentificador, rolActor, fechaHora e ipOrigen en menos de 1 minuto

  Escenario: EAC-01 - Modificabilidad declarativa de reglas y plantillas en menos de 16 horas-hombre con 0% de alteración en prácticas activas y actas previas
    Dado que el sistema se encuentra desplegado en operación normal con prácticas empresariales activas y actas finales emitidas bajo la versión 1 de la ReglaPrograma del programa académico
    Y el Coordinador de prácticas o la Decanatura solicita cambiar la estructura, los criteriosRubrica, las horasRequeridas o el formato visual de la plantillaActa del ActaFinal en PDF
    Cuando la nueva versión de la ReglaPrograma y su plantillaActa se configuran en estado "Borrador", se simulan y se activan oficialmente en el módulo de reglas y motor de plantillas sin modificar la lógica de negocio ni la estructura de la base de datos
    Entonces la modificación se completa y despliega en menos de 16 horas-hombre
    Y el cambio afecta como máximo a 2 componentes de la arquitectura (Módulo Reglas y Adaptador PDF y Hash)
    Y el sistema garantiza un 0% de alteración en las condiciones de las prácticas activas iniciadas previamente y un 0% de alteración en las actas finales emitidas con anterioridad
