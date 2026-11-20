"""Entidad de dominio ActaFinal.

Traza: CU-10, EAC-03, PA-03, RN-01, RN-02, RN-03, ADR-002, ADR-006, ADR-008, ADR-010,
Vista Lógica §2 (01-logica.puml).

Modela el documento oficial de culminación de la práctica empresarial renderizado
en PDF con firmas electrónicas secuenciales (DocenteAsesor -> Coordinador de prácticas)
y preservación inmutable garantizada mediante sellado criptográfico SHA-256.
"""

from __future__ import annotations

import hmac
import re
import uuid
from datetime import datetime
from typing import Optional

from dominio.errores import (
    ActaYaAprobadaPorActorError,
    FaltaAprobacionDocentePreviaError,
    IntegridadActaInvalidaError,
)


class ActaFinal:
    """Entidad de dominio que representa el acta final de una práctica empresarial.

    Atributos del diagrama UML (01-logica.puml) y del plan técnico (plan.md):
        - id: Identificador único del acta final.
        - practica_id: Identificador de la práctica empresarial vinculada (relación 1 a 0..1).
        - numero_acta: Número oficial consecutivo o código institucional del acta.
        - fecha_emision: Marca temporal de generación inicial del acta en PDF.
        - ruta_archivo_pdf: Ruta o identificador en el volumen de almacenamiento de actas PDF.
        - hash_integridad_sha256: Huella criptográfica SHA-256 (64 caracteres hexadecimales) del binario PDF.
        - aprobada_por_docente: Indica si el DocenteAsesor asignado ya asentó su firma electrónica (Paso 1).
        - aprobada_por_coordinador: Indica si el Coordinador de prácticas ya asentó su firma electrónica (Paso 2).
        - docente_aprobador_id: Identificador del DocenteAsesor que aprobó electrónicamente el acta.
        - fecha_aprobacion_docente: Marca temporal de la aprobación electrónica del DocenteAsesor.
        - coordinador_aprobador_id: Identificador del Coordinador de prácticas que aprobó el acta.
        - fecha_aprobacion_coordinador: Marca temporal de la aprobación electrónica del Coordinador.
    """

    _PATRON_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")

    __slots__ = (
        "_id",
        "_practica_id",
        "_numero_acta",
        "_fecha_emision",
        "_ruta_archivo_pdf",
        "_hash_integridad_sha256",
        "_aprobada_por_docente",
        "_aprobada_por_coordinador",
        "_docente_aprobador_id",
        "_fecha_aprobacion_docente",
        "_coordinador_aprobador_id",
        "_fecha_aprobacion_coordinador",
    )

    def __init__(
        self,
        *,
        practica_id: str,
        numero_acta: str,
        ruta_archivo_pdf: str,
        hash_integridad_sha256: str,
        fecha_emision: Optional[datetime] = None,
        aprobada_por_docente: bool = False,
        aprobada_por_coordinador: bool = False,
        docente_aprobador_id: Optional[str] = None,
        fecha_aprobacion_docente: Optional[datetime] = None,
        coordinador_aprobador_id: Optional[str] = None,
        fecha_aprobacion_coordinador: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        if not practica_id or not practica_id.strip():
            raise ValueError("El identificador de la práctica es obligatorio para el ActaFinal.")
        if not numero_acta or not numero_acta.strip():
            raise ValueError("El número de acta es obligatorio para el ActaFinal.")
        if not ruta_archivo_pdf or not ruta_archivo_pdf.strip():
            raise ValueError("La ruta del archivo PDF es obligatoria para el ActaFinal.")

        hash_validado = self._validar_formato_sha256(hash_integridad_sha256)

        if bool(aprobada_por_coordinador) and not bool(aprobada_por_docente):
            raise FaltaAprobacionDocentePreviaError(
                practica_id=practica_id.strip(),
                acta_id=id.strip() if id and id.strip() else None,
            )

        self._id: str = id.strip() if id and id.strip() else str(uuid.uuid4())
        self._practica_id: str = practica_id.strip()
        self._numero_acta: str = numero_acta.strip()
        self._fecha_emision: datetime = fecha_emision or datetime.now()
        self._ruta_archivo_pdf: str = ruta_archivo_pdf.strip()
        self._hash_integridad_sha256: str = hash_validado
        self._aprobada_por_docente: bool = bool(aprobada_por_docente)
        self._aprobada_por_coordinador: bool = bool(aprobada_por_coordinador)
        self._docente_aprobador_id: Optional[str] = (
            docente_aprobador_id.strip()
            if docente_aprobador_id and docente_aprobador_id.strip()
            else None
        )
        self._fecha_aprobacion_docente: Optional[datetime] = fecha_aprobacion_docente
        self._coordinador_aprobador_id: Optional[str] = (
            coordinador_aprobador_id.strip()
            if coordinador_aprobador_id and coordinador_aprobador_id.strip()
            else None
        )
        self._fecha_aprobacion_coordinador: Optional[datetime] = fecha_aprobacion_coordinador

    # -- Validación e integridad criptográfica (ADR-008) -------------------

    @classmethod
    def _validar_formato_sha256(cls, valor_hash: str) -> str:
        """Valida que la huella SHA-256 sea una cadena hexadecimal válida de 64 caracteres."""
        if not isinstance(valor_hash, str) or not valor_hash.strip():
            raise ValueError("El hashIntegridadSha256 del ActaFinal no puede estar vacío.")
        limpio = valor_hash.strip().lower()
        if not cls._PATRON_SHA256.match(limpio):
            raise ValueError(
                "El hashIntegridadSha256 debe ser una cadena hexadecimal SHA-256 válida de 64 caracteres."
            )
        return limpio

    def verificar_integridad_hash(self, hash_recalculado: str) -> None:
        """Compara de forma segura el hash SHA-256 recalculado del PDF contra el registrado.

        Traza: CU-10, Escenarios 1, 2 y 4 (Verificación de huella SHA-256 del binario PDF
        antes de asentar firmas electrónicas), PA-03, ADR-008.

        Raises:
            IntegridadActaInvalidaError: Si el hash recalculado está vacío, tiene formato inválido
                o no coincide exactamente con el hashIntegridadSha256 registrado.
        """
        if not isinstance(hash_recalculado, str) or not hash_recalculado.strip():
            raise IntegridadActaInvalidaError(
                acta_id=self._id,
                practica_id=self._practica_id,
                hash_esperado=self._hash_integridad_sha256,
                hash_recalculado=hash_recalculado if isinstance(hash_recalculado, str) else None,
            )

        candidato = hash_recalculado.strip().lower()
        if not hmac.compare_digest(candidato, self._hash_integridad_sha256):
            raise IntegridadActaInvalidaError(
                acta_id=self._id,
                practica_id=self._practica_id,
                hash_esperado=self._hash_integridad_sha256,
                hash_recalculado=candidato,
            )

    # -- Operaciones de aprobación electrónica secuencial (RN-02, ADR-010) -

    def aprobar_por_docente(
        self,
        docente_id: str,
        fecha_aprobacion: Optional[datetime] = None,
    ) -> None:
        """Registra la aprobación electrónica del DocenteAsesor asignado (Paso 1).

        Traza: CU-10, Escenario 1 (Aprobación electrónica exitosa del acta final por el
        Docente asesor asignado) y Escenario 6 (Intento de aprobación electrónica duplicada).

        Raises:
            ValueError: Si el identificador del docente está vacío.
            ActaYaAprobadaPorActorError: Si la aprobación del DocenteAsesor ya fue asentada previamente.
        """
        if not docente_id or not docente_id.strip():
            raise ValueError("El identificador del DocenteAsesor es obligatorio para aprobar el acta.")

        if self._aprobada_por_docente:
            raise ActaYaAprobadaPorActorError(
                rol_actor="DocenteAsesor",
                actor_id=docente_id.strip(),
                practica_id=self._practica_id,
                acta_id=self._id,
                estado_actual="Completada" if self.esta_en_firme else "Evaluada",
            )

        self._aprobada_por_docente = True
        self._docente_aprobador_id = docente_id.strip()
        self._fecha_aprobacion_docente = fecha_aprobacion or datetime.now()

    def aprobar_por_coordinador(
        self,
        coordinador_id: str,
        fecha_aprobacion: Optional[datetime] = None,
    ) -> None:
        """Registra la aprobación electrónica final del Coordinador de prácticas (Paso 2).

        Traza: CU-10, Escenario 2 (Aprobación electrónica final exitosa por el Coordinador
        de prácticas), Escenario 3 (Intento de aprobación por el Coordinador sin la firma
        previa del Docente asesor) y Escenario 6 (Intento de aprobación electrónica duplicada).

        Raises:
            ValueError: Si el identificador del coordinador está vacío.
            ActaYaAprobadaPorActorError: Si la aprobación del Coordinador ya fue asentada previamente.
            FaltaAprobacionDocentePreviaError: Si el DocenteAsesor aún no ha firmado electrónicamente el acta.
        """
        if not coordinador_id or not coordinador_id.strip():
            raise ValueError(
                "El identificador del Coordinador de prácticas es obligatorio para aprobar el acta."
            )

        if self._aprobada_por_coordinador:
            raise ActaYaAprobadaPorActorError(
                rol_actor="Coordinador de prácticas",
                actor_id=coordinador_id.strip(),
                practica_id=self._practica_id,
                acta_id=self._id,
                estado_actual="Completada",
            )

        if not self._aprobada_por_docente:
            raise FaltaAprobacionDocentePreviaError(
                practica_id=self._practica_id,
                acta_id=self._id,
                docente_asesor_id=self._docente_aprobador_id,
            )

        self._aprobada_por_coordinador = True
        self._coordinador_aprobador_id = coordinador_id.strip()
        self._fecha_aprobacion_coordinador = fecha_aprobacion or datetime.now()

    # -- Propiedades de lectura --------------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def practica_id(self) -> str:
        return self._practica_id

    @property
    def numero_acta(self) -> str:
        return self._numero_acta

    @property
    def fecha_emision(self) -> datetime:
        return self._fecha_emision

    @property
    def ruta_archivo_pdf(self) -> str:
        return self._ruta_archivo_pdf

    @property
    def hash_integridad_sha256(self) -> str:
        return self._hash_integridad_sha256

    @property
    def aprobada_por_docente(self) -> bool:
        return self._aprobada_por_docente

    @property
    def aprobada_por_coordinador(self) -> bool:
        return self._aprobada_por_coordinador

    @property
    def docente_aprobador_id(self) -> Optional[str]:
        return self._docente_aprobador_id

    @property
    def fecha_aprobacion_docente(self) -> Optional[datetime]:
        return self._fecha_aprobacion_docente

    @property
    def coordinador_aprobador_id(self) -> Optional[str]:
        return self._coordinador_aprobador_id

    @property
    def fecha_aprobacion_coordinador(self) -> Optional[datetime]:
        return self._fecha_aprobacion_coordinador

    @property
    def esta_en_firme(self) -> bool:
        """Retorna True únicamente cuando tanto el DocenteAsesor como el Coordinador han aprobado el acta."""
        return self._aprobada_por_docente and self._aprobada_por_coordinador

    # -- Representación e igualdad -----------------------------------------

    def __repr__(self) -> str:
        return (
            f"ActaFinal(id={self._id!r}, "
            f"practica_id={self._practica_id!r}, "
            f"numero_acta={self._numero_acta!r}, "
            f"aprobada_por_docente={self._aprobada_por_docente!r}, "
            f"aprobada_por_coordinador={self._aprobada_por_coordinador!r}, "
            f"esta_en_firme={self.esta_en_firme!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ActaFinal):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
