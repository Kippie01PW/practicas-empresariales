"""Adaptador simulado para almacenamiento en memoria de binarios PDF, renderizado de plantillas y cálculo de hash SHA-256.

Traza: CU-09, CU-10, CU-12, EAC-01, EAC-03, OB-05, PA-03, RN-02,
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-007 (Configuración declarativa de reglas versionadas por programa),
ADR-008 (Generación y preservación del acta final mediante plantillas y sellado criptográfico),
Vista de Desarrollo §3 (03-desarrollo.md) y Vista de Procesos §2 (02-procesos.md).

Implementa el puerto `ServicioPdfHashPort` y la simulación en memoria de `ServicioGeneradorActaPdfPort`
simulando de forma determinista el componente "Adaptador PDF y Hash" y el "Repositorio de actas PDF"
(volumen local `vol_pdf`). Permite almacenar binarios PDF, calcular y recalcular su huella criptográfica
SHA-256 (64 caracteres hexadecimales), verificar la integridad frente al `hashIntegridadSha256`
registrado en `ActaFinal`, simular escenarios de alteración o indisponibilidad del documento PDF
(CU-10, Escenarios 1, 2 y 4) y previsualizar en memoria plantillas de actas de `ReglaPrograma` en
estado `Borrador` sin persistirlas en el repositorio oficial (CU-12, Escenarios 3 y 10).
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from aplicacion.dtos.acta_final_dto import (
    DatosRenderizadoActaDTO,
    ResultadoRenderizadoPdfDTO,
)
from aplicacion.dtos.consolidado_auditoria_dto import DatosRenderizadoConsolidadoPdfDTO
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

    def simular_acta_pdf_en_memoria(
        self,
        datos: DatosRenderizadoActaDTO,
    ) -> ResultadoRenderizadoPdfDTO:
        """Renderiza en memoria la plantilla HTML/CSS a un binario PDF de prueba sin persistir en el repositorio oficial (CU-12).

        Traza: CU-12, Escenarios 3 y 10, EAC-01, ADR-007, ADR-008.
        Genera el documento HTML intermedio y el binario PDF de previsualización aplicando
        `datos.plantilla_acta`, `datos.horas_requeridas` y `datos.respuestas_rubrica`, y calcula
        su huella criptográfica SHA-256 de 64 caracteres hexadecimales sin escribir ninguna entrada
        en `self._archivos_pdf` (garantizando 0 escrituras en el repositorio oficial de actas PDF).
        """
        html_renderizado = self._renderizar_plantilla_html(datos)
        contenido_pdf = self._empaquetar_binario_pdf(datos, html_renderizado)
        hash_sha256 = self.calcular_hash_sha256(contenido_pdf)
        ruta_simulacion_memoria = f"memory://simulacion/{datos.numero_acta}.pdf"

        return ResultadoRenderizadoPdfDTO(
            ruta_archivo_pdf=ruta_simulacion_memoria,
            contenido_pdf=contenido_pdf,
            hash_integridad_sha256=hash_sha256,
            plantilla_utilizada=datos.plantilla_acta,
        )

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
        cabecera = (
            f"% ActaFinal: {datos.numero_acta}\n"
            f"% Practica: {datos.practica_id}\n"
            f"% Plantilla: {datos.plantilla_acta} (Version: {datos.version_regla})\n"
        )
        return self._empaquetar_pdf_generico(cabecera, html_renderizado)

    @staticmethod
    def _empaquetar_pdf_generico(cabecera_comentarios: str, html_renderizado: str) -> bytes:
        """Empaqueta contenido HTML renderizado en un binario PDF-1.4 determinista."""
        cuerpo_pdf = (
            "%PDF-1.4\n"
            f"{cabecera_comentarios}"
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

    def generar_consolidado_auditoria_pdf(
        self, datos: DatosRenderizadoConsolidadoPdfDTO
    ) -> tuple[bytes, str]:
        """Renderiza en PDF el consolidado histórico de prácticas y sus ActaFinal con sellado SHA-256 (CU-14)."""
        html_renderizado = self._renderizar_consolidado_html(datos)
        cabecera = (
            f"% ConsolidadoAuditoria: {datos.programa_academico} ({datos.periodo})\n"
            f"% TotalPracticas: {datos.total_practicas}\n"
            f"% Actor: {datos.actor_id}\n"
        )
        contenido_pdf = self._empaquetar_pdf_generico(cabecera, html_renderizado)
        hash_sha256 = self.calcular_hash_sha256(contenido_pdf)
        return contenido_pdf, hash_sha256

    def _renderizar_consolidado_html(
        self, datos: DatosRenderizadoConsolidadoPdfDTO
    ) -> str:
        """Construye el HTML determinista del consolidado histórico de auditoría (CU-14)."""
        rango_texto = (
            f"{datos.fecha_inicio.isoformat() if datos.fecha_inicio else 'N/A'} a "
            f"{datos.fecha_fin.isoformat() if datos.fecha_fin else 'N/A'}"
        )
        estado_texto = datos.estado_practica_filtro or "Todos"

        if datos.total_practicas == 0:
            cuerpo_registros = (
                "  <p><strong>Aviso:</strong> No se encontraron registros históricos "
                "para los criterios indicados.</p>\n"
            )
        else:
            filas: list[str] = []
            for reg in datos.registros:
                acta_info = (
                    f"Acta={reg.numero_acta}, Emisión={reg.fecha_emision_acta.isoformat() if reg.fecha_emision_acta else 'N/A'}, "
                    f"Firmas(Docente={reg.aprobada_por_docente}, Coordinador={reg.aprobada_por_coordinador}, "
                    f"EnFirme={reg.acta_en_firme}), SHA256={reg.hash_integridad_sha256}"
                    if reg.numero_acta
                    else "Sin ActaFinal emitida"
                )
                filas.append(
                    f"    <li>Practica={reg.practica_id} | Estudiante={reg.estudiante_id} | "
                    f"Estado={reg.estado_actual} | Docente={reg.docente_asesor_id or 'N/A'} "
                    f"({reg.nombre_docente_asesor or 'N/A'}) | Supervisor={reg.supervisor_empresa_id or 'N/A'} | "
                    f"Horas={reg.horas_acumuladas_aprobadas}/{reg.horas_requeridas or 'N/A'} | "
                    f"Nota={reg.calificacion_cuantitativa if reg.calificacion_cuantitativa is not None else 'N/A'} | "
                    f"{acta_info}</li>"
                )
            cuerpo_registros = "  <ul>\n" + "\n".join(filas) + "\n  </ul>\n"

        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"es\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            f"  <title>Consolidado de Auditoría - {datos.programa_academico} ({datos.periodo})</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>CONSOLIDADO HISTÓRICO DE AUDITORÍA - {datos.programa_academico}</h1>\n"
            f"  <p><strong>Período:</strong> {datos.periodo}</p>\n"
            f"  <p><strong>Rango de Fechas:</strong> {rango_texto}</p>\n"
            f"  <p><strong>Estado Filtrado:</strong> {estado_texto}</p>\n"
            f"  <p><strong>Solicitado por:</strong> {datos.actor_id}</p>\n"
            f"  <p><strong>Fecha de Generación:</strong> {datos.fecha_generacion.isoformat()}</p>\n"
            f"  <p><strong>Total Prácticas:</strong> {datos.total_practicas} | "
            f"<strong>Completadas:</strong> {datos.total_completadas} | "
            f"<strong>Con Acta en Firme:</strong> {datos.total_con_acta_en_firme}</p>\n"
            f"{cuerpo_registros}"
            "</body>\n"
            "</html>"
        )

