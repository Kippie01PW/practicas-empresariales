# Plan: 015 Migrar prácticas en curso desde Excel

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Organización estricta en las tres capas concéntricas (`dominio/`, `aplicacion/` e `infraestructura/`), con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de `dominio/` define la excepción específica de migración (`ArchivoMigracionInvalidoError`) en `dominio/errores.py` y reutiliza las entidades e invariantes existentes (`Practica`, `EstadoPractica`, `Estudiante`, `DocenteAsesor`, `ReglaPrograma`, `EventoBitacora`) sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de `aplicacion/` define el caso de uso `MigrarPracticasExcelCasoUso` (ubicado en el `Módulo Postulaciones` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada/salida, el puerto de lectura de la plantilla normalizada (`LectorPlantillaExcelPort`) y el permiso exclusivo en `AutorizadorRBAC`.
  - La capa de `infraestructura/` implementa el adaptador de lectura de plantilla normalizada (`LectorPlantillaExcelSimulado` / lector CSV-Excel en memoria o archivo sin dependencias externas no aprobadas) y reutiliza los repositorios en memoria existentes.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - En esta etapa se utilizan adaptadores en memoria (`InMemory...`) para los repositorios y un lector determinista de plantilla normalizada, sin base de datos real ni librerías externas no contempladas por los ADR.
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/autorizador_rbac.py` incorpora el rol `ADMIN_DBA = "Administrador DBA"` en `RolUsuario` y aplica la política centralizada *deny-by-default*.
  - La operación `"migrar_practicas_excel"` queda restringida exclusivamente al rol `"Administrador DBA"`. Cualquier intento por `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`, `Coordinador de prácticas` o usuario sin sesión válida es rechazado de inmediato con `AccesoDenegadoError`, `0 registros importados` y registro en `EventoBitacora` en `< 1 minuto` (**RN-01**, **RN-03**, Escenario 8).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada ejecución en modo definitivo registra un `EventoBitacora` inmutable sellado con `huellaDigital` SHA-256 con el identificador del `Administrador DBA`, fecha, hora y resumen de registros importados, omitidos y rechazados (Escenario 1).
  - Cada intento rechazado por rol o sesión no autorizada inserta de forma inmediata un `EventoBitacora` de rechazo (Escenario 8).
  - Las ejecuciones en modo *dry-run* no alteran entidades de negocio (Escenario 2).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - Cada `Practica` migrada se vincula a la `ReglaPrograma` activa vigente de su `programaAcademico`. Si no existe una `ReglaPrograma` configurada para dicho programa, el registro se rechaza evitando crear prácticas huérfanas (Escenario 7).
- **ADR-009 (Estrategia de migración inicial mediante plantilla normalizada y script CLI):**
  - Implementación de un proceso CLI de un solo uso que reutiliza la lógica de dominio y casos de uso existentes sin contaminar la interfaz web de producción (`PA-05`, `RT-02`).
  - Soporte explícito de ejecución en modo **solo validación (`dry_run=True`)** para emitir reportes de advertencias e inconsistencias sin escribir en el almacenamiento (`R-03`, Escenario 2), y en modo **carga definitiva (`dry_run=False`)** que importa los registros válidos, omite los duplicados y rechaza únicamente los inválidos por fila (Escenarios 1, 3 y 4).
- **ADR-010 (Patrón Máquina de Estados Finitos en entidad `Practica`):**
  - Las prácticas migradas nacen o transicionan respetando los estados formales de `EstadoPractica`. Ante ausencia de `fechaInicio` formal (`DT-04`), se aplica la regla determinista basada en hitos completados (Escenario 5).
  - Se respeta el invariante de cupo máximo de 10 prácticas activas por `DocenteAsesor` (`R-04`, Escenario 6).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/errores.py` *(Modificar)*:
  - Agregar `ArchivoMigracionInvalidoError(ErrorDominio)`: lanzada cuando la ruta o contenido de la plantilla normalizada es ilegible, está vacía o carece de las columnas obligatorias requeridas.
- `dominio/modelos/practica.py` *(Reutilizar / verificar)*:
  - Reutilizar `Practica`, `EstadoPractica` y `ESTADOS_PRACTICA_ACTIVA` para reconstruir/transicionar el estado formal de cada práctica migrada según los hitos completados (`Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`), respetando la máquina de estados finitos (`ADR-010`, `DT-04`, Escenario 5).

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/migracion_excel_dto.py` *(Nuevo)*:
  - `FilaPlantillaMigracionDTO` (`@dataclass(frozen=True, slots=True)`): representa una fila leída de la plantilla normalizada con `numero_fila: int`, `documento_estudiante: str`, `nombre_estudiante: str`, `correo_estudiante: str`, `programa_academico: str`, `nombre_empresa: str`, `nit_empresa: str`, `supervisor_nombre: str`, `supervisor_correo: str`, `docente_asesor_id: str`, `horas_acumuladas: str`, `estado_o_hito: str`, `fecha_postulacion: str`, `fecha_inicio: str`, `fecha_fin: str`.
  - `MigrarPracticasExcelComando` (`@dataclass(frozen=True, slots=True)`):
    - `origen_datos: str` (ruta de plantilla o identificador de lote)
    - `dry_run: bool = True`
    - `actor_id: str`
    - `rol_actor: str = "Administrador DBA"`
    - `ip_origen: str = "127.0.0.1"`
  - `ResultadoFilaMigracionDTO` (`@dataclass(frozen=True, slots=True)`):
    - `numero_fila: int`, `documento_estudiante: str`, `estado_resultado: str` (`"VALIDA"`, `"IMPORTADA"`, `"OMITIDA_DUPLICADA"`, `"RECHAZADA"`), `estado_practica_asignado: Optional[str]`, `mensaje: str`.
  - `MigrarPracticasExcelRespuestaDTO` (`@dataclass(frozen=True, slots=True)`):
    - `dry_run: bool`, `total_filas: int`, `total_validas: int`, `total_importadas: int`, `total_omitidas_duplicadas: int`, `total_rechazadas: int`, `resultados_filas: tuple[ResultadoFilaMigracionDTO, ...]`, `mensaje: str`.
- `aplicacion/puertos/lector_plantilla_excel.py` *(Nuevo)*:
  - `LectorPlantillaExcelPort` (`Protocol`):
    - `leer_filas(origen_datos: str) -> list[FilaPlantillaMigracionDTO]`: lee la plantilla normalizada (o lanza `ArchivoMigracionInvalidoError` si el archivo/lote no existe o no cumple la estructura mínima de columnas).
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Agregar `ADMIN_DBA = "Administrador DBA"` en `RolUsuario`.
  - Registrar `"migrar_practicas_excel": {RolUsuario.ADMIN_DBA.value}` en `_MATRIZ_PERMISOS`.
  - Agregar método `validar_migracion_excel(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "migrar_practicas_excel") -> None` bajo política *deny-by-default* (Escenario 8).
- `aplicacion/casos_uso/migrar_practicas_excel.py` *(Nuevo, en `Módulo Postulaciones`)*:
  - Clase `MigrarPracticasExcelCasoUso`:
    - Inyecta `LectorPlantillaExcelPort`, `RepositorioPracticaPort`, `RepositorioDocentePort`, `RepositorioReglaProgramaPort`, `RepositorioBitacoraPort` (o puerto de bitácora existente) y `AutorizadorRBAC`.
    - Métodos públicos `ejecutar(comando, contexto=None)` y `__call__(comando, contexto=None)`:
      1. Valida identidad y rol exclusivo `"Administrador DBA"` mediante `autorizador_rbac.validar_migracion_excel(...)`; si falla, inserta de inmediato un `EventoBitacora` de rechazo en `< 1 minuto` y lanza `AccesoDenegadoError` con `0 registros importados` (Escenario 8).
      2. Lee las filas de la plantilla mediante `LectorPlantillaExcelPort.leer_filas(comando.origen_datos)`.
      3. Recorre fila por fila de forma independiente (Escenario 3: importa/acepta las válidas y rechaza únicamente las inválidas):
         - Valida campos obligatorios y formatos (documento de `Estudiante`, `programaAcademico`, `Empresa`, `SupervisorEmpresa`, `horas_acumuladas` numérico `>= 0`, formato de fechas cuando están presentes).
         - Verifica duplicidad dentro del propio lote y contra prácticas existentes del `Estudiante` en `RepositorioPracticaPort`; si existe, marca la fila como `OMITIDA_DUPLICADA` sin sobrescribir datos (Escenario 4).
         - Verifica existencia de `ReglaPrograma` vigente para `programaAcademico`; si no existe, rechaza esa fila (Escenario 7).
         - Verifica existencia de `DocenteAsesor` (cuando aplica según el hito) y valida que no supere el cupo máximo de 10 prácticas activas (`R-04`, Escenario 6), considerando tanto las prácticas ya activas en repositorio como las acumuladas durante el mismo lote.
         - Determina el `EstadoPractica` formal mediante la regla determinista de hitos (incluso sin `fechaInicio`, `DT-04`, Escenario 5).
      4. Si `comando.dry_run` es `True` (Escenario 2), no persiste ninguna entidad ni modifica cupos y retorna el reporte con los conteos de válidas, omitidas y rechazadas.
      5. Si `comando.dry_run` es `False` (Escenario 1), persiste cada `Practica` válida junto con su `Estudiante`, actualiza el conteo de prácticas activas del `DocenteAsesor`, registra un `EventoBitacora` inmutable de auditoría de la migración y retorna `MigrarPracticasExcelRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/lector_plantilla_excel_simulado.py` *(Nuevo)*:
  - Implementa `LectorPlantillaExcelPort` leyendo archivos CSV/Excel normalizados en texto plano o lotes deterministas registrados en memoria para pruebas y demostración CLI, validando las columnas obligatorias sin añadir dependencias externas fuera de los ADR.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `MigrarPracticasExcelCasoUso`, DTOs de `aplicacion/dtos/migracion_excel_dto.py` y `LectorPlantillaExcelSimulado`.
  - Agregar `caso_uso_migrar_practicas_excel: MigrarPracticasExcelCasoUso` en `SistemaPracticasEmpresariales` e instanciarlo en `inicializar_sistema()`.
  - Incluir demostración CLI de `CU-15` (modo *dry-run* y carga definitiva) en `main()`.

---

## Flujo

No existe un diagrama de secuencia específico para `CU-15` en `docs/diagramas/secuencias/`. El flujo sigue `ADR-009` (`Script CLI de migración` -> `Módulo Postulaciones` -> `Núcleo de Dominio` + `Autorizador RBAC` + `EventoBitacora`):

1. El `Administrador DBA` ejecuta el proceso CLI de migración indicando la plantilla normalizada de Excel y si se ejecuta en modo *dry-run* o carga definitiva.
2. `AutorizadorRBAC` valida que el actor tenga rol exclusivo `"Administrador DBA"`. Si falla, registra un `EventoBitacora` de rechazo en `< 1 minuto` y lanza `AccesoDenegadoError` sin importar registros.
3. `LectorPlantillaExcelPort` lee y entrega las filas normalizadas de la plantilla.
4. `MigrarPracticasExcelCasoUso` valida cada fila contra las reglas de dominio: campos obligatorios, formatos, detección de duplicados (omitiéndolos), existencia de `ReglaPrograma` vigente, cupo máximo de 10 prácticas activas del `DocenteAsesor` y mapeo determinista de hitos a `EstadoPractica` (cubriendo casos sin `fechaInicio`).
5. Si `dry_run=True`, retorna el reporte detallado de validación sin persistir cambios.
6. Si `dry_run=False`, persiste únicamente las prácticas válidas, actualiza la carga de cada `DocenteAsesor`, registra un `EventoBitacora` inmutable con el resumen de la migración y retorna `MigrarPracticasExcelRespuestaDTO`.

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `Practica` (`EstadoPractica`): agregado raíz creado para cada registro válido migrado, con su `estadoActual` determinado por los hitos completados.
- `Estudiante`: entidad asociada a cada práctica migrada (identificada por su documento).
- `DocenteAsesor`: entidad consultada y actualizada en su conteo de prácticas activas respetando el límite máximo de 10 (`R-04`).
- `SupervisorEmpresa` y `Empresa`: datos del supervisor externo y organización receptora vinculados a la práctica.
- `ReglaPrograma`: configuración versionada vigente por `programaAcademico` a la que queda atada cada práctica migrada (`ADR-007`).
- `EventoBitacora`: registro inmutable *Append-Only* donde se audita la ejecución definitiva de la migración y cualquier intento de acceso rechazado (`ADR-006`).

---

## Fuera de alcance

- Interfaz gráfica web o endpoint REST para cargar archivos Excel en la `Aplicación web` (excluido explícitamente por `ADR-009` y `PA-05`).
- Sobrescritura o actualización de prácticas ya existentes en el sistema cuando coinciden con registros de la plantilla (los duplicados se omiten y se reportan).
- Migración de archivos Excel heterogéneos sin pasar previamente por la plantilla normalizada oficial (`ADR-009`).

---

## Decisiones pendientes

Ninguna. Todas las aclaraciones sobre alcance de prácticas, columnas de la plantilla, importación parcial de filas válidas, omisión de duplicados y mapeo de hitos a `EstadoPractica` quedaron resueltas y reflejadas en `specs/015-migrar-practicas-en-curso-desde-excel/spec.md`.
