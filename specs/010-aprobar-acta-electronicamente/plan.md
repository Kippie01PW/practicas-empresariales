# Plan: 010 Aprobar el acta electrónicamente

## Decisiones que aplican

- **ADR-001 (Resiliencia e integración asíncrona):**
  - Una vez que el `Coordinador de prácticas` asienta la aprobación electrónica final del `ActaFinal` y la `Practica` transiciona a estado `Completada`, el sistema publica el evento asíncrono `ActaFinalEmitida` en el bróker de mensajería (`PublicadorEventosPort`) y despacha la notificación por correo electrónico (`ServicioCorreoPort`) al `Estudiante` titular confirmando la culminación exitosa de la práctica con el enlace o ruta del acta oficial en PDF (**OB-05**, `docs/diagramas/secuencias/cu10-aprobar-acta.puml`). Si el envío de correo o el bróker presenta una intermitencia transitoria, la transacción atómica de aprobación y cierre de la práctica no se revierte.
- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Organización estricta en las tres capas concéntricas (`dominio/`, `aplicacion/` e `infraestructura/`), con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de `dominio/` incorpora la entidad `ActaFinal`, sus invariantes de firmas secuenciales e integridad SHA-256, las excepciones de negocio para `CU-10` y la transición formal `completar()` (`Evaluada → Completada`) en la entidad raíz `Practica`, sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de `aplicacion/` define el caso de uso `AprobarActaElectronicamenteCasoUso` (dentro del `Módulo Actas` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada y salida, y los puertos `RepositorioActaFinalPort` y `ServicioPdfHashPort`.
  - La capa de `infraestructura/` implementa los adaptadores en memoria `InMemoryRepositorioActaFinal` y `AdaptadorPdfHashSimulado` (simulando el `Repositorio de actas PDF` y el `Adaptador PDF y Hash` de `docs/vistas/03-desarrollo.md`).
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - En el Paso 1 (Docente asesor), la actualización de `ActaFinal` (`aprobadaPorDocente = True`) y la inserción de `EventoBitacora` ocurren atómicamente.
  - En el Paso 2 (Coordinador de prácticas), la actualización de `ActaFinal` (`aprobadaPorCoordinador = True`), la transición de `Practica` a `Completada`, la liberación de 1 cupo en `DocenteAsesor` (`liberar_practica()`) y la inserción de `EventoBitacora` se ejecutan de forma atómica.
- **ADR-004 (Esquema de autenticación híbrida):**
  - Tanto el `DocenteAsesor` como el `Coordinador de prácticas` son actores internos que operan autenticados mediante sesión institucional (`SSO Institucional` / `ContextoUsuario`). Cualquier solicitud sin identidad institucional válida o con credenciales inválidas es rechazada de inmediato con 0 datos expuestos y registro en bitácora (**EAC-03**, Escenario 9).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en `aplicacion/seguridad/` aplica la política centralizada *deny-by-default*.
  - Solo los roles `DocenteAsesor` (o `Docente`, operación `aprobar_acta_docente`) y `CoordinadorPracticas` (o `Coordinador`, operación `aprobar_acta_coordinador`) están autorizados para ejecutar `CU-10`. Cualquier intento por `Estudiante`, `SupervisorEmpresa` u otro rol no autorizado es rechazado con registro inmediato en bitácora y 0 datos expuestos (**RN-03**, **EAC-03**, Escenarios 8 y 9).
  - Validación de pertenencia contextual (*Context-Based Access Control*, **RN-01**): cuando el actor es `DocenteAsesor`, su identificador debe coincidir estrictamente con `practica.docente_asesor_id`. Si un docente intenta aprobar el acta de una práctica asignada a otro tutor, se deniega con 0 datos expuestos y se registra el intento en bitácora (Escenario 7).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada aprobación electrónica exitosa (Paso 1 por docente y Paso 2 por coordinador) y cada intento rechazado (violación de RBAC, docente no asignado, fallo de integridad SHA-256 o credenciales inválidas) inserta atómicamente un `EventoBitacora` inmutable sellado con `huellaDigital` SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada` en menos de 1 minuto (**PA-03**, **EAC-03**).
- **ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico):**
  - Antes de asentar la firma del `DocenteAsesor` o del `Coordinador de prácticas`, el caso de uso lee el binario PDF almacenado en el `Repositorio de actas PDF` a través del puerto `ServicioPdfHashPort`, recalcula su huella criptográfica SHA-256 y comprueba que coincide exactamente con `acta.hash_integridad_sha256` (**PA-03**).
  - Si el archivo PDF fue alterado, corrompido o no está disponible y la huella recalculada difiere del `hashIntegridadSha256` registrado, el sistema bloquea la aprobación electrónica, registra un `EventoBitacora` de alerta de seguridad por fallo de integridad y lanza `IntegridadActaInvalidaError` (Escenario 4).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La entidad `Practica` gobierna la transición formal `Evaluada → Completada` (`completar()`).
  - No se puede aprobar electrónicamente un acta si la práctica no se encuentra en estado `Evaluada` o si no cuenta con un `ActaFinal` previamente generada (Escenario 5, **RN-02**).
  - La entidad `ActaFinal` impone el orden secuencial estricto de firmas: el `Coordinador de prácticas` no puede aprobar si `aprobadaPorDocente` es `False` (Escenario 3, **RN-02**), y ningún actor puede registrar una aprobación duplicada si su firma ya fue asentada en firme (Escenario 6).

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/acta_final.py` *(Nuevo)*:
  - Entidad `ActaFinal` conforme al modelo de dominio UML (`docs/diagramas/01-logica.puml` y `docs/vistas/01-logica.md`):
    - Atributos:
      - `id: str`
      - `practica_id: str`
      - `numero_acta: str`
      - `fecha_emision: datetime`
      - `ruta_archivo_pdf: str`
      - `hash_integridad_sha256: str`
      - `aprobada_por_docente: bool = False`
      - `aprobada_por_coordinador: bool = False`
      - `docente_aprobador_id: Optional[str] = None`
      - `fecha_aprobacion_docente: Optional[datetime] = None`
      - `coordinador_aprobador_id: Optional[str] = None`
      - `fecha_aprobacion_coordinador: Optional[datetime] = None`
    - Métodos e invariantes de dominio:
      - Validación en construcción: `practica_id`, `numero_acta`, `ruta_archivo_pdf` y `hash_integridad_sha256` (cadena hexadecimal SHA-256 válida de 64 caracteres) no pueden estar vacíos; si `aprobada_por_coordinador` es `True` en la construcción, `aprobada_por_docente` también debe ser `True`.
      - `verificar_integridad_hash(hash_recalculado: str) -> None`: compara de forma segura en minúsculas `hash_recalculado` con `self._hash_integridad_sha256`; si no coinciden o el hash recalculado está vacío, lanza `IntegridadActaInvalidaError` (Escenarios 1, 2 y 4, **ADR-008**).
      - `aprobar_por_docente(docente_id: str, fecha_aprobacion: Optional[datetime] = None) -> None`:
        - Si `self._aprobada_por_docente` ya es `True`, lanza `ActaYaAprobadaPorActorError` indicando que la aprobación del docente asesor ya fue registrada previamente (Escenario 6).
        - Marca `self._aprobada_por_docente = True`, registra `docente_aprobador_id` y `fecha_aprobacion_docente` (Escenario 1).
      - `aprobar_por_coordinador(coordinador_id: str, fecha_aprobacion: Optional[datetime] = None) -> None`:
        - Si `self._aprobada_por_coordinador` ya es `True`, lanza `ActaYaAprobadaPorActorError` indicando que la aprobación del coordinador ya fue registrada previamente (Escenario 6).
        - Si `not self._aprobada_por_docente`, lanza `FaltaAprobacionDocentePreviaError` bloqueando la firma del coordinador por falta de firma previa del docente asesor (Escenario 3, **RN-02**).
        - Marca `self._aprobada_por_coordinador = True`, registra `coordinador_aprobador_id` y `fecha_aprobacion_coordinador` (Escenario 2).
      - Propiedad `esta_en_firme -> bool`: retorna `True` cuando `aprobada_por_docente and aprobada_por_coordinador`.
- `dominio/modelos/practica.py` *(Modificar)*:
  - Método de consulta `puede_aprobar_acta() -> bool`:
    - Retorna `True` únicamente cuando `self._estado_actual == EstadoPractica.EVALUADA`.
  - Método de transición `completar(acta_en_firme: bool = True, fecha_fin: Optional[datetime] = None) -> None`:
    - Verifica que `self._estado_actual == EstadoPractica.EVALUADA`; si ya está en `EstadoPractica.COMPLETADA`, lanza `ActaYaAprobadaPorActorError` (Escenario 6); si está en otro estado distinto a `Evaluada`, lanza `EstadoPracticaInvalidoParaAprobarActaError` (Escenario 5).
    - Verifica que `acta_en_firme` sea `True` (ambas firmas asentadas); de lo contrario lanza `FaltaAprobacionDocentePreviaError`.
    - Ejecuta `self._transicionar(EstadoPractica.COMPLETADA)` y actualiza `self._fecha_fin` si se proporciona (**ADR-010**, Escenario 2).
- `dominio/errores.py` *(Modificar)*:
  - Agregar las excepciones de dominio para CU-10:
    - `ActaFinalNoEncontradaError`: lanzada cuando la práctica no cuenta con un `ActaFinal` generada o el identificador del acta no existe (Escenario 5).
    - `EstadoPracticaInvalidoParaAprobarActaError`: lanzada cuando se intenta aprobar electrónicamente un acta sobre una práctica cuyo `estadoActual` no es `Evaluada` (Escenario 5).
    - `FaltaAprobacionDocentePreviaError`: lanzada cuando el `Coordinador de prácticas` intenta aprobar un `ActaFinal` que aún no cuenta con la firma electrónica previa del `DocenteAsesor` (`aprobadaPorDocente == False`) (Escenario 3).
    - `ActaYaAprobadaPorActorError`: lanzada cuando el `DocenteAsesor` o el `Coordinador de prácticas` intenta registrar nuevamente una aprobación electrónica que ya fue asentada en firme sobre el `ActaFinal` (Escenario 6).
    - `IntegridadActaInvalidaError`: lanzada cuando el hash SHA-256 recalculado del archivo PDF en el repositorio de actas no coincide con el `hashIntegridadSha256` registrado en el `ActaFinal` o el binario no está disponible (Escenario 4).
- `dominio/modelos/__init__.py` *(Modificar)*:
  - Exportar `ActaFinal` junto con las entidades del modelo de dominio.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/aprobacion_acta_dto.py` *(Nuevo)*:
  - `AprobarActaComando`: DTO inmutable de entrada (`@dataclass(frozen=True, slots=True)`):
    - `practica_id: str`
    - `actor_id: str`
    - `rol_actor: str`
    - `acta_id: Optional[str] = None`
    - `ip_origen: str = "127.0.0.1"`
  - `AprobacionActaRespuestaDTO`: DTO inmutable de salida (`@dataclass(frozen=True, slots=True)`):
    - `acta_id: str`
    - `numero_acta: str`
    - `practica_id: str`
    - `estado_practica: str`
    - `aprobada_por_docente: bool`
    - `aprobada_por_coordinador: bool`
    - `acta_en_firme: bool`
    - `hash_integridad_sha256: str`
    - `ruta_archivo_pdf: str`
    - `actor_aprobador_id: str`
    - `rol_aprobador: str`
    - `cupo_docente_liberado: bool`
    - `practicas_activas_docente: Optional[int]`
    - `fecha_aprobacion: datetime`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_acta_final.py` *(Nuevo)*:
  - Protocol `RepositorioActaFinalPort` (`@runtime_checkable`):
    - `guardar(acta: ActaFinal) -> None`
    - `actualizar(acta: ActaFinal) -> None`
    - `buscar_por_id(acta_id: str) -> Optional[ActaFinal]`
    - `buscar_por_practica(practica_id: str) -> Optional[ActaFinal]`
- `aplicacion/puertos/servicio_pdf_hash.py` *(Nuevo)*:
  - Protocol `ServicioPdfHashPort` (`@runtime_checkable`) (correspondiente al `Adaptador PDF y Hash` y `Repositorio de actas PDF` en `docs/vistas/03-desarrollo.md`):
    - `calcular_hash_sha256(contenido_pdf: bytes) -> str`
    - `obtener_binario_pdf(ruta_archivo_pdf: str) -> bytes`
    - `recalcular_hash_archivo(ruta_archivo_pdf: str) -> str`
    - `verificar_integridad_pdf(ruta_archivo_pdf: str, hash_esperado_sha256: str) -> bool`
- `aplicacion/puertos/publicador_eventos.py` *(Modificar)*:
  - Agregar DTO inmutable `EventoActaFinalEmitida`:
    - `practica_id: str`
    - `acta_id: str`
    - `numero_acta: str`
    - `estudiante_id: str`
    - `ruta_archivo_pdf: str`
    - `hash_integridad_sha256: str`
    - `fecha_emision: datetime`
  - Agregar método `publicar_acta_final_emitida(evento: EventoActaFinalEmitida) -> None` en `PublicadorEventosPort` (conforme al paso 79 de `docs/diagramas/secuencias/cu10-aprobar-acta.puml`: `Publica evento "ActaFinalEmitida" (id_practica, rutaArchivoPdf) [AMQP]`).
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Las operaciones `"aprobar_acta_docente"` y `"aprobar_acta_coordinador"` ya existen en `_MATRIZ_PERMISOS`.
  - Agregar método `validar_aprobacion_acta(rol_actor: str, usuario_id: Optional[str] = None) -> str`:
    - Verifica bajo política *deny-by-default* que el rol normalizado pertenezca exclusivamente a `{RolUsuario.DOCENTE.value, RolUsuario.DOCENTE_ASESOR.value, RolUsuario.COORDINADOR.value, RolUsuario.COORDINADOR_PRACTICAS.value}` y retorna la operación autorizada (`"aprobar_acta_docente"` o `"aprobar_acta_coordinador"`).
    - Si el rol es `Estudiante`, `SupervisorEmpresa`, vacío o desconocido, lanza `AccesoDenegadoError` (Escenarios 8 y 9).
- `aplicacion/casos_uso/aprobar_acta_electronicamente.py` *(Nuevo)*:
  - Clase `AprobarActaElectronicamenteCasoUso` (dentro del `Módulo Actas` de `docs/vistas/03-desarrollo.md`):
    - Inyecta `RepositorioPracticaPort`, `RepositorioActaFinalPort`, `RepositorioDocentePort`, `ServicioPdfHashPort`, `AutorizadorRBAC`, `PublicadorEventosPort` (opcional) y `ServicioCorreoPort` (opcional).
    - Método `ejecutar(comando: AprobarActaComando, contexto: Optional[ContextoUsuario] = None) -> AprobacionActaRespuestaDTO` (y `__call__`):
      1. **Autenticación y Autorización RBAC (ADR-004, ADR-005, EAC-03):**
         - Construye o valida el `ContextoUsuario` y ejecuta `autorizador_rbac.validar_aprobacion_acta(rol, actor_id)`.
         - Si el usuario no tiene sesión válida o su rol no es `DocenteAsesor` ni `Coordinador de prácticas` (por ejemplo, `Estudiante` o `SupervisorEmpresa`), registra de inmediato un `EventoBitacora` inmutable de rechazo en `< 1 minuto` y relanza `AccesoDenegadoError` garantizando `0 datos expuestos` (Escenarios 8 y 9).
      2. **Recuperación de la Práctica y validación de pertenencia contextual del Docente Asesor (RN-01, ADR-005):**
         - Busca la `Practica` por `comando.practica_id` (o a partir del `acta_id` si fue provisto). Si la práctica no existe, lanza `PracticaNoEncontradaError`.
         - Si el actor tiene rol `DocenteAsesor` (o `Docente`), invoca `autorizador_rbac.validar_pertenencia_docente(contexto_usuario, practica.docente_asesor_id, operacion="aprobar_acta_docente")`. Si la práctica pertenece a otro docente asesor, registra de inmediato un `EventoBitacora` por intento de acceso y firma sobre recurso ajeno y lanza `AccesoDenegadoError` con `0 datos expuestos` (Escenario 7).
      3. **Verificación de existencia de ActaFinal, duplicidad y máquina de estados (ADR-010, RN-02):**
         - Recupera el `ActaFinal` asociada a la práctica mediante `RepositorioActaFinalPort.buscar_por_practica(practica.id)`.
         - Si la práctica ya está en estado `Completada` (o si el `ActaFinal` ya tiene asentada la firma del rol que intenta aprobar), lanza `ActaYaAprobadaPorActorError` sin alterar ningún dato (Escenario 6).
         - Si la práctica está en un estado distinto a `Evaluada` (`Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `PendienteVerificacion` o `Rechazada`), lanza `EstadoPracticaInvalidoParaAprobarActaError` (Escenario 5).
         - Si no existe un `ActaFinal` generada para la práctica en estado `Evaluada`, lanza `ActaFinalNoEncontradaError` / `EstadoPracticaInvalidoParaAprobarActaError` informando que solo se puede aprobar un `ActaFinal` previamente generada sobre una práctica en estado `Evaluada` (Escenario 5).
      4. **Verificación de integridad criptográfica SHA-256 del binario PDF (ADR-008, PA-03):**
         - Obtiene el hash SHA-256 recalculado del archivo PDF desde `ServicioPdfHashPort.recalcular_hash_archivo(acta.ruta_archivo_pdf)` y ejecuta `acta.verificar_integridad_hash(hash_recalculado)`.
         - Si el archivo no existe, fue corrompido o el hash SHA-256 recalculado no coincide con `acta.hash_integridad_sha256`, registra de inmediato un `EventoBitacora` de alerta de seguridad por fallo de integridad del `ActaFinal` y lanza `IntegridadActaInvalidaError` sin asentar la firma ni cambiar el estado de la práctica (Escenario 4).
      5. **Ejecución del Paso 1 (Docente asesor) o Paso 2 (Coordinador de prácticas) (ADR-003, ADR-006, ADR-010):**
         - **Si el rol es `DocenteAsesor` (Paso 1 - Escenario 1):**
           - Invoca `acta.aprobar_por_docente(actor_id, ahora)`.
           - Actualiza `ActaFinal` en `RepositorioActaFinalPort` manteniendo `Practica` en estado `Evaluada`.
           - Registra atómicamente el `EventoBitacora` inmutable de aprobación electrónica de acta por docente con `huellaDigital` SHA-256.
         - **Si el rol es `Coordinador de prácticas` (Paso 2 - Escenarios 2 y 3):**
           - Invoca `acta.aprobar_por_coordinador(actor_id, ahora)` (si `aprobada_por_docente == False`, lanza `FaltaAprobacionDocentePreviaError`, Escenario 3).
           - Invoca `practica.completar(acta_en_firme=acta.esta_en_firme, fecha_fin=ahora)` transicionando la `Practica` de `Evaluada` a `Completada`.
           - Recupera al `DocenteAsesor` asignado (`practica.docente_asesor_id`) desde `RepositorioDocentePort`, invoca `docente.liberar_practica()` decrementando automáticamente en 1 su contador `practicasActivas` y lo actualiza en `RepositorioDocentePort` (Escenario 2).
           - Actualiza `ActaFinal` y `Practica` en sus repositorios y registra atómicamente el `EventoBitacora` inmutable de aprobación electrónica final de acta y cierre de práctica.
           - Publica el evento `EventoActaFinalEmitida` en `PublicadorEventosPort` y despacha la notificación por correo electrónico (`ServicioCorreoPort`) al `Estudiante` titular confirmando la culminación de la práctica con la referencia al PDF del `ActaFinal` (**ADR-001**, **OB-05**, Escenario 2).
      6. **Retorno:**
         - Retorna `AprobacionActaRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - Agregar `InMemoryRepositorioActaFinal(RepositorioActaFinalPort)`:
    - Almacena en memoria las instancias de `ActaFinal` indexadas por `id` y por `practica_id` (relación `1 a 0..1` entre `Practica` y `ActaFinal` según `docs/diagramas/01-logica.puml`).
    - Implementa `guardar`, `actualizar`, `buscar_por_id`, `buscar_por_practica`, `listar_todas` y `limpiar`.
- `infraestructura/adaptadores/adaptador_pdf_hash_simulado.py` *(Nuevo)*:
  - Clase `AdaptadorPdfHashSimulado(ServicioPdfHashPort)` (correspondiente al `Adaptador PDF y Hash` y al `Repositorio de actas PDF` en `docs/vistas/03-desarrollo.md` y `docs/vistas/02-procesos.md`):
    - Mantiene un almacén en memoria `_archivos_pdf: dict[str, bytes]` que simula el volumen local de archivos PDF (`vol_pdf`).
    - Implementa `guardar_binario_pdf(ruta_archivo_pdf: str, contenido_pdf: bytes) -> str` (retorna el hash SHA-256 calculado con `hashlib.sha256`), `obtener_binario_pdf(ruta_archivo_pdf: str) -> bytes`, `calcular_hash_sha256(contenido_pdf: bytes) -> str`, `recalcular_hash_archivo(ruta_archivo_pdf: str) -> str`, `verificar_integridad_pdf(ruta_archivo_pdf: str, hash_esperado_sha256: str) -> bool`, `alterar_binario_pdf(ruta_archivo_pdf: str, nuevo_contenido: bytes) -> None` (para pruebas deterministas de corrupción/adulteración del Escenario 4) y `limpiar() -> None`.
- `infraestructura/adaptadores/broker_memoria.py` *(Modificar)*:
  - Agregar la lista `_eventos_acta_emitida: list[EventoActaFinalEmitida]` en `InMemoryBrokerMensajes`.
  - Implementar `publicar_acta_final_emitida(evento: EventoActaFinalEmitida) -> None` y `obtener_eventos_acta_emitida() -> list[EventoActaFinalEmitida]`.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `AprobarActaElectronicamenteCasoUso`, `AprobarActaComando`, `AprobacionActaRespuestaDTO`, `ActaFinal`, `InMemoryRepositorioActaFinal` y `AdaptadorPdfHashSimulado`.
  - Agregar `caso_uso_aprobar_acta: AprobarActaElectronicamenteCasoUso`, `repositorio_acta_final: InMemoryRepositorioActaFinal` y `servicio_pdf_hash: AdaptadorPdfHashSimulado` en `SistemaPracticasEmpresariales` e `inicializar_sistema()`.
  - Incluir la demostración CLI de `CU-10` (Paso 1: firma del `DocenteAsesor`; Paso 2: firma del `Coordinador de prácticas`, transición a `Completada`, liberación de cupo del docente y emisión del evento `ActaFinalEmitida`) en `main()`.

---

## Flujo

Secuencia basada directamente en `docs/diagramas/secuencias/cu10-aprobar-acta.puml` (ESC-04):

1. **Paso 1: Aprobación electrónica del Docente asesor (`POST /actas/{id}/aprobar`):**
   - El `DocenteAsesor` solicita registrar su firma electrónica sobre el `ActaFinal`.
   - Se valida la identidad institucional (`SSO Institucional` / `ContextoUsuario`, **ADR-004**) y el `AutorizadorRBAC` verifica bajo política *deny-by-default* que el rol sea `DocenteAsesor` y que sea el tutor asignado a la `Practica` (**ADR-005**, **RN-01**). Si falla, se registra `EventoBitacora` en `< 1 min` y se rechaza con `0 datos expuestos` (Escenarios 7, 8 y 9, **EAC-03**).
   - Se consulta la `Practica` y el `ActaFinal` (`hashIntegridadSha256`), verificando que la práctica esté en estado `Evaluada` y que el docente no haya firmado previamente (Escenarios 5 y 6, **ADR-010**).
   - Se lee el binario PDF desde el `Repositorio de actas PDF` (`ServicioPdfHashPort`), se recalcula su huella SHA-256 y se comprueba que coincide exactamente con `ActaFinal.hashIntegridadSha256` (**ADR-008**). Si hay discrepancia, se bloquea la firma y se registra un `EventoBitacora` de alerta de integridad (Escenario 4).
   - Se actualiza atómicamente `ActaFinal` (`aprobadaPorDocente = True`) y se inserta el `EventoBitacora` Append-Only con huella digital SHA-256 (**ADR-006**), manteniendo la `Practica` en estado `Evaluada`.
2. **Paso 2: Aprobación electrónica final del Coordinador de prácticas (`POST /actas/{id}/aprobar`):**
   - El `Coordinador de prácticas` revisa y aprueba electrónicamente el `ActaFinal`.
   - Se valida la identidad institucional y el `AutorizadorRBAC` verifica que el rol sea `Coordinador de prácticas` (**ADR-005**).
   - **Guarda `break` [`ActaFinal.aprobadaPorDocente == False` - RN-02]:**
     - Si el `DocenteAsesor` aún no ha firmado el acta, se deniega la operación (`409 Conflict` / `FaltaAprobacionDocentePreviaError`) informando que falta la firma previa del docente asesor (Escenario 3, **ADR-010**).
   - Se recalcula el hash SHA-256 del binario PDF en el `Repositorio de actas PDF` y se verifica que coincide con `ActaFinal.hashIntegridadSha256` (**ADR-008**).
   - En una transacción atómica:
     - Se actualiza `ActaFinal` (`aprobadaPorCoordinador = True`).
     - Se transiciona `Practica` de `Evaluada` a `Completada` (**ADR-010**).
     - Se decrementa automáticamente en 1 el contador `practicasActivas` del `DocenteAsesor` asignado (`docente.liberar_practica()`), liberando su cupo disponible.
     - Se inserta el `EventoBitacora` inmutable de cierre (**ADR-006**).
3. **Publicación de evento y notificación asíncrona al Estudiante:**
   - Se publica el evento `"ActaFinalEmitida"` (`id_practica`, `rutaArchivoPdf`) en el `Broker de mensajes` (**ADR-001**).
   - Se envía la notificación y referencia del acta final en PDF por correo electrónico al `Estudiante` titular (**OB-05**).

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `ActaFinal`: documento oficial de cierre con `numeroActa`, `fechaEmision`, `rutaArchivoPdf`, `hashIntegridadSha256`, `aprobadaPorDocente` y `aprobadaPorCoordinador` (**ADR-008**).
- `Practica`: agregado raíz que formaliza su cierre en `0..1` `ActaFinal` y transiciona su `estadoActual` de `Evaluada` a `Completada` únicamente cuando ambas firmas electrónicas han sido asentadas (**ADR-010**, **RN-02**).
- `DocenteAsesor`: tutor académico asignado a la práctica, responsable de la primera firma electrónica (**RN-01**, **ADR-005**); al completarse la práctica con la segunda firma, su contador `practicasActivas` se decrementa automáticamente en 1 liberando cupo (**RT-01**).
- `Estudiante`: practicante titular que recibe la notificación oficial de culminación junto con su `ActaFinal` en PDF (**OB-05**).
- `EventoBitacora`: registro inmutable *Append-Only* con huella SHA-256 para cada aprobación electrónica asentada, fallo de integridad del PDF e intento de acceso o firma no autorizado (**ADR-006**, **PA-03**, **EAC-03**).

---

## Fuera de alcance

- Renderizado inicial de la plantilla HTML/CSS a archivo binario PDF y creación inicial de la entidad `ActaFinal` (cubierto en `CU-09: Generar acta final de la práctica`).
- Flujo de rechazo, devolución o anulación de un `ActaFinal` generada (conforme a la especificación aprobada en `spec.md`, `CU-10` contempla únicamente la acción de aprobación electrónica).
- Configuración o modificación de plantillas HTML/CSS y reglas normativas por programa académico (cubierto en `CU-12`).
- Exportación de consolidados históricos de actas y bitácoras para acreditación (cubierto en `CU-14`).

---

## Decisiones pendientes

Ninguna. Todas las reglas de negocio y decisiones arquitectónicas para `CU-10` (secuencia estricta de firmas `DocenteAsesor → Coordinador de prácticas`, verificación de integridad SHA-256 del binario PDF antes de firmar, decremento automático de `practicasActivas` del `DocenteAsesor` al transicionar la `Practica` a `Completada`, alcance exclusivo de aprobación electrónica, control RBAC *deny-by-default* con pertenencia contextual y bitácora inmutable *Append-Only*) están completamente definidas en `spec.md` y respaldadas por los **ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-008 y ADR-010**.

