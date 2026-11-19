# Plan: 004 Registrar horas de práctica semanales

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas concéntricas: `dominio/`, `aplicacion/` e `infraestructura/`.
  - La capa de dominio define la entidad `RegistroHoras` y extiende la entidad `Practica` sin acoplamiento a frameworks ni librerías externas.
  - La capa de aplicación define el caso de uso `RegistrarHorasCasoUso` (dentro del Módulo Seguimiento y Evaluación según `03-desarrollo.md`), sus DTOs inmutables de entrada y salida, y los puertos necesarios.
  - La capa de infraestructura provee el adaptador en memoria `InMemoryRepositorioRegistroHoras` y extiende `InMemoryRepositorioPractica`.
  - `main.py` actúa como único punto de composición e inyección de dependencias.
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política *deny-by-default*.
  - La operación `registrar_horas` está restringida exclusivamente a usuarios autenticados con rol `Estudiante` (`RolUsuario.ESTUDIANTE`).
  - Validación de pertenencia contextual de datos (*Context-Based Access Control*, RN-01): el estudiante autenticado solo puede registrar horas en su propia práctica (coincidencia de `usuario_id` o `documento` con el titular).
  - Cualquier intento de acceso por roles no autorizados o estudiantes no titulares es denegado inmediatamente, registrando la alerta en la bitácora de auditoría sin exponer datos de la práctica (cumpliendo **EAC-03**).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Registro inmutable de auditoría mediante `EventoBitacora` para la transición de estado de la práctica (`Asignada → EnEjecucion`) al registrar el primer reporte de horas.
  - Registro inmediato de intentos de acceso denegados por RBAC o violación de pertenencia en menos de 1 minuto con IP, fecha y hora (**EAC-03**).
- **ADR-007 (Configuración declarativa de reglas de negocio y plantillas versionadas por programa):**
  - Cada práctica permanece vinculada a la `ReglaPrograma` vigente al momento de su inicio, la cual define las `horasRequeridas` de referencia institucional.
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La entidad `Practica` gobierna su ciclo de vida y controla las transiciones formales:
    - `Asignada → EnEjecucion`: transición ejecutada ante el primer reporte de horas semanales del estudiante.
    - Estados válidos para registrar horas: `EnEjecucion` (y `Asignada` que transiciona automáticamente a `EnEjecucion`).
    - Intentos de registrar horas en estados no permitidos (`PendienteVerificacion`, `Solicitada`, `Rechazada`, `Aprobada`, `Evaluada`, `Completada`) son rechazados por la máquina de estados con `TransicionEstadoInvalidaError` o `EstadoPracticaInvalidoParaRegistroHorasError` (RN-02).

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/registro_horas.py` *(Nuevo)*:
  - Enumeración `EstadoValidacionHoras`:
    - `PENDIENTE = "Pendiente"`
    - `APROBADO = "Aprobado"`
    - `RECHAZADO = "Rechazado"`
  - Entidad `RegistroHoras`:
    - Atributos del modelo de dominio (`01-logica.puml`): `id: str`, `practica_id: str`, `semana: int`, `cantidad_horas: int`, `descripcion_actividades: str`, `estado_validacion: EstadoValidacionHoras`, `fecha_registro: datetime`.
    - Invariantes de dominio:
      - `semana >= 1`: valida número de semana positivo (Escenario 7).
      - `0 < cantidad_horas <= 60`: valida que las horas sean positivas y no excedan el límite reglamentario semanal (Escenarios 4 y 5).
      - `descripcion_actividades` obligatoria no vacía (Escenario 6).
- `dominio/modelos/practica.py` *(Modificar)*:
  - Método en `Practica`:
    - `iniciar_ejecucion() -> None`: valida que el estado actual sea `EstadoPractica.ASIGNADA` y transiciona formalmente a `EstadoPractica.EN_EJECUCION` según `_TRANSICIONES_VALIDAS` (Escenario 2).
    - `puede_registrar_horas() -> bool`: verifica si la práctica está habilitada para registrar horas (`ASIGNADA` o `EN_EJECUCION`).
- `dominio/modelos/evento_bitacora.py` *(Existente)*:
  - Entidad `EventoBitacora`: modela los registros inmutables de auditoría para transiciones de estado y accesos no autorizados.
- `dominio/errores.py` *(Modificar)*:
  - Excepciones de dominio:
    - `CantidadHorasInvalidaError`: lanzada cuando la cantidad de horas es `<= 0` o excede el límite máximo de 60 horas semanales.
    - `DescripcionActividadesRequeridaError`: lanzada cuando la descripción de actividades está vacía o en blanco.
    - `SemanaInvalidaError`: lanzada cuando el número de semana es `<= 0`.
    - `SemanaHorasYaRegistradaError`: lanzada cuando ya existe un reporte de horas para la misma semana en la práctica.
    - `EstadoPracticaInvalidoParaRegistroHorasError`: lanzada cuando la práctica se encuentra en un estado que no permite el registro de horas.
    - `PracticaNoEncontradaError` *(Existente)*: si el identificador de la práctica no existe.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/registro_horas_dto.py` *(Nuevo)*:
  - `RegistrarHorasComando`: DTO inmutable de entrada con `practica_id: str`, `semana: int`, `cantidad_horas: int`, `descripcion_actividades: str`.
  - `RegistroHorasRespuestaDTO`: DTO inmutable de respuesta con `registro_horas_id: str`, `practica_id: str`, `semana: int`, `cantidad_horas: int`, `descripcion_actividades: str`, `estado_validacion: str`, `estado_practica: str`, `fecha_registro: datetime`, `mensaje: str`.
- `aplicacion/puertos/repositorio_registro_horas.py` *(Nuevo)*:
  - Protocol `RepositorioRegistroHorasPort`:
    - `guardar(registro: RegistroHoras) -> None`
    - `buscar_por_id(registro_id: str) -> Optional[RegistroHoras]`
    - `buscar_por_practica_y_semana(practica_id: str, semana: int) -> Optional[RegistroHoras]`
    - `listar_por_practica(practica_id: str) -> list[RegistroHoras]`
- `aplicacion/puertos/repositorio_practica.py` *(Existente)*:
  - Protocol `RepositorioPracticaPort`: `buscar_por_id(practica_id: str)` y `guardar(practica: Practica)`.
- `aplicacion/puertos/repositorio_bitacora.py` *(Existente)*:
  - Protocol `RepositorioBitacoraPort`: `registrar_evento(evento: EventoBitacora)`.
- `aplicacion/seguridad/autorizador_rbac.py` *(Existente)*:
  - Uso de la operación configurada `"registrar_horas": {RolUsuario.ESTUDIANTE.value}`.
  - Aplicación de `validar_pertenencia_estudiante(contexto, estudiante_id)` para asegurar que el estudiante solo opere sobre su propia práctica.
- `aplicacion/casos_uso/registrar_horas.py` *(Nuevo)*:
  - Caso de uso `RegistrarHorasCasoUso` (Módulo Seguimiento y Evaluación):
    - Orquesta la validación de autorización RBAC (*deny-by-default*).
    - Recupera la práctica desde `RepositorioPracticaPort` (o lanza `PracticaNoEncontradaError`).
    - Valida pertenencia de datos del estudiante autenticado contra el titular de la práctica.
    - Valida que la práctica se encuentre en estado permitido (`Asignada` o `EnEjecucion`).
    - Valida que la semana no esté previamente reportada mediante `RepositorioRegistroHorasPort.buscar_por_practica_y_semana`.
    - Si la práctica está en estado `Asignada`, ejecuta `practica.iniciar_ejecucion()`, guarda el nuevo estado `EnEjecucion` y asienta el `EventoBitacora` de cambio de estado.
    - Instancia la entidad `RegistroHoras` en estado `Pendiente`.
    - Persiste el `RegistroHoras` mediante `RepositorioRegistroHorasPort`.
    - Retorna `RegistroHorasRespuestaDTO` con la confirmación del registro.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - `InMemoryRepositorioRegistroHoras`: almacén en memoria para registros de horas con soporte de búsqueda por práctica y semana, garantizando consistencia transaccional concurrente (**RT-01**).
  - Soporte en `InMemoryRepositorioPractica` para persistir la transición a `EnEjecucion`.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Instanciar `InMemoryRepositorioRegistroHoras`.
  - Instanciar `RegistrarHorasCasoUso` inyectando `RepositorioPracticaPort`, `RepositorioRegistroHorasPort`, `RepositorioBitacoraPort` y `AutorizadorRBAC`.

## Flujo

Secuencia operativa para el registro de horas de práctica semanales:

1. **Autorización y validación RBAC (ADR-005):**
   - El `AutorizadorRBAC` valida que el actor en `ContextoUsuario` tenga rol `Estudiante`.
   - Si el rol no está autorizado, se registra de inmediato un `EventoBitacora` de acceso no autorizado y se deniega la petición (EAC-03) con 0 datos expuestos.
2. **Búsqueda de la práctica y validación de pertenencia (RN-01):**
   - Se consulta `RepositorioPracticaPort.buscar_por_id(practica_id)`. Si no existe, se arroja `PracticaNoEncontradaError`.
   - Se valida la pertenencia contextual mediante `AutorizadorRBAC.validar_pertenencia_estudiante`: si el estudiante autenticado no es el titular de la práctica, se deniega la operación y se asienta el evento en bitácora.
3. **Validación del estado de la práctica en la máquina de estados (ADR-010):**
   - Si la práctica no está en `EstadoPractica.ASIGNADA` ni `EstadoPractica.EN_EJECUCION`, se deniega el registro lanzando `EstadoPracticaInvalidoParaRegistroHorasError`.
4. **Verificación de duplicidad de la semana:**
   - Se invoca `RepositorioRegistroHorasPort.buscar_por_practica_y_semana(practica_id, semana)`.
   - Si ya existe un registro para esa semana, se interrumpe el flujo arrojando `SemanaHorasYaRegistradaError`.
5. **Transición formal a EnEjecucion (si aplica):**
   - Si la práctica se encuentra en `EstadoPractica.ASIGNADA`:
     - La entidad ejecuta `practica.iniciar_ejecucion()` cambiando su estado a `EstadoPractica.EN_EJECUCION`.
     - Se persiste la práctica actualizada en `RepositorioPracticaPort`.
     - Se registra un `EventoBitacora` inmutable con la acción `INICIO_EJECUCION_PRACTICA`, identificador del estudiante, fecha, hora e IP.
6. **Creación y validación del RegistroHoras (Dominio):**
   - Se crea la entidad `RegistroHoras` con `estado_validacion = EstadoValidacionHoras.PENDIENTE`.
   - La entidad valida invariantes: semana `>= 1`, `0 < cantidad_horas <= 60`, y descripción no vacía. Ante cualquier dato inválido, lanza la excepción de dominio respectiva.
7. **Persistencia del reporte semanal:**
   - Se persiste el nuevo `RegistroHoras` atómicamente en `RepositorioRegistroHorasPort`.
8. **Respuesta:**
   - Se retorna `RegistroHorasRespuestaDTO` con los datos del registro y el estado actual de la práctica.

## Datos

Entidades del modelo de dominio involucradas [docs/vistas/01-logica.md]:

- `RegistroHoras`: reporte semanal con `id`, `practica_id`, `semana`, `cantidad_horas`, `descripcion_actividades`, `estado_validacion` (`Pendiente`, `Aprobado`, `Rechazado`) y `fecha_registro`.
- `Practica`: entidad agregada que almacena `id`, `estudiante_id`, `estadoActual` (`Asignada`, `EnEjecucion`), `horasAcumuladasAprobadas` y `regla_programa_id`.
- `Estudiante`: titular de la práctica referenciado para validación de pertenencia e identidad.
- `ReglaPrograma`: regla vigente del programa académico que define las `horasRequeridas` institucionales.
- `EventoBitacora`: registro append-only de auditoría con `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada`.

## Fuera de alcance

- Validación o aprobación de horas semanales por parte del supervisor de empresa (CU-05).
- Revisión y consulta de acumulados de avance por el docente asesor (CU-06).
- Evaluación de desempeño cualitativa y cuantitativa por el supervisor (CU-07).
- Generación y firma electrónica del acta final en PDF (CU-09, CU-10).
- Asignación de docente asesor (CU-03) y evaluación inicial de postulación (CU-01, CU-02).

## Decisiones pendientes

Ninguna. La estructura modular, el control de acceso RBAC deny-by-default, la trazabilidad inmutable en bitácora, la máquina de estados finitos y la persistencia en memoria están completamente respaldadas por los ADR-002, ADR-005, ADR-006, ADR-007 y ADR-010.
