# Plan: 012 Configurar reglas y plantillas por programa

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Organización estricta en las tres capas concéntricas (`dominio/`, `aplicacion/` e `infraestructura/`), con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de `dominio/` amplía la entidad `ReglaPrograma` con las invariantes de validación normativa (`horas_requeridas > 0` entero positivo, `criterios_rubrica` no vacíos admitiendo lista simple de criterios sin peso o diccionario de criterios con ponderaciones positivas, `plantilla_acta` no vacía), la edición controlada `actualizar_borrador(...)` permitida exclusivamente mientras `estado_vigencia == EstadoVigenciaRegla.BORRADOR`, la activación formal `activar(fecha_vigencia)` y las excepciones de negocio para `CU-12`, sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de `aplicacion/` define el caso de uso `ConfigurarReglasProgramaCasoUso` (ubicado en el `Módulo Reglas` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada y salida, y amplía los contratos de los puertos `RepositorioReglaProgramaPort` y `ServicioGeneradorActaPdfPort` (para la simulación en memoria de la vista previa del PDF sin persistir en el repositorio oficial de actas).
  - La capa de `infraestructura/` amplía `InMemoryRepositorioReglaPrograma` y `AdaptadorPdfYHashSimulado` (simulando el `Adaptador PostgreSQL` y el `Adaptador PDF y Hash` de `docs/vistas/03-desarrollo.md`).
  - Cumple estrictamente **EAC-01**: cualquier modificación o adición de reglas, criterios de rúbrica y plantillas de acta se resuelve tocando como máximo **2 componentes** de la arquitectura (`Módulo Reglas` y `Adaptador PDF y Hash`) en menos de 16 horas-hombre y sin alterar la lógica de otros módulos.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - Al activar oficialmente una nueva versión de `ReglaPrograma` en estado `Borrador`, la transición de la versión anterior del mismo programa académico a `Inactiva` (histórica), el paso de la nueva versión a `Activa` y el registro del `EventoBitacora` se ejecutan de forma atómica, garantizando que exista como máximo una única `ReglaPrograma` en estado `Activa` por programa académico.
- **ADR-004 (Esquema de autenticación híbrida):**
  - El `Coordinador de prácticas` es un actor interno que opera autenticado mediante sesión institucional (`SSO Institucional` / `ContextoUsuario`). Cualquier solicitud sin identidad institucional válida es rechazada de inmediato con `0 datos expuestos` y registro en bitácora (**EAC-03**, Escenario 9).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/` aplica la política centralizada *deny-by-default*.
  - La operación `"configurar_reglas"` está restringida exclusivamente a los roles `Coordinador` y `CoordinadorPracticas` (`"Coordinador de prácticas"`). Cualquier intento de crear, editar, simular o activar una `ReglaPrograma` por parte de `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa` o un usuario no autenticado es rechazado con registro inmediato en bitácora y `0 datos expuestos` (**RN-03**, **EAC-03**, Escenario 9).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada creación de borrador de `ReglaPrograma` (Escenario 1), cada edición de un borrador (Escenario 2), cada activación oficial de una versión (Escenario 4) y cada intento rechazado por rol o sesión no autorizada (Escenario 9) inserta atómicamente un `EventoBitacora` inmutable sellado con `huellaDigital` SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` en menos de 1 minuto (**PA-03**, **EAC-03**).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - Implementa el flujo completo de ciclo de vida de `ReglaPrograma`:
    1. Creación de una nueva versión en `estadoVigencia = EstadoVigenciaRegla.BORRADOR` sin afectar la versión `Activa` actual (Escenario 1).
    2. Edición permitida únicamente mientras la regla permanezca en `estadoVigencia = EstadoVigenciaRegla.BORRADOR` (Escenario 2); cualquier intento de editar o eliminar una versión `Activa` o `Inactiva` (histórica) es bloqueado con `ReglaProgramaInmutableError` para preservar la integridad histórica (Escenario 8).
    3. Simulación de vista previa del acta y rúbrica antes de publicar para mitigar errores humanos de configuración (Escenario 3).
    4. Activación oficial que pasa la versión anterior a `Inactiva` (histórica) y la nueva a `Activa` (Escenario 4).
  - Dado que cada `Practica` captura el identificador `regla_programa_id` vigente al momento de su postulación (CU-01) y tanto la evaluación (CU-07) como la generación del acta (CU-09) consultan la regla por ese `regla_programa_id`, la publicación de una nueva versión garantiza un **0% de alteración** en las prácticas en curso y un **0% de alteración** en las actas finales emitidas previamente (**EAC-01**, **OB-05**, Escenarios 4 y 10).
- **ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico):**
  - Durante la simulación de una `ReglaPrograma` en estado `Borrador` (`POST /reglas-programa/{id}/simular` en `docs/diagramas/secuencias/cu12-configurar-reglas.puml`), el componente `Adaptador PDF y Hash` renderiza en memoria la `plantillaActa`, las `horasRequeridas` y los `criteriosRubrica` del borrador con datos de prueba y calcula su hash SHA-256 de previsualización, sin escribir ningún archivo definitivo en el `Repositorio de actas PDF` ni crear registros de `ActaFinal` (Escenario 3).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/errores.py` *(Modificar)*:
  - Agregar las excepciones de dominio para CU-12:
    - `ReglaProgramaNoEncontradaError(ErrorDominio)`: lanzada cuando no existe una `ReglaPrograma` con el identificador solicitado para edición, simulación o activación.
    - `DatosReglaProgramaInvalidosError(ErrorDominio)`: lanzada cuando `programaAcademico`, `version` o `plantillaActa` están vacíos o cuando `horasRequeridas` no es un número entero positivo mayor a `0` (`<= 0` o tipo no entero) (Escenario 5).
    - `CriteriosRubricaInvalidosError(ErrorDominio)`: lanzada cuando `criteriosRubrica` está vacío (lista vacía, diccionario vacío o `None`), contiene nombres de criterio vacíos o en blanco, criterios duplicados en lista, o ponderaciones no numéricas / menores o iguales a `0` cuando se suministra como diccionario (Escenario 6).
    - `VersionReglaProgramaDuplicadaError(ErrorDominio)`: lanzada cuando se intenta crear o renombrar una `ReglaPrograma` con una `version` que ya existe para el mismo `programaAcademico` (Escenario 7).
    - `ReglaProgramaInmutableError(ErrorDominio)`: lanzada cuando se intenta editar directamente los atributos normativos o eliminar una `ReglaPrograma` cuyo `estadoVigencia` ya es `Activa` o `Inactiva` (histórica), dado que solo se permite editar mientras permanezca en estado `Borrador` (Escenario 8).
- `dominio/modelos/regla_programa.py` *(Modificar)*:
  - Ampliar la validación e invariantes de `ReglaPrograma`:
    - Validar mediante métodos de dominio que:
      - `programa_academico`, `version` y `plantilla_acta` sean cadenas no vacías (de lo contrario lanza `DatosReglaProgramaInvalidosError`, Escenario 5).
      - `horas_requeridas` sea estrictamente un número entero (`int`, no `bool`) positivo mayor a `0` (`horas_requeridas > 0`; de lo contrario lanza `DatosReglaProgramaInvalidosError`, Escenario 5).
      - `criterios_rubrica` sea:
        - Una **lista simple no vacía de criterios sin peso** (`list[str]`, ej. `["dominio_tecnico", "habilidades_blandas", "cumplimiento_objetivos"]`), donde cada nombre de criterio sea una cadena no vacía y sin duplicados, **o**
        - Un **diccionario no vacío de criterios** (`dict[str, float | int]`), donde cada clave sea un nombre de criterio no vacío y cada peso sea un número positivo mayor a `0` (de lo contrario lanza `CriteriosRubricaInvalidosError`, Escenario 6).
    - Agregar propiedad `nombres_criterios -> list[str]`: retorna la lista ordenada o secuencial de nombres de criterios tanto cuando `criterios_rubrica` es una `list[str]` como cuando es un `dict[str, Any]`, garantizando compatibilidad transparente con `EvaluacionDesempeno` y con el renderizador de plantillas HTML/PDF.
    - Agregar método `es_borrador() -> bool`: retorna `self._estado_vigencia == EstadoVigenciaRegla.BORRADOR`.
    - Agregar método `actualizar_borrador(*, horas_requeridas: Optional[int] = None, criterios_rubrica: Optional[dict[str, Any] | list[str]] = None, plantilla_acta: Optional[str] = None, version: Optional[str] = None) -> None`:
      - Verifica que `self._estado_vigencia == EstadoVigenciaRegla.BORRADOR`; si el estado es `Activa` o `Inactiva`, lanza `ReglaProgramaInmutableError` (Escenarios 2 y 8).
      - Valida los nuevos valores con las mismas invariantes de dominio y actualiza los atributos del borrador.
    - Ampliar `activar(fecha_vigencia: Optional[datetime] = None) -> None`:
      - Verifica que la regla no esté ya `Inactiva` (o si ya está `Activa` / `Inactiva`, valida la transición desde `Borrador`; si se intenta reactivar o modificar una regla que no está en `Borrador`, lanza `ReglaProgramaInmutableError`), cambia `self._estado_vigencia = EstadoVigenciaRegla.ACTIVA` y actualiza `self._fecha_vigencia = fecha_vigencia or datetime.now()` (Escenario 4).
    - Mantener `desactivar() -> None` para marcar la versión activa anterior como `EstadoVigenciaRegla.INACTIVA` (histórica) cuando se activa la nueva versión `N+1` (Escenario 4).

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/regla_programa_dto.py` *(Nuevo)*:
  - `CrearBorradorReglaComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `programa_academico: str`
    - `version: str`
    - `horas_requeridas: int`
    - `criterios_rubrica: dict[str, Any] | list[str]`
    - `plantilla_acta: str`
    - `actor_id: str`
    - `rol_actor: str = "Coordinador de prácticas"`
    - `ip_origen: str = "127.0.0.1"`
    - `regla_id: Optional[str] = None`
  - `EditarBorradorReglaComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `regla_id: str`
    - `actor_id: str`
    - `rol_actor: str = "Coordinador de prácticas"`
    - `horas_requeridas: Optional[int] = None`
    - `criterios_rubrica: Optional[dict[str, Any] | list[str]] = None`
    - `plantilla_acta: Optional[str] = None`
    - `version: Optional[str] = None`
    - `ip_origen: str = "127.0.0.1"`
  - `SimularReglaProgramaComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `regla_id: str`
    - `actor_id: str`
    - `rol_actor: str = "Coordinador de prácticas"`
    - `estudiante_prueba_id: str = "EST-SIMULACION-001"`
    - `docente_prueba_id: str = "DOC-SIMULACION-001"`
    - `nombre_docente_prueba: str = "Docente Asesor Simulación"`
    - `supervisor_prueba_id: str = "SUP-SIMULACION-001"`
    - `calificacion_prueba: float = 4.5`
    - `observaciones_prueba: str = "Simulación de vista previa del acta final y rúbrica en estado Borrador."`
    - `ip_origen: str = "127.0.0.1"`
  - `ActivarReglaProgramaComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `regla_id: str`
    - `actor_id: str`
    - `rol_actor: str = "Coordinador de prácticas"`
    - `ip_origen: str = "127.0.0.1"`
    - `fecha_vigencia: Optional[datetime] = None`
  - `EliminarReglaProgramaComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `regla_id: str`
    - `actor_id: str`
    - `rol_actor: str = "Coordinador de prácticas"`
    - `ip_origen: str = "127.0.0.1"`
  - `ReglaProgramaRespuestaDTO`: DTO inmutable de salida (`@dataclass(frozen=True, slots=True)`):
    - `regla_id: str`
    - `programa_academico: str`
    - `version: str`
    - `horas_requeridas: int`
    - `criterios_rubrica: dict[str, Any] | list[str]`
    - `nombres_criterios: tuple[str, ...]`
    - `plantilla_acta: str`
    - `estado_vigencia: str`
    - `fecha_vigencia: datetime`
    - `regla_anterior_inactivada_id: Optional[str]`
    - `version_anterior_inactivada: Optional[str]`
    - `mensaje: str`
  - `SimulacionReglaProgramaRespuestaDTO`: DTO inmutable de salida para la previsualización en memoria (`@dataclass(frozen=True, slots=True)`):
    - `regla_id: str`
    - `programa_academico: str`
    - `version: str`
    - `estado_vigencia: str`
    - `horas_requeridas: int`
    - `criterios_rubrica: dict[str, Any] | list[str]`
    - `nombres_criterios: tuple[str, ...]`
    - `plantilla_utilizada: str`
    - `contenido_pdf_simulacion: bytes`
    - `vista_previa_html: str`
    - `hash_sha256_simulacion: str`
    - `persistido_en_repositorio: bool` (siempre `False` en simulación)
    - `mensaje: str`
- `aplicacion/puertos/repositorio_regla.py` *(Modificar)*:
  - Ampliar `RepositorioReglaProgramaPort` con los métodos requeridos por `CU-12`:
    - `actualizar(regla: ReglaPrograma) -> None`
    - `buscar_por_programa_y_version(programa_academico: str, version: str) -> Optional[ReglaPrograma]`
    - `listar_por_programa(programa_academico: str) -> list[ReglaPrograma]`
    - `listar_todas() -> list[ReglaPrograma]`
- `aplicacion/puertos/servicio_generador_acta_pdf.py` *(Modificar)*:
  - Agregar el método `simular_acta_pdf_en_memoria(datos: DatosRenderizadoActaDTO) -> ResultadoRenderizadoPdfDTO` en `ServicioGeneradorActaPdfPort`, el cual renderiza la plantilla HTML/CSS y empaqueta el binario PDF de prueba en memoria con su hash SHA-256 sin escribir ni alterar archivos en el `Repositorio de actas PDF` (Escenario 3, `docs/diagramas/secuencias/cu12-configurar-reglas.puml` pasos 38-41).
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - La operación `"configurar_reglas"` ya está registrada en `_MATRIZ_PERMISOS` para `{RolUsuario.COORDINADOR.value, RolUsuario.COORDINADOR_PRACTICAS.value}`.
  - Agregar método `validar_configuracion_reglas(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "configurar_reglas") -> None`:
    - Verifica bajo política *deny-by-default* que el usuario tenga identidad institucional válida (no vacía) y rol `Coordinador` o `CoordinadorPracticas` (`"Coordinador de prácticas"`).
    - Si el rol es `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`, vacío o desconocido, lanza `AccesoDenegadoError` (Escenario 9).
- `aplicacion/casos_uso/configurar_reglas_programa.py` *(Nuevo)*:
  - Clase `ConfigurarReglasProgramaCasoUso` (ubicada en el `Módulo Reglas` de `docs/vistas/03-desarrollo.md`):
    - Inyecta `RepositorioReglaProgramaPort`, `RepositorioPracticaPort` (para registro atómico en la bitácora *Append-Only* `EventoBitacora`), `ServicioGeneradorActaPdfPort` y `AutorizadorRBAC`.
    - Métodos públicos del caso de uso:
      1. `crear_borrador(comando: CrearBorradorReglaComando, contexto: Optional[ContextoUsuario] = None) -> ReglaProgramaRespuestaDTO` (también invocable vía `ejecutar` / `__call__`):
         - Valida identidad institucional y rol `Coordinador de prácticas` mediante `autorizador_rbac.validar_configuracion_reglas(...)`. Si falla, registra de inmediato un `EventoBitacora` de rechazo en `< 1 minuto` y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenario 9).
         - Verifica que `programa_academico` y `version` no estén vacíos y comprueba mediante `repositorio_regla.buscar_por_programa_y_version(programa_academico, version)` que no exista ya esa versión para el mismo programa académico; si existe, lanza `VersionReglaProgramaDuplicadaError` (Escenario 7).
         - Instancia `ReglaPrograma(..., estado_vigencia=EstadoVigenciaRegla.BORRADOR)`, lo que valida todas las invariantes normativas (`horas_requeridas > 0`, `criterios_rubrica` válidos como lista simple sin peso o diccionario con pesos positivos, `plantilla_acta` no vacía; Escenarios 5 y 6).
         - Persiste el borrador en `RepositorioReglaProgramaPort.guardar(regla)` manteniendo intacta cualquier versión `Activa` previa del programa (Escenario 1).
         - Registra atómicamente el `EventoBitacora` inmutable de creación de borrador y retorna `ReglaProgramaRespuestaDTO`.
      2. `editar_borrador(comando: EditarBorradorReglaComando, contexto: Optional[ContextoUsuario] = None) -> ReglaProgramaRespuestaDTO`:
         - Valida identidad y rol `Coordinador de prácticas` (si falla, registra `EventoBitacora` y lanza `AccesoDenegadoError`, Escenario 9).
         - Busca la `ReglaPrograma` por `comando.regla_id`; si no existe, lanza `ReglaProgramaNoEncontradaError`.
         - Si se solicitó cambiar `version` a una versión distinta que ya existe para ese mismo programa académico, lanza `VersionReglaProgramaDuplicadaError` (Escenario 7).
         - Invoca `regla.actualizar_borrador(...)`: si la regla está en estado `Activa` o `Inactiva` (histórica), lanza `ReglaProgramaInmutableError` bloqueando la edición directa (Escenario 8); si está en `Borrador`, valida las invariantes (Escenarios 5 y 6) y actualiza sus atributos (Escenario 2).
         - Persiste el cambio en `RepositorioReglaProgramaPort.actualizar(regla)`, registra atómicamente el `EventoBitacora` y retorna `ReglaProgramaRespuestaDTO`.
      3. `simular_previsualizacion(comando: SimularReglaProgramaComando, contexto: Optional[ContextoUsuario] = None) -> SimulacionReglaProgramaRespuestaDTO`:
         - Valida identidad y rol `Coordinador de prácticas` (si falla, registra `EventoBitacora` y lanza `AccesoDenegadoError`, Escenario 9).
         - Recupera la `ReglaPrograma` por `comando.regla_id`; si no existe, lanza `ReglaProgramaNoEncontradaError`.
         - Construye un `DatosRenderizadoActaDTO` con datos de prueba para cada criterio de `regla.nombres_criterios`, las `regla.horas_requeridas` y la `regla.plantilla_acta`.
         - Invoca `servicio_pdf.simular_acta_pdf_en_memoria(datos_simulacion)` generando en memoria el PDF y la vista previa HTML sin almacenar ningún archivo en el `Repositorio de actas PDF` ni crear un `ActaFinal` ni modificar el estado `Borrador` de la regla (Escenario 3).
         - Retorna `SimulacionReglaProgramaRespuestaDTO`.
      4. `activar_regla(comando: ActivarReglaProgramaComando, contexto: Optional[ContextoUsuario] = None) -> ReglaProgramaRespuestaDTO`:
         - Valida identidad y rol `Coordinador de prácticas` (si falla, registra `EventoBitacora` y lanza `AccesoDenegadoError`, Escenario 9).
         - Recupera la `ReglaPrograma` por `comando.regla_id`; si no existe, lanza `ReglaProgramaNoEncontradaError`.
         - Verifica que la regla se encuentre en `EstadoVigenciaRegla.BORRADOR` (si ya está `Activa` o `Inactiva`, lanza `ReglaProgramaInmutableError`).
         - Busca todas las reglas del mismo `programa_academico` que estén en `EstadoVigenciaRegla.ACTIVA`, las transiciona a `EstadoVigenciaRegla.INACTIVA` (`regla_activa.desactivar()`) y las actualiza en `RepositorioReglaProgramaPort`.
         - Activa la nueva versión (`regla.activar(fecha_vigencia=comando.fecha_vigencia)`) y la actualiza en `RepositorioReglaProgramaPort`, sin tocar ninguna `Practica` ni `ActaFinal` existente (0% de alteración en prácticas activas y actas previas, Escenarios 4 y 10).
         - Registra atómicamente el `EventoBitacora` inmutable de activación oficial y retorna `ReglaProgramaRespuestaDTO`.
      5. `eliminar_regla(comando: EliminarReglaProgramaComando, contexto: Optional[ContextoUsuario] = None) -> None`:
         - Valida identidad y rol `Coordinador de prácticas` (Escenario 9).
         - Recupera la `ReglaPrograma` por `comando.regla_id`; si no existe, lanza `ReglaProgramaNoEncontradaError`.
         - Si la regla está en `EstadoVigenciaRegla.ACTIVA` o `EstadoVigenciaRegla.INACTIVA`, lanza `ReglaProgramaInmutableError` impidiendo su eliminación para proteger la inmutabilidad normativa de las cohortes vinculadas (Escenario 8).

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - Ampliar `InMemoryRepositorioReglaPrograma(RepositorioReglaProgramaPort)`:
    - Implementar `actualizar(regla: ReglaPrograma) -> None`.
    - Implementar `buscar_por_programa_y_version(programa_academico: str, version: str) -> Optional[ReglaPrograma]` (comparando programa y versión normalizados).
    - Implementar `listar_por_programa(programa_academico: str) -> list[ReglaPrograma]` ordenadas por `fecha_vigencia`.
- `infraestructura/adaptadores/adaptador_pdf_hash_simulado.py` y `main.py` (`AdaptadorPdfYHashSimulado`) *(Modificar)*:
  - Implementar `simular_acta_pdf_en_memoria(datos: DatosRenderizadoActaDTO) -> ResultadoRenderizadoPdfDTO`:
    - Renderiza la plantilla HTML/CSS configurada en `datos.plantilla_acta`, empaqueta el binario PDF de prueba en memoria y calcula su hash SHA-256 con `calcular_hash_sha256(contenido_pdf)`, sin guardar la entrada en `self._archivos_pdf` ni en `self._html_renderizados` (garantizando 0 escrituras en el repositorio oficial de actas durante la simulación del Escenario 3).

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `ConfigurarReglasProgramaCasoUso` y los DTOs de `aplicacion/dtos/regla_programa_dto.py`.
  - Agregar `caso_uso_configurar_reglas: ConfigurarReglasProgramaCasoUso` en `SistemaPracticasEmpresariales` e inyectarlo en `inicializar_sistema()`.
  - Incluir la demostración CLI de `CU-12` (creación de versión `"2026-2"` en estado `Borrador`, edición en `Borrador` con lista simple de criterios sin peso, simulación en memoria del PDF de vista previa y activación oficial pasando `"2026-1"` a `Inactiva` con 0% de alteración en la práctica previa) en `main()`.

---

## Flujo

Secuencia basada directamente en `docs/diagramas/secuencias/cu12-configurar-reglas.puml` (ESC-05):

1. **Creación y edición en estado Borrador (`POST /reglas-programa` / actualización de borrador):**
   - El `Coordinador de prácticas` registra una nueva configuración de `ReglaPrograma` (o edita una existente que aún permanezca en `estadoVigencia = Borrador`) indicando `programaAcademico`, `version`, `horasRequeridas` (entero positivo `> 0`), `criteriosRubrica` (lista simple de criterios sin peso o diccionario de criterios con pesos positivos) y `plantillaActa`.
   - Se valida la sesión institucional (`SSO Institucional` / `ContextoUsuario`, **ADR-004**) y el `AutorizadorRBAC` verifica bajo política *deny-by-default* que el rol sea exclusivamente `Coordinador de prácticas` (**ADR-005**, **RN-03**). Si falla, se inserta un `EventoBitacora` de rechazo en `< 1 minuto` y se deniega con `0 datos expuestos` (Escenario 9, **EAC-03**).
   - Se verifican las invariantes de dominio y unicidad de `(programaAcademico, version)` (Escenarios 5, 6 y 7). Si se intenta editar o eliminar una versión que ya está en estado `Activa` o `Inactiva` (histórica), se deniega con `ReglaProgramaInmutableError` (Escenario 8).
   - Se persiste la `ReglaPrograma` con `estadoVigencia = Borrador` junto con su `EventoBitacora` atómico (**ADR-006**), sin alterar la versión `Activa` vigente ni las prácticas en curso (Escenarios 1 y 2).
2. **Simulación opcional de vista previa antes de activar (`POST /reglas-programa/{id}/simular`, Mitigación ADR-007):**
   - El `Coordinador de prácticas` solicita previsualizar el acta final y la rúbrica con datos de prueba para la `ReglaPrograma` en estado `Borrador`.
   - El `Módulo Reglas` invoca al `Adaptador PDF y Hash` (`simular_acta_pdf_en_memoria`), que renderiza en memoria la `plantillaActa`, las `horasRequeridas` y los `criteriosRubrica` del borrador devolviendo el binario PDF de prueba sin almacenar un `ActaFinal` oficial ni modificar el estado `Borrador` de la regla (Escenario 3, **ADR-008**).
3. **Publicación y activación oficial (`PUT /reglas-programa/{id}/activar`):**
   - El `Coordinador de prácticas` publica y activa oficialmente la `ReglaPrograma` en estado `Borrador`.
   - En una operación atómica (**ADR-003**, **ADR-006**, **ADR-007**):
     - La versión anterior que estaba en `estadoVigencia = Activa` para ese `programaAcademico` pasa a `estadoVigencia = Inactiva` (histórica).
     - La nueva versión `N+1` pasa de `Borrador` a `estadoVigencia = Activa` actualizando su `fechaVigencia`.
     - Se inserta el `EventoBitacora` inmutable de activación oficial.
   - Las prácticas en curso o completadas conservan intacto su `regla_programa_id` anterior (`0% de alteración` en prácticas activas y actas emitidas previamente, **EAC-01**, **OB-05**), mientras que las siguientes postulaciones del programa académico se vinculan automáticamente a la nueva versión `Activa` (Escenarios 4 y 10).

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `ReglaPrograma`: configuración declarativa versionada por programa académico con atributos `id`, `programaAcademico`, `version`, `horasRequeridas` (entero positivo `> 0`), `criteriosRubrica` (lista simple de criterios sin peso o diccionario de criterios con pesos), `plantillaActa`, `estadoVigencia` (`Borrador`, `Activa`, `Inactiva`) y `fechaVigencia` (**ADR-007**, **EAC-01**).
- `Practica`: agregado raíz vinculado de forma inmutable (`regla_programa_id`) a la versión de `ReglaPrograma` que estaba `Activa` al momento de su postulación (`ReglaPrograma "1" -- "0..*" Practica : rige condiciones de >`), garantizando `0% de alteración` ante nuevas versiones activadas posteriormente (**OB-05**, **EAC-01**).
- `EventoBitacora`: registro transaccional inmutable *Append-Only* con huella digital SHA-256 que audita la creación de borradores, la edición de borradores, la activación oficial de versiones y cualquier intento de acceso o configuración por roles no autorizados (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Vinculación inicial de una `Practica` a la `ReglaPrograma` activa durante la postulación del estudiante (cubierto en `CU-01: Postulación de estudiante a la práctica`).
- Diligenciamiento de la evaluación de desempeño por el supervisor externo contra la rúbrica de la regla vinculada (cubierto en `CU-07: Evaluar desempeño del practicante`).
- Generación oficial y almacenamiento definitivo del `ActaFinal` de una práctica evaluada en el repositorio de actas PDF (cubierto en `CU-09: Generar acta final de la práctica`).
- Aprobación y firma electrónica secuencial del `ActaFinal` (cubierto en `CU-10: Aprobar el acta electrónicamente`).

---

## Decisiones pendientes

Ninguna. Las tres aclaraciones planteadas durante la fase de especificación fueron resueltas por el usuario e integradas en `specs/012-configurar-reglas-plantillas-programa/spec.md`:
1. Para `horasRequeridas` basta con que sea un número entero positivo mayor a `0`.
2. Para `criteriosRubrica` se permite una lista simple de criterios sin peso (además del soporte existente de diccionario de criterios).
3. Se permite editar los atributos de una `ReglaPrograma` mientras permanezca en `estadoVigencia = "Borrador"`, bloqueando la edición o eliminación directa de versiones en estado `"Activa"` o `"Inactiva"` (histórica).

