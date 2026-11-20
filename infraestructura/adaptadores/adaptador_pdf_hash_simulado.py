"""Adaptador simulado para almacenamiento en memoria de binarios PDF y cálculo de hash SHA-256.

Traza: CU-09, CU-10, EAC-03, OB-05, PA-03, RN-02,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico),
Vista de Desarrollo §3 (03-desarrollo.md) y Vista de Procesos §2 (02-procesos.md).

Implementa el puerto `ServicioPdfHashPort` simulando en memoria de forma determinista el
componente "Adaptador PDF y Hash" y el "Repositorio de actas PDF" (volumen local `vol_pdf`).
Permite almacenar binarios PDF, calcular y recalcular su huella criptográfica SHA-256
(64 caracteres hexadecimales), verificar la integridad frente al `hashIntegridadSha256`
registrado en `ActaFinal`, y simular escenarios de alteración o indisponibilidad del
documento PDF (CU-10, Escenarios 1, 2 y 4).
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from aplicacion.puertos.servicio_pdf_hash import ServicioPdfHashPort
from dominio.errores import IntegridadActaInvalidaError


class AdaptadorPdfHashSimulado(ServicioPdfHashPort):
    """Adaptador en memoria que simula el almacenamiento de actas PDF y el cálculo SHA-256.

    Corresponde al "Adaptador PDF y Hash" y al "Repositorio de actas PDF" de la capa
    de Infraestructura (`docs/vistas/03-desarrollo.md`), inyectado en el caso de uso
    `AprobarActaElectronicamenteCasoUso` (CU-10).
    """

    def __init__(
        self,
        archivos_iniciales: Optional[dict[str, bytes]] = None,
    ) -> None:
        """Inicializa el almacén en memoria de archivos binarios PDF (`vol_pdf`).

        Args:
            archivos_iniciales: Diccionario opcional `{ruta_archivo_pdf: contenido_pdf}`
                para precargar documentos PDF simulados.
        """
        self._archivos_pdf: dict[str, bytes] = {}
        if archivos_iniciales:
            for ruta, contenido in archivos_iniciales.items():
                self.guardar_binario_pdf(ruta, contenido)

    @staticmethod
    def _normalizar_ruta(ruta_archivo_pdf: str) -> str:
        """Valida y normaliza la ruta del archivo PDF."""
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            raise ValueError("La ruta del archivo PDF no puede estar vacía.")
        return ruta_archivo_pdf.strip()

    @staticmethod
    def _asegurar_bytes(contenido_pdf: bytes | str) -> bytes:
        """Convierte o valida que el contenido del archivo PDF sea `bytes`."""
        if isinstance(contenido_pdf, bytes):
            return contenido_pdf
        if isinstance(contenido_pdf, str):
            return contenido_pdf.encode("utf-8")
        raise TypeError("El contenido del documento PDF debe ser de tipo 'bytes' o 'str'.")

    def calcular_hash_sha256(self, contenido_pdf: bytes) -> str:
        """Calcula la huella criptográfica SHA-256 (64 caracteres hexadecimales) de un binario PDF.

        Args:
            contenido_pdf: Bytes del documento PDF.

        Returns:
            Cadena hexadecimal en minúsculas de 64 caracteres con el digest SHA-256.
        """
        datos = self._asegurar_bytes(contenido_pdf)
        return hashlib.sha256(datos).hexdigest().lower()

    def guardar_binario_pdf(self, ruta_archivo_pdf: str, contenido_pdf: bytes) -> str:
        """Almacena un documento binario PDF en el repositorio en memoria y retorna su hash SHA-256.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento (`vol_pdf`).
            contenido_pdf: Bytes del documento PDF generado.

        Returns:
            Huella criptográfica SHA-256 (64 caracteres hexadecimales) calculada sobre el binario.
        """
        ruta = self._normalizar_ruta(ruta_archivo_pdf)
        datos = self._asegurar_bytes(contenido_pdf)
        self._archivos_pdf[ruta] = datos
        return self.calcular_hash_sha256(datos)

    def obtener_binario_pdf(self, ruta_archivo_pdf: str) -> bytes:
        """Recupera el contenido binario del archivo PDF desde el repositorio de actas.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento.

        Returns:
            Bytes del archivo PDF almacenado.

        Raises:
            IntegridadActaInvalidaError: Si el archivo PDF no existe o no está disponible
                en el repositorio de actas (CU-10, Escenario 4).
        """
        ruta = self._normalizar_ruta(ruta_archivo_pdf)
        if ruta not in self._archivos_pdf:
            raise IntegridadActaInvalidaError(
                mensaje=(
                    f"El archivo PDF del ActaFinal en la ruta '{ruta}' no está disponible "
                    f"en el repositorio de actas y su integridad SHA-256 no puede ser verificada."
                )
            )
        return self._archivos_pdf[ruta]

    def recalcular_hash_archivo(self, ruta_archivo_pdf: str) -> str:
        """Lee el archivo PDF desde la ruta indicada y recalcula su huella criptográfica SHA-256.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento.

        Returns:
            Cadena hexadecimal de 64 caracteres con el hash SHA-256 recalculado del archivo,
            o cadena vacía si el archivo no está disponible en el almacenamiento.
        """
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            return ""
        ruta = ruta_archivo_pdf.strip()
        contenido = self._archivos_pdf.get(ruta)
        if contenido is None:
            return ""
        return self.calcular_hash_sha256(contenido)

    def verificar_integridad_pdf(
        self,
        ruta_archivo_pdf: str,
        hash_esperado_sha256: str,
    ) -> bool:
        """Comprueba en tiempo constante si el hash SHA-256 recalculado coincide con el esperado.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento.
            hash_esperado_sha256: Huella SHA-256 registrada en la entidad ActaFinal.

        Returns:
            True si el archivo existe y su hash SHA-256 recalculado coincide exactamente
            con `hash_esperado_sha256`; False en caso contrario.
        """
        if not isinstance(hash_esperado_sha256, str) or not hash_esperado_sha256.strip():
            return False
        hash_recalculado = self.recalcular_hash_archivo(ruta_archivo_pdf)
        if not hash_recalculado:
            return False
        return hmac.compare_digest(
            hash_recalculado.lower(),
            hash_esperado_sha256.strip().lower(),
        )

    def alterar_binario_pdf(self, ruta_archivo_pdf: str, nuevo_contenido: bytes) -> None:
        """Sobrescribe el binario PDF en memoria para simular corrupción o alteración (Escenario 4).

        Args:
            ruta_archivo_pdf: Ruta del archivo PDF a alterar en el repositorio en memoria.
            nuevo_contenido: Bytes alterados o corruptos que reemplazan al documento original.
        """
        ruta = self._normalizar_ruta(ruta_archivo_pdf)
        self._archivos_pdf[ruta] = self._asegurar_bytes(nuevo_contenido)

    def eliminar_binario_pdf(self, ruta_archivo_pdf: str) -> bool:
        """Elimina un archivo PDF del almacén en memoria para simular indisponibilidad (Escenario 4)."""
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            return False
        return self._archivos_pdf.pop(ruta_archivo_pdf.strip(), None) is not None

    def existe_archivo_pdf(self, ruta_archivo_pdf: str) -> bool:
        """Indica si existe un binario PDF almacenado en la ruta especificada."""
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            return False
        return ruta_archivo_pdf.strip() in self._archivos_pdf

    def listar_rutas(self) -> list[str]:
        """Retorna la lista de rutas de archivos PDF actualmente almacenadas en memoria."""
        return list(self._archivos_pdf.keys())

    def limpiar(self) -> None:
        """Elimina todos los archivos PDF almacenados en memoria."""
        self._archivos_pdf.clear()
