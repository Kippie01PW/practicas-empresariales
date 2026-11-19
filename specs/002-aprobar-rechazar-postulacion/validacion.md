# Validación: 002 Aprobar o rechazar postulación

## Validación funcional

| Escenario | Resultado | Evidencia |
|---|---|---|
| **Escenario 1: Aprobación exitosa de postulación solicitada** | Cumple | `aplicacion/casos_uso/evaluar_postulacion.py` (`EvaluarPostulacionCasoUso.ejecutar`), `dominio/modelos/practica.py` (`Practica.aprobar`), `infraestructura/adaptadores/servicio_correo_simulado.py` (`AdaptadorCorreoSimulado.enviar_notificacion`), `main.py`. Cuando el Coordinador de prácticas (`rol_actor="Coordinador de prácticas"`) aprueba una práctica en estado `Solicitada`, el sistema actualiza su estado a `Aprobada`, registra en la bitácora append-only el `EventoBitacora` con el identificador del coordinador, rol, acción, práctica afectada, fecha, hora e IP, y despacha la notificación por correo institucional al estudiante titular. |
| **Escenario 2: Rechazo administrativo de postulación solicitada con justificación** | Cumple | `aplicacion/casos_uso/evaluar_postulacion.py` (`EvaluarPostulacionCasoUso.ejecutar`), `dominio/modelos/practica.py` (`Practica.rechazar`). Cuando el Coordinador de prácticas rechaza la postulación indicando una justificación válida ("No cumple con el perfil empresarial del programa"), el sistema transiciona la práctica a estado `Rechazada`, asocia la justificación al atributo `motivo_rechazo` de la entidad, asienta el `EventoBitacora` de auditoría con la justificación y envía la notificación al estudiante informando el rechazo y su causa. |
| **Escenario 3: Rechazo fallido por ausencia de justificación obligatoria** | Cumple | `dominio/modelos/practica.py` (`Practica.rechazar`, RN-02), `dominio/errores.py` (`MotivoRechazoRequeridoError`), `aplicacion/casos_uso/evaluar_postulacion.py`. Si el coordinador intenta rechazar una postulación sin proveer una justificación o con texto vacío, el sistema interrumpe la operación arrojando `MotivoRechazoRequeridoError`, preservando la `Practica` intacta en estado `Solicitada` sin alterar sus datos. |
| **Escenario 4: Intento de evaluar postulación en estado no permitido por la máquina de estados** | Cumple | `dominio/modelos/practica.py` (`Practica.aprobar`, `Practica.rechazar`), `dominio/errores.py` (`TransicionEstadoInvalidaError`), `aplicacion/casos_uso/evaluar_postulacion.py`. Si se intenta evaluar una práctica en estado `PendienteVerificacion`, la entidad deniega la transición lanzando `TransicionEstadoInvalidaError`, garantizando que la práctica permanezca en `PendienteVerificacion` e informando que solo puede ser evaluada cuando se encuentre en estado `Solicitada`. |
| **Escenario 5: Intento de evaluar postulación con decisión previa ya asentada** | Cumple | `dominio/modelos/practica.py` (`Practica._asegurar_sin_decision_en_firme`), `dominio/errores.py` (`DecisionPreviaEnFirmeError`). Si se intenta reevaluar una práctica que ya cuenta con decisión en firme (`Aprobada` o `Rechazada`), el sistema deniega la operación arrojando `DecisionPreviaEnFirmeError` e informando al coordinador que la decisión administrativa es en firme, manteniendo el ciclo de vida sin alteraciones. |
| **Escenario 6: Intento de aprobación o rechazo por rol no autorizado** | Cumple | `aplicacion/seguridad/autorizador_rbac.py` (`AutorizadorRBAC.validar_evaluacion_postulacion`), `aplicacion/casos_uso/evaluar_postulacion.py`. Ante intentos de evaluación por usuarios con roles como `DocenteAsesor` o `Estudiante`, la política *deny-by-default* rechaza la solicitud arrojando `AccesoDenegadoError`, mantiene la práctica en `Solicitada` y registra un `EventoBitacora` de acceso no autorizado con identificador del usuario, rol, fecha, hora e IP de origen. |
| **Escenario 7: EAC-03 - Seguridad, confidencialidad y trazabilidad de accesos no autorizados** | Cumple | `aplicacion/seguridad/autorizador_rbac.py`, `aplicacion/casos_uso/evaluar_postulacion.py` (líneas 119-142). Se garantiza el rechazo del 100% de los accesos de roles no autorizados, asegurando 0 datos expuestos de la postulación y del estudiante (la bitácora audita hacia la entidad genérica `ModuloPostulaciones`), y registrando inmediatamente el evento de auditoría en la bitácora con IP, fecha y hora. |

## Validación arquitectónica

- **Regla de dependencia:** Cumple estrictamente.
  - La capa `dominio/` no depende de `aplicacion/` ni de `infraestructura/`.
  - La capa `aplicacion/` depende exclusivamente de `dominio/` y define puertos abstractos sin importar `infraestructura/`.
  - La capa `infraestructura/` implementa los puertos de persistencia y servicios.
  - `main.py` actúa como Composition Root exclusivo de inyección de dependencias.
- **ADR citados en plan.md:**
  - **ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores):** Estructura en tres capas (`dominio/`, `aplicacion/`, `infraestructura/`) y Composition Root en `main.py`.
  - **ADR-005 (Control de acceso RBAC centralizado en Casos de Uso):** Implementado en `aplicacion/seguridad/autorizador_rbac.py` con política *deny-by-default*, permitiendo evaluar exclusivamente a `RolUsuario.COORDINADOR` y `RolUsuario.COORDINADOR_PRACTICAS`.
  - **ADR-006 (Bitácora de auditoría Append-Only):** Registro inmutable en `EventoBitacora` para aprobaciones, rechazos justificados e intentos de acceso no autorizado (EAC-03).
  - **ADR-010 (Máquina de estados finitos):** El ciclo de vida de `Practica` encapsula transiciones formales estrictas: `Solicitada → Aprobada` y `Solicitada → Rechazada` (con justificación obligatoria), denegando evaluaciones en estados no permitidos o decisiones previas en firme.
- **Convenciones de AGENTS.md:**
  - Python 3.12+ con tipado estático riguroso (`typing`, `from __future__ import annotations`).
  - DTOs inmutables implementados con `@dataclass(frozen=True, slots=True)` (`EvaluarPostulacionComando`, `EvaluacionPostulacionRespuestaDTO`).
  - Vocabulario y nomenclatura rigurosamente alineados con el glosario del dominio (`Practica`, `EventoBitacora`, `EstadoPractica`, `DecisionEvaluacion`).
  - Adaptadores en memoria deterministas sin dependencias externas pesadas ni bases de datos reales en esta etapa.
