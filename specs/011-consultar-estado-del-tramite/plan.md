# Plan: 011 Consultar estado del trámite

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`, con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de `dominio/` provee las entidades `Practica` (con su máquina de estados `EstadoPractica`), `ReglaPrograma`, `DocenteAsesor`, `RegistroHoras`, `EvaluacionDesempeno`, `ActaFinal`, `IntentoValidacion` y `EventoBitacora` sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de `aplicacion/` define el caso de uso `ConsultarEstadoTramiteCasoUso` (ubicado dentro del `Módulo Postulaciones` conforme a `docs/vistas/03-desarrollo.md` y `docs/diagramas/03-desarrollo.puml`), sus DTOs inmutables de entrada y salida, la política de autorización exclusiva para el rol `Estudiante` en `AutorizadorRBAC` y la extensión del puerto `RepositorioPracticaPort` para recuperar la práctica activa o más reciente de un estudiante.
  - La capa de `infraestructura/` extiende `InMemoryRepositorioPractica` para consultar la práctica activa o más reciente de un estudiante.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - Consultas de solo lectura sobre los repositorios en memoria (`InMemoryRepositorioPractica`, `InMemoryRepositorioReglaPrograma`, `InMemoryRepositorioDocente`, `InMemoryRepositorioRegistroHoras`, `InMemoryRepositorioEvaluacionDesempeno`, `InMemoryRepositorioActaFinal`), garantizando lecturas consistentes y sin bloqueos ni fugas de información bajo concurrencia de 500 estudiantes simultáneos (**RT-01**, **OB-04**).
- **ADR-004 (Esquema de autenticación híbrida):**
  - El `Estudiante` titular es un actor interno autenticado mediante el sistema institucional (`SSO Institucional` / `ContextoUsuario`). Toda solicitud sin identidad institucional válida es rechazada de inmediato con 0 datos expuestos y registro en bitácora (**EAC-03**).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/` aplica la política centralizada *deny-by-default*.
  - La operación `consultar_estado_tramite` (`CU-11`) está autorizada **exclusivamente** para el rol `Estudiante` (`RolUsuario.ESTUDIANTE`). Cualquier intento de invocación por roles distintos (`DocenteAsesor`, `Coordinador de prácticas`, `SupervisorEmpresa` o usuarios sin sesión válida) es denegado de inmediato con 0 datos expuestos y registro en bitácora (**RN-03**, **EAC-03**, Escenarios 10 y 11).
  - Validación estricta de pertenencia contextual de datos (*Context-Based Access Control*, **RN-01**): el `Estudiante` autenticado únicamente puede consultar el estado del trámite de su propia `Practica` (`practica.estudiante_id == contexto.usuario_id`). Si intenta consultar una práctica ajena, se deniega la operación con 0 datos expuestos y se registra el rechazo en bitácora (Escenario 9).
  - Protección contextual del detalle de la evaluación de desempeño: mientras la `Practica` se encuentre en estado `Evaluada` (y el `ActaFinal` aún no haya alcanzado el estado `Completada`), el estudiante solo visualiza que la `EvaluacionDesempeno` ya fue realizada (`evaluacion_realizada = True` y `fecha_evaluacion`), manteniendo ocultos `calificacionCuantitativa`, `respuestasRubrica` y `observaciones` hasta que el `ActaFinal` esté en firme y la práctica en estado `Completada` (Escenarios 4 y 5).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Toda consulta exitosa del estado del trámite sobre una práctica y todo intento de acceso rechazado (por rol no autorizado o por intento de consulta de práctica ajena) registra un único `EventoBitacora` inmutable sellado con `huellaDigital` SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` en menos de 1 minuto (**EAC-03**).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - El cálculo de `horasRequeridas`, `horasRestantes` y `porcentajeAvance` en la vista del estado del trámite se realiza estrictamente contra la versión de `ReglaPrograma` vinculada a la `Practica` al momento de su postulación (`practica.regla_programa_id`), asegurando un 0% de alteración ante nuevas versiones publicadas posteriormente para el mismo programa académico (**EAC-01**, Escenario 12).
- **ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico):**
  - Cuando la práctica cuenta con un `ActaFinal`, el estado del trámite expone el estado de sus firmas electrónicas (`aprobadaPorDocente`, `aprobadaPorCoordinador`), y una vez la práctica alcanza el estado `Completada`, expone los metadatos oficiales del documento (`numeroActa`, `fechaEmision`, `rutaArchivoPdf` y `hashIntegridadSha256`) para su referencia o descarga por el estudiante (**OB-05**, Escenarios 4 y 5).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - El caso de uso es estrictamente de solo lectura: proyecta un rastreador (*tracker*) de progreso basado en los nodos formales de `EstadoPractica` (`PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`, `Rechazada`), indicando la etapa actual, los hitos completados y el siguiente paso esperado en el ciclo de vida sin alterar el estado de la entidad `Practica` (**RN-02**, **OB-04**).
  - Cuando el estudiante posee múltiples prácticas registradas (por ejemplo, una postulación previa `Rechazada` y una nueva postulación activa), la consulta selecciona automáticamente la práctica activa en curso o, en su defecto, la más reciente por `fechaPostulacion` (Escenario 7).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/practica.py` *(Existente)*:
  - Entidad raíz `Practica` y enumeración `EstadoPractica` (`PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`, `Rechazada`), con propiedades `id`, `estudiante_id`, `regla_programa_id`, `estado_actual`, `fecha_postulacion`, `horas_acumuladas_aprobadas`, `fecha_inicio`, `fecha_fin`, `motivo_rechazo`, `docente_asesor_id`, `supervisor_empresa_id` y método `es_activa()`.
- `dominio/modelos/regla_programa.py` *(Existente)*:
  - Entidad `ReglaPrograma` con propiedades `id`, `programa_academico`, `version` y `horas_requeridas`.
- `dominio/modelos/docente_asesor.py` *(Existente)*:
  - Entidad `DocenteAsesor` con propiedades `id`, `nombre_completo` y `correo_institucional`.
- `dominio/modelos/registro_horas.py` *(Existente)*:
  - Entidad `RegistroHoras` y enumeración `EstadoValidacionHoras` (`Pendiente`, `Aprobado`, `Rechazado`).
- `dominio/modelos/evaluacion_desempeno.py` *(Existente)*:
  - Entidad `EvaluacionDesempeno` con propiedades `id`, `calificacion_cuantitativa`, `es_aprobatoria`, `observaciones`, `respuestas_rubrica` y `fecha_evaluacion`.
- `dominio/modelos/acta_final.py` *(Existente)*:
  - Entidad `ActaFinal` con propiedades `id`, `numero_acta`, `fecha_emision`, `ruta_archivo_pdf`, `hash_integridad_sha256`, `aprobada_por_docente`, `aprobada_por_coordinador` y `esta_en_firme`.
- `dominio/modelos/intento_validacion.py` *(Existente)*:
  - Entidad `IntentoValidacion` con `resultado_sia` y `detalle_estado` para exponer la causal académica en caso de rechazo en verificación de requisitos (Escenario 6).
- `dominio/modelos/evento_bitacora.py` *(Existente)*:
  - Entidad inmutable `EventoBitacora` con sellado SHA-256 para registrar la auditoría de cada consulta de estado o intento de acceso denegado.
- `dominio/errores.py` *(Existente)*:
  - Uso de `PracticaNoEncontradaError` cuando el estudiante no cuenta con ninguna postulación o práctica registrada en el sistema (Escenario 8) o cuando el `practica_id` consultado no existe.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/estado_tramite_dto.py` *(Nuevo)*:
  - `ConsultarEstadoTramiteComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `actor_id: str`
    - `rol_actor: str`
    - `estudiante_id: Optional[str] = None` (si se omite, se asume `actor_id`)
    - `practica_id: Optional[str] = None` (si se omite, se selecciona la práctica activa o más reciente del estudiante titular)
    - `ip_origen: str = "127.0.0.1"`
  - `ResumenEvaluacionTramiteDTO`: DTO inmutable con el estado de la evaluación de desempeño adaptado a la etapa de la práctica (Escenarios 4 y 5):
    - `evaluacion_realizada: bool`
    - `fecha_evaluacion: Optional[datetime] = None`
    - `calificacion_visible: bool = False`
    - `calificacion_cuantitativa: Optional[float] = None` (solo presente cuando `estado_actual == "Completada"`)
    - `es_aprobatoria: Optional[bool] = None` (solo presente cuando `estado_actual == "Completada"`)
    - `observaciones: Optional[str] = None` (solo presente cuando `estado_actual == "Completada"`)
    - `respuestas_rubrica: Optional[dict[str, float]] = None` (solo presente cuando `estado_actual == "Completada"`)
  - `ResumenActaTramiteDTO`: DTO inmutable con el estado de firmas y metadatos del `ActaFinal` (Escenarios 4 y 5):
    - `acta_generada: bool`
    - `aprobada_por_docente: bool = False`
    - `aprobada_por_coordinador: bool = False`
    - `acta_en_firme: bool = False`
    - `descarga_habilitada: bool = False`
    - `numero_acta: Optional[str] = None` (visible cuando `acta_generada == True`, descarga habilitada en `"Completada"`)
    - `fecha_emision: Optional[datetime] = None`
    - `ruta_archivo_pdf: Optional[str] = None` (expuesto para descarga cuando `estado_actual == "Completada"`)
    - `hash_integridad_sha256: Optional[str] = None` (expuesto cuando `estado_actual == "Completada"`)
  - `EstadoTramitePracticaRespuestaDTO`: DTO inmutable de salida con la proyección completa del estado del trámite en autoservicio:
    - `practica_id: str`
    - `estudiante_id: str`
    - `estado_actual: str`
    - `fecha_postulacion: datetime`
    - `fecha_inicio: Optional[datetime]`
    - `fecha_fin: Optional[datetime]`
    - `regla_programa_id: str`
    - `version_regla: str`
    - `horas_requeridas: int`
    - `horas_acumuladas_aprobadas: int`
    - `horas_pendientes_validacion: int`
    - `horas_restantes: int`
    - `porcentaje_avance_horas: float`
    - `cantidad_reportes_pendientes: int`
    - `requisito_horas_cumplido: bool`
    - `docente_asesor_id: Optional[str]`
    - `nombre_docente_asesor: Optional[str]`
    - `correo_docente_asesor: Optional[str]`
    - `supervisor_empresa_id: Optional[str]`
    - `motivo_rechazo: Optional[str]`
    - `evaluacion: ResumenEvaluacionTramiteDTO`
    - `acta_final: ResumenActaTramiteDTO`
    - `siguiente_paso: str`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_practica.py` *(Modificar)*:
  - Extender `RepositorioPracticaPort` con el método:
    - `buscar_mas_reciente_o_activa_por_estudiante(estudiante_id: str) -> Optional[Practica]`: retorna la práctica activa en curso del estudiante (`es_activa() == True`) o, si no tiene una activa en curso, la práctica más reciente según `fecha_postulacion` (y orden de inserción como desempate determinista) (Escenario 7).
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Agregar en `_MATRIZ_PERMISOS`:
    - `"consultar_estado_tramite": {RolUsuario.ESTUDIANTE.value}`
  - Agregar método `validar_consulta_estado_tramite(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "consultar_estado_tramite") -> None`:
    - Verifica bajo política *deny-by-default* que el actor tenga **exclusivamente** el rol `Estudiante` (`RolUsuario.ESTUDIANTE.value`). Si el actor tiene rol `DocenteAsesor`, `Coordinador de prácticas`, `SupervisorEmpresa` o vacío, lanza `AccesoDenegadoError` (Escenarios 10 y 11).
  - Reutilizar `validar_pertenencia_estudiante(contexto: ContextoUsuario, estudiante: Union[Estudiante, str], operacion: Optional[str] = None) -> None` para asegurar que el estudiante solo consulte su propia práctica (Escenario 9).
- `aplicacion/casos_uso/consultar_estado_tramite.py` *(Nuevo)*:
  - Clase `ConsultarEstadoTramiteCasoUso` (dentro del `Módulo Postulaciones` según `docs/vistas/03-desarrollo.md`):
    - Inyecta `RepositorioPracticaPort`, `RepositorioReglaProgramaPort`, `RepositorioDocentePort` (opcional), `RepositorioRegistroHorasPort` (opcional), `RepositorioEvaluacionDesempenoPort` (opcional), `RepositorioActaFinalPort` (opcional) y `AutorizadorRBAC`.
    - Método `ejecutar(comando: ConsultarEstadoTramiteComando) -> EstadoTramitePracticaRespuestaDTO` (y `__call__`):
      1. **Verificación de rol exclusivo `Estudiante` (*deny-by-default*, ADR-005, EAC-03):**
         - Construye el `ContextoUsuario` y valida la operación `consultar_estado_tramite` en `AutorizadorRBAC`.
         - Si el rol no es `Estudiante` (ej. `DocenteAsesor`, `CoordinadorPracticas`, `SupervisorEmpresa`), registra de inmediato un único `EventoBitacora` de rechazo (`ACCESO_DENEGADO_ROL_NO_AUTORIZADO_ESTADO_TRAMITE`) y propaga `AccesoDenegadoError` con 0 datos expuestos (Escenarios 10 y 11).
      2. **Validación de pertenencia contextual del estudiante consultado y resolución de la práctica (RN-01, ADR-005):**
         - Si `comando.practica_id` fue especificado:
           - Busca la práctica con `RepositorioPracticaPort.buscar_por_id(comando.practica_id)`. Si no existe, lanza `PracticaNoEncontradaError`.
           - Verifica con `autorizador_rbac.validar_pertenencia_estudiante(contexto, practica.estudiante_id, operacion="consultar_estado_tramite")` que la práctica pertenezca al estudiante autenticado. Si pertenece a otro estudiante, registra un único `EventoBitacora` (`ACCESO_DENEGADO_RECURSO_AJENO_ESTADO_TRAMITE`) y lanza `AccesoDenegadoError` con 0 datos expuestos (Escenario 9).
         - Si `comando.practica_id` no fue especificado:
           - Si `comando.estudiante_id` fue provisto y difiere de `contexto.usuario_id`, `validar_pertenencia_estudiante` falla, registra `EventoBitacora` de acceso a recurso ajeno y lanza `AccesoDenegadoError` con 0 datos expuestos (Escenario 9).
           - Obtiene la práctica activa o más reciente del estudiante titular mediante `RepositorioPracticaPort.buscar_mas_reciente_o_activa_por_estudiante(contexto.usuario_id)`.
           - Si el estudiante no tiene ninguna práctica registrada, lanza `PracticaNoEncontradaError` informando que aún no cuenta con ninguna postulación o práctica registrada en el sistema (Escenarios 7 y 8).
      3. **Proyección de datos de solo lectura (ADR-007, ADR-008, ADR-010):**
         - Recupera la `ReglaPrograma` vinculada (`practica.regla_programa_id`) para obtener `version` y `horas_requeridas` inmutables (Escenario 12, **EAC-01**).
         - Si `practica.docente_asesor_id` existe y se dispone de `RepositorioDocentePort`, recupera nombre y correo institucional del `DocenteAsesor` asignado (Escenario 2).
         - Si se dispone de `RepositorioRegistroHorasPort`, contabiliza las horas y cantidad de reportes en estado `Pendiente` (Escenario 3).
         - Si el estado es `Rechazada` y `practica.motivo_rechazo` es nulo, consulta el último `IntentoValidacion` en `RepositorioPracticaPort.buscar_intentos_por_practica(practica.id)` para obtener la causal académica del rechazo (Escenario 6).
         - Si se dispone de `RepositorioEvaluacionDesempenoPort`, consulta si existe `EvaluacionDesempeno` para la práctica:
           - Si la práctica está en estado distinto a `Completada` (ej. `Evaluada`), construye `ResumenEvaluacionTramiteDTO` con `evaluacion_realizada=True`, `fecha_evaluacion=evaluacion.fecha_evaluacion`, `calificacion_visible=False` y oculta (`None`) `calificacion_cuantitativa`, `es_aprobatoria`, `observaciones` y `respuestas_rubrica` (Escenario 4).
           - Si la práctica está en estado `Completada`, construye `ResumenEvaluacionTramiteDTO` con `evaluacion_realizada=True`, `calificacion_visible=True` y expone `calificacion_cuantitativa`, `es_aprobatoria`, `observaciones` y `respuestas_rubrica` (Escenario 5).
         - Si se dispone de `RepositorioActaFinalPort`, consulta si existe `ActaFinal` para la práctica:
           - Si la práctica está en estado `Evaluada`, expone `acta_generada=True`, `aprobada_por_docente`, `aprobada_por_coordinador`, `acta_en_firme=False` y `descarga_habilitada=False` (sin exponer `ruta_archivo_pdf` ni `hash_integridad_sha256` como descargables aún) (Escenario 4).
           - Si la práctica está en estado `Completada` y el acta está en firme, expone `descarga_habilitada=True`, `numero_acta`, `fecha_emision`, `ruta_archivo_pdf` y `hash_integridad_sha256` (Escenario 5).
         - Determina la descripción clara del `siguiente_paso` según el `estadoActual` en la máquina de estados finitos (**ADR-010**).
      4. **Registro en bitácora Append-Only (ADR-006):**
         - Registra un único `EventoBitacora` inmutable con acción `"CONSULTA_ESTADO_TRAMITE"`, `actor_identificador=contexto.usuario_id`, `rol_actor=contexto.rol`, `ip_origen=contexto.ip_origen` y `entidad_afectada=f"Practica:{practica.id}"`.
      5. **Retorno:**
         - Retorna `EstadoTramitePracticaRespuestaDTO` sin realizar ninguna mutación sobre `Practica` ni sus entidades asociadas.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - En `InMemoryRepositorioPractica`:
    - Implementar `buscar_mas_reciente_o_activa_por_estudiante(estudiante_id: str) -> Optional[Practica]`:
      - Filtra todas las prácticas cuyo `estudiante_id` coincida con el solicitado.
      - Si no hay ninguna, retorna `None`.
      - Si existe una práctica activa en curso (`practica.es_activa()`), la prioriza; si existen varias prácticas, retorna la más reciente según `fecha_postulacion` (preservando el último registro insertado en caso de empate de timestamp) (Escenario 7).

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `ConsultarEstadoTramiteCasoUso`, `ConsultarEstadoTramiteComando` y `EstadoTramitePracticaRespuestaDTO`.
  - Agregar el atributo `caso_uso_consultar_estado_tramite: ConsultarEstadoTramiteCasoUso` a `SistemaPracticasEmpresariales`.
  - Instanciar `ConsultarEstadoTramiteCasoUso` en `inicializar_sistema()` inyectando `repo_practica`, `repo_regla`, `repo_docente`, `repo_registro_horas`, `repo_evaluacion`, `repo_acta` y `autorizador_rbac`.
  - Agregar en `main()` la demostración CLI de `CU-11`.

---

## Flujo

Secuencia operativa para la consulta del estado del trámite en autoservicio (CU-11):

1. **Autenticación y Autorización RBAC (*deny-by-default*, ADR-004, ADR-005):**
   - El caso de uso construye el `ContextoUsuario` y ejecuta `autorizador_rbac.validar_consulta_estado_tramite(rol_actor, usuario_id)`.
   - Solo se admite el rol `Estudiante`. Si un `DocenteAsesor`, `Coordinador de prácticas`, `SupervisorEmpresa` o solicitud sin rol válido intenta ejecutar `CU-11`, se inserta de inmediato un único `EventoBitacora` de rechazo en `< 1 minuto` y se lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenarios 10 y 11, **EAC-03**).
2. **Validación de pertenencia contextual y selección de la práctica (RN-01, ADR-005, ADR-010):**
   - Si el comando especifica `practica_id`, se busca la práctica en `RepositorioPracticaPort.buscar_por_id(practica_id)` (lanzando `PracticaNoEncontradaError` si no existe) y se verifica que `practica.estudiante_id == contexto.usuario_id`.
   - Si el comando no especifica `practica_id`, se valida que `estudiante_id` (si fue provisto) coincida con `contexto.usuario_id` y se invoca `RepositorioPracticaPort.buscar_mas_reciente_o_activa_por_estudiante(contexto.usuario_id)`, que prioriza la práctica activa en curso sobre postulaciones previas rechazadas o históricas (Escenario 7). Si el estudiante no posee ninguna práctica registrada, se lanza `PracticaNoEncontradaError` (Escenario 8).
   - Cualquier intento de un estudiante de consultar la práctica de otro estudiante es bloqueado, registrando un único `EventoBitacora` de acceso a recurso ajeno y lanzando `AccesoDenegadoError` con `0 datos expuestos` (Escenario 9, **EAC-03**).
3. **Recopilación de información del ciclo de vida en modo solo lectura (ADR-007, ADR-008, ADR-010):**
   - Se consulta la `ReglaPrograma` vinculada a la práctica al momento de su postulación (`practica.regla_programa_id`) para calcular el progreso frente a sus `horasRequeridas` inmutables (Escenario 12, **EAC-01**).
   - Se consultan los datos institucionales del `DocenteAsesor` asignado (si ya fue asignado en `CU-03`), los reportes de `RegistroHoras` pendientes de validación, la causal de rechazo (si `estadoActual == "Rechazada"`), la `EvaluacionDesempeno` y el `ActaFinal`.
   - **Regla de visibilidad de la evaluación de desempeño (Escenarios 4 y 5):**
     - Si `estadoActual != "Completada"`, solo se informa si la evaluación ya fue realizada (`evaluacion_realizada` y `fecha_evaluacion`), ocultando la calificación cuantitativa, rúbrica y observaciones.
     - Si `estadoActual == "Completada"`, se exponen la calificación cuantitativa, el concepto y las observaciones junto con los datos de descarga e integridad SHA-256 del `ActaFinal`.
4. **Registro en bitácora Append-Only (ADR-006):**
   - Se registra un único `EventoBitacora` inmutable con la acción `"CONSULTA_ESTADO_TRAMITE"`, identificador del estudiante, rol `"Estudiante"`, IP de origen, fecha y hora.
5. **Entrega de respuesta:**
   - Se retorna el DTO inmutable `EstadoTramitePracticaRespuestaDTO` sin alterar el estado de ninguna entidad del dominio.

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `Practica`: agregado raíz consultado; provee `id`, `estudiante_id`, `regla_programa_id`, `estadoActual` (`EstadoPractica`), `fechaPostulacion`, `horasAcumuladasAprobadas`, `fechaInicio`, `fechaFin`, `motivo_rechazo`, `docente_asesor_id` y `supervisor_empresa_id` (**ADR-010**).
- `Estudiante`: actor titular autenticado que consulta en autoservicio su trámite más reciente o activo (**RN-01**, **OB-04**).
- `ReglaPrograma`: configuración versionada vinculada a la práctica al iniciar; provee `version` y `horasRequeridas` inmutables frente a nuevas versiones normativas (**ADR-007**, **EAC-01**).
- `DocenteAsesor`: tutor académico asignado a la práctica; provee `nombreCompleto` y `correoInstitucional`.
- `RegistroHoras`: reportes semanales asociados a la práctica para informar cuántas horas se encuentran en estado `Pendiente` de validación por el `SupervisorEmpresa`.
- `EvaluacionDesempeno`: evaluación emitida por el supervisor externo; antes de `Completada` solo se informa su existencia y `fechaEvaluacion`, y en estado `Completada` se exponen `calificacionCuantitativa`, `observaciones` y `respuestasRubrica`.
- `ActaFinal`: documento oficial de cierre; en estado `Evaluada` expone el avance de firmas (`aprobadaPorDocente`, `aprobadaPorCoordinador`) y en estado `Completada` habilita la referencia al PDF (`numeroActa`, `fechaEmision`, `rutaArchivoPdf`, `hashIntegridadSha256`) (**ADR-008**).
- `IntentoValidacion`: registro de validación frente al SIA utilizado para mostrar el detalle de incumplimiento académico cuando la práctica fue rechazada en la postulación.
- `EventoBitacora`: registro inmutable *Append-Only* sellado con SHA-256 generado en cada consulta autorizada y en cada intento de acceso denegado (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Modificación de datos de la postulación, cambio de estado de la práctica o registro de horas semanales (el caso de uso `CU-11` es estrictamente de solo lectura).
- Revisión detallada y consolidada de avances de horas por parte del `DocenteAsesor` (cubierto en `CU-06`).
- Tablero de monitoreo general del estado de todas las prácticas para el `Coordinador de prácticas` (cubierto en `CU-13`).
- Generación del archivo PDF del acta final (`CU-09`) o registro de firmas electrónicas sobre el acta (`CU-10`).

---

## Decisiones pendientes

Ninguna. Todas las aclaraciones de negocio fueron resueltas e incorporadas en `spec.md` (registro de un único `EventoBitacora` por consulta o rechazo, visibilidad únicamente de que la evaluación fue realizada hasta que la práctica esté en estado `Completada`, selección automática de la práctica activa o más reciente del estudiante, y uso exclusivo para el rol `Estudiante`), quedando íntegramente respaldadas por los **ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008 y ADR-010**.
