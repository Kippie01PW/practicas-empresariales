"""Adaptador simulado para el Servicio de Registro Académico (SIA) con Circuit Breaker y timeout.

Traza: CU-01, EAC-02, RT-01, RT-03, ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Clean Architecture y Puertos y Adaptadores), Vista Lógica §2, Vista de Procesos §2.

Implementa el puerto `ServicioRegistroAcademicoPort` simulando el comportamiento del Sistema
de Información Académica (SIA) institucional de manera determinista, integrando:
1. Simulación de respuestas de cumplimiento e incumplimiento de requisitos académicos.
2. Simulación de timeouts (> 5.0 s) y caídas de servicio (5xx / red).
3. Patrón Circuit Breaker (ADR-001): transiciona a estado ABIERTO tras un umbral de fallos
   consecutivos y rechaza de inmediato llamadas subsiguientes para proteger el sistema.
4. Trazabilidad de consultas recibidas para validación de invariantes (e.g. que no se consulte
   al SIA si falla la precondición de práctica activa o de regla de programa).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from aplicacion.puertos.servicio_registro_academico import (
    IndisponibilidadRegistroAcademicoError,
    ResultadoRequisitosAcademicos,
    ServicioRegistroAcademicoPort,
    TimeoutRegistroAcademicoError,
)


class EstadoCircuitBreaker(str, Enum):
    """Estados formales del Circuit Breaker (ADR-001)."""

    CERRADO = "Cerrado"      # Operación normal: solicitudes fluyen al SIA
    ABIERTO = "Abierto"      # Circuito abierto: rechazo inmediato sin consultar al SIA
    SEMI_ABIERTO = "SemiAbierto"  # Modo de prueba tras ventana de recuperación


class ModoFalloSia(str, Enum):
    """Modo de fallo forzado para simulación de contingencias operativas."""

    NINGUNO = "Ninguno"
    TIMEOUT = "Timeout"
    ERROR_SERVICIO = "ErrorServicio"


class AdaptadorSiaSimulado(ServicioRegistroAcademicoPort):
    """Implementación simulada y determinista de ServicioRegistroAcademicoPort.

    Permite controlar las respuestas del SIA y simular caídas, timeouts y apertura
    del Circuit Breaker para los escenarios de spec.md (1, 2, 5, 6, 7).
    """

    def __init__(
        self,
        *,
        umbral_fallos: int = 3,
        timeout_limite_segundos: float = 5.0,
    ) -> None:
        """Inicializa el adaptador simulado.

        Args:
            umbral_fallos: Cantidad de fallos consecutivos requeridos para abrir el Circuit Breaker.
            timeout_limite_segundos: Umbral en segundos para considerar timeout de consulta (RT-03).
        """
        self._umbral_fallos: int = umbral_fallos
        self._timeout_limite_segundos: float = timeout_limite_segundos
        self._contador_fallos_consecutivos: int = 0
        self._estado_circuit_breaker: EstadoCircuitBreaker = EstadoCircuitBreaker.CERRADO
        self._modo_fallo_forzado: ModoFalloSia = ModoFalloSia.NINGUNO

        # Almacén de respuestas personalizadas por documento de estudiante
        self._estudiantes_registrados: dict[str, ResultadoRequisitosAcademicos] = {}

        # Historial de consultas realizadas para verificación y auditoría
        self._consultas_realizadas: list[str] = []

    # -- Propiedades de estado del Circuit Breaker --------------------------

    @property
    def estado_circuit_breaker(self) -> EstadoCircuitBreaker:
        return self._estado_circuit_breaker

    @property
    def consultas_realizadas(self) -> list[str]:
        return list(self._consultas_realizadas)

    @property
    def contador_fallos(self) -> int:
        return self._contador_fallos_consecutivos

    # -- Métodos de configuración para pruebas deterministas ---------------

    def configurar_estudiante(
        self,
        documento: str,
        resultado: ResultadoRequisitosAcademicos,
    ) -> None:
        """Configura la respuesta del SIA para un documento específico."""
        self._estudiantes_registrados[documento.strip()] = resultado

    def configurar_estudiante_cumple(
        self,
        documento: str,
        *,
        creditos_aprobados: int = 140,
        porcentaje_avance: float = 85.0,
    ) -> None:
        """Atajo para registrar un estudiante que cumple con los requisitos académicos."""
        self.configurar_estudiante(
            documento,
            ResultadoRequisitosAcademicos.cumple(
                creditos_aprobados=creditos_aprobados,
                porcentaje_avance=porcentaje_avance,
            ),
        )

    def configurar_estudiante_no_cumple(
        self,
        documento: str,
        causal: str,
        *,
        creditos_aprobados: int = 90,
        porcentaje_avance: float = 55.0,
    ) -> None:
        """Atajo para registrar un estudiante que NO cumple los requisitos académicos."""
        self.configurar_estudiante(
            documento,
            ResultadoRequisitosAcademicos.no_cumple(
                causal=causal,
                creditos_aprobados=creditos_aprobados,
                porcentaje_avance=porcentaje_avance,
            ),
        )

    def simular_timeout(self) -> None:
        """Fuerza que las consultas al SIA fallen por timeout (> 5 s)."""
        self._modo_fallo_forzado = ModoFalloSia.TIMEOUT

    def simular_caida(self) -> None:
        """Fuerza que las consultas al SIA fallen por error de servicio (503/red)."""
        self._modo_fallo_forzado = ModoFalloSia.ERROR_SERVICIO

    def simular_recuperacion(self) -> None:
        """Restablece el servicio SIA a operación normal y cierra el Circuit Breaker."""
        self._modo_fallo_forzado = ModoFalloSia.NINGUNO
        self._contador_fallos_consecutivos = 0
        self._estado_circuit_breaker = EstadoCircuitBreaker.CERRADO

    def restablecer_servicio(self) -> None:
        """Alias de simular_recuperacion."""
        self.simular_recuperacion()

    def abrir_circuit_breaker(self) -> None:
        """Fuerza la apertura inmediata del Circuit Breaker."""
        self._estado_circuit_breaker = EstadoCircuitBreaker.ABIERTO

    def limpiar_historial(self) -> None:
        """Limpia el registro de consultas realizadas."""
        self._consultas_realizadas.clear()

    # -- Implementación del contrato ServicioRegistroAcademicoPort ----------

    def consultar_requisitos_academicos(
        self, documento_estudiante: str
    ) -> ResultadoRequisitosAcademicos:
        """Consulta los requisitos académicos del estudiante aplicando Circuit Breaker y timeout.

        Raises:
            IndisponibilidadRegistroAcademicoError: Si el Circuit Breaker está ABIERTO o hay caída de servicio.
            TimeoutRegistroAcademicoError: Si se simula un retardo superior a 5 segundos.
        """
        doc = documento_estudiante.strip()

        # 1. Validación de Circuit Breaker: si está ABIERTO, rechazar de inmediato
        if self._estado_circuit_breaker == EstadoCircuitBreaker.ABIERTO:
            raise IndisponibilidadRegistroAcademicoError(
                documento_estudiante=doc,
                causa="Circuit Breaker en estado ABIERTO tras fallos consecutivos del SIA.",
                circuit_breaker_abierto=True,
            )

        # Se registra la consulta en el historial
        self._consultas_realizadas.append(doc)

        # 2. Manejo de fallos forzados de infraestructura (EAC-02, RT-03)
        if self._modo_fallo_forzado == ModoFalloSia.TIMEOUT:
            self._registrar_fallo()
            raise TimeoutRegistroAcademicoError(
                documento_estudiante=doc,
                timeout_segundos=self._timeout_limite_segundos,
                mensaje=(
                    f"Tiempo de espera agotado ({self._timeout_limite_segundos}s) "
                    f"en el servicio de Registro Académico para el estudiante '{doc}'."
                ),
            )

        if self._modo_fallo_forzado == ModoFalloSia.ERROR_SERVICIO:
            self._registrar_fallo()
            raise IndisponibilidadRegistroAcademicoError(
                documento_estudiante=doc,
                causa="HTTP 503 Servicio No Disponible (caída del backend SIA).",
                circuit_breaker_abierto=False,
            )

        # 3. Respuesta exitosa: restablecer contador de fallos
        self._contador_fallos_consecutivos = 0

        # Si el estudiante está en el almacén simulado, retornar su configuración
        if doc in self._estudiantes_registrados:
            return self._estudiantes_registrados[doc]

        # Por defecto determinista: cumple requisitos
        return ResultadoRequisitosAcademicos.cumple(
            creditos_aprobados=140,
            porcentaje_avance=85.0,
            detalles={"origen": "Simulador SIA - Respuesta predeterminada"},
        )

    # -- Mecanismo interno del Circuit Breaker -------------------------------

    def _registrar_fallo(self) -> None:
        """Incrementa el contador de fallos consecutivos y abre el circuito si supera el umbral."""
        self._contador_fallos_consecutivos += 1
        if self._contador_fallos_consecutivos >= self._umbral_fallos:
            self._estado_circuit_breaker = EstadoCircuitBreaker.ABIERTO
