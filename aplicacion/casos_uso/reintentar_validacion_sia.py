"""Caso de uso de integración y reintento asíncrono con Registro Académico (SIA).

Traza: CU-01, EAC-02, RT-01, RT-03, PA-04,
ADR-001 (Resiliencia e integración asíncrona con Registro Académico),
ADR-002 (Clean Architecture y Puertos y Adaptadores),
ADR-006 (Bitácora Append-Only),
ADR-010 (Máquina de estados finitos),
Vista de Procesos §2, Vista de Desarrollo §2,
diagramas/secuencias/cu01-postularse.puml.

Implementa la orquestación del procesamiento en segundo plano (Worker de integración)
para las postulaciones en estado 'PendienteVerificacion' (Escenarios 6 y 7 de spec.md):
- Escenario 6: Recuperación del SIA (< 30 min) -> Reintento exitoso, transición de la
  práctica a 'Solicitada', registro de EventoBitacora y notificación por correo electrónico.
- Escenario 7: Indisponibilidad persistente tras 5 reintentos consecutivos con retroceso
  exponencial -> Preservación de la práctica en 'PendienteVerificacion' (0% pérdidas),
  registro de cada IntentoValidacion fallido, derivación a la Dead-Letter Queue (DLQ)
  y emisión de alerta operativa a soporte técnico (TI) sin rechazar al estudiante.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from aplicacion.puertos.publicador_eventos import (
    DatosTareaValidacionSia,
    ErrorPublicacionEvento,
    PublicadorEventosPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.servicio_correo import (
    ErrorServicioCorreo,
    ServicioCorreoPort,
)
from aplicacion.puertos.servicio_registro_academico import (
    ErrorRegistroAcademico,
    IndisponibilidadRegistroAcademicoError,
    ResultadoRequisitosAcademicos,
    ServicioRegistroAcademicoPort,
    TimeoutRegistroAcademicoError,
)
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.intento_validacion import (
    IntentoValidacion,
    ResultadoValidacionSia,
)
from dominio.modelos.practica import EstadoPractica, Practica


# ---------------------------------------------------------------------------
# DTO inmutable de resultado del reintento asíncrono
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ResultadoReintentoSiaDTO:
    """DTO inmutable con el resultado del procesamiento de un reintento de verificación SIA.

    Atributos:
        - exito: True si el estudiante cumplió los requisitos y la práctica fue actualizada a 'Solicitada'.
        - practica_id: Identificador único de la práctica procesada.
        - estado_practica: Estado final de la práctica tras el procesamiento ('Solicitada', 'PendienteVerificacion', etc.).
        - numero_reintento: Número ordinal del reintento ejecutado (1 a 5).
        - mensaje: Descripción legible del resultado para logs y auditoría operativa.
        - reintentos_agotados: True si se alcanzaron los 5 reintentos sin obtener respuesta del SIA (Escenario 7).
        - alerta_soporte_emitida: True si se notificó al equipo de TI debido al agotamiento de reintentos.
        - enrutado_dlq: True si el mensaje fue enviado a la Dead-Letter Queue tras agotar reintentos.
        - correo_enviado: True si se despachó la notificación por correo al estudiante (Escenario 6).
        - tarea_siguiente: Objeto DatosTareaValidacionSia programado para el siguiente reintento si aún no se agotan.
        - detalles: Diccionario opcional con metadatos o diagnósticos adicionales.
    """

    exito: bool
    practica_id: str
    estado_practica: str
    numero_reintento: int
    mensaje: str
    reintentos_agotados: bool = False
    alerta_soporte_emitida: bool = False
    enrutado_dlq: bool = False
    correo_enviado: bool = False
    tarea_siguiente: Optional[DatosTareaValidacionSia] = None
    detalles: Optional[dict[str, Any]] = None

    @classmethod
    def crear_exitoso(
        cls,
        *,
        practica_id: str,
        numero_reintento: int,
        correo_enviado: bool,
        mensaje: str = "Verificación asíncrona completada exitosamente. Práctica actualizada a 'Solicitada'.",
        detalles: Optional[dict[str, Any]] = None,
    ) -> ResultadoReintentoSiaDTO:
        """Crea un resultado exitoso de verificación tras recuperación del SIA (Escenario 6)."""
        return cls(
            exito=True,
            practica_id=practica_id,
            estado_practica=EstadoPractica.SOLICITADA.value,
            numero_reintento=numero_reintento,
            mensaje=mensaje,
            reintentos_agotados=False,
            alerta_soporte_emitida=False,
            enrutado_dlq=False,
            correo_enviado=correo_enviado,
            tarea_siguiente=None,
            detalles=detalles,
        )

    @classmethod
    def crear_rechazado(
        cls,
        *,
        practica_id: str,
        numero_reintento: int,
        causal: str,
        correo_enviado: bool = False,
        detalles: Optional[dict[str, Any]] = None,
    ) -> ResultadoReintentoSiaDTO:
        """Crea un resultado de rechazo si el SIA responde indicando incumplimiento académico."""
        return cls(
            exito=False,
            practica_id=practica_id,
            estado_practica=EstadoPractica.RECHAZADA.value,
            numero_reintento=numero_reintento,
            mensaje=f"Postulación rechazada en verificación asíncrona: {causal}",
            reintentos_agotados=False,
            alerta_soporte_emitida=False,
            enrutado_dlq=False,
            correo_enviado=correo_enviado,
            tarea_siguiente=None,
            detalles=detalles,
        )

    @classmethod
    def crear_reintento_programado(
        cls,
        *,
        practica_id: str,
        numero_reintento: int,
        tarea_siguiente: DatosTareaValidacionSia,
        motivo_falla: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> ResultadoReintentoSiaDTO:
        """Crea un resultado cuando el SIA sigue fallando pero restan reintentos disponibles."""
        return cls(
            exito=False,
            practica_id=practica_id,
            estado_practica=EstadoPractica.PENDIENTE_VERIFICACION.value,
            numero_reintento=numero_reintento,
            mensaje=(
                f"Fallo en reintento {numero_reintento} ({motivo_falla}). "
                f"Programado reintento {tarea_siguiente.numero_reintento} de {tarea_siguiente.max_reintentos}."
            ),
            reintentos_agotados=False,
            alerta_soporte_emitida=False,
            enrutado_dlq=False,
            correo_enviado=False,
            tarea_siguiente=tarea_siguiente,
            detalles=detalles,
        )

    @classmethod
    def crear_reintentos_agotados(
        cls,
        *,
        practica_id: str,
        numero_reintento: int,
        motivo_falla: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> ResultadoReintentoSiaDTO:
        """Crea un resultado cuando se agotan los 5 reintentos consecutivos (Escenario 7, ADR-001)."""
        return cls(
            exito=False,
            practica_id=practica_id,
            estado_practica=EstadoPractica.PENDIENTE_VERIFICACION.value,
            numero_reintento=numero_reintento,
            mensaje=(
                f"Se han agotado los {numero_reintento} reintentos consecutivos sin respuesta del SIA. "
                f"La práctica se mantiene en 'PendienteVerificacion', mensaje enrutado a DLQ y alerta emitida a TI."
            ),
            reintentos_agotados=True,
            alerta_soporte_emitida=True,
            enrutado_dlq=True,
            correo_enviado=False,
            tarea_siguiente=None,
            detalles=detalles,
        )

    @classmethod
    def crear_ya_procesada(
        cls,
        *,
        practica_id: str,
        estado_actual: str,
        numero_reintento: int,
    ) -> ResultadoReintentoSiaDTO:
        """Crea un resultado idempotente cuando la práctica ya no está en 'PendienteVerificacion'."""
        return cls(
            exito=True if estado_actual == EstadoPractica.SOLICITADA.value else False,
            practica_id=practica_id,
            estado_practica=estado_actual,
            numero_reintento=numero_reintento,
            mensaje=f"La práctica ya se encuentra en estado '{estado_actual}'. Tarea descartada por idempotencia.",
            reintentos_agotados=False,
            alerta_soporte_emitida=False,
            enrutado_dlq=False,
            correo_enviado=False,
            tarea_siguiente=None,
        )

    @classmethod
    def crear_practica_no_encontrada(
        cls,
        *,
        practica_id: str,
        numero_reintento: int,
    ) -> ResultadoReintentoSiaDTO:
        """Crea un resultado de error cuando la práctica no existe en el repositorio."""
        return cls(
            exito=False,
            practica_id=practica_id,
            estado_practica="Desconocido",
            numero_reintento=numero_reintento,
            mensaje=f"No se encontró en el repositorio la práctica con ID '{practica_id}'.",
            reintentos_agotados=False,
            alerta_soporte_emitida=False,
            enrutado_dlq=False,
            correo_enviado=False,
            tarea_siguiente=None,
        )


# ---------------------------------------------------------------------------
# Caso de uso: ReintentarValidacionSiaCasoUso
# ---------------------------------------------------------------------------

class ReintentarValidacionSiaCasoUso:
    """Caso de uso para el procesamiento asíncrono y reintentos de validación con el SIA.

    Orquesta el flujo del Worker de integración (ADR-001, diagramas/secuencias/cu01-postularse.puml):
    1. Verifica la existencia e invariantes de la práctica en estado 'PendienteVerificacion'.
    2. Reintenta la consulta de requisitos académicos al SIA.
    3. Si el SIA se recupera y cumple: actualiza a 'Solicitada', asienta EventoBitacora
       y envía correo institucional al estudiante (Escenario 6).
    4. Si el SIA sigue fallando:
       - Si no ha agotado reintentos (< 5): persiste el IntentoValidacion fallido y programa
         el siguiente reintento en el bróker.
       - Si agota los 5 reintentos: preserva la práctica en 'PendienteVerificacion' (0% pérdidas),
         persiste el IntentoValidacion fallido, traslada la tarea a la DLQ y emite alerta a TI (Escenario 7).
    """

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        servicio_registro_academico: ServicioRegistroAcademicoPort,
        publicador_eventos: PublicadorEventosPort,
        servicio_correo: ServicioCorreoPort,
    ) -> None:
        """Inicializa el caso de uso con sus puertos colaboradores.

        Args:
            repositorio_practica: Puerto de persistencia de prácticas, intentos y bitácora.
            servicio_registro_academico: Puerto de integración con el SIA.
            publicador_eventos: Puerto de publicación para encolamiento, DLQ y alertas.
            servicio_correo: Puerto para despacho de notificaciones por correo electrónico.
        """
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._servicio_registro_academico: ServicioRegistroAcademicoPort = servicio_registro_academico
        self._publicador_eventos: PublicadorEventosPort = publicador_eventos
        self._servicio_correo: ServicioCorreoPort = servicio_correo

    def __call__(self, tarea: DatosTareaValidacionSia) -> ResultadoReintentoSiaDTO:
        """Permite invocar la instancia del caso de uso como función callable."""
        return self.ejecutar(tarea)

    def ejecutar(self, tarea: DatosTareaValidacionSia) -> ResultadoReintentoSiaDTO:
        """Ejecuta una iteración de reintento para la tarea de validación asíncrona.

        Args:
            tarea: DTO inmutable con los datos de la tarea encolada en el bróker.

        Returns:
            ResultadoReintentoSiaDTO con el diagnóstico y estado resultante.
        """
        # 1. Recuperar la entidad Práctica y validar su estado
        practica: Optional[Practica] = self._repositorio_practica.buscar_por_id(tarea.practica_id)
        if practica is None:
            return ResultadoReintentoSiaDTO.crear_practica_no_encontrada(
                practica_id=tarea.practica_id,
                numero_reintento=tarea.numero_reintento,
            )

        # Idempotencia: si la práctica ya no está en PendienteVerificacion, no reprocesar
        if practica.estado_actual != EstadoPractica.PENDIENTE_VERIFICACION:
            return ResultadoReintentoSiaDTO.crear_ya_procesada(
                practica_id=practica.id,
                estado_actual=practica.estado_actual.value,
                numero_reintento=tarea.numero_reintento,
            )

        # 2. Reintentar consulta frente al servicio de Registro Académico (SIA)
        try:
            resultado_sia: ResultadoRequisitosAcademicos = (
                self._servicio_registro_academico.consultar_requisitos_academicos(
                    tarea.documento_estudiante
                )
            )
        except (
            TimeoutRegistroAcademicoError,
            IndisponibilidadRegistroAcademicoError,
            ErrorRegistroAcademico,
        ) as error_sia:
            return self._manejar_fallo_reintento(
                practica=practica,
                tarea=tarea,
                error=error_sia,
            )
        except Exception as error_inesperado:
            return self._manejar_fallo_reintento(
                practica=practica,
                tarea=tarea,
                error=error_inesperado,
            )

        # 3. Procesar respuesta del SIA tras recuperación (Escenario 6 o rechazo)
        return self._manejar_exito_comunicacion(
            practica=practica,
            tarea=tarea,
            resultado_sia=resultado_sia,
        )

    # -----------------------------------------------------------------------
    # Métodos privados de procesamiento
    # -----------------------------------------------------------------------

    def _manejar_exito_comunicacion(
        self,
        *,
        practica: Practica,
        tarea: DatosTareaValidacionSia,
        resultado_sia: ResultadoRequisitosAcademicos,
    ) -> ResultadoReintentoSiaDTO:
        """Procesa la respuesta válida del SIA una vez restablecida la comunicación."""
        num_intento = self._determinar_numero_intento(practica.id, tarea.numero_reintento)

        if resultado_sia.cumple_requisitos:
            # Escenario 6: Validación exitosa tras recuperación del SIA (< 30 min)
            practica.solicitar()
            self._repositorio_practica.actualizar(practica)

            # Registro del IntentoValidacion exitoso (ADR-001)
            intento = IntentoValidacion(
                practica_id=practica.id,
                numero_intento=num_intento,
                resultado_sia=ResultadoValidacionSia.CUMPLE_REQUISITOS,
                exitoso=True,
                detalle_estado=(
                    "Requisitos académicos validados satisfactoriamente "
                    "tras restablecimiento del servicio de Registro Académico."
                ),
            )
            self._repositorio_practica.guardar_intento_validacion(intento)

            # Registro de auditoría append-only del cambio de estado (ADR-006)
            self._registrar_bitacora(
                actor_id="Sistema:WorkerIntegracion",
                rol="Sistema",
                ip="127.0.0.1",
                accion="Verificación asíncrona exitosa: Práctica actualizada a 'Solicitada'",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "practica_id": practica.id,
                    "documento_estudiante": tarea.documento_estudiante,
                    "numero_reintento": tarea.numero_reintento,
                    "creditos_aprobados": resultado_sia.creditos_aprobados,
                    "porcentaje_avance": resultado_sia.porcentaje_avance,
                    "estado_anterior": EstadoPractica.PENDIENTE_VERIFICACION.value,
                    "nuevo_estado": EstadoPractica.SOLICITADA.value,
                },
            )

            # Envío de notificación por correo electrónico al estudiante (Escenario 6)
            correo_enviado = self._notificar_estudiante_aprobacion(
                practica_id=practica.id,
                tarea=tarea,
            )

            return ResultadoReintentoSiaDTO.crear_exitoso(
                practica_id=practica.id,
                numero_reintento=tarea.numero_reintento,
                correo_enviado=correo_enviado,
                detalles={
                    "creditos_aprobados": resultado_sia.creditos_aprobados,
                    "porcentaje_avance": resultado_sia.porcentaje_avance,
                },
            )
        else:
            # Caso alterno: El SIA responde indicando que no cumple requisitos
            causal = (
                resultado_sia.causal_incumplimiento
                if resultado_sia.causal_incumplimiento
                else "Incumplimiento de requisitos académicos según Registro Académico."
            )
            practica.rechazar()
            self._repositorio_practica.actualizar(practica)

            intento = IntentoValidacion(
                practica_id=practica.id,
                numero_intento=num_intento,
                resultado_sia=ResultadoValidacionSia.REQUISITOS_INCUMPLIDOS,
                exitoso=False,
                detalle_estado=causal,
            )
            self._repositorio_practica.guardar_intento_validacion(intento)

            self._registrar_bitacora(
                actor_id="Sistema:WorkerIntegracion",
                rol="Sistema",
                ip="127.0.0.1",
                accion="Postulación rechazada por requisitos académicos en verificación asíncrona",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "practica_id": practica.id,
                    "documento_estudiante": tarea.documento_estudiante,
                    "causal_rechazo": causal,
                },
            )

            correo_enviado = self._notificar_estudiante_rechazo(
                practica_id=practica.id,
                tarea=tarea,
                causal=causal,
            )

            return ResultadoReintentoSiaDTO.crear_rechazado(
                practica_id=practica.id,
                numero_reintento=tarea.numero_reintento,
                causal=causal,
                correo_enviado=correo_enviado,
                detalles={
                    "creditos_aprobados": resultado_sia.creditos_aprobados,
                    "porcentaje_avance": resultado_sia.porcentaje_avance,
                },
            )

    def _manejar_fallo_reintento(
        self,
        *,
        practica: Practica,
        tarea: DatosTareaValidacionSia,
        error: Exception,
    ) -> ResultadoReintentoSiaDTO:
        """Maneja el fallo persistente o timeout en la llamada al SIA durante el reintento."""
        es_timeout = isinstance(error, TimeoutRegistroAcademicoError)
        resultado_sia = (
            ResultadoValidacionSia.TIMEOUT
            if es_timeout
            else ResultadoValidacionSia.ERROR_COMUNICACION
        )
        detalle_diagnostico = str(error) or error.__class__.__name__

        # 1. Registrar cada IntentoValidacion fallido (spec.md, Escenario 7)
        num_intento = self._determinar_numero_intento(practica.id, tarea.numero_reintento)
        intento = IntentoValidacion(
            practica_id=practica.id,
            numero_intento=num_intento,
            resultado_sia=resultado_sia,
            exitoso=False,
            detalle_estado=detalle_diagnostico,
        )
        self._repositorio_practica.guardar_intento_validacion(intento)

        # 2. Verificar si se han agotado los reintentos permitidos (5 según ADR-001)
        if tarea.ha_agotado_reintentos():
            # Escenario 7: Agotamiento de 5 reintentos consecutivos
            # El sistema mantiene la Práctica en 'PendienteVerificacion' garantizando 0% pérdida de datos.
            # Enrutar a Dead-Letter Queue (DLQ)
            try:
                self._publicador_eventos.publicar_en_cola_muerta(
                    tarea,
                    motivo_fallo=detalle_diagnostico,
                )
            except ErrorPublicacionEvento:
                pass

            # Generar alerta operativa a TI para gestión administrativa sin rechazar al estudiante
            asunto_alerta = (
                f"Alerta operativa: Agotamiento de reintentos validación SIA - "
                f"Práctica {practica.id}"
            )
            mensaje_alerta = (
                f"Se han agotado los {tarea.max_reintentos} reintentos consecutivos con el "
                f"servicio de Registro Académico para la práctica ID '{practica.id}' "
                f"(estudiante: '{tarea.documento_estudiante}').\n"
                f"Diagnóstico técnico: {detalle_diagnostico}.\n"
                f"La práctica se mantiene en estado 'PendienteVerificacion' para intervención técnica."
            )
            contexto_alerta = {
                "practica_id": practica.id,
                "documento_estudiante": tarea.documento_estudiante,
                "correo_estudiante": tarea.correo_estudiante,
                "max_reintentos": tarea.max_reintentos,
                "motivo_fallo": detalle_diagnostico,
            }
            try:
                self._publicador_eventos.publicar_alerta_soporte(
                    asunto=asunto_alerta,
                    mensaje=mensaje_alerta,
                    contexto=contexto_alerta,
                )
            except ErrorPublicacionEvento:
                pass

            # Registro de auditoría append-only
            self._registrar_bitacora(
                actor_id="Sistema:WorkerIntegracion",
                rol="Sistema",
                ip="127.0.0.1",
                accion="Agotamiento de reintentos validación SIA: derivado a DLQ y alerta operativa",
                entidad=f"Practica:{practica.id}",
                detalles={
                    "practica_id": practica.id,
                    "documento_estudiante": tarea.documento_estudiante,
                    "reintentos_ejecutados": tarea.numero_reintento,
                    "max_reintentos": tarea.max_reintentos,
                    "motivo_fallo": detalle_diagnostico,
                },
            )

            return ResultadoReintentoSiaDTO.crear_reintentos_agotados(
                practica_id=practica.id,
                numero_reintento=tarea.numero_reintento,
                motivo_falla=detalle_diagnostico,
                detalles={
                    "tipo_error": error.__class__.__name__,
                    "diagnostico": detalle_diagnostico,
                },
            )

        # 3. Si aún restan reintentos (< 5), programar el siguiente reintento en el bróker
        siguiente_tarea = tarea.siguiente_reintento(
            metadata={
                "ultimo_fallo": detalle_diagnostico,
                "tipo_fallo": error.__class__.__name__,
                "intento_previo": num_intento,
            }
        )
        try:
            self._publicador_eventos.publicar_tarea_validacion_sia(siguiente_tarea)
        except ErrorPublicacionEvento:
            pass

        return ResultadoReintentoSiaDTO.crear_reintento_programado(
            practica_id=practica.id,
            numero_reintento=tarea.numero_reintento,
            tarea_siguiente=siguiente_tarea,
            motivo_falla=detalle_diagnostico,
            detalles={
                "tipo_error": error.__class__.__name__,
                "diagnostico": detalle_diagnostico,
                "siguiente_reintento": siguiente_tarea.numero_reintento,
            },
        )

    # -----------------------------------------------------------------------
    # Métodos utilitarios de apoyo
    # -----------------------------------------------------------------------

    def _determinar_numero_intento(self, practica_id: str, fallback_reintento: int) -> int:
        """Determina la posición ordinal del intento basándose en el historial persistido."""
        try:
            intentos = self._repositorio_practica.buscar_intentos_por_practica(practica_id)
            if intentos:
                return len(intentos) + 1
        except Exception:
            pass
        return fallback_reintento + 1

    def _notificar_estudiante_aprobacion(
        self,
        *,
        practica_id: str,
        tarea: DatosTareaValidacionSia,
    ) -> bool:
        """Envía correo de validación exitosa al estudiante (Escenario 6)."""
        if not tarea.correo_estudiante:
            return False

        asunto = "Postulación a práctica empresarial: Requisitos académicos validados exitosamente"
        cuerpo = (
            f"Estimado/a estudiante ({tarea.documento_estudiante}):\n\n"
            f"Le informamos que su postulación a la práctica empresarial con identificador "
            f"'{practica_id}' ha sido verificada satisfactoriamente con el Sistema de Información "
            f"Académica (SIA) tras la recuperación del servicio.\n\n"
            f"Su solicitud ha avanzado al estado 'Solicitada' y continuará el proceso de revisión "
            f"por parte de la Coordinación de prácticas.\n\n"
            f"Atentamente,\n"
            f"Sistema de Gestión de Prácticas Empresariales"
        )
        try:
            self._servicio_correo.enviar_notificacion(
                destinatario=tarea.correo_estudiante,
                asunto=asunto,
                cuerpo=cuerpo,
            )
            return True
        except ErrorServicioCorreo:
            return False

    def _notificar_estudiante_rechazo(
        self,
        *,
        practica_id: str,
        tarea: DatosTareaValidacionSia,
        causal: str,
    ) -> bool:
        """Envía correo informando el rechazo por requisitos académicos."""
        if not tarea.correo_estudiante:
            return False

        asunto = "Postulación a práctica empresarial: Notificación de rechazo de solicitud"
        cuerpo = (
            f"Estimado/a estudiante ({tarea.documento_estudiante}):\n\n"
            f"Le informamos que su postulación a la práctica empresarial con identificador "
            f"'{practica_id}' ha sido rechazada tras la validación con el Sistema de Información "
            f"Académica (SIA).\n\n"
            f"Causal del rechazo: {causal}\n\n"
            f"Si considera que se trata de una inconsistencia, por favor comuníquese con su facultad.\n\n"
            f"Atentamente,\n"
            f"Sistema de Gestión de Prácticas Empresariales"
        )
        try:
            self._servicio_correo.enviar_notificacion(
                destinatario=tarea.correo_estudiante,
                asunto=asunto,
                cuerpo=cuerpo,
            )
            return True
        except ErrorServicioCorreo:
            return False

    def _registrar_bitacora(
        self,
        *,
        actor_id: str,
        rol: str,
        ip: str,
        accion: str,
        entidad: str,
        detalles: Optional[dict[str, Any]] = None,
    ) -> None:
        """Registra un evento inmutable en la bitácora de auditoría sin interrumpir el flujo."""
        try:
            evento = EventoBitacora(
                actor_identificador=actor_id,
                rol_actor=rol,
                ip_origen=ip,
                accion_realizada=accion,
                entidad_afectada=entidad,
                detalles=detalles,
            )
            self._repositorio_practica.guardar_evento_bitacora(evento)
        except Exception:
            pass

    @staticmethod
    def calcular_espera_exponencial(
        numero_reintento: int,
        base_segundos: float = 2.0,
        factor: float = 2.0,
        max_segundos: float = 300.0,
    ) -> float:
        """Calcula el tiempo de espera en segundos aplicando retroceso exponencial (ADR-001).

        Fórmula: min(max_segundos, base_segundos * (factor ** (numero_reintento - 1)))
        """
        if numero_reintento <= 1:
            return base_segundos
        espera = base_segundos * (factor ** (numero_reintento - 1))
        return min(espera, max_segundos)

    def ejecutar_ciclo_completo(
        self,
        tarea_inicial: DatosTareaValidacionSia,
        *,
        al_esperar: Optional[Callable[[int, float], None]] = None,
    ) -> list[ResultadoReintentoSiaDTO]:
        """Ejecuta iterativamente los reintentos asíncronos hasta el éxito o agotamiento.

        Permite simular o ejecutar de forma determinista el ciclo completo de reintentos
        del worker de integración en entornos de prueba o procesamiento por lotes (Escenario 7).

        Args:
            tarea_inicial: Instancia inicial de DatosTareaValidacionSia.
            al_esperar: Callback opcional invocado en cada intervalo de retroceso exponencial
                recibiendo (numero_reintento, espera_segundos).

        Returns:
            Lista de ResultadoReintentoSiaDTO generados en cada iteración ejecutada.
        """
        resultados: list[ResultadoReintentoSiaDTO] = []
        tarea_actual: Optional[DatosTareaValidacionSia] = tarea_inicial

        while tarea_actual is not None:
            resultado = self.ejecutar(tarea_actual)
            resultados.append(resultado)

            if (
                resultado.exito
                or resultado.reintentos_agotados
                or resultado.tarea_siguiente is None
            ):
                break

            espera = self.calcular_espera_exponencial(tarea_actual.numero_reintento)
            if al_esperar is not None:
                al_esperar(tarea_actual.numero_reintento, espera)

            tarea_actual = resultado.tarea_siguiente

        return resultados
