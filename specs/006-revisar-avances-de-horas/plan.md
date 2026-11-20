# Plan: 006 Revisar avances de horas

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`.
  - La capa de dominio provee las entidades `Practica`, `RegistroHoras` (con `EstadoValidacionHoras`), `ReglaPrograma` y `EventoBitacora` sin acoplamiento a frameworks ni librerías externas.
  - La capa de aplicación define el caso de uso `RevisarAvancesHorasCasoUso` (dentro del `Módulo Seguimiento y Evaluación` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada y salida, la política de autorización en `AutorizadorRBAC` y la extensión del puerto `RepositorioPracticaPort`.
  - La capa de infraestructura extiende `InMemoryRepositorioPractica` para listar prácticas asignadas por docente asesor.
  - `main.py` actúa como único punto de composición e inyección de dependencias.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`) y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - Uso de adaptadores deterministas en memoria (`InMemoryRepositorioPractica`, `InMemoryRepositorioRegistroHoras`, `InMemoryRepositorioReglaPrograma`) que garantizan lecturas consistentes bajo concurrencia de 50 tutores y 500 estudiantes (**RT-01**).
- **ADR-004 (Autenticación híbrida SSO OIDC para actores internos):**
  - Los actores internos autorizados (`DocenteAsesor` y `Estudiante`) se autentican mediante el proveedor de identidad institucional generando un `ContextoUsuario` verificado.
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política centralizada *deny-by-default*.
  - La operación `revisar_avances_horas` (CU-06) está autorizada exclusivamente para los roles `DocenteAsesor` (`RolUsuario.DOCENTE_ASESOR` / `RolUsuario.DOCENTE`) y `Estudiante` (`RolUsuario.ESTUDIANTE`). El rol `Coordinador de prácticas` está excluido de CU-06 (ya que realiza su monitoreo general a través de CU-13), al igual que `SupervisorEmpresa`.
  - Validación estricta de pertenencia contextual de datos (*Context-Based Access Control*, RN-01):
    - Un `DocenteAsesor` únicamente puede consultar el avance de prácticas donde figure como tutor asignado (`practica.docente_asesor_id == contexto.usuario_id`). Si la práctica no tiene tutor asignado o está asignada a otro docente, el acceso es denegado.
    - Un `Estudiante` únicamente puede consultar el avance de la práctica de la cual es titular (`practica.estudiante_id == contexto.usuario_id`).
  - Todo intento de acceso con rol no autorizado o que viole la pertenencia contextual es rechazado con 0 datos expuestos (**EAC-03**).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Toda ejecución del caso de uso (tanto la consulta exitosa de solo lectura como cualquier intento de acceso denegado por rol o por pertenencia contextual) registra un único `EventoBitacora` inmutable con huella digital SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` en menos de 1 minuto (**EAC-03**).
- **ADR-007 (Configuración declarativa de reglas de negocio y plantillas versionadas por programa):**
  - El cálculo del porcentaje de avance y de las horas restantes se realiza estrictamente contra las `horasRequeridas` de la versión de `ReglaPrograma` vinculada a la `Practica` al momento de su postulación (`practica.regla_programa_id`), garantizando 0% de alteración ante nuevas versiones normativas publicadas posteriormente (**EAC-01**).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - El caso de uso es estrictamente de consulta (solo lectura): inspecciona el `estadoActual` de la `Practica` y el `estadoValidacion` de cada `RegistroHoras` sin provocar transiciones de estado ni mutar acumulados.

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/practica.py` *(Existente)*:
  - Entidad raíz `Practica` con propiedades de lectura `id`, `estudiante_id`, `docente_asesor_id`, `regla_programa_id`, `estado_actual` (`EstadoPractica`) y `horas_acumuladas_aprobadas`.
- `dominio/modelos/registro_horas.py` *(Existente)*:
  - Entidad `RegistroHoras` y enumeración `EstadoValidacionHoras` (`Pendiente`, `Aprobado`, `Rechazado`) con propiedades `id`, `practica_id`, `semana`, `cantidad_horas`, `descripcion_actividades`, `estado_validacion`, `observaciones_rechazo` y `fecha_registro`.
- `dominio/modelos/regla_programa.py` *(Existente)*:
  - Entidad `ReglaPrograma` con propiedades `id`, `programa_academico`, `version` y `horas_requeridas`.
- `dominio/modelos/evento_bitacora.py` *(Existente)*:
  - Entidad inmutable `EventoBitacora` con sellado SHA-256 para registrar el evento de auditoría de cada consulta o rechazo de acceso.
- `dominio/errores.py` *(Existente)*:
  - Excepción `PracticaNoEncontradaError`: lanzada cuando el identificador de la práctica consultada no existe en el sistema.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/avance_horas_dto.py` *(Nuevo)*:
  - `ConsultarAvanceHorasComando`: DTO inmutable de entrada para consultar el detalle de avance de una práctica específica:
    - `practica_id: str`
    - `actor_id: str`
    - `rol_actor: str`
    - `ip_origen: str = "127.0.0.1"`
  - `ConsultarAvancesDocenteComando`: DTO inmutable de entrada para la consulta consolidada de las prácticas asignadas a un docente asesor:
    - `docente_asesor_id: str`
    - `actor_id: str`
    - `rol_actor: str`
    - `ip_origen: str = "127.0.0.1"`
  - `DetalleReporteHorasDTO`: DTO inmutable con el detalle de cada reporte semanal en modo solo lectura:
    - `registro_horas_id: str`
    - `semana: int`
    - `cantidad_horas: int`
    - `descripcion_actividades: str`
    - `estado_validacion: str`
    - `observaciones_rechazo: Optional[str]`
    - `fecha_registro: datetime`
  - `AvanceHorasPracticaRespuestaDTO`: DTO inmutable de salida con el resumen y desglose completo del avance de horas de una práctica:
    - `practica_id: str`
    - `estudiante_id: str`
    - `docente_asesor_id: Optional[str]`
    - `estado_practica: str`
    - `regla_programa_id: str`
    - `version_regla: str`
    - `horas_requeridas: int`
    - `horas_acumuladas_aprobadas: int`
    - `horas_pendientes_validacion: int`
    - `horas_rechazadas: int`
    - `horas_restantes: int`
    - `porcentaje_avance: float`
    - `requisito_horas_cumplido: bool`
    - `reportes_semanales: tuple[DetalleReporteHorasDTO, ...]`
    - `mensaje: str`
  - `ResumenAvancePracticaDTO`: DTO inmutable con el resumen de una práctica dentro del listado consolidado del docente asesor:
    - `practica_id: str`
    - `estudiante_id: str`
    - `estado_actual: str`
    - `horas_acumuladas_aprobadas: int`
    - `horas_requeridas: int`
    - `horas_restantes: int`
    - `porcentaje_avance: float`
    - `cantidad_reportes_pendientes: int`
    - `requisito_horas_cumplido: bool`
  - `ListadoAvancesDocenteRespuestaDTO`: DTO inmutable de salida para la consulta consolidada del docente asesor:
    - `docente_asesor_id: str`
    - `total_practicas_asignadas: int`
    - `practicas: tuple[ResumenAvancePracticaDTO, ...]`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_practica.py` *(Modificar)*:
  - Extender `RepositorioPracticaPort` con el método:
    - `listar_por_docente(docente_asesor_id: str) -> list[Practica]`: retorna las prácticas asignadas al docente asesor indicado.
- `aplicacion/puertos/repositorio_registro_horas.py` *(Existente)*:
  - Uso de `RepositorioRegistroHorasPort.listar_por_practica(practica_id: str) -> list[RegistroHoras]`.
- `aplicacion/puertos/repositorio_regla.py` *(Existente)*:
  - Uso de `RepositorioReglaProgramaPort.buscar_por_id(regla_id: str) -> Optional[ReglaPrograma]`.
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Agregar en `_MATRIZ_PERMISOS`:
    - `"revisar_avances_horas": {RolUsuario.DOCENTE.value, RolUsuario.DOCENTE_ASESOR.value, RolUsuario.ESTUDIANTE.value}`
    - `"listar_avances_docente": {RolUsuario.DOCENTE.value, RolUsuario.DOCENTE_ASESOR.value}`
  - Agregar método `validar_revision_avances_horas(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "revisar_avances_horas") -> None`.
  - Agregar método `validar_pertenencia_docente(contexto: ContextoUsuario, docente_asignado_id: Optional[str], operacion: Optional[str] = None) -> None`:
    - Si el actor tiene rol `Docente` o `DocenteAsesor`, verifica que la práctica tenga `docente_asignado_id` no nulo y que coincida exactamente con `contexto.usuario_id`; de lo contrario, lanza `AccesoDenegadoError` (Escenarios 7 y 9).
  - Reutilizar `validar_pertenencia_estudiante(contexto: ContextoUsuario, estudiante: Union[Estudiante, str], operacion: Optional[str] = None) -> None` cuando el actor autenticado tiene rol `Estudiante` (Escenarios 2 y 8).
- `aplicacion/casos_uso/revisar_avances_horas.py` *(Nuevo)*:
  - Clase `RevisarAvancesHorasCasoUso` (Módulo Seguimiento y Evaluación):
    - Inyecta `RepositorioPracticaPort`, `RepositorioRegistroHorasPort`, `RepositorioReglaProgramaPort` y `AutorizadorRBAC`.
    - Método `ejecutar(comando: ConsultarAvanceHorasComando) -> AvanceHorasPracticaRespuestaDTO` (y `__call__`):
      1. Valida que el rol del actor esté autorizado en `revisar_avances_horas` (`DocenteAsesor` o `Estudiante`). Si el rol no está autorizado (ej. `CoordinadorPracticas` o `SupervisorEmpresa`), registra un único `EventoBitacora` de acceso rechazado y propaga `AccesoDenegadoError` con 0 datos expuestos (Escenarios 11 y 12).
      2. Busca la `Practica` en `RepositorioPracticaPort.buscar_por_id(comando.practica_id)`. Si no existe, lanza `PracticaNoEncontradaError` (Escenario 10).
      3. Verifica la pertenencia contextual según el rol del actor:
         - Si es `DocenteAsesor`, invoca `autorizador_rbac.validar_pertenencia_docente(contexto, practica.docente_asesor_id)`. Si la práctica no tiene docente asignado o pertenece a otro docente, registra un único `EventoBitacora` de rechazo y propaga `AccesoDenegadoError` con 0 datos expuestos (Escenarios 7 y 9).
         - Si es `Estudiante`, invoca `autorizador_rbac.validar_pertenencia_estudiante(contexto, practica.estudiante_id)`. Si pertenece a otro estudiante, registra un único `EventoBitacora` de rechazo y propaga `AccesoDenegadoError` con 0 datos expuestos (Escenario 8).
      4. Recupera la `ReglaPrograma` vinculada a la práctica mediante `RepositorioReglaProgramaPort.buscar_por_id(practica.regla_programa_id)` para obtener las `horas_requeridas` de la versión con la que inició la práctica (Escenario 13, **EAC-01**, **ADR-007**).
      5. Recupera los reportes semanales ordenados cronológicamente con `RepositorioRegistroHorasPort.listar_por_practica(practica.id)`.
      6. Calcula en modo estrictamente de solo lectura:
         - `horas_acumuladas_aprobadas` (de la práctica).
         - `horas_pendientes_validacion` (suma de `cantidad_horas` de reportes en estado `Pendiente`).
         - `horas_rechazadas` (suma de `cantidad_horas` de reportes en estado `Rechazado`).
         - `horas_restantes = max(0, horas_requeridas - horas_acumuladas_aprobadas)`.
         - `porcentaje_avance = round((horas_acumuladas_aprobadas / horas_requeridas) * 100.0, 2)` (si `horas_requeridas > 0`).
         - `requisito_horas_cumplido = horas_acumuladas_aprobadas >= horas_requeridas`.
      7. Registra un único `EventoBitacora` con acción `"CONSULTA_AVANCE_HORAS"`, `actor_identificador`, `rol_actor`, `ip_origen` y `entidad_afectada=f"Practica:{practica.id}"` (Escenarios 1 a 5, **ADR-006**).
      8. Retorna `AvanceHorasPracticaRespuestaDTO` sin modificar la práctica ni los reportes.
    - Método `listar_por_docente(comando: ConsultarAvancesDocenteComando) -> ListadoAvancesDocenteRespuestaDTO`:
      1. Valida que el actor tenga rol `DocenteAsesor` (`listar_avances_docente`) y que `comando.actor_id == comando.docente_asesor_id`. Si falla, registra un único `EventoBitacora` de acceso denegado y lanza `AccesoDenegadoError` con 0 datos expuestos.
      2. Consulta `RepositorioPracticaPort.listar_por_docente(comando.docente_asesor_id)` filtrando exclusivamente las prácticas asignadas a dicho tutor (Escenario 6).
      3. Para cada práctica asignada, recupera su `ReglaPrograma` vinculada y sus `RegistroHoras` para construir `ResumenAvancePracticaDTO` (incluyendo conteo de reportes en estado `Pendiente`).
      4. Registra un único `EventoBitacora` con acción `"CONSULTA_CONSOLIDADA_AVANCES_DOCENTE"` y `entidad_afectada=f"DocenteAsesor:{comando.docente_asesor_id}"`.
      5. Retorna `ListadoAvancesDocenteRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - En `InMemoryRepositorioPractica`:
    - Implementar `listar_por_docente(docente_asesor_id: str) -> list[Practica]`: retorna las prácticas cuyo `docente_asesor_id` coincide con el identificador solicitado, sin exponer prácticas de otros tutores (**RN-01**, **RT-01**).

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `RevisarAvancesHorasCasoUso`, `ConsultarAvanceHorasComando` y `ConsultarAvancesDocenteComando`.
  - Agregar el atributo `caso_uso_revisar_avances_horas: RevisarAvancesHorasCasoUso` a `SistemaPracticasEmpresariales`.
  - Instanciar `RevisarAvancesHorasCasoUso` en `inicializar_sistema()` inyectando `repo_practica`, `repo_registro_horas`, `repo_regla` y `autorizador_rbac`.
  - Agregar en `main()` la demostración CLI de CU-06.

---

## Flujo

Secuencia operativa para la revisión de avances de horas (CU-06):

1. **Verificación de rol RBAC (*deny-by-default*, ADR-005):**
   - El caso de uso construye el `ContextoUsuario` y valida la operación `revisar_avances_horas` en `AutorizadorRBAC`.
   - Solo se admiten los roles `DocenteAsesor` (`Docente`) y `Estudiante`. Si un `CoordinadorPracticas`, `SupervisorEmpresa` u otro rol no autorizado invoca el caso de uso, se inserta de inmediato un único `EventoBitacora` de rechazo y se aborta la operación lanzando `AccesoDenegadoError` con 0 datos expuestos (**EAC-03**).
2. **Recuperación de la práctica y validación de pertenencia contextual (RN-01, ADR-005):**
   - Se consulta la práctica en `RepositorioPracticaPort.buscar_por_id(practica_id)`. Si no existe, se lanza `PracticaNoEncontradaError`.
   - Si el actor es `DocenteAsesor`, se verifica que `practica.docente_asesor_id` exista y sea igual a `contexto.usuario_id`.
   - Si el actor es `Estudiante`, se verifica que `practica.estudiante_id` sea igual a `contexto.usuario_id`.
   - Ante cualquier discrepancia de pertenencia o ausencia de tutor asignado, se registra inmediatamente un único `EventoBitacora` de acceso rechazado y se lanza `AccesoDenegadoError` sin exponer datos de la práctica, del estudiante ni de los reportes (**EAC-03**).
3. **Recuperación de la regla versionada y de los reportes semanales (ADR-007):**
   - Se obtiene la `ReglaPrograma` vinculada a la práctica mediante `RepositorioReglaProgramaPort.buscar_por_id(practica.regla_programa_id)`.
   - Se obtienen todos los reportes de `RegistroHoras` de la práctica ordenados por semana mediante `RepositorioRegistroHorasPort.listar_por_practica(practica.id)`.
4. **Cálculo de métricas de progreso en modo solo lectura (EAC-01, ADR-010):**
   - Se calculan `horas_acumuladas_aprobadas`, `horas_pendientes_validacion`, `horas_rechazadas`, `horas_restantes`, `porcentaje_avance` respecto a las `horas_requeridas` de la versión de `ReglaPrograma` asociada a la práctica, y el indicador booleano `requisito_horas_cumplido`.
   - Se mapea cada `RegistroHoras` a `DetalleReporteHorasDTO` incluyendo `observaciones_rechazo` cuando el reporte esté en estado `Rechazado`.
   - No se realiza ninguna mutación sobre `Practica` ni sobre `RegistroHoras`.
5. **Registro en bitácora Append-Only (ADR-006):**
   - Se registra un único `EventoBitacora` inmutable asentando la consulta realizada con identificador del actor, rol, IP, fecha, hora y entidad consultada.
6. **Entrega de respuesta:**
   - Se retorna el DTO inmutable `AvanceHorasPracticaRespuestaDTO` (o `ListadoAvancesDocenteRespuestaDTO` en la consulta consolidada por docente).

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md`):

- `Practica`: entidad raíz consultada; provee `id`, `estudiante_id`, `docente_asesor_id`, `regla_programa_id`, `estadoActual` y `horasAcumuladasAprobadas`.
- `RegistroHoras`: reportes semanales asociados a la práctica; proveen `id`, `semana`, `cantidadHoras`, `descripcionActividades`, `estadoValidacion` (`Pendiente`, `Aprobado`, `Rechazado`), `observaciones_rechazo` y `fechaRegistro`.
- `ReglaPrograma`: configuración declarativa versionada vinculada a la práctica; provee `version` y `horasRequeridas` (ej. 320 horas) inmutables frente a cambios normativos posteriores (**ADR-007**, **EAC-01**).
- `DocenteAsesor`: tutor académico asignado a la práctica, sujeto de la validación de pertenencia contextual.
- `Estudiante`: estudiante titular de la práctica, sujeto de la validación de pertenencia contextual cuando consulta su propio avance.
- `EventoBitacora`: registro inmutable de auditoría (*Append-Only*) generado tanto en consultas autorizadas como en rechazos de acceso (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Registro o modificación de horas semanales por parte del estudiante (cubierto en CU-04).
- Aprobación o rechazo de reportes semanales de horas por parte del supervisor de empresa (cubierto en CU-05).
- Registro de comentarios, alertas o calificaciones por parte del docente asesor durante la revisión (el caso de uso CU-06 es estrictamente de solo lectura).
- Tablero de monitoreo general de prácticas para el Coordinador de prácticas (cubierto exclusivamente en CU-13).
- Evaluación de desempeño del practicante por el supervisor de empresa (cubierto en CU-07) y generación o aprobación del acta final en PDF (cubiertos en CU-09 y CU-10).

---

## Decisiones pendientes

Ninguna. Todas las reglas de negocio aclaradas (operación estrictamente de solo lectura, acceso autorizado para `DocenteAsesor` asignado y `Estudiante` titular mientras el `Coordinador de prácticas` opera en CU-13, y generación de un único `EventoBitacora` por operación) están cubiertas por los **ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007 y ADR-010**.

