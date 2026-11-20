"""Puerto de servicio para lectura de binarios PDF y cálculo de huella criptográfica SHA-256.

Traza: CU-09, CU-10, EAC-03, OB-05, PA-03, RN-02,
ADR-002 (Clean Architecture y Puertos y Adaptadores),
ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico),
Vista de Desarrollo §3 (03-desarrollo.md) y Vista de Procesos §2 (02-procesos.md).

Define el contrato formal (Protocol) que la capa de aplicación exige a los
adaptadores de infraestructura ("Adaptador PDF y Hash" / "Repositorio de actas PDF")
para obtener los bytes del documento PDF almacenado, calcular o recalcular su huella
criptográfica SHA-256 (64 caracteres hexadecimales) y comprobar su integridad.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ServicioPdfHashPort(Protocol):
    """Puerto para lectura de binarios PDF y verificación de huella SHA-256.

    Corresponde al contrato hacia el "Adaptador PDF y Hash" y el "Repositorio de actas PDF"
    definido en `docs/vistas/03-desarrollo.md`, utilizado por `AprobarActaElectronicamenteCasoUso`
    (CU-10, Escenarios 1, 2 y 4) para recalcular el hash SHA-256 del documento PDF almacenado
    antes de asentar cada firma electrónica.
    """

    def calcular_hash_sha256(self, contenido_pdf: bytes) -> str:
        """Calcula la huella criptográfica SHA-256 (64 caracteres hexadecimales) de un binario PDF.

        Args:
            contenido_pdf: Bytes del documento PDF.

        Returns:
            Cadena hexadecimal en minúsculas de 64 caracteres con el digest SHA-256.
        """
        ...

    def obtener_binario_pdf(self, ruta_archivo_pdf: str) -> bytes:
        """Recupera el contenido binario del archivo PDF desde el repositorio de actas.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento.

        Returns:
            Bytes del archivo PDF almacenado.
        """
        ...

    def recalcular_hash_archivo(self, ruta_archivo_pdf: str) -> str:
        """Lee el archivo PDF desde la ruta indicada y recalcula su huella criptográfica SHA-256.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento.

        Returns:
            Cadena hexadecimal de 64 caracteres con el hash SHA-256 recalculado del archivo,
            o cadena vacía / excepción de dominio si el archivo no está disponible.
        """
        ...

    def verificar_integridad_pdf(
        self,
        ruta_archivo_pdf: str,
        hash_esperado_sha256: str,
    ) -> bool:
        """Comprueba si el hash SHA-256 recalculado del archivo PDF coincide con el hash esperado.

        Args:
            ruta_archivo_pdf: Ruta o identificador del archivo PDF en el almacenamiento.
            hash_esperado_sha256: Huella SHA-256 registrada en la entidad ActaFinal.

        Returns:
            True si el archivo existe y su hash SHA-256 recalculado coincide exactamente
            con hash_esperado_sha256; False en caso contrario.
        """
        ...
