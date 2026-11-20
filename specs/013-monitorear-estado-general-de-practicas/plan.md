# Plan: 013 Monitorear estado general de prácticas

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`, con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de `dominio/` provee las entidades `Practica` (con su máquina de estados `EstadoPractica`), `ReglaPrograma`, `DocenteAsesor`, `RegistroHoras`, `EvaluacionDesempeno`, `ActaFinal`, `IntentoValidacion` y `EventoBitacora` sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de `aplicacion/` define el caso de uso `MonitorearPracticasCasoUso` (ubicado dentro del `Módulo Postulaciones` conforme a `docs/vistas/03-desarrollo.md` y `docs/diagramas/03-desarrollo.puml`), sus DTOs inmutables de entrada y salida, la política de autorización exclusiva para el rol `Coordinador de prácticas` con pertenencia contextual por `programaAcademico` en `AutorizadorRBAC`, y la consulta a través de `RepositorioPracticaPort` y los puertos de lectura de reglas, docentes, horas, evaluaciones y actas.
  - La capa de `infraestructura/` provee en `InMemoryRepositorioPractica` y los demás adaptadores en memoria los métodos deterministas de lectura sin acoplar detalles de infraestructura a la lógica de aplicación.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - Consultas consolidadas estrictamente de solo lectura sobre los repositorios en memoria (`InMemoryRepositorioPractica`, `InMemoryRepositorioReglaPrograma`, `InMemoryRepositorioDocente`, `InMemoryRepositorioRegistroHoras`, `InMemoryRepositorioEvaluacionDesempeno`, `InMemoryRepositorioActaFinal`), garantizando lecturas consistentes y sin bloqueos transaccionales sobre el volumen de 500 estudiantes y 50 tutores simultáneos (**RT-01**, **OB-02**).
- **ADR-004 (Esquema de autenticación híbrida):**
  - El `Coordinador de prácticas` es un actor interno autenticado mediante el sistema institucional (`SSO Institucional` / `ContextoUsuario`). Toda solicitud sin identidad institucional válida o sin adscripción de programa académico válida es rechazada de inmediato con 0 datos expuestos y registro en bitácora (**EAC-03**).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/` aplica la política centralizada *deny-by-default*.
  - La operación `monitorear_practicas` (`CU-13`) está autorizada **exclusivamente** para el rol `Coordinador de prácticas` (`RolUsuario.COORDINADOR` / `RolUsuario.COORDINADOR_PRACTICAS`). Cualquier intento de invocación por roles distintos (`Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`, `SISTEMA` o usuarios sin sesión válida) es denegado de inmediato con 0 datos expuestos y registro en bitácora (**RN-03**, **EAC-03**, Escenarios 7 y 8).
  - Validación estricta de pertenencia contextual de datos por programa académico (*Context-Based Access Control*, **RN-01**): el tablero de monitoreo y la consulta de detalle de una práctica restringen automáticamente la visibilidad únicamente a las prácticas del `programaAcademico` al que pertenece el coordinador autenticado (determinado a través de la `ReglaPrograma` vinculada a cada `Practica`). Si el coordinador intenta consultar el detalle de una práctica perteneciente a otro `programaAcademico` o filtrar un programa distinto al suyo, el acceso es denegado con 0 datos expuestos y registro en bitácora (Escenarios 1 y 5).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Toda consulta exitosa del tablero de monitoreo general (con o sin filtros por documento del `Estudiante`, `estadoActual` o `DocenteAsesor`), toda consulta de detalle de una práctica en el monitoreo y todo intento de acceso rechazado (por rol no autorizado o por intento de acceso a una práctica de otro programa académico) registra un único `EventoBitacora` inmutable sellado con `huellaDigital` SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` en menos de 1 minuto (**EAC-03**).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - En el tablero de monitoreo, el cálculo de `horasRequeridas`, `horasRestantes` y `porcentajeAvance` de cada `Practica` se realiza individualmente contra la versión específica de `ReglaPrograma` vinculada a dicha práctica al momento de su postulación (`practica.regla_programa_id`), permitiendo que coexistan prácticas del mismo programa académico bajo diferentes versiones normativas con un 0% de alteración (**EAC-01**, Escenario 9).
- **ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico):**
  - El monitoreo expone en modo de solo lectura para cada práctica el estado de generación y firmas electrónicas de su `ActaFinal` (`aprobadaPorDocente`, `aprobadaPorCoordinador`, `numeroActa`, `fechaEmision` y `hashIntegridadSha256`) para que el Coordinador supervise qué actas se encuentran pendientes de firma o en firme (**OB-01**, **OB-05**, Escenarios 1 y 4).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - El caso de uso es estrictamente de solo lectura: agrega y contabiliza las prácticas del programa académico en los ocho estados formales de `EstadoPractica` (`PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`, `Rechazada`) sin provocar transiciones ni alterar ninguna entidad del dominio (**RN-02**, **OB-02**).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/practica.py` *(Existente)*:
  - Entidad raíz `Practica` y enumeración `EstadoPractica` (`PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`, `Rechazada`), con propiedades `id`, `estudiante_id`, `regla_programa_id`, `estado_actual`, `fecha_postulacion`, `horas_acumuladas_aprobadas`, `fecha_inicio`, `fecha_fin`, `motivo_rechazo`, `docente_asesor_id`, `supervisor_empresa_id` y método `es_activa()`.
- `dominio/modelos/regla_programa.py` *(Existente)*:
  - Entidad `ReglaPrograma` con propiedades `id`, `programa_academico`, `version` y `horas_requeridas`.
- `dominio/modelos/docente_asesor.py` *(Existente)*:
  - Entidad `DocenteAsesor` con propiedades `id`, `documento`, `nombre_completo`, `correo_institucional`, `cupo_maximo_practicas`, `practicas_activas`, `cupos_disponibles` y `activo`.
- `dominio/modelos/registro_horas.py` *(Existente)*:
  - Entidad `RegistroHoras` y enumeración `EstadoValidacionHoras` (`Pendiente`, `Aprobado`, `Rechazado`).
- `dominio/modelos/evaluacion_desempeno.py` *(Existente)*:
  - Entidad `EvaluacionDesempeno` con propiedades `id`, `calificacion_cuantitativa`, `es_aprobatoria`, `observaciones`, `respuestas_rubrica` y `fecha_evaluacion`.
- `dominio/modelos/acta_final.py` *(Existente)*:
  - Entidad `ActaFinal` con propiedades `id`, `numero_acta`, `fecha_emision`, `ruta_archivo_pdf`, `hash_integridad_sha256`, `aprobada_por_docente`, `aprobada_por_coordinador` y `esta_en_firme`.
- `dominio/modelos/intento_validacion.py` *(Existente)*:
  - Entidad `IntentoValidacion` con `numero_intento`, `fecha_intento`, `resultado_sia` y `detalle_estado`.
- `dominio/modelos/evento_bitacora.py` *(Existente)*:
  - Entidad inmutable `EventoBitacora` con sellado SHA-256 para registrar la auditoría de cada consulta del tablero de monitoreo o intento de acceso denegado.
- `dominio/errores.py` *(Existente)*:
  - Uso de `PracticaNoEncontradaError` cuando el identificador de práctica consultado en el detalle del monitoreo no existe en el sistema.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/monitoreo_practicas_dto.py` *(Nuevo)*:
  - `ConsultarMonitoreoPracticasComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`) para consultar el tablero general de prácticas del programa académico del coordinador:
    - `actor_id: str`
    - `rol_actor: str`
    - `programa_academico_coordinador: str` (programa académico al que pertenece el coordinador autenticado)
    - `filtro_documento_estudiante: Optional[str] = None` (filtro por documento o identificador del `Estudiante`, Escenario 2)
    - `filtro_estado_actual: Optional[str] = None` (filtro opcional por valor de `EstadoPractica`, Escenario 3)
    - `filtro_docente_asesor_id: Optional[str] = None` (filtro opcional por identificador del `DocenteAsesor`, Escenario 3)
    - `filtro_programa_academico: Optional[str] = None` (si se especifica y difiere de `programa_academico_coordinador`, se rechaza por pertenencia contextual, Escenario 5)
    - `ip_origen: str = "127.0.0.1"`
  - `ConsultarDetallePracticaMonitoreoComando`: DTO inmutable de entrada para consultar la trazabilidad detallada de una práctica específica desde el tablero de monitoreo (Escenarios 4 y 5):
    - `practica_id: str`
    - `actor_id: str`
    - `rol_actor: str`
    - `programa_academico_coordinador: str`
    - `ip_origen: str = "127.0.0.1"`
  - `IndicadorCargaDocenteDTO`: DTO inmutable con el resumen de ocupación de cupo de un `DocenteAsesor` (Escenarios 1 y 10):
    - `docente_asesor_id: str`
    - `documento: str`
    - `nombre_completo: str`
    - `correo_institucional: str`
    - `cupo_maximo_practicas: int`
    - `practicas_activas: int`
    - `cupos_disponibles: int`
    - `activo: bool`
  - `ItemPracticaMonitoreoDTO`: DTO inmutable con la fila consolidada de una `Practica` dentro del listado del tablero de monitoreo (Escenarios 1, 2, 3 y 9):
    - `practica_id: str`
    - `documento_estudiante: str`
    - `programa_academico: str`
    - `regla_programa_id: str`
    - `version_regla: str`
    - `estado_actual: str`
    - `fecha_postulacion: datetime`
    - `fecha_inicio: Optional[datetime]`
    - `fecha_fin: Optional[datetime]`
    - `docente_asesor_id: Optional[str]`
    - `nombre_docente_asesor: Optional[str]`
    - `supervisor_empresa_id: Optional[str]`
    - `horas_requeridas: int`
    - `horas_acumuladas_aprobadas: int`
    - `horas_pendientes_validacion: int`
    - `horas_restantes: int`
    - `porcentaje_avance_horas: float`
    - `requisito_horas_cumplido: bool`
    - `evaluacion_realizada: bool`
    - `calificacion_cuantitativa: Optional[float]`
    - `acta_generada: bool`
    - `numero_acta: Optional[str]`
    - `aprobada_por_docente: bool`
    - `aprobada_por_coordinador: bool`
    - `acta_en_firme: bool`
  - `TableroMonitoreoPracticasRespuestaDTO`: DTO inmutable de salida con el tablero consolidado del monitoreo general de prácticas (Escenarios 1, 2, 3, 6, 9 y 10):
    - `programa_academico: str`
    - `total_practicas_programa: int`
    - `total_practicas_filtradas: int`
    - `resumen_por_estado: dict[str, int]` (conteo para cada uno de los 8 valores de `EstadoPractica`)
    - `carga_docentes: tuple[IndicadorCargaDocenteDTO, ...]`
    - `practicas: tuple[ItemPracticaMonitoreoDTO, ...]`
    - `mensaje: str`
  - `DetallePracticaMonitoreoRespuestaDTO`: DTO inmutable de salida con la trazabilidad completa de una práctica consultada desde el monitoreo (Escenario 4):
    - `practica_id: str`
    - `documento_estudiante: str`
    - `programa_academico: str`
    - `regla_programa_id: str`
    - `version_regla: str`
    - `estado_actual: str`
    - `fecha_postulacion: datetime`
    - `fecha_inicio: Optional[datetime]`
    - `fecha_fin: Optional[datetime]`
    - `docente_asesor_id: Optional[str]`
    - `nombre_docente_asesor: Optional[str]`
    - `correo_docente_asesor: Optional[str]`
    - `supervisor_empresa_id: Optional[str]`
    - `horas_requeridas: int`
    - `horas_acumuladas_aprobadas: int`
    - `horas_pendientes_validacion: int`
    - `horas_restantes: int`
    - `porcentaje_avance_horas: float`
    - `cantidad_reportes_pendientes: int`
    - `requisito_horas_cumplido: bool`
    - `motivo_rechazo: Optional[str]`
    - `evaluacion_realizada: bool`
    - `calificacion_cuantitativa: Optional[float]`
    - `es_aprobatoria: Optional[bool]`
    - `observaciones_evaluacion: Optional[str]`
    - `fecha_evaluacion: Optional[datetime]`
    - `acta_generada: bool`
    - `numero_acta: Optional[str]`
    - `fecha_emision_acta: Optional[datetime]`
    - `aprobada_por_docente: bool`
    - `aprobada_por_coordinador: bool`
    - `acta_en_firme: bool`
    - `hash_integridad_sha256: Optional[str]`
    - `ultimo_resultado_sia: Optional[str]`
    - `ultimo_detalle_sia: Optional[str]`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_practica.py` *(Modificar)*:
  - Extender `RepositorioPracticaPort` con el método formal en el protocolo:
    - `listar_todas() -> list[Practica]`: retorna todas las prácticas registradas en el almacén de datos (ya implementado en `InMemoryRepositorioPractica.listar_todas()`, se declara explícitamente en el `Protocol` del puerto).
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Agregar en `_MATRIZ_PERMISOS`:
    - `"monitorear_practicas": {RolUsuario.COORDINADOR.value, RolUsuario.COORDINADOR_PRACTICAS.value}`
  - Agregar método `validar_monitoreo_practicas(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "monitorear_practicas") -> None`:
    - Verifica bajo política *deny-by-default* que el actor tenga identidad institucional válida (no vacía) y posea exclusivamente el rol `Coordinador` o `CoordinadorPracticas` (`"Coordinador de prácticas"`). Si el actor tiene rol `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`, `SISTEMA` o vacío, lanza `AccesoDenegadoError` (Escenarios 7 y 8).
  - Agregar método `validar_pertenencia_programa_coordinador(contexto: ContextoUsuario, programa_coordinador: str, programa_objetivo: str, operacion: str = "monitorear_practicas") -> None`:
    - Verifica bajo control de acceso contextual (*Context-Based RBAC*, **RN-01**, **ADR-005**) que el `programa_coordinador` esté definido y coincida (comparación normalizada sin distinción de mayúsculas/espacios extremos) con el `programa_objetivo` de la práctica o del filtro solicitado. Si difieren, lanza `AccesoDenegadoError` (Escenario 5).
- `aplicacion/casos_uso/monitorear_practicas.py` *(Nuevo)*:
  - Clase `MonitorearPracticasCasoUso` (dentro del `Módulo Postulaciones` según `docs/vistas/03-desarrollo.md`):
    - Inyecta `RepositorioPracticaPort`, `RepositorioReglaProgramaPort`, `RepositorioDocentePort` (opcional), `RepositorioRegistroHorasPort` (opcional), `RepositorioEvaluacionDesempenoPort` (opcional), `RepositorioActaFinalPort` (opcional) y `AutorizadorRBAC`.
    - Método `ejecutar(comando: ConsultarMonitoreoPracticasComando, contexto: Optional[ContextoUsuario] = None) -> TableroMonitoreoPracticasRespuestaDTO` (y `__call__`):
      1. **Verificación de rol exclusivo `Coordinador de prácticas` (*deny-by-default*, ADR-004, ADR-005, EAC-03):**
         - Verifica identidad institucional no vacía y rol con `autorizador_rbac.validar_monitoreo_practicas(rol_actor, usuario_id)`.
         - Si falla, registra de inmediato un único `EventoBitacora` de rechazo (`ACCESO_DENEGADO_ROL_NO_AUTORIZADO_MONITOREO`) y propaga `AccesoDenegadoError` con 0 datos expuestos (Escenarios 7 y 8).
      2. **Validación de pertenencia contextual al `programaAcademico` del coordinador (RN-01, ADR-005):**
         - Verifica que `comando.programa_academico_coordinador` no esté vacío.
         - Si `comando.filtro_programa_academico` fue especificado, valida con `autorizador_rbac.validar_pertenencia_programa_coordinador(...)` que coincida con `comando.programa_academico_coordinador`. Si el coordinador intenta consultar o filtrar prácticas de otro programa académico, registra un único `EventoBitacora` (`ACCESO_DENEGADO_PROGRAMA_AJENO_MONITOREO`) y lanza `AccesoDenegadoError` con 0 datos expuestos (Escenario 5).
      3. **Filtrado automático por el `programaAcademico` del coordinador y aplicación de criterios de búsqueda (Escenarios 1, 2, 3, 6, 9 y 10):**
         - Recupera las prácticas de `RepositorioPracticaPort.listar_todas()` y resuelve para cada una su `ReglaPrograma` vinculada (`practica.regla_programa_id`).
         - Selecciona **únicamente** las prácticas cuya `ReglaPrograma` pertenezca al `programaAcademico` del coordinador autenticado (comparación normalizada), omitiendo cualquier práctica de otros programas (Escenario 1).
         - Aplica los filtros opcionales solicitados dentro del programa del coordinador:
           - `filtro_documento_estudiante`: filtra por coincidencia exacta con `practica.estudiante_id` (documento del `Estudiante`, Escenario 2).
           - `filtro_estado_actual`: filtra por coincidencia con `practica.estado_actual.value` (Escenario 3).
           - `filtro_docente_asesor_id`: filtra por coincidencia con `practica.docente_asesor_id` (Escenario 3).
      4. **Construcción de indicadores consolidados en modo solo lectura (ADR-007, ADR-008, ADR-010):**
         - Calcula `resumen_por_estado` inicializando los 8 estados de `EstadoPractica` en `0` y contabilizando las prácticas resultantes.
         - Construye `carga_docentes` a partir de `RepositorioDocentePort.listar_todos()` (o filtrado al `filtro_docente_asesor_id` cuando se especifica), proyectando `cupo_maximo_practicas`, `practicas_activas` y `cupos_disponibles`.
         - Construye cada `ItemPracticaMonitoreoDTO` calculando el porcentaje de avance respecto a las `horasRequeridas` inmutables de la versión de `ReglaPrograma` vinculada a cada práctica (**EAC-01**, Escenario 9), junto con los datos de `EvaluacionDesempeno` y `ActaFinal`.
      5. **Registro en bitácora Append-Only (ADR-006):**
         - Registra un único `EventoBitacora` inmutable con acción `"CONSULTA_MONITOREO_PRACTICAS"`, `actor_identificador`, `rol_actor`, `ip_origen` y `entidad_afectada=f"ProgramaAcademico:{programa_academico}"`.
      6. **Retorno:**
         - Retorna `TableroMonitoreoPracticasRespuestaDTO` sin alterar ninguna entidad del dominio.
    - Método `consultar_detalle_practica(comando: ConsultarDetallePracticaMonitoreoComando, contexto: Optional[ContextoUsuario] = None) -> DetallePracticaMonitoreoRespuestaDTO`:
      1. Verifica identidad y rol exclusivo `Coordinador de prácticas` con `validar_monitoreo_practicas`. Si falla, registra un único `EventoBitacora` (`ACCESO_DENEGADO_ROL_NO_AUTORIZADO_MONITOREO`) y lanza `AccesoDenegadoError` con 0 datos expuestos (Escenarios 7 y 8).
      2. Busca la práctica en `RepositorioPracticaPort.buscar_por_id(comando.practica_id)`. Si no existe, lanza `PracticaNoEncontradaError`.
      3. Recupera la `ReglaPrograma` vinculada a la práctica y valida con `validar_pertenencia_programa_coordinador` que su `programa_academico` coincida con `comando.programa_academico_coordinador`. Si la práctica pertenece a otro programa académico, registra un único `EventoBitacora` (`ACCESO_DENEGADO_PROGRAMA_AJENO_MONITOREO`) y lanza `AccesoDenegadoError` con 0 datos expuestos (Escenario 5).
      4. Recopila en modo solo lectura la trazabilidad completa de la práctica (`DocenteAsesor`, `RegistroHoras`, `EvaluacionDesempeno`, `ActaFinal` y último `IntentoValidacion`), registra un único `EventoBitacora` (`"CONSULTA_DETALLE_PRACTICA_MONITOREO"`) con `entidad_afectada=f"Practica:{practica.id}"` y retorna `DetallePracticaMonitoreoRespuestaDTO` (Escenario 4).

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Existente)*:
  - `InMemoryRepositorioPractica.listar_todas()` ya retorna la lista de prácticas en memoria sin bloqueos y manteniendo el orden de inserción determinista.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `MonitorearPracticasCasoUso`, `ConsultarMonitoreoPracticasComando`, `ConsultarDetallePracticaMonitoreoComando`, `TableroMonitoreoPracticasRespuestaDTO` y `DetallePracticaMonitoreoRespuestaDTO`.
  - Agregar el atributo `caso_uso_monitorear_practicas: MonitorearPracticasCasoUso` a `SistemaPracticasEmpresariales`.
  - Instanciar `MonitorearPracticasCasoUso` en `inicializar_sistema()` inyectando `repo_practica`, `repo_regla`, `repo_docente`, `repo_registro_horas`, `repo_evaluacion`, `repo_acta` y `autorizador_rbac`.
  - Agregar en `main()` la demostración CLI de `CU-13`.

---

## Flujo

Secuencia operativa para monitorear el estado general de prácticas (CU-13):

1. **Autenticación y Autorización RBAC (*deny-by-default*, ADR-004, ADR-005):**
   - El caso de uso construye el `ContextoUsuario` y ejecuta `autorizador_rbac.validar_monitoreo_practicas(rol_actor, usuario_id)`.
   - Solo se admite el rol `Coordinador de prácticas` (`Coordinador` / `CoordinadorPracticas`). Si un `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa` o solicitud sin sesión válida intenta ejecutar `CU-13`, se inserta de inmediato un único `EventoBitacora` de rechazo en `< 1 minuto` y se lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenarios 7 y 8, **EAC-03**).
2. **Validación de pertenencia contextual al programa académico del coordinador (RN-01, ADR-005):**
   - El sistema verifica el `programaAcademico` al que pertenece el coordinador autenticado.
   - Si en la consulta del tablero se solicita filtrar un programa distinto al del coordinador, o si en la consulta de detalle de una práctica la `ReglaPrograma` vinculada pertenece a otro `programaAcademico`, `autorizador_rbac.validar_pertenencia_programa_coordinador` bloquea la operación, registra un único `EventoBitacora` de rechazo y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenario 5, **EAC-03**).
3. **Recuperación y filtrado de prácticas en modo solo lectura (ADR-007, ADR-008, ADR-010):**
   - Se recuperan las prácticas registradas y se seleccionan exclusivamente aquellas cuya `ReglaPrograma` vinculada (`practica.regla_programa_id`) pertenece al `programaAcademico` del coordinador autenticado (Escenario 1).
   - Si el coordinador especificó criterios de filtrado (`filtro_documento_estudiante` por documento del `Estudiante`, `filtro_estado_actual` o `filtro_docente_asesor_id`), se aplican sobre el subconjunto del programa académico (Escenarios 2, 3 y 6).
   - Para cada práctica se calcula su progreso frente a las `horasRequeridas` inmutables de su versión específica de `ReglaPrograma` (**EAC-01**, Escenario 9) y se consolidan su `DocenteAsesor`, `RegistroHoras` pendientes, `EvaluacionDesempeno` y estado de firmas del `ActaFinal`.
   - Se contabilizan los totales por cada uno de los 8 estados de `EstadoPractica` y la disponibilidad de cupo de los registros de `DocenteAsesor` (**RT-01**, Escenarios 1 y 10).
4. **Registro en bitácora Append-Only (ADR-006):**
   - Se registra un único `EventoBitacora` inmutable con la acción `"CONSULTA_MONITOREO_PRACTICAS"` (o `"CONSULTA_DETALLE_PRACTICA_MONITOREO"`), identificador del coordinador, rol `"Coordinador de prácticas"`, IP de origen, fecha y hora.
5. **Entrega de respuesta:**
   - Se retorna el DTO inmutable `TableroMonitoreoPracticasRespuestaDTO` (o `DetallePracticaMonitoreoRespuestaDTO`) sin modificar ninguna entidad del dominio.

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `Practica`: agregado raíz monitoreado; provee `id`, `estudiante_id` (documento del `Estudiante`), `regla_programa_id`, `estadoActual` (`EstadoPractica`), `fechaPostulacion`, `horasAcumuladasAprobadas`, `fechaInicio`, `fechaFin`, `motivo_rechazo`, `docente_asesor_id` y `supervisor_empresa_id` (**ADR-010**).
- `ReglaPrograma`: configuración versionada vinculada a cada práctica al iniciar; provee el `programaAcademico` (utilizado para restringir el monitoreo al programa del coordinador autenticado), la `version` y las `horasRequeridas` inmutables frente a nuevas versiones normativas (**ADR-007**, **EAC-01**).
- `Estudiante`: estudiante titular identificado por su documento en cada práctica monitoreada y criterio principal de búsqueda en el tablero (**RN-01**, Escenario 2).
- `DocenteAsesor`: tutores académicos cuya carga (`cupoMaximoPracticas`, `practicasActivas` y cupos disponibles) y asignación por práctica se supervisan en el tablero (**RT-01**, Escenarios 1, 3 y 10).
- `RegistroHoras`: reportes semanales asociados a cada práctica para contabilizar las horas en estado `Pendiente` de validación.
- `EvaluacionDesempeno`: calificación cuantitativa y fecha de evaluación registradas por el supervisor externo sobre cada práctica evaluada o completada.
- `ActaFinal`: documento oficial de cierre cuyo número de acta, hash SHA-256 y estado de firmas electrónicas (`aprobadaPorDocente`, `aprobadaPorCoordinador`) se exponen en el monitoreo (**ADR-008**, **OB-05**).
- `IntentoValidacion`: registro de validación frente al SIA consultado al inspeccionar el detalle de una práctica en el monitoreo (Escenario 4).
- `EventoBitacora`: registro inmutable *Append-Only* sellado con SHA-256 generado en cada consulta del monitoreo y en cada intento de acceso denegado (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Modificación de estados de las prácticas, aprobación o rechazo de postulaciones (`CU-02`), asignación de docentes asesores (`CU-03`) o firma electrónica de actas (`CU-10`): el caso de uso `CU-13` es estrictamente de solo lectura.
- Consulta del estado del trámite en autoservicio por parte del `Estudiante` titular (cubierto exclusivamente en `CU-11`).
- Revisión de avances de horas por parte del `DocenteAsesor` asignado (cubierto exclusivamente en `CU-06`).
- Exportación de consolidados históricos de auditoría para acreditación académica (cubierto en `CU-14`).

---

## Decisiones pendientes

Ninguna. Las aclaraciones de negocio fueron resueltas e incorporadas en `spec.md` (restricción automática del tablero de monitoreo exclusivamente a las prácticas del `programaAcademico` al que pertenece el coordinador autenticado y filtrado por el `documento` del `Estudiante`), quedando íntegramente respaldadas por los **ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008 y ADR-010**.
