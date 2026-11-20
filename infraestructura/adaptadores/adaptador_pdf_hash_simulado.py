"""Adaptador simulado para renderizado de plantilla HTML/CSS a PDF, sellado SHA-256 y almacenamiento de actas.

Traza: CU-09, CU-10, EAC-01, EAC-03, OB-01, OB-05, PA-03, RN-01, RN-02, DT-02,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional y compensación atómica),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico SHA-256),
Vista de Desarrollo §2 (03-desarrollo.md) y Vista de Procesos §2 (02-procesos.md).

Implementa en memoria el componente 'Adaptador PDF y Hash' junto con el contenedor simulado
'Repositorio de actas PDF' (`vol_pdf`), satisfaciendo simultáneamente los contratos de los puertos
`ServicioGeneradorActaPdfPort` (CU-09) y `ServicioPdfHashPort` (CU-10):
- Renderiza dinámicamente la plantilla HTML/CSS (`plantillaActa`) de la versión original de
  `ReglaPrograma` vinculada a la práctica (EAC-01), inyectando los datos del Estudiante,
  DocenteAsesor, SupervisorEmpresa, horas acumuladas aprobadas, horas requeridas y
  EvaluacionDesempeno (con calificación cuantitativa aprobatoria o reprobatoria y observaciones).
- Empaqueta un documento binario PDF determinista (`%PDF-1.4 ... %%EOF`) y calcula su huella
  criptográfica SHA-256 de 64 caracteres hexadecimales con `hashlib.sha256` (ADR-008).
- Almacena el archivo binario en el volumen simulado de actas PDF confirmando su `rutaArchivoPdf`.
- Permite recuperar el binario, recalcular su hash SHA-256, verificar su integridad criptográfica,
  eliminar archivos por compensación transaccional para evitar PDFs huérfanos (DT-02, Escenario 10)
  y simular fallos deterministas de escritura o corrupción para pruebas de escenarios.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from aplicacion.dtos.acta_final_dto import (
    DatosRenderizadoActaDTO,
    ResultadoRenderizadoPdfDTO,
)
from aplicacion.puertos.servicio_generador_acta_pdf import (
    ServicioGeneradorActaPdfPort,
)
from aplicacion.puertos.servicio_pdf_hash import ServicioPdfHashPort
from dominio.errores import ErrorAlmacenamientoActaPdfError


class AdaptadorPdfYHashSimulado(ServicioGeneradorActaPdfPort, ServicioPdfHashPort):
    """Adaptador determinista en memoria para renderizado HTML/CSS a PDF, sellado SHA-256 y repositorio de actas.

    Corresponde al componente 'Adaptador PDF y Hash' y al contenedor 'Repositorio de actas PDF'
    definidos en `docs/vistas/03-desarrollo.md` y `docs/vistas/02-procesos.md`.
    """

    def __init__(
        self,
        directorio_base: str = "/repositorio_actas",
    ) -> None:
        self._directorio_base: str = directorio_base.rstrip("/") or "/repositorio_actas"
        self._archivos_pdf: dict[str, bytes] = {}
        self._html_renderizados: dict[str, str] = {}
        self._fallo_escritura_activo: bool = False
        self._mensaje_fallo_escritura: str = (
            "Fallo simulado de entrada/salida al escribir en el repositorio de actas PDF."
        )

    # -----------------------------------------------------------------------
    # Implementación de ServicioGeneradorActaPdfPort (CU-09)
    # -----------------------------------------------------------------------

    def generar_y_guardar_acta_pdf(
        self,
        datos: DatosRenderizadoActaDTO,
    ) -> ResultadoRenderizadoPdfDTO:
        """Renderiza la plantilla HTML/CSS a PDF, calcula su hash SHA-256 y guarda el binario (CU-09).

        Traza: CU-09, Escenarios 1, 6, 10 y 11, ADR-007, ADR-008, EAC-01, DT-02.

        Args:
            datos: DTO inmutable con los datos consolidados de la práctica y la plantilla de la regla vinculada.

        Returns:
            ResultadoRenderizadoPdfDTO con la ruta confirmada, el binario PDF, el hash SHA-256
            de 64 caracteres hexadecimales y la plantilla utilizada.

        Raises:
            ErrorAlmacenamientoActaPdfError: Si ocurre o se simula un error de escritura en el
                repositorio de actas PDF (Escenario 10, DT-02).
        """
        anio_emision = datos.fecha_emision.year
        ruta_archivo_pdf = (
            f"{self._directorio_base}/{anio_emision}/{datos.numero_acta}.pdf"
        )

        if self._fallo_escritura_activo:
            raise ErrorAlmacenamientoActaPdfError(
                practica_id=datos.practica_id,
                ruta_archivo_pdf=ruta_archivo_pdf,
                causa=self._mensaje_fallo_escritura,
            )

        html_renderizado = self._renderizar_plantilla_html(datos)
        contenido_pdf = self._empaquetar_binario_pdf(datos, html_renderizado)
        hash_sha256 = self.calcular_hash_sha256(contenido_pdf)

        self._archivos_pdf[ruta_archivo_pdf] = contenido_pdf
        self._html_renderizados[ruta_archivo_pdf] = html_renderizado

        return ResultadoRenderizadoPdfDTO(
            ruta_archivo_pdf=ruta_archivo_pdf,
            contenido_pdf=contenido_pdf,
            hash_integridad_sha256=hash_sha256,
            plantilla_utilizada=datos.plantilla_acta,
        )

    def obtener_contenido_pdf(self, ruta_archivo_pdf: str) -> Optional[bytes]:
        """Recupera el contenido binario de un archivo PDF almacenado en el repositorio de actas."""
        return self._archivos_pdf.get(ruta_archivo_pdf)

    def verificar_integridad_pdf(
        self,
        ruta_archivo_pdf: str,
        hash_esperado: str,
    ) -> bool:
        """Verifica en tiempo constante que el hash SHA-256 del PDF almacenado coincida con el esperado."""
        contenido = self._archivos_pdf.get(ruta_archivo_pdf)
        if contenido is None or not hash_esperado or not hash_esperado.strip():
            return False
        hash_actual = self.calcular_hash_sha256(contenido)
        return hmac.compare_digest(hash_actual, hash_esperado.strip().lower())

    def eliminar_archivo_pdf(self, ruta_archivo_pdf: str) -> None:
        """Elimina un archivo PDF del repositorio de actas para compensación transaccional (DT-02, Escenario 10)."""
        self._archivos_pdf.pop(ruta_archivo_pdf, None)
        self._html_renderizados.pop(ruta_archivo_pdf, None)

    # -----------------------------------------------------------------------
    # Implementación complementaria de ServicioPdfHashPort (CU-10)
    # -----------------------------------------------------------------------

    def calcular_hash_sha256(self, contenido_pdf: bytes) -> str:
        """Calcula la huella criptográfica SHA-256 de 64 caracteres hexadecimales en minúsculas (ADR-008)."""
        return hashlib.sha256(contenido_pdf).hexdigest().lower()

    def guardar_binario_pdf(
        self,
        ruta_archivo_pdf: str,
        contenido_pdf: bytes,
    ) -> str:
        """Almacena directamente un binario PDF en la ruta indicada y retorna su hash SHA-256."""
        if self._fallo_escritura_activo:
            raise ErrorAlmacenamientoActaPdfError(
                ruta_archivo_pdf=ruta_archivo_pdf,
                causa=self._mensaje_fallo_escritura,
            )
        self._archivos_pdf[ruta_archivo_pdf] = contenido_pdf
        return self.calcular_hash_sha256(contenido_pdf)

    def obtener_binario_pdf(self, ruta_archivo_pdf: str) -> bytes:
        """Recupera los bytes del archivo PDF almacenado o retorna b'' si no existe."""
        return self._archivos_pdf.get(ruta_archivo_pdf, b"")

    def recalcular_hash_archivo(self, ruta_archivo_pdf: str) -> str:
        """Lee el archivo PDF desde la ruta indicada y recalcula su huella criptográfica SHA-256."""
        contenido = self._archivos_pdf.get(ruta_archivo_pdf)
        if contenido is None:
            return ""
        return self.calcular_hash_sha256(contenido)

    # -----------------------------------------------------------------------
    # Métodos de inspección y simulación determinista para validación (CU-09 / CU-10)
    # -----------------------------------------------------------------------

    def configurar_fallo_escritura(
        self,
        activar: bool,
        mensaje: Optional[str] = None,
    ) -> None:
        """Activa o desactiva la simulación determinista de fallo de escritura en disco (Escenario 10, DT-02)."""
        self._fallo_escritura_activo = activar
        if mensaje is not None:
            self._mensaje_fallo_escritura = mensaje

    def alterar_binario_pdf(
        self,
        ruta_archivo_pdf: str,
        nuevo_contenido: bytes,
    ) -> None:
        """Simula la alteración o corrupción de un archivo PDF en el repositorio para pruebas de integridad."""
        self._archivos_pdf[ruta_archivo_pdf] = nuevo_contenido

    def obtener_html_renderizado(self, ruta_archivo_pdf: str) -> Optional[str]:
        """Retorna el documento HTML intermedio renderizado a partir de la plantilla para inspección."""
        return self._html_renderizados.get(ruta_archivo_pdf)

    def existe_archivo_pdf(self, ruta_archivo_pdf: str) -> bool:
        """Indica si existe un archivo PDF almacenado en la ruta especificada."""
        return ruta_archivo_pdf in self._archivos_pdf

    def listar_rutas_archivos(self) -> list[str]:
        """Retorna la lista ordenada de todas las rutas de archivos PDF almacenados."""
        return sorted(self._archivos_pdf.keys())

    def cantidad_archivos_almacenados(self) -> int:
        """Retorna el total de archivos PDF actualmente almacenados en el repositorio."""
        return len(self._archivos_pdf)

    def limpiar(self) -> None:
        """Reinicia el almacén en memoria de archivos PDF y desactiva fallos simulados."""
        self._archivos_pdf.clear()
        self._html_renderizados.clear()
        self._fallo_escritura_activo = False

    # -----------------------------------------------------------------------
    # Métodos internos de renderizado HTML/CSS y empaquetado PDF
    # -----------------------------------------------------------------------

    def _renderizar_plantilla_html(self, datos: DatosRenderizadoActaDTO) -> str:
        """Inyecta los datos consolidados de la práctica en la plantilla HTML/CSS de la ReglaPrograma (ADR-007, ADR-008)."""
        concepto_desempeno = (
            "APROBATORIA" if datos.es_aprobatoria else "REPROBATORIA"
        )
        observaciones_texto = (
            datos.observaciones_evaluacion
            if datos.observaciones_evaluacion
            else "Sin observaciones adicionales."
        )
        criterios_rubrica = "; ".join(
            f"{criterio}: {puntaje:.2f}"
            for criterio, puntaje in sorted(datos.respuestas_rubrica.items())
        )
        fecha_iso = datos.fecha_emision.isoformat()

        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"es\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            f"  <meta name=\"template\" content=\"{datos.plantilla_acta}\">\n"
            f"  <meta name=\"regla-programa-id\" content=\"{datos.regla_programa_id}\">\n"
            f"  <meta name=\"regla-version\" content=\"{datos.version_regla}\">\n"
            f"  <title>Acta Final de Práctica Empresarial - {datos.numero_acta}</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>ACTA FINAL DE PRÁCTICA EMPRESARIAL - {datos.numero_acta}</h1>\n"
            f"  <p><strong>Plantilla Aplicada:</strong> {datos.plantilla_acta} "
            f"(Regla: {datos.regla_programa_id}, Versión: {datos.version_regla})</p>\n"
            f"  <p><strong>Programa Académico:</strong> {datos.programa_academico}</p>\n"
            f"  <p><strong>Identificador de Práctica:</strong> {datos.practica_id}</p>\n"
            f"  <p><strong>Estudiante:</strong> {datos.estudiante_id}</p>\n"
            f"  <p><strong>Docente Asesor:</strong> {datos.docente_asesor_id} - {datos.nombre_docente_asesor}</p>\n"
            f"  <p><strong>Supervisor de Empresa:</strong> {datos.supervisor_empresa_id}</p>\n"
            f"  <p><strong>Horas Aprobadas / Horas Requeridas:</strong> "
            f"{datos.horas_acumuladas_aprobadas} / {datos.horas_requeridas}</p>\n"
            f"  <p><strong>Calificación Cuantitativa:</strong> {datos.calificacion_cuantitativa:.2f} "
            f"({concepto_desempeno})</p>\n"
            f"  <p><strong>Detalle de Rúbrica:</strong> {criterios_rubrica}</p>\n"
            f"  <p><strong>Observaciones de Evaluación:</strong> {observaciones_texto}</p>\n"
            f"  <p><strong>Fecha de Emisión:</strong> {fecha_iso}</p>\n"
            "</body>\n"
            "</html>"
        )

    def _empaquetar_binario_pdf(
        self,
        datos: DatosRenderizadoActaDTO,
        html_renderizado: str,
    ) -> bytes:
        """Construye un documento binario PDF determinista a partir del HTML renderizado."""
        cuerpo_pdf = (
            "%PDF-1.4\n"
            f"% ActaFinal: {datos.numero_acta}\n"
            f"% Practica: {datos.practica_id}\n"
            f"% Plantilla: {datos.plantilla_acta} (Version: {datos.version_regla})\n"
            "1 0 obj\n"
            "<< /Type /Catalog /Pages 2 0 R >>\n"
            "endobj\n"
            "2 0 obj\n"
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            "endobj\n"
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\n"
            "endobj\n"
            "4 0 obj\n"
            f"<< /Length {len(html_renderizado.encode('utf-8'))} >>\n"
            "stream\n"
            f"{html_renderizado}\n"
            "endstream\n"
            "endobj\n"
            "%%EOF\n"
        )
        return cuerpo_pdf.encode("utf-8")


AdaptadorPdfHashSimulado = AdaptadorPdfYHashSimulado
