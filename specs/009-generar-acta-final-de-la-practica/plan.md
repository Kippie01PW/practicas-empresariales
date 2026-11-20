# Plan: 009 Generar acta final de la práctica

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Organización estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`, con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de dominio incorpora la entidad `ActaFinal` y las excepciones de negocio para la generación del acta (`EstadoPracticaInvalidoParaActaError`, `HorasInsuficientesParaActaError`, `EvaluacionDesempenoFaltanteParaActaError`, `ActaFinalYaGeneradaError`, `ErrorAlmacenamientoActaPdfError`), y extiende la entidad raíz `Practica` con la validación formal `validar_requisitos_generacion_acta(...)`, sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de aplicación define el caso de uso `GenerarActaFinalCasoUso` (ubicado en el `Módulo Actas` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada y salida (`GenerarActaFinalComando`, `ActaFinalRespuestaDTO`) y los puertos de salida `RepositorioActaFinalPort` y `ServicioGeneradorActaPdfPort`.
  - La capa de infraestructura provee los adaptadores `InMemoryRepositorioActaFinal` y `AdaptadorPdfYHashSimulado` (correspondiente al componente `Adaptador PDF y Hash` y al contenedor `Repositorio de actas PDF` en `docs/vistas/03-desarrollo.md` y `docs/vistas/02-procesos.md`).
  - Cumple el grafo acíclico de dependencias entre módulos definido en `docs/vistas/03-desarrollo.md` §3:
    $$\text{Módulo Actas} \rightarrow \text{Módulo Seguimiento y Evaluación} \rightarrow \text{Módulo Postulaciones} \rightarrow \text{Módulo Reglas}$$
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - La escritura del archivo binario PDF en el `Repositorio de actas PDF`, el registro de `ActaFinal` en el repositorio transaccional y la inserción de `EventoBitacora` se ejecutan garantizando consistencia atómica y transacción compensatoria ante fallos (**DT-02**, Escenario 10): si ocurre un error al escribir en el repositorio de actas PDF o al guardar el `ActaFinal`, se revierte o elimina cualquier archivo PDF huérfano evitando inconsistencias.
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política centralizada *deny-by-default*.
  - La operación `generar_acta` está permitida exclusivamente para el rol `DocenteAsesor` (`RolUsuario.DOCENTE_ASESOR` / `RolUsuario.DOCENTE`), conforme a `docs/diagramas/secuencias/cu09-generar-acta.puml` (ESC-03), `docs/contexto.md` y la matriz de permisos de `AutorizadorRBAC`. Cualquier intento por otros roles (`Estudiante`, `SupervisorEmpresa`, `CoordinadorPracticas`) es rechazado con registro inmediato en bitácora y `0 datos expuestos` (**RN-03**, Escenarios 8 y 12).
  - Validación de pertenencia contextual de datos (*Context-Based Access Control*, **RN-01**): el `DocenteAsesor` autenticado debe coincidir exactamente con el `docente_asesor_id` asignado a la `Practica` (`autorizador_rbac.validar_pertenencia_docente(...)`). Si intenta generar el acta de una práctica asignada a otro tutor, se rechaza con registro inmediato en bitácora y `0 datos expuestos` (Escenarios 7 y 12).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada generación exitosa de `ActaFinal` inserta atómicamente un `EventoBitacora` inmutable sellado con `hashIntegridadSha256`, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` (**PA-03**, Escenarios 1 y 6).
  - Todo intento de acceso o generación rechazado por rol no autorizado o violación de pertenencia contextual registra de inmediato un `EventoBitacora` en menos de 1 minuto garantizando `0 datos expuestos` (**EAC-03**, Escenarios 7, 8 y 12).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - La verificación de `horasRequeridas` y la selección de `plantillaActa` utilizan estrictamente la versión de `ReglaPrograma` vinculada a la `Practica` al momento de su postulación (`practica.regla_programa_id`), asegurando un `0% de alteración` en las condiciones normativas de prácticas activas y un `0% de alteración` en actas emitidas previamente frente a nuevas versiones publicadas por el Coordinador (**EAC-01**, **OB-05**, Escenario 11).
- **ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico):**
  - El componente `Adaptador PDF y Hash` toma la `plantillaActa` HTML/CSS de la `ReglaPrograma` vinculada, inyecta dinámicamente los datos de la práctica (`Practica`, `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`, `horasAcumuladasAprobadas`, `horasRequeridas`, `EvaluacionDesempeno` incluyendo `calificacionCuantitativa` aprobatoria o reprobatoria y `observaciones`), renderiza el binario PDF y calcula su huella criptográfica `hashIntegridadSha256` (64 caracteres hexadecimales en minúsculas con `hashlib.sha256`).
  - El archivo binario se almacena en el `Repositorio de actas PDF` confirmando su `rutaArchivoPdf`, y la entidad `ActaFinal` persiste el `numeroActa` (con formato consecutivo anual `"ACTA-<AÑO>-<NNNN>"`, ej. `"ACTA-2026-0001"`), `fechaEmision`, `rutaArchivoPdf`, `hashIntegridadSha256`, `aprobadaPorDocente = False` y `aprobadaPorCoordinador = False` (**PA-03**, **OB-01**, **OB-05**, Escenarios 1 y 6).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La entidad `Practica` gobierna estrictamente las precondiciones del ciclo de vida para permitir la generación del `ActaFinal` (**RN-02**):
    1. `practica.estado_actual == EstadoPractica.EVALUADA` (si está en `PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Completada` o `Rechazada`, bloquea la operación con `EstadoPracticaInvalidoParaActaError`, Escenario 2).
    2. Existencia de la `EvaluacionDesempeno` registrada para la práctica (ya sea con calificación aprobatoria `>= 3.0` o reprobatoria `< 3.0` con observaciones justificativas; si no existe, lanza `EvaluacionDesempenoFaltanteParaActaError`, Escenarios 4 y 6).
    3. Cumplimiento total de horas aprobadas: `practica.horas_acumuladas_aprobadas >= regla_programa.horas_requeridas` (si es inferior, lanza `HorasInsuficientesParaActaError` detallando las horas acumuladas, las requeridas y las faltantes, Escenario 3).
    4. Unicidad del acta por práctica (multiplicidad `1` a `0..1` en `docs/diagramas/01-logica.puml`): cada `Practica` puede tener como máximo una única `ActaFinal`; si ya cuenta con un `ActaFinal` generada, lanza `ActaFinalYaGeneradaError` conservando intacto el documento original y su hash SHA-256 (Escenario 5).
  - Al finalizar CU-09, la `Practica` permanece en estado `Evaluada` a la espera de las firmas electrónicas del `DocenteAsesor` y del `Coordinador de prácticas` en CU-10 (momento en el cual transicionará a `Completada`).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/acta_final.py` *(Nuevo)*:
  - Entidad `ActaFinal` conforme al modelo de dominio UML (`docs/diagramas/01-logica.puml` y `docs/vistas/01-logica.md`):
    - Atributos del modelo de dominio:
      - `id: str`
      - `practica_id: str`
      - `numero_acta: str` (formato `"ACTA-<AÑO>-<NNNN>"`, ej. `"ACTA-2026-0001"`)
      - `fecha_emision: datetime`
      - `ruta_archivo_pdf: str`
      - `hash_integridad_sha256: str` (huella criptográfica SHA-256 de 64 caracteres hexadecimales)
      - `aprobada_por_docente: bool` (nace en `False` en CU-09)
      - `aprobada_por_coordinador: bool` (nace en `False` en CU-09)
    - Invariantes de dominio validados en construcción:
      - `practica_id`, `numero_acta` y `ruta_archivo_pdf` no pueden estar vacíos.
      - `hash_integridad_sha256` debe ser una cadena hexadecimal válida de 64 caracteres.
    - Métodos de consulta y apoyo para el flujo de cierre:
      - `esta_completamente_aprobada() -> bool`: retorna `self._aprobada_por_docente and self._aprobada_por_coordinador`.
      - `verificar_integridad_hash(hash_calculado: str) -> bool`: compara en tiempo constante si `hash_calculado` coincide con `self._hash_integridad_sha256` (**ADR-008**).
- `dominio/modelos/practica.py` *(Modificar)*:
  - Agregar método de consulta `puede_generar_acta(horas_requeridas: int, tiene_evaluacion: bool = True, tiene_acta_previa: bool = False) -> bool`.
  - Agregar método de validación de máquina de estados e invariantes de cierre `validar_requisitos_generacion_acta(*, horas_requeridas: int, tiene_evaluacion: bool, tiene_acta_previa: bool = False) -> None`:
    - Si `tiene_acta_previa` es `True`, lanza `ActaFinalYaGeneradaError` (Escenario 5).
    - Si `self._estado_actual != EstadoPractica.EVALUADA`, lanza `EstadoPracticaInvalidoParaActaError` (Escenario 2, **ADR-010**, **RN-02**).
    - Si `not tiene_evaluacion`, lanza `EvaluacionDesempenoFaltanteParaActaError` (Escenario 4).
    - Si `self._horas_acumuladas_aprobadas < horas_requeridas`, lanza `HorasInsuficientesParaActaError` indicando `horas_acumuladas_aprobadas`, `horas_requeridas` y la diferencia `horas_faltantes = horas_requeridas - self._horas_acumuladas_aprobadas` (Escenario 3).
- `dominio/errores.py` *(Modificar)*:
  - Agregar las excepciones de dominio para CU-09:
    - `EstadoPracticaInvalidoParaActaError(TransicionEstadoInvalidaError)`: lanzada cuando se intenta generar el acta de una práctica cuyo `estadoActual` es distinto de `Evaluada` (Escenario 2).
    - `HorasInsuficientesParaActaError(ErrorDominio)`: lanzada cuando `horasAcumuladasAprobadas < horasRequeridas` de la `ReglaPrograma` vinculada, informando horas acumuladas, requeridas y faltantes (Escenario 3).
    - `EvaluacionDesempenoFaltanteParaActaError(ErrorDominio)`: lanzada cuando la práctica carece de una `EvaluacionDesempeno` registrada (Escenario 4).
    - `ActaFinalYaGeneradaError(DecisionPreviaEnFirmeError)`: lanzada cuando la práctica ya tiene asociada un `ActaFinal` emitida previamente, garantizando la relación `1 a 0..1` (Escenario 5).
    - `ErrorAlmacenamientoActaPdfError(ErrorDominio)`: lanzada cuando ocurre un fallo de escritura o persistencia en el `Repositorio de actas PDF` o en el repositorio transaccional para disparar la reversión compensatoria (**DT-02**, Escenario 10).
- `dominio/modelos/__init__.py` *(Modificar)*:
  - Exportar `ActaFinal`.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/acta_final_dto.py` *(Nuevo)*:
  - `DatosRenderizadoActaDTO`: DTO inmutable con los datos consolidados del agregado `Practica` que se inyectan en la plantilla HTML/CSS (`plantillaActa`) de la `ReglaPrograma` vinculada (**ADR-007**, **ADR-008**):
    - `numero_acta: str`
    - `practica_id: str`
    - `estudiante_id: str`
    - `docente_asesor_id: str`
    - `nombre_docente_asesor: str`
    - `supervisor_empresa_id: str`
    - `regla_programa_id: str`
    - `programa_academico: str`
    - `version_regla: str`
    - `plantilla_acta: str`
    - `horas_requeridas: int`
    - `horas_acumuladas_aprobadas: int`
    - `calificacion_cuantitativa: float`
    - `es_aprobatoria: bool`
    - `observaciones_evaluacion: Optional[str]`
    - `respuestas_rubrica: dict[str, float]`
    - `fecha_emision: datetime`
  - `ResultadoRenderizadoPdfDTO`: DTO inmutable retornado por el puerto `ServicioGeneradorActaPdfPort`:
    - `ruta_archivo_pdf: str`
    - `contenido_pdf: bytes`
    - `hash_integridad_sha256: str`
    - `plantilla_utilizada: str`
  - `GenerarActaFinalComando`: DTO inmutable de entrada para CU-09:
    - `practica_id: str`
    - `actor_id: str`
    - `rol_actor: str = "DocenteAsesor"`
    - `ip_origen: str = "127.0.0.1"`
    - `fecha_emision: Optional[datetime] = None`
  - `ActaFinalRespuestaDTO`: DTO inmutable de salida para CU-09:
    - `acta_id: str`
    - `numero_acta: str`
    - `practica_id: str`
    - `estudiante_id: str`
    - `docente_asesor_id: str`
    - `supervisor_empresa_id: Optional[str]`
    - `regla_programa_id: str`
    - `programa_academico: str`
    - `version_regla: str`
    - `plantilla_acta: str`
    - `horas_requeridas: int`
    - `horas_acumuladas_aprobadas: int`
    - `calificacion_cuantitativa: float`
    - `es_aprobatoria: bool`
    - `observaciones_evaluacion: Optional[str]`
    - `ruta_archivo_pdf: str`
    - `hash_integridad_sha256: str`
    - `aprobada_por_docente: bool`
    - `aprobada_por_coordinador: bool`
    - `estado_practica: str`
    - `fecha_emision: datetime`
    - `previsualizacion_disponible: bool`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_acta_final.py` *(Nuevo)*:
  - Protocol `RepositorioActaFinalPort` (`@runtime_checkable`):
    - `guardar(acta: ActaFinal) -> None`
    - `buscar_por_id(acta_id: str) -> Optional[ActaFinal]`
    - `buscar_por_practica(practica_id: str) -> Optional[ActaFinal]`
    - `buscar_por_numero_acta(numero_acta: str) -> Optional[ActaFinal]`
    - `siguiente_numero_acta(anio: int) -> str` (genera el consecutivo anual con formato `"ACTA-<AÑO>-<NNNN>"`, ej. `"ACTA-2026-0001"`)
    - `eliminar_por_id(acta_id: str) -> None` (para compensación transaccional si falla un paso posterior, **DT-02**)
    - `listar_todas() -> list[ActaFinal]`
- `aplicacion/puertos/servicio_generador_acta_pdf.py` *(Nuevo)*:
  - Protocol `ServicioGeneradorActaPdfPort` (`@runtime_checkable`):
    - `generar_y_guardar_acta_pdf(datos: DatosRenderizadoActaDTO) -> ResultadoRenderizadoPdfDTO`
    - `obtener_contenido_pdf(ruta_archivo_pdf: str) -> Optional[bytes]`
    - `verificar_integridad_pdf(ruta_archivo_pdf: str, hash_esperado: str) -> bool`
    - `eliminar_archivo_pdf(ruta_archivo_pdf: str) -> None` (compensación transaccional para evitar archivos PDF huérfanos en caso de fallo al escribir en base de datos, **DT-02**, Escenario 10)
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - La operación `"generar_acta"` ya figura en `_MATRIZ_PERMISOS` restringida a `{RolUsuario.DOCENTE.value, RolUsuario.DOCENTE_ASESOR.value}`.
  - Agregar método `validar_generacion_acta(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "generar_acta") -> None` para validar explícitamente bajo política *deny-by-default* que solo el rol `DocenteAsesor` (o `Docente`) pueda invocar CU-09 (Escenarios 8 y 12).
  - Reutilizar `validar_pertenencia_docente(contexto, practica.docente_asesor_id, operacion="generar_acta")` para garantizar que el docente autenticado sea estrictamente el tutor asignado a la práctica (Escenarios 1, 7 y 12, **RN-01**, **ADR-005**).
- `aplicacion/casos_uso/generar_acta_final.py` *(Nuevo)*:
  - Clase `GenerarActaFinalCasoUso` (`Módulo Actas` en `docs/vistas/03-desarrollo.md`):
    - Inyecta `RepositorioPracticaPort`, `RepositorioReglaProgramaPort`, `RepositorioEvaluacionDesempenoPort`, `RepositorioActaFinalPort`, `ServicioGeneradorActaPdfPort`, `AutorizadorRBAC` y `RepositorioDocentePort` (opcional).
    - Método `ejecutar(comando: GenerarActaFinalComando) -> ActaFinalRespuestaDTO` (y `__call__`):
      1. **Autorización de rol RBAC (*deny-by-default*, ADR-005, RN-03, EAC-03):**
         - Construye `ContextoUsuario` y ejecuta `autorizador_rbac.validar_generacion_acta(comando.rol_actor, comando.actor_id)`.
         - Si un usuario con rol `Estudiante`, `SupervisorEmpresa` o `CoordinadorPracticas` intenta invocar la operación, registra inmediatamente un `EventoBitacora` de acceso denegado en `< 1 minuto` y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenarios 8 y 12).
      2. **Recuperación de la Práctica y validación de pertenencia contextual (RN-01, ADR-005, EAC-03):**
         - Consulta la `Practica` en `RepositorioPracticaPort.buscar_por_id(comando.practica_id)`. Si no existe, lanza `PracticaNoEncontradaError` (Escenario 9).
         - Invoca `autorizador_rbac.validar_pertenencia_docente(contexto, practica.docente_asesor_id, operacion="generar_acta")`. Si la práctica pertenece a otro docente asesor (ej. `"DOC-002"` cuando el actor es `"DOC-001"`), registra inmediatamente un `EventoBitacora` por intento de acceso a recurso ajeno en `< 1 minuto` y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenarios 7 y 12).
      3. **Verificación de unicidad del ActaFinal, estado Evaluada, Evaluación de Desempeño y Horas Requeridas (ADR-007, ADR-010, RN-02, EAC-01):**
         - Consulta `RepositorioActaFinalPort.buscar_por_practica(practica.id)`. Si ya existe un `ActaFinal` para la práctica, lanza `ActaFinalYaGeneradaError` conservando intacta el acta original (Escenario 5).
         - Recupera la `ReglaPrograma` vinculada originalmente a la práctica (`RepositorioReglaProgramaPort.buscar_por_id(practica.regla_programa_id)`), garantizando el uso de `horasRequeridas` y `plantillaActa` de esa versión exacta con `0% de alteración` ante nuevas versiones publicadas después (**ADR-007**, **EAC-01**, Escenario 11).
         - Recupera la `EvaluacionDesempeno` asociada a la práctica (`RepositorioEvaluacionDesempenoPort.buscar_por_practica(practica.id)`).
         - Invoca `practica.validar_requisitos_generacion_acta(horas_requeridas=regla.horas_requeridas, tiene_evaluacion=(evaluacion is not None), tiene_acta_previa=False)`:
           - Si `practica.estado_actual != EstadoPractica.EVALUADA`, lanza `EstadoPracticaInvalidoParaActaError` (Escenario 2).
           - Si `evaluacion is None`, lanza `EvaluacionDesempenoFaltanteParaActaError` (Escenario 4).
           - Si `practica.horas_acumuladas_aprobadas < regla.horas_requeridas`, lanza `HorasInsuficientesParaActaError` (Escenario 3).
         - Si la `EvaluacionDesempeno` tiene una `calificacionCuantitativa` reprobatoria (`< 3.0`) con sus observaciones justificativas, permite la generación e inyecta la nota reprobatoria y las observaciones en la plantilla del acta (Escenario 6).
      4. **Renderizado desde plantilla HTML/CSS a PDF, sellado SHA-256 y persistencia atómica con compensación (ADR-003, ADR-006, ADR-008, DT-02):**
         - Obtiene el `numero_acta` consecutivo anual mediante `repositorio_acta.siguiente_numero_acta(fecha_emision.year)` (ej. `"ACTA-2026-0001"`).
         - Construye `DatosRenderizadoActaDTO` con los datos completos de la práctica, estudiante, tutor, supervisor, regla vinculada, horas acumuladas aprobadas y evaluación de desempeño.
         - Invoca `servicio_pdf.generar_y_guardar_acta_pdf(datos_renderizado)` que renderiza la plantilla HTML/CSS a binario PDF, calcula su `hashIntegridadSha256` y lo guarda en el `Repositorio de actas PDF`.
         - Instancia la entidad `ActaFinal` (`aprobada_por_docente=False`, `aprobada_por_coordinador=False`).
         - En un bloque transaccional protegido (`try / except`):
           - Persiste `ActaFinal` en `RepositorioActaFinalPort.guardar(acta)`.
           - Registra atómicamente el `EventoBitacora` en `RepositorioPracticaPort.guardar_evento_bitacora(...)` incluyendo `hash_integridad_sha256` en la huella y detalle de la acción.
           - Si ocurre cualquier fallo al persistir `ActaFinal` o `EventoBitacora`, ejecuta la compensación eliminando el archivo PDF generado (`servicio_pdf.eliminar_archivo_pdf(resultado_pdf.ruta_archivo_pdf)`) y eliminando cualquier registro parcial de `ActaFinal` para evitar archivos PDF huérfanos o registros inconsistentes (**DT-02**, Escenario 10).
      5. **Retorno:**
         - Mantiene la `Practica` en estado `Evaluada` y retorna `ActaFinalRespuestaDTO` con los datos del acta, su `hashIntegridadSha256` y `previsualizacion_disponible = True` lista para la aprobación electrónica de CU-10 (Escenario 1).

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/adaptador_pdf_hash_simulado.py` *(Nuevo)*:
  - Clase `AdaptadorPdfYHashSimulado(ServicioGeneradorActaPdfPort)` (componente `Adaptador PDF y Hash` de `docs/vistas/03-desarrollo.md` y contenedor `Repositorio de actas PDF` de `docs/vistas/02-procesos.md`):
    - Renderiza dinámicamente la plantilla HTML/CSS especificada en `datos.plantilla_acta` de la `ReglaPrograma` vinculada inyectando todos los campos de la práctica, horas y evaluación de desempeño (aprobatoria o reprobatoria), y empaqueta un binario PDF determinista (`%PDF-1.4 ... %%EOF`).
    - Calcula la huella criptográfica `hashlib.sha256(contenido_pdf).hexdigest()` de 64 caracteres hexadecimales (**ADR-008**).
    - Almacena el archivo binario en el volumen simulado en memoria (`dict[str, bytes]` indexado por `ruta_archivo_pdf`, ej. `"/repositorio_actas/2026/ACTA-2026-0001.pdf"`).
    - Soporta simulación determinista de fallos de I/O (`configurar_fallo_escritura(activar: bool)`) para verificar el Escenario 10 (**DT-02**) y métodos `obtener_contenido_pdf`, `verificar_integridad_pdf` y `eliminar_archivo_pdf`.
- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - Agregar `InMemoryRepositorioActaFinal(RepositorioActaFinalPort)`:
    - Almacena en memoria las instancias de `ActaFinal` indexadas por `id`, por `practica_id` (garantizando la relación `1 a 0..1` entre `Practica` y `ActaFinal`) y por `numero_acta`.
    - Mantiene el contador consecutivo anual para `siguiente_numero_acta(anio: int) -> str` con formato `"ACTA-{anio}-{consecutivo:04d}"` (ej. `"ACTA-2026-0001"`).
    - Soporta simulación determinista de fallo de persistencia (`configurar_fallo_guardado(activar: bool)`) para validar la compensación atómica del Escenario 10 (**DT-02**).

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `GenerarActaFinalCasoUso`, `GenerarActaFinalComando`, `ActaFinalRespuestaDTO`, `InMemoryRepositorioActaFinal` y `AdaptadorPdfYHashSimulado`.
  - Agregar `caso_uso_generar_acta: GenerarActaFinalCasoUso`, `repositorio_acta: InMemoryRepositorioActaFinal` y `servicio_pdf: AdaptadorPdfYHashSimulado` en `SistemaPracticasEmpresariales`.
  - Instanciar e inyectar `InMemoryRepositorioActaFinal`, `AdaptadorPdfYHashSimulado` y `GenerarActaFinalCasoUso` en `inicializar_sistema()`.
  - Incluir la demostración CLI de CU-09 en `main()`.

---

## Flujo

Secuencia alineada con `docs/diagramas/secuencias/cu09-generar-acta.puml` (ESC-03):

1. **Solicitud de generación de acta (`POST /practicas/{id}/acta`):**
   - El `DocenteAsesor` autenticado solicita generar el acta final de la práctica desde la `Aplicación web`.
2. **Validación de identidad y autorización RBAC contextual (ADR-004, ADR-005, EAC-03):**
   - Se valida la sesión institucional del usuario y `AutorizadorRBAC` verifica bajo política *deny-by-default* que el actor tenga el rol `DocenteAsesor` (`validar_generacion_acta`) y que sea el tutor asignado a la `Practica` (`validar_pertenencia_docente`).
   - **Guarda de seguridad [Rol no autorizado o práctica asignada a otro docente - RN-01, RN-03, EAC-03]:**
     - Se registra de inmediato un `EventoBitacora` de rechazo en `< 1 minuto` (**ADR-006**) y se deniega la operación con `0 datos expuestos` (Escenarios 7, 8 y 12).
3. **Consulta del agregado `Practica` y verificación en la Máquina de Estados (ADR-007, ADR-010, RN-02):**
   - Se consultan `Practica`, la versión vinculada de `ReglaPrograma`, `EvaluacionDesempeno` y la inexistencia de un `ActaFinal` previa.
   - **Guarda `break` [`Practica.estadoActual != Evaluada`, falta `EvaluacionDesempeno`, `horasAcumuladasAprobadas < ReglaPrograma.horasRequeridas` o ya existe `ActaFinal` - RN-02, ADR-010]:**
     - La máquina de estados bloquea la operación e informa al `DocenteAsesor` el requisito exacto faltante sin renderizar ningún PDF ni crear registro de `ActaFinal` (Escenarios 2, 3, 4 y 5).
4. **Renderizado dinámico desde plantilla HTML/CSS a PDF y sellado SHA-256 (ADR-007, ADR-008, EAC-01):**
   - El `Adaptador PDF y Hash` toma la `plantillaActa` configurada en la versión de `ReglaPrograma` vinculada a la práctica, inyecta los datos del estudiante, empresa, supervisor, tutor, horas aprobadas y evaluación de desempeño (aprobatoria o reprobatoria con observaciones), genera el binario PDF y calcula su huella `hashIntegridadSha256` (Escenarios 1, 6 y 11).
5. **Almacenamiento en Repositorio de actas PDF y persistencia transaccional con bitácora (ADR-003, ADR-006, ADR-008, DT-02):**
   - Se guarda el archivo binario PDF en el `Repositorio de actas PDF` obteniendo `rutaArchivoPdf`.
   - Se inserta `ActaFinal` (`numeroActa = "ACTA-2026-0001"`, `rutaArchivoPdf`, `hashIntegridadSha256`, `aprobadaPorDocente = False`, `aprobadaPorCoordinador = False`) y se inserta atómicamente el `EventoBitacora`.
   - Si falla la escritura en disco o la persistencia en el repositorio, se ejecuta la compensación atómica eliminando cualquier archivo PDF huérfano (Escenario 10).
6. **Confirmación y previsualización:**
   - Se retorna `ActaFinalRespuestaDTO` con los datos del `ActaFinal`, el hash SHA-256 y la previsualización del PDF lista para la aprobación electrónica en CU-10, manteniendo la `Practica` en estado `Evaluada`.

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `ActaFinal`: documento oficial de cierre que formaliza la culminación de la práctica (`1` a `0..1` con `Practica`); contiene `id`, `practica_id`, `numeroActa` (`"ACTA-2026-0001"`), `fechaEmision`, `rutaArchivoPdf`, `hashIntegridadSha256`, `aprobadaPorDocente` (`False`) y `aprobadaPorCoordinador` (`False`) (**ADR-008**).
- `Practica`: agregado raíz que verifica su `estadoActual == Evaluada`, la existencia de su `EvaluacionDesempeno`, la unicidad de `ActaFinal` y que `horasAcumuladasAprobadas >= ReglaPrograma.horasRequeridas` (**ADR-010**, **RN-02**).
- `ReglaPrograma`: configuración declarativa versionada vinculada a la práctica al momento de su postulación; provee `horasRequeridas` y `plantillaActa` inmutables frente a cambios normativos posteriores (**ADR-007**, **EAC-01**).
- `EvaluacionDesempeno`: calificación cuantitativa (aprobatoria `>= 3.0` o reprobatoria `< 3.0`) y cualitativa (`observaciones`, `respuestasRubrica`) registrada por el `SupervisorEmpresa` en CU-07 e incorporada en el contenido del `ActaFinal`.
- `RegistroHoras`: reportes semanales en estado `Aprobado` cuyo total conforma las `horasAcumuladasAprobadas` de la práctica.
- `DocenteAsesor`: tutor académico asignado a la práctica, único actor autorizado para generar el `ActaFinal` de sus practicantes asignados (**ADR-005**, **RN-01**, **RN-03**).
- `Estudiante`, `Empresa` y `SupervisorEmpresa`: actores cuyos datos de identificación y vinculación se inyectan en la plantilla del `ActaFinal`.
- `EventoBitacora`: registro inmutable *Append-Only* sellado con SHA-256 que audita la emisión del `ActaFinal` y cualquier intento de acceso o generación rechazado (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Firma o aprobación electrónica del `ActaFinal` por parte del `DocenteAsesor` (`aprobadaPorDocente = True`) y del `Coordinador de prácticas` (`aprobadaPorCoordinador = True`), así como la transición de `Practica` de `Evaluada` a `Completada` y el envío del acta firmada por correo al estudiante (cubiertos en CU-10).
- Registro y validación de reportes semanales de horas (cubiertos en CU-04 y CU-05).
- Diligenciamiento de la evaluación de desempeño por el supervisor de empresa (cubierto en CU-07).
- Creación, edición o activación de nuevas versiones de `ReglaPrograma` y sus plantillas HTML/CSS (cubierto en CU-12).
- Exportación de consolidados históricos de actas para auditoría de acreditación (cubierto en CU-14).

---

## Decisiones pendientes

Ninguna. Todas las aclaraciones de negocio fueron resueltas e integradas en `specs/009-generar-acta-final-de-la-practica/spec.md` (1. formato consecutivo anual `"ACTA-2026-0001"` para `numeroActa`; 2. unicidad estricta de un único `ActaFinal` por `Practica`; 3. generación del `ActaFinal` también con nota reprobatoria dejando constancia en el PDF; 4. autorización exclusiva para el `DocenteAsesor` asignado a la práctica conforme a ESC-03 y `AutorizadorRBAC`), quedando respaldadas por los **ADR-002, ADR-003, ADR-005, ADR-006, ADR-007, ADR-008 y ADR-010**.
