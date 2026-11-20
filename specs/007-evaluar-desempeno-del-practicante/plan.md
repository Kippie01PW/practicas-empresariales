# Plan: 007 Evaluar desempeño del practicante

## Decisiones que aplican

- **ADR-001 (Resiliencia e integración asíncrona):**
  - Una vez asentada la evaluación de desempeño, el caso de uso notifica al `DocenteAsesor` asignado a la práctica (mediante `ServicioCorreoPort`) informando que la práctica ha pasado a estado `Evaluada` y está lista para generar el `ActaFinal` (conforme a `docs/diagramas/secuencias/cu07-evaluar-desempeno.puml`). Si el despacho de correo experimenta un fallo transitorio, no revierte la transacción atómica de la evaluación.
- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Organización estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`, con `main.py` como único punto de composición e inyección de dependencias.
  - La capa de dominio incorpora la entidad `EvaluacionDesempeno` y las excepciones de negocio asociadas, y extiende la entidad raíz `Practica` con la transición formal `registrar_evaluacion_desempeno()` (`EnEjecucion → Evaluada`), sin importar nada de `aplicacion/` ni de `infraestructura/`.
  - La capa de aplicación define el caso de uso `EvaluarDesempenoCasoUso` (dentro del `Módulo Seguimiento y Evaluación` según `docs/vistas/03-desarrollo.md`), sus DTOs inmutables de entrada y salida, y el puerto `RepositorioEvaluacionDesempenoPort`.
  - La capa de infraestructura provee el adaptador en memoria `InMemoryRepositorioEvaluacionDesempeno` y reutiliza `InterceptorIdentidad` e `InMemoryRepositorioTokenEvaluacion`.
- **ADR-003 (Plataforma tecnológica y persistencia transaccional):**
  - Implementación en Python 3.12 con tipado estático (`typing`), una clase o componente principal por archivo y DTOs inmutables (`@dataclass(frozen=True, slots=True)`).
  - La persistencia de `EvaluacionDesempeno`, la actualización de `Practica` a estado `Evaluada`, el marcado de `TokenEvaluacion` como `usado = True` y la inserción de `EventoBitacora` se ejecutan de forma atómica sobre los repositorios en memoria deterministas.
- **ADR-004 (Esquema de autenticación híbrida con enlaces criptográficos efímeros):**
  - El `SupervisorEmpresa` externo accede al formulario de rúbrica y envía la evaluación utilizando un enlace criptográfico efímero (`TokenEvaluacion`, Magic Link firmado con HMAC-SHA256) sin requerir cuenta en el directorio activo universitario (**RN-04**, **SUP-02**).
  - El token tiene vigencia máxima de 15 días calendario y carácter de un solo uso: consultar el formulario (`obtener_formulario_evaluacion`) verifica el token sin consumirlo (`usado = False`), mientras que registrar la evaluación en firme (`ejecutar`) marca el token con `usado = True`.
  - Cualquier intento de consulta o envío con token alterado, firma HMAC inválida, expirado (`> 15 días`) o previamente utilizado es rechazado de inmediato con 0 datos expuestos (**EAC-03**).
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política centralizada *deny-by-default*.
  - La operación `evaluar_desempeno` está permitida exclusivamente para el rol `SupervisorEmpresa` (`RolUsuario.SUPERVISOR_EMPRESA` / `RolUsuario.SUPERVISOR`). Cualquier intento por roles internos (`Estudiante`, `DocenteAsesor`, `CoordinadorPracticas`) es rechazado con registro en bitácora (**RN-03**).
  - Validación de pertenencia contextual de datos (*Context-Based Access Control*, **RN-01**): el supervisor autenticado debe coincidir exactamente con el `supervisor_empresa_id` vinculado a la `Practica`.
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada registro exitoso de `EvaluacionDesempeno` y transición a `Evaluada` inserta atómicamente un `EventoBitacora` inmutable con huella digital SHA-256, `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada`.
  - Todo intento de acceso rechazado (token expirado, token inválido/alterado, token ya usado, violación de pertenencia contextual o rol no autorizado) registra de inmediato un `EventoBitacora` en menos de 1 minuto garantizando 0 datos expuestos (**EAC-03**).
- **ADR-007 (Configuración declarativa de reglas versionadas por programa):**
  - La presentación del formulario y la validación de `respuestasRubrica` se realizan estrictamente contra los `criteriosRubrica` de la versión de `ReglaPrograma` vinculada a la `Practica` al momento de su postulación (`practica.regla_programa_id`), asegurando un 0% de alteración ante nuevas versiones publicadas posteriormente (**EAC-01**).
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La entidad `Practica` gobierna la transición formal `EnEjecucion → Evaluada`.
  - Solo se permite registrar la `EvaluacionDesempeno` cuando `practica.estado_actual == EstadoPractica.EN_EJECUCION`. Si la práctica está en cualquier otro estado (`PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `Evaluada`, `Completada` o `Rechazada`), la operación es denegada sin consumir el `TokenEvaluacion` (**RN-02**).
  - Se permite registrar la evaluación de desempeño mientras la práctica está en `EnEjecucion` independientemente del acumulado de horas aprobadas; la validación del cumplimiento total de `horasRequeridas` se exige al generar el `ActaFinal` en CU-09.

---

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/evaluacion_desempeno.py` *(Nuevo)*:
  - Entidad `EvaluacionDesempeno` conforme al modelo de dominio UML (`docs/diagramas/01-logica.puml` y `docs/vistas/01-logica.md`):
    - Atributos:
      - `id: str`
      - `practica_id: str`
      - `supervisor_id: str`
      - `calificacion_cuantitativa: float`
      - `observaciones: Optional[str]`
      - `respuestas_rubrica: dict[str, float]`
      - `fecha_evaluacion: datetime`
    - Constantes de negocio:
      - `CALIFICACION_MINIMA: float = 0.0`
      - `CALIFICACION_MAXIMA: float = 5.0`
      - `UMBRAL_APROBACION: float = 3.0`
    - Invariantes de dominio validados en construcción y métodos:
      - `calificacion_cuantitativa` debe ser numérica dentro de la escala `[0.0, 5.0]`; de lo contrario lanza `CalificacionCuantitativaInvalidaError` (Escenario 6).
      - Si `calificacion_cuantitativa < 3.0` (calificación reprobatoria), `observaciones` es obligatoria y no puede estar vacía ni en blanco; si falta, lanza `ObservacionesReprobatoriaRequeridasError` (Escenarios 3, 4 y 5). Si `calificacion_cuantitativa >= 3.0`, las observaciones son opcionales.
      - `respuestas_rubrica` debe ser un diccionario no vacío `dict[str, float]` que cubra el 100% de las claves definidas en `criterios_rubrica` de la `ReglaPrograma` vinculada, y cada criterio debe tener una calificación numérica en el rango `[0.0, 5.0]`; si faltan criterios, sobran criterios no definidos o algún valor está fuera de `[0.0, 5.0]`, lanza `RespuestasRubricaInvalidasError` (Escenario 7).
      - Propiedad `es_aprobatoria -> bool`: retorna `True` si `calificacion_cuantitativa >= 3.0`.
- `dominio/modelos/practica.py` *(Modificar)*:
  - Método de consulta `puede_evaluar_desempeno() -> bool`:
    - Retorna `True` únicamente cuando `self._estado_actual == EstadoPractica.EN_EJECUCION`.
  - Método de transición `registrar_evaluacion_desempeno(fecha_fin: Optional[datetime] = None) -> None`:
    - Verifica que `self._estado_actual == EstadoPractica.EN_EJECUCION`; si la práctica ya está en `EstadoPractica.EVALUADA`, lanza `PracticaYaEvaluadaError` (Escenarios 11 y 12); si está en cualquier otro estado distinto a `EnEjecucion`, lanza `EstadoPracticaInvalidoParaEvaluacionError` (Escenario 11).
    - Ejecuta `self._transicionar(EstadoPractica.EVALUADA)` y asigna `self._fecha_fin = fecha_fin or datetime.now()` (**ADR-010**).
- `dominio/errores.py` *(Modificar)*:
  - Agregar las excepciones de dominio para CU-07:
    - `EstadoPracticaInvalidoParaEvaluacionError`: lanzada cuando se intenta evaluar una práctica cuyo `estadoActual` no es `EnEjecucion` (Escenario 11).
    - `PracticaYaEvaluadaError`: lanzada cuando la práctica ya cuenta con una `EvaluacionDesempeno` registrada en firme (Escenario 12).
    - `CalificacionCuantitativaInvalidaError`: lanzada cuando la `calificacionCuantitativa` está fuera de la escala `[0.0, 5.0]` (Escenario 6).
    - `ObservacionesReprobatoriaRequeridasError`: lanzada cuando la `calificacionCuantitativa` es reprobatoria (`< 3.0`) y no se suministran `observaciones` justificativas no vacías (Escenario 5).
    - `RespuestasRubricaInvalidasError`: lanzada cuando `respuestasRubrica` está vacía, omite criterios obligatorios de `criteriosRubrica` de la `ReglaPrograma` vinculada o contiene valores fuera de la escala `[0.0, 5.0]` (Escenario 7).
- `dominio/modelos/__init__.py` *(Modificar)*:
  - Exportar `EvaluacionDesempeno`.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/evaluacion_desempeno_dto.py` *(Nuevo)*:
  - `ConsultarFormularioEvaluacionComando`: DTO inmutable de entrada para abrir el enlace de evaluación (Escenario 1):
    - `token_acceso: str`
    - `practica_id: Optional[str] = None`
    - `ip_origen: str = "127.0.0.1"`
  - `FormularioEvaluacionRespuestaDTO`: DTO inmutable de salida con los datos del practicante y la rúbrica dinámica de su `ReglaPrograma` vinculada (Escenarios 1 y 16):
    - `practica_id: str`
    - `estudiante_id: str`
    - `supervisor_id: str`
    - `estado_practica: str`
    - `regla_programa_id: str`
    - `programa_academico: str`
    - `version_regla: str`
    - `criterios_rubrica: dict[str, Any]`
    - `escala_minima: float`
    - `escala_maxima: float`
    - `umbral_aprobacion: float`
    - `mensaje: str`
  - `EvaluarDesempenoComando`: DTO inmutable de entrada para enviar la evaluación de desempeño:
    - `practica_id: str`
    - `calificacion_cuantitativa: float`
    - `respuestas_rubrica: dict[str, float]`
    - `observaciones: Optional[str] = None`
    - `token_acceso: Optional[str] = None`
    - `supervisor_id: Optional[str] = None`
    - `ip_origen: str = "127.0.0.1"`
  - `EvaluacionDesempenoRespuestaDTO`: DTO inmutable de salida tras registrar la evaluación:
    - `evaluacion_id: str`
    - `practica_id: str`
    - `supervisor_id: str`
    - `calificacion_cuantitativa: float`
    - `es_aprobatoria: bool`
    - `observaciones: Optional[str]`
    - `respuestas_rubrica: dict[str, float]`
    - `estado_practica: str`
    - `regla_programa_id: str`
    - `version_regla: str`
    - `token_consumido: bool`
    - `fecha_evaluacion: datetime`
    - `mensaje: str`
- `aplicacion/puertos/repositorio_evaluacion_desempeno.py` *(Nuevo)*:
  - Protocol `RepositorioEvaluacionDesempenoPort` (`@runtime_checkable`):
    - `guardar(evaluacion: EvaluacionDesempeno) -> None`
    - `buscar_por_id(evaluacion_id: str) -> Optional[EvaluacionDesempeno]`
    - `buscar_por_practica(practica_id: str) -> Optional[EvaluacionDesempeno]`
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - La operación `"evaluar_desempeno"` ya se encuentra en `_MATRIZ_PERMISOS` para `{RolUsuario.SUPERVISOR.value, RolUsuario.SUPERVISOR_EMPRESA.value}`.
  - Agregar método `validar_evaluacion_desempeno(rol_actor: str, usuario_id: Optional[str] = None, operacion: str = "evaluar_desempeno") -> None` para validar explícitamente que solo el rol `SupervisorEmpresa` (o `Supervisor`) ejecute CU-07 bajo política *deny-by-default* (Escenario 14).
- `aplicacion/casos_uso/evaluar_desempeno.py` *(Nuevo)*:
  - Clase `EvaluarDesempenoCasoUso` (Módulo Seguimiento y Evaluación):
    - Inyecta `RepositorioPracticaPort`, `RepositorioReglaProgramaPort`, `RepositorioEvaluacionDesempenoPort`, `RepositorioTokenEvaluacionPort`, `RepositorioDocentePort` (opcional), `ServicioCorreoPort` (opcional), `AutorizadorRBAC` e `InterceptorIdentidad` (opcional).
    - Método `obtener_formulario_evaluacion(comando: ConsultarFormularioEvaluacionComando) -> FormularioEvaluacionRespuestaDTO`:
      1. Verifica el `TokenEvaluacion` mediante `InterceptorIdentidad` / `RepositorioTokenEvaluacionPort`. Si el token es alterado, expirado (`> 15 días`) o ya fue usado, registra inmediatamente un `EventoBitacora` de rechazo en `< 1 min` y lanza la excepción correspondiente con 0 datos expuestos (Escenarios 8, 9, 10 y 15, **EAC-03**).
      2. Recupera la `Practica` vinculada al token y valida pertenencia contextual del supervisor (`practica.supervisor_empresa_id == token.supervisor_id`).
      3. Recupera la `ReglaPrograma` vinculada a la práctica (`practica.regla_programa_id`, **ADR-007**, **EAC-01**).
      4. Mantiene el `TokenEvaluacion` con `usado = False` y retorna `FormularioEvaluacionRespuestaDTO` con los datos del estudiante y los `criteriosRubrica` de la versión de `ReglaPrograma` vinculada (Escenario 1).
    - Método `ejecutar(comando: EvaluarDesempenoComando, contexto: Optional[ContextoUsuario] = None) -> EvaluacionDesempenoRespuestaDTO` (y `__call__`):
      1. **Autenticación y Autorización (ADR-004, ADR-005, EAC-03):**
         - Si se provee `comando.token_acceso`, autentica el token efímero verificando firma HMAC, vigencia `<= 15 días`, estado `usado == False` y correspondencia con `comando.practica_id`. Ante fallo, registra `EventoBitacora` inmediato y rechaza con 0 datos expuestos (Escenarios 8, 9, 10 y 15).
         - Si se provee `contexto`, valida el rol con `autorizador_rbac.validar_evaluacion_desempeno(contexto.rol, contexto.usuario_id)`. Si un `Estudiante`, `DocenteAsesor` o `CoordinadorPracticas` intenta evaluar, registra `EventoBitacora` y lanza `AccesoDenegadoError` (Escenario 14).
      2. **Recuperación de la Práctica y pertenencia contextual (RN-01, ADR-005):**
         - Busca la `Practica` en `RepositorioPracticaPort.buscar_por_id(comando.practica_id)`. Si no existe, lanza `PracticaNoEncontradaError`.
         - Verifica que el supervisor autenticado coincida con `practica.supervisor_empresa_id`. Si pertenece a otro supervisor, registra `EventoBitacora` por intento de acceso a recurso ajeno y lanza `SupervisorNoAsignadoAPracticaError` con 0 datos expuestos (Escenario 13).
      3. **Verificación de unicidad de evaluación y máquina de estados (ADR-010, RN-02):**
         - Consulta `RepositorioEvaluacionDesempenoPort.buscar_por_practica(practica.id)`. Si ya existe una evaluación previa para la práctica, lanza `PracticaYaEvaluadaError` sin consumir el token (Escenario 12).
         - Verifica que la práctica esté en estado `EstadoPractica.EN_EJECUCION` (`practica.puede_evaluar_desempeno()`). Si está en un estado distinto, lanza `EstadoPracticaInvalidoParaEvaluacionError` sin consumir el token (Escenario 11).
         - Conforme a la regla de negocio 2, permite evaluar en `EnEjecucion` aunque `horasAcumuladasAprobadas < horasRequeridas`, difiriendo la validación del total de horas a CU-09 (Escenario 3).
      4. **Recuperación de la ReglaPrograma vinculada y validación de rúbrica y calificación (ADR-007, EAC-01):**
         - Recupera la `ReglaPrograma` mediante `RepositorioReglaProgramaPort.buscar_por_id(practica.regla_programa_id)`.
         - Instancia `EvaluacionDesempeno` validando:
           - `calificacion_cuantitativa` en `[0.0, 5.0]` (Escenario 6).
           - `observaciones` obligatorias cuando `calificacion_cuantitativa < 3.0` (Escenarios 4 y 5).
           - `respuestas_rubrica` completas y en `[0.0, 5.0]` para todos los `criterios_rubrica` de la versión de `ReglaPrograma` vinculada a la práctica (Escenarios 7 y 16).
         - Si alguna validación de dominio falla, no se persiste la evaluación, la práctica permanece en `EnEjecucion` y el `TokenEvaluacion` continúa con `usado = False`.
      5. **Transición de estado, consumo de token y persistencia atómica (ADR-003, ADR-004, ADR-006, ADR-010):**
         - Invoca `practica.registrar_evaluacion_desempeno(ahora)` cambiando el estado de `EnEjecucion` a `Evaluada`.
         - Si se usó `TokenEvaluacion`, invoca `token_entidad.marcar_usado(ahora)` y lo guarda en `RepositorioTokenEvaluacionPort`.
         - Guarda la `EvaluacionDesempeno` en `RepositorioEvaluacionDesempenoPort` y actualiza la `Practica` en `RepositorioPracticaPort`.
         - Registra atómicamente un `EventoBitacora` con acción `"Evaluación de desempeño registrada"`, identificador del supervisor, rol `SupervisorEmpresa`, IP de origen y detalles de la calificación y transición.
      6. **Notificación al DocenteAsesor (ADR-001):**
         - Envía correo electrónico al `DocenteAsesor` asignado a la práctica mediante `ServicioCorreoPort` informando que la evaluación fue registrada y la práctica está lista para generar el `ActaFinal` (Escenario 2).
      7. **Retorno:**
         - Retorna `EvaluacionDesempenoRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - Agregar `InMemoryRepositorioEvaluacionDesempeno(RepositorioEvaluacionDesempenoPort)`:
    - Almacena en memoria las instancias de `EvaluacionDesempeno` indexadas por `id` y por `practica_id` (relación `1 a 0..1` entre `Practica` y `EvaluacionDesempeno` según `01-logica.puml`).
    - Implementa `guardar`, `buscar_por_id`, `buscar_por_practica`, `listar_todas` y `limpiar`.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Importar `EvaluarDesempenoCasoUso`, `ConsultarFormularioEvaluacionComando`, `EvaluarDesempenoComando`, `EvaluacionDesempenoRespuestaDTO` e `InMemoryRepositorioEvaluacionDesempeno`.
  - Agregar `caso_uso_evaluar_desempeno: EvaluarDesempenoCasoUso` y `repositorio_evaluacion: InMemoryRepositorioEvaluacionDesempeno` en `SistemaPracticasEmpresariales`.
  - Instanciar e inyectar `InMemoryRepositorioEvaluacionDesempeno` y `EvaluarDesempenoCasoUso` en `inicializar_sistema()`.
  - Incluir la demostración CLI de CU-07 en `main()`.

---

## Flujo

Secuencia basada directamente en `docs/diagramas/secuencias/cu07-evaluar-desempeno.puml` (ESC-02):

1. **Apertura del enlace criptográfico efímero y consulta de la rúbrica (`GET /evaluaciones/{token}`):**
   - El `SupervisorEmpresa` abre el enlace recibido por correo (Magic Link).
   - `InterceptorIdentidad` verifica la firma criptográfica HMAC-SHA256 del token y consulta `TokenEvaluacion` en `RepositorioTokenEvaluacionPort` (`vigencia <= 15 días` y `usado == False`, **ADR-004**).
   - **Guarda `break` [token alterado, ya utilizado o emitido hace más de 15 días - EAC-03]:**
     - Se inserta de inmediato un `EventoBitacora` (`AccesoRechazadoTokenInvalido`, `AccesoRechazadoTokenExpirado` o `AccesoRechazadoTokenYaUsado`) con IP, fecha y hora en `< 1 minuto` (**ADR-006**).
     - Se deniega el acceso sin exponer ningún dato del estudiante ni de la práctica (`0 datos expuestos`).
   - Si el token es válido, se consulta la `Practica` y los `criteriosRubrica` de su `ReglaPrograma` vinculada (**ADR-007**, **EAC-01**) y se retorna `FormularioEvaluacionRespuestaDTO` manteniendo `usado == False`.
2. **Diligenciamiento y envío de la evaluación (`POST /evaluaciones/{token}`):**
   - El `SupervisorEmpresa` envía las calificaciones por criterio (`respuestasRubrica`), la `calificacionCuantitativa` (escala `0.0` a `5.0`) y las `observaciones`.
   - Se verifica nuevamente el token HMAC (o el contexto RBAC bajo política *deny-by-default*, **ADR-005**) y la pertenencia contextual del supervisor sobre la práctica (**RN-01**).
   - Se verifica en el dominio que la `Practica` no tenga una evaluación previa y que su `estadoActual` sea formalmente `EnEjecucion` (**ADR-010**, **RN-02**).
   - Se construye y valida la entidad `EvaluacionDesempeno` contra los `criteriosRubrica` de la `ReglaPrograma` vinculada, verificando la escala `0.0 a 5.0` y exigiendo `observaciones` no vacías si la `calificacionCuantitativa < 3.0`.
3. **Transacción atómica y transición de estado:**
   - Se persiste `EvaluacionDesempeno` en `RepositorioEvaluacionDesempenoPort`.
   - Se marca `TokenEvaluacion` con `usado = True` y se guarda en `RepositorioTokenEvaluacionPort`.
   - Se transiciona la `Practica` de `EnEjecucion` a `Evaluada` (`practica.registrar_evaluacion_desempeno()`) y se actualiza en `RepositorioPracticaPort`.
   - Se inserta el `EventoBitacora` inmutable de confirmación (**ADR-006**).
4. **Notificación asíncrona al Docente Asesor:**
   - Se notifica por correo electrónico al `DocenteAsesor` asignado que la práctica ha sido evaluada y está lista para generar el `ActaFinal` (CU-09).

---

## Datos

Entidades del modelo de dominio que intervienen (`docs/vistas/01-logica.md` y `docs/diagramas/01-logica.puml`):

- `EvaluacionDesempeno`: calificación cualitativa y cuantitativa asentada por el supervisor externo; contiene `id`, `practica_id`, `supervisor_id`, `calificacionCuantitativa` (`0.0` a `5.0`), `observaciones` (obligatorias si `< 3.0`), `respuestasRubrica` (`dict[str, float]` alineado con `criteriosRubrica`) y `fechaEvaluacion`.
- `Practica`: agregado raíz que recibe `0..1` `EvaluacionDesempeno` y transiciona su `estadoActual` de `EnEjecucion` a `Evaluada` (**ADR-010**).
- `TokenEvaluacion`: credencial criptográfica efímera (Magic Link HMAC-SHA256) de un solo uso y vigencia de 15 días calendario vinculada a la práctica y al supervisor (**ADR-004**).
- `ReglaPrograma`: configuración declarativa versionada vinculada a la práctica al iniciar; provee los `criteriosRubrica` inmutables frente a cambios normativos posteriores (**ADR-007**, **EAC-01**).
- `SupervisorEmpresa`: jefe inmediato externo autorizado para evaluar el desempeño del practicante bajo su supervisión (**RN-01**, **RN-04**).
- `DocenteAsesor`: tutor académico asignado a la práctica, receptor de la notificación de evaluación completada.
- `Estudiante`: practicante titular evaluado.
- `EventoBitacora`: registro inmutable *Append-Only* con huella SHA-256 para el asentamiento de la evaluación y para cualquier intento de acceso rechazado (**ADR-006**, **EAC-03**).

---

## Fuera de alcance

- Validación o bloqueo por incumplimiento del total de `horasRequeridas` al momento de evaluar (diferido exclusivamente a la generación del `ActaFinal` en CU-09).
- Generación del documento `ActaFinal` en PDF y cálculo de su hash SHA-256 (cubierto en CU-09).
- Aprobación y firma electrónica del acta final por `DocenteAsesor` y `Coordinador de prácticas` (cubierto en CU-10).
- Envío programado de recordatorios automáticos por vencimiento de plazos de evaluación (cubierto en CU-08).
- Registro y validación de reportes semanales de horas (cubiertos en CU-04 y CU-05).
- Configuración o versionamiento de nuevas reglas y rúbricas de programa (cubierto en CU-12).

---

## Decisiones pendientes

Ninguna. Las tres aclaraciones de negocio (escala cuantitativa de `0.0` a `5.0` con validación de `respuestasRubrica` contra `criteriosRubrica`, permiso para registrar la evaluación en estado `EnEjecucion` difiriendo la exigencia del total de horas a CU-09, y obligatoriedad de `observaciones` únicamente cuando la calificación es reprobatoria `< 3.0`) han quedado incorporadas en `spec.md` y están respaldadas por los **ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007 y ADR-010**.
