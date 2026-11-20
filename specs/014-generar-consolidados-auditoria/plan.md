# Plan: 014 Generar consolidados para auditoría

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Organización estricta en las tres capas concéntricas (`dominio/`, `aplicacion/` e `infraestructura/`), con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de `dominio/` incorpora la excepción `FiltrosConsolidadoInvalidosError` en `dominio/errores.py` para validar los filtros obligatorios (`programaAcademico`, `periodo`) y la consistencia del rango opcional de fechas (`fecha_inicio <= fecha_fin`), sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de `aplicacion/` define el caso de uso `GenerarConsolidadosAuditoriaCasoUso` (ubicado en el `Módulo Actas` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada y salida, el permiso en `AutorizadorRBAC`, y amplía los contratos `RepositorioPracticaPort` y `ServicioGeneradorActaPdfPort`.
  - La capa de `infraestructura/` implementa el renderizado del consolidado histórico a PDF y el cálculo de su huella SHA-256 en `AdaptadorPdfHashSimulado` / `AdaptadorPdfYHashSimulado` (simulando el `Adaptador PDF y Hash` de `docs/vistas/03-desarrollo.md`).
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - La consulta histórica cruzada lee de forma consistente las entidades persistidas (`Practica`, `ActaFinal`, `DocenteAsesor`, `EvaluacionDesempeno`, `ReglaPrograma`) en modo solo lectura sin mutar ni eliminar registros históricos.
- **ADR-004 (Esquema de autenticación híbrida):**
  - El `Coordinador de prácticas` es un actor interno autenticado mediante sesión institucional (`SSO Institucional` / `ContextoUsuario`). Cualquier solicitud sin identidad institucional válida es rechazada de inmediato con `0 datos expuestos` y registro en bitácora (**EAC-03**, Escenario 6).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/autorizador_rbac.py` aplica la política centralizada *deny-by-default*.
  - La nueva operación `"generar_consolidados_auditoria"` queda restringida exclusivamente a los roles `Coordinador` y `CoordinadorPracticas` (`"Coordinador de prácticas"`). Cualquier intento por `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa` o un usuario sin sesión válida es rechazado con registro inmediato en bitácora y `0 datos expuestos` (**RN-01**, **RN-03**, **EAC-03**, Escenario 6).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada generación de consolidado (con o sin registros coincidentes) y cada intento rechazado por rol o sesión no autorizada inserta de forma inmutable un `EventoBitacora` sellado con `huellaDigital` SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` en menos de 1 minuto (**PA-03**, **EAC-03**, **OB-02**).
  - El conteo y contenido de los `EventoBitacora` previos permanecen intactos (solo inserción, sin edición ni borrado, Escenario 4).
- **ADR-008 (Generación y preservación de documentos mediante plantillas y sellado criptográfico):**
  - El componente `Adaptador PDF y Hash` renderiza en PDF el resumen histórico de prácticas y su `ActaFinal` (número oficial, fecha de emisión, estado de firmas y `hashIntegridadSha256`) y calcula la huella SHA-256 del documento PDF consolidado exportado (Escenarios 1, 2, 3 y 4).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/errores.py` *(Modificar)*:
  - Agregar `FiltrosConsolidadoInvalidosError(ErrorDominio)`: lanzada cuando `programa_academico` o `periodo` están vacíos, cuando `estado_practica` opcional no corresponde a un `EstadoPractica` válido, o cuando `fecha_inicio > fecha_fin` (Escenario 5).

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/consolidado_auditoria_dto.py` *(Nuevo)*:
  - `GenerarConsolidadoAuditoriaComando` (`@dataclass(frozen=True, slots=True)`):
    - `programa_academico: str` (obligatorio)
    - `periodo: str` (obligatorio, ej. `"2026-1"`)
    - `actor_id: str`
    - `rol_actor: str = "Coordinador de prácticas"`
    - `fecha_inicio: Optional[datetime] = None` (opcional)
    - `fecha_fin: Optional[datetime] = None` (opcional)
    - `estado_practica: Optional[str] = None` (opcional)
    - `ip_origen: str = "127.0.0.1"`
  - `RegistroConsolidadoPracticaDTO` (`@dataclass(frozen=True, slots=True)`): resumen histórico de cada `Practica` y su `ActaFinal` (sin incluir detalle de `EventoBitacora`):
    - `practica_id: str`, `estudiante_id: str`, `programa_academico: str`, `periodo: str`, `estado_actual: str`, `fecha_postulacion: datetime`, `fecha_inicio: Optional[datetime]`, `fecha_fin: Optional[datetime]`, `docente_asesor_id: Optional[str]`, `nombre_docente_asesor: Optional[str]`, `supervisor_empresa_id: Optional[str]`, `horas_acumuladas_aprobadas: int`, `horas_requeridas: Optional[int]`, `calificacion_cuantitativa: Optional[float]`, `es_aprobatoria: Optional[bool]`, `numero_acta: Optional[str]`, `fecha_emision_acta: Optional[datetime]`, `aprobada_por_docente: Optional[bool]`, `aprobada_por_coordinador: Optional[bool]`, `acta_en_firme: Optional[bool]`, `hash_integridad_sha256: Optional[str]`.
  - `DatosRenderizadoConsolidadoPdfDTO` (`@dataclass(frozen=True, slots=True)`): estructura inmutable con los metadatos de filtro, totales y `registros: tuple[RegistroConsolidadoPracticaDTO, ...]` enviada al `Adaptador PDF y Hash`.
  - `ConsolidadoAuditoriaRespuestaDTO` (`@dataclass(frozen=True, slots=True)`):
    - `programa_academico: str`, `periodo: str`, `fecha_inicio: Optional[datetime]`, `fecha_fin: Optional[datetime]`, `estado_practica_filtro: Optional[str]`, `total_practicas: int`, `total_completadas: int`, `total_con_acta_en_firme: int`, `registros: tuple[RegistroConsolidadoPracticaDTO, ...]`, `contenido_pdf: bytes`, `hash_sha256_pdf: str`, `nombre_archivo_pdf: str`, `fecha_generacion: datetime`, `mensaje: str`.
- `aplicacion/puertos/repositorio_practica.py` *(Modificar)*:
  - Agregar `listar_todas() -> list[Practica]` en `RepositorioPracticaPort` (contrato ya implementado por `InMemoryRepositorioPractica.listar_todas()`).
- `aplicacion/puertos/servicio_generador_acta_pdf.py` *(Modificar)*:
  - Agregar `generar_consolidado_auditoria_pdf(datos: DatosRenderizadoConsolidadoPdfDTO) -> tuple[bytes, str]` en `ServicioGeneradorActaPdfPort` para renderizar en PDF el resumen histórico de prácticas y sus actas finales y retornar `(contenido_pdf, hash_sha256)`.
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Registrar `"generar_consolidados_auditoria": {RolUsuario.COORDINADOR.value, RolUsuario.COORDINADOR_PRACTICAS.value}` en `_MATRIZ_PERMISOS`.
  - Agregar método `validar_generacion_consolidados_auditoria(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "generar_consolidados_auditoria") -> None` bajo política *deny-by-default* (Escenario 6).
- `aplicacion/casos_uso/generar_consolidados_auditoria.py` *(Nuevo, en `Módulo Actas`)*:
  - Clase `GenerarConsolidadosAuditoriaCasoUso`:
    - Inyecta `RepositorioPracticaPort`, `RepositorioActaFinalPort`, `RepositorioReglaProgramaPort`, `RepositorioDocentePort`, `RepositorioEvaluacionDesempenoPort`, `ServicioGeneradorActaPdfPort` y `AutorizadorRBAC`.
    - Métodos públicos `ejecutar(comando, contexto=None)` y `__call__(comando, contexto=None)`:
      1. Valida identidad institucional y rol exclusivo `Coordinador de prácticas` mediante `autorizador_rbac.validar_generacion_consolidados_auditoria(...)`; si falla, inserta de inmediato un `EventoBitacora` de rechazo en `< 1 minuto` y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenario 6).
      2. Valida los filtros obligatorios (`programa_academico` y `periodo` no vacíos) y los opcionales (`fecha_inicio <= fecha_fin` y `estado_practica` válido contra `EstadoPractica`); ante cualquier invalidez lanza `FiltrosConsolidadoInvalidosError` sin generar archivo PDF (Escenario 5).
      3. Consulta las prácticas en modo solo lectura filtrando por `programa_academico`, `periodo` (asociado a la regla/fecha de la práctica o parámetro de período), y los filtros opcionales `fecha_inicio`, `fecha_fin` y `estado_practica` (Escenarios 1, 2 y 3).
      4. Proyecta cada práctica coincidente junto con los datos de su `ActaFinal` (número oficial, fecha de emisión, `aprobada_por_docente`, `aprobada_por_coordinador`, `esta_en_firme()`, `hash_integridad_sha256`), `ReglaPrograma`, `DocenteAsesor` y `EvaluacionDesempeno`, sin incluir registros detallados de `EventoBitacora` y sin mutar ni borrar ninguna entidad (Escenarios 1 y 4).
      5. Invoca `servicio_pdf.generar_consolidado_auditoria_pdf(datos_pdf)` para generar el binario PDF y su huella SHA-256 (incluso cuando `total_practicas == 0`, Escenarios 1, 2 y 3).
      6. Registra atómicamente un `EventoBitacora` inmutable de la consulta/exportación ejecutada y retorna `ConsolidadoAuditoriaRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/adaptador_pdf_hash_simulado.py` y `main.py` (`AdaptadorPdfYHashSimulado`) *(Modificar)*:
  - Implementar `generar_consolidado_auditoria_pdf(datos: DatosRenderizadoConsolidadoPdfDTO) -> tuple[bytes, str]` para renderizar en HTML/PDF determinista el resumen histórico de prácticas y su `ActaFinal` (o el mensaje explícito de 0 registros coincidentes) y calcular su hash SHA-256.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `GenerarConsolidadosAuditoriaCasoUso` y los DTOs de `aplicacion/dtos/consolidado_auditoria_dto.py`.
  - Agregar `caso_uso_generar_consolidados: GenerarConsolidadosAuditoriaCasoUso` en `SistemaPracticasEmpresariales` e inyectarlo en `inicializar_sistema()`.
  - Incluir demostración CLI de `CU-14` en `main()`.

---

## Flujo

No existe un diagrama de secuencia específico para `CU-14` en `docs/diagramas/secuencias/` (solo existen `ESC-01` a `ESC-05` para los casos de uso primarios). El flujo sigue el patrón estándar de casos de uso protegidos por `AutorizadorRBAC` y `EventoBitacora` (`ADR-005`, `ADR-006`, `ADR-008`):

1. El `Coordinador de prácticas` autenticado por `SSO Institucional` (`ContextoUsuario`) invoca `GenerarConsolidadosAuditoriaCasoUso` con `programa_academico` y `periodo` obligatorios y filtros opcionales (`fecha_inicio`, `fecha_fin`, `estado_practica`).
2. `AutorizadorRBAC` valida identidad y rol bajo política *deny-by-default*. Si falla, registra un `EventoBitacora` de rechazo en `< 1 minuto` y lanza `AccesoDenegadoError` con `0 datos expuestos`.
3. Se validan los filtros obligatorios y el rango de fechas; si falta `programa_academico` o `periodo` o `fecha_inicio > fecha_fin`, se lanza `FiltrosConsolidadoInvalidosError` sin generar PDF.
4. Se consultan en modo solo lectura las `Practica` coincidentes y su `ActaFinal` asociada (junto con datos de `DocenteAsesor`, `ReglaPrograma` y `EvaluacionDesempeno`), sin alterar ningún registro histórico.
5. `Adaptador PDF y Hash` renderiza el consolidado en formato PDF y calcula su huella SHA-256 (tanto si hay registros como si el resultado es vacío con `total_practicas == 0`).
6. Se inserta atómicamente un `EventoBitacora` inmutable con la trazabilidad de la exportación y se retorna `ConsolidadoAuditoriaRespuestaDTO`.

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `Practica` (`EstadoPractica`): entidad consultada para filtrar por programa académico, período, rango de fechas y estado de la práctica.
- `ActaFinal`: entidad asociada (0..1) de la cual se proyectan `numeroActa`, `fechaEmision`, `aprobadaPorDocente`, `aprobadaPorCoordinador` y `hashIntegridadSha256`.
- `ReglaPrograma`, `DocenteAsesor`, `EvaluacionDesempeno`: entidades de referencia consultadas en modo solo lectura para enriquecer el resumen histórico de cada práctica en el consolidado.
- `EventoBitacora`: registro inmutable *Append-Only* donde se audita tanto la generación del consolidado como los intentos rechazados de acceso no autorizado (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Exportación en formatos distintos a PDF (como CSV o Excel `.xlsx`).
- Inclusión del listado detallado de eventos individuales de `EventoBitacora` dentro del cuerpo del consolidado (se exporta únicamente el resumen histórico de prácticas y su `ActaFinal`).
- Edición, corrección o eliminación de registros históricos de prácticas, actas o bitácora desde el consolidado.

---

## Decisiones pendientes

Ninguna. Todas las aclaraciones de formato (`PDF`), filtros obligatorios (`programaAcademico`, `periodo`) y opcionales (`rango de fechas`, `estadoPractica`) y alcance de datos (`resumen histórico de prácticas y su ActaFinal`) quedaron resueltas y reflejadas en `specs/014-generar-consolidados-auditoria/spec.md`.

