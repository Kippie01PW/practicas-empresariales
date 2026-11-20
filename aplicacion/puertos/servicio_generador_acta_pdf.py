"""Puerto para la generación, sellado criptográfico SHA-256 y gestión de archivos de actas finales en PDF.

Traza: CU-09, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, DT-02,
ADR-002 (Clean Architecture y Puertos y Adaptadores), ADR-003 (Persistencia transaccional),
ADR-007 (Configuración declarativa de reglas versionadas), ADR-008 (Generación y preservación
del acta final mediante plantillas y sellado criptográfico SHA-256), Vista de Desarrollo §2 (03-desarrollo.md).

Define el contrato formal (Protocol) que la capa de aplicación exige al componente
Adaptador PDF y Hash y al Repositorio de actas PDF para:
- Renderizar la plantilla HTML/CSS configurada en la versión vinculada de ReglaPrograma a un binario PDF.
- Calcular la huella criptográfica SHA-256 de 64 caracteres hexadecimales sobre el binario generado.
- Almacenar y recuperar el archivo PDF confirmando su rutaArchivoPdf.
- Verificar la integridad del documento contra su huella SHA-256 y eliminar archivos PDF
  huérfanos mediante compensación transaccional si falla la persistencia en base de datos (DT-02, Escenario 10).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from aplicacion.dtos.acta_final_dto import (
    DatosRenderizadoActaDTO,
    ResultadoRenderizadoPdfDTO,
)


@runtime_checkable
class ServicioGeneradorActaPdfPort(Protocol):
    """Puerto de salida para el renderizado HTML/CSS a PDF, sellado SHA-256 y compensación de archivos (CU-09).

    Corresponde a la abstracción del componente 'Adaptador PDF y Hash' que interactúa con el
    contenedor 'Repositorio de actas PDF' (ADR-002, ADR-007, ADR-008).
    """

    def generar_y_guardar_acta_pdf(
        self, datos: DatosRenderizadoActaDTO
    ) -> ResultadoRenderizadoPdfDTO:
        """Renderiza la plantilla HTML/CSS a PDF, calcula su hash SHA-256 y almacena el binario.

        Toma la plantilla configurada en la versión de ReglaPrograma vinculada a la práctica
        (EAC-01, ADR-007), inyecta los datos del estudiante, empresa, supervisor, docente asesor,
        horas aprobadas y evaluación de desempeño (aprobatoria o reprobatoria con observaciones),
        calcula la huella criptográfica SHA-256 de 64 caracteres hexadecimales sobre el binario PDF
        y lo persiste en el repositorio de actas confirmando su rutaArchivoPdf (ADR-008).

        Args:
            datos: DTO inmutable con los datos consolidados de la práctica y la plantilla a renderizar.

        Returns:
            DTO inmutable ResultadoRenderizadoPdfDTO con ruta_archivo_pdf, contenido_pdf,
            hash_integridad_sha256 y plantilla_utilizada.

        Raises:
            ErrorAlmacenamientoActaPdfError: Si ocurre un error de entrada/salida al escribir
                el archivo binario en el repositorio de actas PDF (Escenario 10, DT-02).
        """
        ...

    def obtener_contenido_pdf(self, ruta_archivo_pdf: str) -> Optional[bytes]:
        """Recupera el contenido binario de un archivo PDF almacenado en el repositorio de actas.

        Args:
            ruta_archivo_pdf: Ruta del archivo PDF dentro del repositorio de actas.

        Returns:
            Contenido binario (bytes) del archivo PDF si existe, o None si no se encuentra.
        """
        ...

    def verificar_integridad_pdf(
        self, ruta_archivo_pdf: str, hash_esperado: str
    ) -> bool:
        """Verifica que la huella SHA-256 del binario PDF almacenado coincida con el hash esperado.

        Args:
            ruta_archivo_pdf: Ruta del archivo PDF dentro del repositorio de actas.
            hash_esperado: Huella criptográfica SHA-256 de 64 caracteres hexadecimales registrada.

        Returns:
            True si el archivo existe y su hash SHA-256 recalculado coincide con hash_esperado;
            False en caso contrario.
        """
        ...

    def eliminar_archivo_pdf(self, ruta_archivo_pdf: str) -> None:
        """Elimina un archivo PDF del repositorio de actas para compensación transaccional (DT-02).

        Invocado cuando ocurre un fallo al persistir el registro de ActaFinal o el EventoBitacora
        en el repositorio transaccional, evitando dejar archivos PDF huérfanos sin su huella
        hashIntegridadSha256 registrada (Escenario 10, ADR-003, ADR-008).

        Args:
            ruta_archivo_pdf: Ruta del archivo PDF a eliminar.
        """
        ...

    def simular_acta_pdf_en_memoria(
        self, datos: DatosRenderizadoActaDTO
    ) -> ResultadoRenderizadoPdfDTO:
        """Renderiza en memoria la plantilla HTML/CSS a un binario PDF de prueba sin persistir en el repositorio oficial (CU-12).

        Permite al Coordinador de prácticas previsualizar el formato del ActaFinal, las horasRequeridas
        y los criteriosRubrica de una ReglaPrograma en estado Borrador antes de activarla oficialmente,
        sin escribir ningún archivo en el Repositorio de actas PDF ni alterar ninguna Práctica o ActaFinal
        existente (Escenarios 3 y 10 de CU-12, ADR-007, ADR-008).

        Args:
            datos: DTO inmutable con los datos de simulación y la plantilla del borrador a renderizar.

        Returns:
            DTO inmutable ResultadoRenderizadoPdfDTO con contenido_pdf, hash_integridad_sha256 y
            plantilla_utilizada generados exclusivamente en memoria.
        """
        ...
