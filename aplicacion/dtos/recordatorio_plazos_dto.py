"""DTOs inmutables para el envío automatizado y manual de recordatorios de plazos (CU-08).

Traza: CU-08, EAC-02, EAC-03, RT-01, RN-01, RN-02, RN-03, RN-04, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010.

Define los objetos de transferencia de datos inmutables (dataclass con frozen=True y slots=True)
utilizados en las fronteras del caso de uso EnviarRecordatoriosPlazosCasoUso:
- EjecutarRecordatoriosComando: DTO de entrada para disparar la tarea diaria o la ejecución manual por Coordinador.
- DetalleRecordatorioEnviadoDTO: DTO con el detalle de cada recordatorio, renovación de token o escalamiento procesado.
- ResultadoEnvioRecordatoriosDTO: DTO de salida con las métricas consolidadas y el listado de detalles del lote.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class EjecutarRecordatoriosComando:
    """Comando inmutable de entrada para disparar la ejecución de recordatorios de plazos.

    Atributos:
        actor_id: Identificador del actor que dispara la tarea ('SISTEMA' o ID del Coordinador de prácticas).
        rol_actor: Rol autenticado del actor ('SISTEMA' o 'Coordinador de prácticas').
        ip_origen: Dirección IP de origen para trazabilidad en bitácora.
        practica_id_filtro: Filtro opcional para procesar una práctica específica en lugar del lote completo.
        fecha_referencia: Instante de evaluación en días calendario (None usa datetime.now en UTC).
        umbral_dias_calendario: Días naturales de inactividad para considerar un trámite pendiente vencido (OB-01).
        cooldown_minutos: Ventana de enfriamiento en minutos para evitar envíos duplicados (60 min = 1 hora, Escenario 7).
        max_recordatorios_antes_escalamiento: Límite de recordatorios al supervisor antes de escalar al DocenteAsesor (Escenario 3).
    """

    actor_id: str = "SISTEMA"
    rol_actor: str = "SISTEMA"
    ip_origen: str = "127.0.0.1"
    practica_id_filtro: Optional[str] = None
    fecha_referencia: Optional[datetime] = None
    umbral_dias_calendario: int = 3
    cooldown_minutos: int = 60
    max_recordatorios_antes_escalamiento: int = 3

    def __post_init__(self) -> None:
        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")

        if not self.rol_actor or not self.rol_actor.strip():
            raise ValueError("El rol del actor no puede estar vacío.")

        if not self.ip_origen or not self.ip_origen.strip():
            raise ValueError("La dirección IP de origen no puede estar vacía.")

        if self.umbral_dias_calendario < 0:
            raise ValueError("El umbral de días calendario no puede ser negativo.")

        if self.cooldown_minutos < 0:
            raise ValueError("La ventana de enfriamiento (cooldown) en minutos no puede ser negativa.")

        if self.max_recordatorios_antes_escalamiento < 1:
            raise ValueError("El límite de recordatorios antes de escalamiento debe ser al menos 1.")

        object.__setattr__(self, "actor_id", self.actor_id.strip())
        object.__setattr__(self, "rol_actor", self.rol_actor.strip())
        object.__setattr__(self, "ip_origen", self.ip_origen.strip())
        if self.practica_id_filtro is not None:
            filtro_limpio = self.practica_id_filtro.strip()
            object.__setattr__(self, "practica_id_filtro", filtro_limpio if filtro_limpio else None)


@dataclass(frozen=True, slots=True)
class DetalleRecordatorioEnviadoDTO:
    """DTO inmutable con el resultado unitario de cada recordatorio, renovación o escalamiento procesado.

    Atributos:
        practica_id: Identificador de la práctica empresarial.
        tipo_recordatorio: Clasificación de la acción recordada o escalada
            ('EVALUACION_DESEMPENO', 'VALIDACION_HORAS', 'REPORTE_HORAS_ESTUDIANTE',
             'TRAMITE_COORDINACION', 'CIERRE_ACTA_INTERNO', 'ESCALAMIENTO_DOCENTE_ASESOR').
        destinatario_id: Identificador del destinatario de la notificación.
        correo_destinatario: Dirección de correo electrónico del destinatario.
        rol_destinatario: Rol del destinatario ('SupervisorEmpresa', 'DocenteAsesor', 'Estudiante', 'Coordinador de prácticas').
        token_emitido: Cadena criptográfica del TokenEvaluacion incluido o emitido (si aplica).
        token_renovado: Indica si se invalidó un token expirado tras 15 días y se emitió uno nuevo.
        escalado_a_docente: Indica si corresponde a una alerta de escalamiento al DocenteAsesor tras 3 recordatorios.
        encolado_por_fallo_correo: Indica si la notificación fue encolada en el bróker ante fallo del servidor de correo (EAC-02).
        mensaje: Descripción del resultado del envío.
    """

    practica_id: str
    tipo_recordatorio: str
    destinatario_id: str
    correo_destinatario: str
    rol_destinatario: str
    token_emitido: Optional[str] = None
    token_renovado: bool = False
    escalado_a_docente: bool = False
    encolado_por_fallo_correo: bool = False
    mensaje: str = ""


@dataclass(frozen=True, slots=True)
class ResultadoEnvioRecordatoriosDTO:
    """DTO inmutable de salida con las métricas consolidadas de la ejecución de recordatorios de plazos.

    Atributos:
        total_practicas_evaluadas: Total de prácticas inspeccionadas en la ejecución.
        total_recordatorios_enviados: Total de notificaciones de recordatorio o escalamiento procesadas.
        total_tokens_renovados: Total de credenciales TokenEvaluacion expiradas que fueron invalidadas y reemitidas.
        total_escalamientos_docente: Total de alertas de escalamiento enviadas a Docentes Asesores tras >= 3 recordatorios.
        total_omitidos_por_cooldown: Total de recordatorios omitidos por encontrarse dentro de la ventana de enfriamiento de 1 hora.
        total_omitidos_al_dia_o_terminales: Total de prácticas excluidas por estar al día o en estado Completada/Rechazada.
        total_encolados_por_fallo_correo: Total de recordatorios conservados en cola persistente ante fallo del servicio de correo.
        detalles: Tupla inmutable con el desglose de cada recordatorio o alerta procesada.
        fecha_ejecucion: Marca temporal de ejecución del lote.
        mensaje: Resumen descriptivo del resultado de la ejecución.
    """

    total_practicas_evaluadas: int
    total_recordatorios_enviados: int
    total_tokens_renovados: int
    total_escalamientos_docente: int
    total_omitidos_por_cooldown: int
    total_omitidos_al_dia_o_terminales: int
    total_encolados_por_fallo_correo: int
    detalles: tuple[DetalleRecordatorioEnviadoDTO, ...]
    fecha_ejecucion: datetime
    mensaje: str
