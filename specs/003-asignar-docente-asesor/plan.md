# Plan: 003 Asignar docente asesor o tutor

## Decisiones que aplican

- **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):**
  - Estructuración estricta en tres capas: `dominio/`, `aplicacion/` e `infraestructura/`.
  - La capa de dominio define la entidad `DocenteAsesor` y extiende `Practica` sin dependencias de frameworks ni librerías externas.
  - La capa de aplicación define el caso de uso `AsignarDocenteAsesorCasoUso` (dentro del Módulo Postulaciones), sus DTOs inmutables de comando y respuesta, y los puertos necesarios.
  - La capa de infraestructura proporciona adaptadores en memoria (`InMemoryRepositorioDocente`, extensiones a `InMemoryRepositorioPractica` y el simulador de correo).
  - `main.py` actúa como único punto de composición e inyección de dependencias.
- **ADR-005 (Control de acceso RBAC centralizado a nivel de Casos de Uso):**
  - El componente `AutorizadorRBAC` en la capa de aplicación aplica la política *deny-by-default*.
  - Solo los usuarios autenticados con rol `Coordinador` o `CoordinadorPracticas` están autorizados para ejecutar la asignación de tutor.
  - Solicitudes provenientes de roles no autorizados (e.g. `Estudiante`, `DocenteAsesor`, `SupervisorEmpresa`) son denegadas inmediatamente, registrando la alerta en bitácora de auditoría sin exponer datos de la práctica, estudiante ni tutor (cumpliendo **EAC-03**).
- **ADR-006 (Bitácora de auditoría transaccional de solo inserción - Append-Only):**
  - Cada asignación exitosa de docente asesor se asienta de forma inmutable mediante `EventoBitacora` con identificador de usuario, rol, acción (`ASIGNACION_DOCENTE_ASESOR`), identificador de práctica, identificador del docente asesor, fecha, hora e IP de origen.
  - Cumplimiento de **EAC-03**: los accesos denegados por RBAC se registran de inmediato en la bitácora en menos de 1 minuto con IP, fecha y hora.
- **ADR-010 (Patrón Máquina de Estados Finitos para control del flujo de prácticas):**
  - La entidad `Practica` encapsula su ciclo de vida y valida la transición formal:
    - `Aprobada → Asignada`: transición válida ante la asignación formal de un docente asesor con disponibilidad de cupo.
  - Cualquier intento de asignar docente a una práctica en un estado distinto a `Aprobada` (e.g. `PendienteVerificacion`, `Solicitada`, `Rechazada`, o que ya cuente con asignación en `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`) es rechazado por la máquina de estados lanzando `TransicionEstadoInvalidaError` o error por asignación previa en firme.

## Componentes

Estructurados según `docs/vistas/03-desarrollo.md` y Clean Architecture en Python 3.12:

### Capa Dominio (`dominio/`)

- `dominio/modelos/docente_asesor.py` *(Nuevo)*:
  - Entidad `DocenteAsesor`: modela los tutores académicos institucionales conforme al modelo de dominio (`01-logica.puml`).
    - Atributos: `id`, `documento`, `nombre_completo`, `correo_institucional`, `cupo_maximo_practicas`, `practicas_activas`, `activo`.
    - Métodos de dominio:
      - `tiene_cupo_disponible() -> bool`: verifica que `practicas_activas < cupo_maximo_practicas`.
      - `asignar_practica() -> None`: incrementa `practicas_activas` en 1 tras verificar disponibilidad; si se superó el cupo, lanza `CupoDocenteExcedidoError`.
      - `liberar_practica() -> None`: decrementa `practicas_activas` en 1 ante finalización o desvinculación.
- `dominio/modelos/practica.py` *(Modificar)*:
  - Atributo de agregado: `docente_asesor_id: Optional[str] = None`.
  - Método en `Practica`:
    - `asignar_tutor(docente_asesor_id: str) -> None`: valida que el estado actual sea `EstadoPractica.APROBADA`, vincula el identificador del docente asesor y transiciona a `EstadoPractica.ASIGNADA`.
- `dominio/modelos/evento_bitacora.py` *(Existente)*:
  - Entidad `EventoBitacora`: modela los registros inmutables de auditoría para asignaciones y accesos no autorizados.
- `dominio/errores.py` *(Modificar)*:
  - Excepciones de dominio:
    - `CupoDocenteExcedidoError`: lanzada cuando el docente asesor seleccionado ha alcanzado su límite de tutorías simultáneas.
    - `DocenteAsesorNoEncontradoError`: lanzada cuando el identificador del docente asesor no existe o no está registrado.
    - `TransicionEstadoInvalidaError` *(Existente)*: lanzada cuando la práctica no está en estado `Aprobada`.
    - `PracticaNoEncontradaError` *(Existente)*: lanzada cuando la práctica indicada no existe.
    - `DecisionPreviaEnFirmeError` *(Existente)*: lanzada cuando la práctica ya tiene tutor asignado en firme.

### Capa Aplicación (`aplicacion/`)

- `aplicacion/dtos/asignacion_docente_dto.py` *(Nuevo)*:
  - `AsignarDocenteComando`: DTO inmutable de entrada con `practica_id: str`, `docente_asesor_id: str`.
  - `AsignacionDocenteRespuestaDTO`: DTO inmutable de respuesta con `practica_id: str`, `docente_asesor_id: str`, `nuevo_estado: str`, `mensaje: str`, `fecha_asignacion: datetime`.
  - `DocenteAsesorResumenDTO`: DTO inmutable para consultas de carga y disponibilidad (`id`, `documento`, `nombre_completo`, `correo_institucional`, `cupo_maximo`, `practicas_activas`, `cupo_disponible`).
- `aplicacion/puertos/repositorio_docente.py` *(Nuevo)*:
  - Protocol `RepositorioDocentePort`:
    - `guardar(docente: DocenteAsesor) -> None`
    - `buscar_por_id(docente_id: str) -> Optional[DocenteAsesor]`
    - `buscar_por_documento(documento: str) -> Optional[DocenteAsesor]`
    - `listar_disponibles() -> list[DocenteAsesor]`
- `aplicacion/puertos/repositorio_practica.py` *(Existente)*:
  - Protocol `RepositorioPracticaPort`: utilización de `buscar_por_id(practica_id: str)` y `guardar(practica: Practica)`.
- `aplicacion/puertos/repositorio_bitacora.py` *(Existente)*:
  - Protocol `RepositorioBitacoraPort`: `registrar_evento(evento: EventoBitacora)`.
- `aplicacion/puertos/servicio_correo.py` *(Existente)*:
  - Protocol `ServicioCorreoPort`: `enviar_notificacion(destinatario: str, asunto: str, cuerpo: str)`.
- `aplicacion/seguridad/autorizador_rbac.py` *(Modificar)*:
  - Registro de la acción de asignación de docente asesor restringida exclusivamente a los roles de Coordinador (`RolUsuario.COORDINADOR`, `RolUsuario.COORDINADOR_PRACTICAS`).
- `aplicacion/casos_uso/asignar_docente_asesor.py` *(Nuevo)*:
  - Caso de uso `AsignarDocenteAsesorCasoUso` (Módulo Postulaciones):
    - Orquesta la validación de autorización RBAC (*deny-by-default*).
    - Recupera la práctica desde `RepositorioPracticaPort` (o lanza `PracticaNoEncontradaError`).
    - Valida precondición de máquina de estados (`practica.estado_actual == EstadoPractica.APROBADA`).
    - Recupera el docente asesor desde `RepositorioDocentePort` (o lanza `DocenteAsesorNoEncontradoError`).
    - Valida que el docente asesor cuente con cupo disponible (`docente.tiene_cupo_disponible()` o lanza `CupoDocenteExcedidoError`).
    - Ejecuta la asignación en la entidad `Practica` (`practica.asignar_tutor(docente.id)` -> transiciona a `EstadoPractica.ASIGNADA`).
    - Incrementa la carga del docente (`docente.asignar_practica()`).
    - Persiste el estado actualizado de la práctica y del docente.
    - Registra el `EventoBitacora` inmutable con el identificador del coordinador, IP, fecha y hora.
    - Emite notificaciones por correo al estudiante titular y al docente asesor asignado mediante `ServicioCorreoPort`.
    - Retorna `AsignacionDocenteRespuestaDTO`.

### Capa Infraestructura (`infraestructura/`)

- `infraestructura/adaptadores/repositorio_memoria.py` *(Modificar)*:
  - `InMemoryRepositorioDocente`: almacén en memoria de tutores académicos con inicialización determinista de los 50 tutores institucionales (RT-01).
  - Soporte en `InMemoryRepositorioPractica` para persistir la asignación del tutor y el nuevo estado `Asignada`.
- `infraestructura/adaptadores/servicio_correo_simulado.py` *(Existente)*:
  - Emulación determinista de envío de notificaciones tanto al estudiante titular como al docente asesor.

### Composición (`main.py`)

- `main.py` *(Modificar)*:
  - Instanciar `InMemoryRepositorioDocente` precargando los tutores disponibles.
  - Instanciar `AsignarDocenteAsesorCasoUso` inyectando repositorios, servicio de correo y autorizador RBAC.

## Flujo

Secuencia operativa de asignación de tutor:

1. **Autorización previa (RBAC - ADR-005):**
   - El `AutorizadorRBAC` valida que el actor en `ContextoUsuario` posea rol `Coordinador` o `CoordinadorPracticas`.
   - Si no está autorizado, se registra de inmediato un `EventoBitacora` de acceso no autorizado y se deniega la petición (EAC-03) con 0 datos expuestos.
2. **Búsqueda y validación de la práctica:**
   - Se consulta `RepositorioPracticaPort.buscar_por_id(practica_id)`. Si no existe, se arroja `PracticaNoEncontradaError`.
   - Se verifica el estado de la práctica: si no es `EstadoPractica.APROBADA`, se interrumpe arrojando `TransicionEstadoInvalidaError` o `DecisionPreviaEnFirmeError`.
3. **Búsqueda y validación del docente asesor:**
   - Se consulta `RepositorioDocentePort.buscar_por_id(docente_asesor_id)`. Si no existe o no está activo, se arroja `DocenteAsesorNoEncontradoError`.
   - Se verifica que `docente.tiene_cupo_disponible()` sea verdadero. Si alcanzó su cupo máximo (`practicas_activas >= cupo_maximo_practicas`), se arroja `CupoDocenteExcedidoError`.
4. **Ejecución de asignación en el dominio (ADR-010):**
   - La entidad `Practica` vincula al docente asesor y ejecuta su transición a `EstadoPractica.ASIGNADA`.
   - La entidad `DocenteAsesor` actualiza su carga de prácticas activas (`docente.asignar_practica()`).
5. **Persistencia transaccional y auditoría (ADR-006):**
   - Se persisten los cambios en `RepositorioPracticaPort` y `RepositorioDocentePort`.
   - Se registra el `EventoBitacora` inmutable con la acción `ASIGNACION_DOCENTE_ASESOR`, coordinador responsable, fecha, hora e IP de origen.
6. **Notificaciones por correo institucional:**
   - Se invoca `ServicioCorreoPort.enviar_notificacion` al correo del estudiante titular notificando el tutor asignado.
   - Se invoca `ServicioCorreoPort.enviar_notificacion` al correo del docente asesor notificando la práctica que le fue asignada.
7. **Respuesta:**
   - Se retorna `AsignacionDocenteRespuestaDTO` confirmando el éxito de la asignación.

## Datos

Entidades del modelo de dominio involucradas [docs/vistas/01-logica.md]:

- `Practica`: entidad raíz que almacena `id`, `estudiante_id`, `docente_asesor_id`, `regla_programa_id` y `estadoActual` (`Aprobada` transiciona a `Asignada`).
- `DocenteAsesor`: tutor académico institucional con `documento`, `nombreCompleto`, `correoInstitucional`, `cupoMaximoPracticas` y `practicasActivas`.
- `Estudiante`: titular de la práctica referenciado para obtener correo institucional y remitir la notificación.
- `EventoBitacora`: registro append-only de auditoría con `fechaHora`, `actorIdentificador`, `rolActor`, `ipOrigen`, `accionRealizada` y `entidadAfectada`.

## Fuera de alcance

- Registro inicial y verificación académica de postulación (CU-01).
- Aprobación o rechazo administrativo inicial de postulación (CU-02).
- Reasignación de docente asesor una vez iniciada la ejecución (se gestionará cuando se formalice la regla de excepciones por fuerza mayor).
- Registro y validación semanal de horas de práctica (CU-04, CU-05, CU-06).
- Calificación y evaluación de desempeño por la empresa receptora (CU-07).
- Generación y aprobación de actas finales en PDF (CU-09, CU-10).
- Monitoreo general del estado de las prácticas en tablero de control (CU-13).
- Configuración y versionamiento de reglas de programas académicos (CU-12).

## Decisiones pendientes

Ninguna. Todas las transiciones de estado, reglas de cupos, esquemas de autorización RBAC (*deny-by-default*), auditoría append-only y persistencia en memoria están completamente fundamentadas en los ADR-002, ADR-005, ADR-006 y ADR-010.
