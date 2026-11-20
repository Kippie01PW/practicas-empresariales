"""Punto de entrada principal y composición de dependencias (Clean Architecture).

Traza: CU-01, EAC-01, EAC-02, RT-01, RT-03, RN-01, RN-03, PA-02, PA-03,
ADR-001 (Resiliencia e integración asíncrona),
ADR-002 (Monolito modular con Clean Architecture y Puertos y Adaptadores),
ADR-003 (Persistencia transaccional),
ADR-004 (Autenticación híbrida),
ADR-005 (Autorización RBAC centralizada),
ADR-006 (Bitácora Append-Only),
ADR-007 (Reglas versionadas por programa),
ADR-010 (Máquina de estados finitos),
Vista Lógica §2, Vista de Procesos §2, Vista de Desarrollo §2, Vista Física §2.

Este archivo actúa como el Composition Root (único punto de composición e inyección
de dependencias) del sistema:
1. Instancia los adaptadores de infraestructura en memoria y simuladores (persistencia,
   SIA con Circuit Breaker, bróker de mensajería, servicio de correo e IdP OIDC).
2. Precarga las reglas de programa activas vigentes (ADR-007).
3. Conecta y cablea los puertos de aplicación con sus adaptadores concretos.
4. Instancia los casos de uso principales: `PostularEstudianteCasoUso` y `ReintentarValidacionSiaCasoUso`.
5. Provee una interfaz estructurada (`SistemaPracticasEmpresariales`) y una ejecución de
   demostración CLI interactiva al ejecutarse como script directo.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from datetime import datetime, timedelta, timezone

from aplicacion.casos_uso.aprobar_acta_electronicamente import (
    AprobarActaElectronicamenteCasoUso,
)
from aplicacion.casos_uso.asignar_docente_asesor import AsignarDocenteAsesorCasoUso
from aplicacion.casos_uso.configurar_reglas_programa import (
    ConfigurarReglasProgramaCasoUso,
)
from aplicacion.casos_uso.consultar_estado_tramite import ConsultarEstadoTramiteCasoUso
from aplicacion.casos_uso.enviar_recordatorios_plazos import (
    EnviarRecordatoriosPlazosCasoUso,
)
from aplicacion.casos_uso.evaluar_desempeno import EvaluarDesempenoCasoUso
from aplicacion.casos_uso.evaluar_postulacion import EvaluarPostulacionCasoUso
from aplicacion.casos_uso.generar_acta_final import GenerarActaFinalCasoUso
from aplicacion.casos_uso.generar_consolidados_auditoria import (
    GenerarConsolidadosAuditoriaCasoUso,
)
from aplicacion.casos_uso.migrar_practicas_excel import MigrarPracticasExcelCasoUso
from aplicacion.casos_uso.monitorear_practicas import MonitorearPracticasCasoUso
from aplicacion.casos_uso.postular_estudiante import PostularEstudianteCasoUso
from aplicacion.casos_uso.registrar_horas import RegistrarHorasCasoUso
from aplicacion.casos_uso.reintentar_validacion_sia import ReintentarValidacionSiaCasoUso
from aplicacion.casos_uso.revisar_avances_horas import RevisarAvancesHorasCasoUso
from aplicacion.casos_uso.validar_horas_registradas import ValidarHorasRegistradasCasoUso
from aplicacion.dtos.acta_final_dto import (
    ActaFinalRespuestaDTO,
    DatosRenderizadoActaDTO,
    GenerarActaFinalComando,
    ResultadoRenderizadoPdfDTO,
)
from aplicacion.dtos.aprobacion_acta_dto import (
    AprobacionActaRespuestaDTO,
    AprobarActaComando,
)
from aplicacion.dtos.asignacion_docente_dto import (
    AsignacionDocenteRespuestaDTO,
    AsignarDocenteComando,
)
from aplicacion.dtos.avance_horas_dto import (
    AvanceHorasPracticaRespuestaDTO,
    ConsultarAvanceHorasComando,
    ConsultarAvancesDocenteComando,
    ListadoAvancesDocenteRespuestaDTO,
)
from aplicacion.dtos.consolidado_auditoria_dto import (
    ConsolidadoAuditoriaRespuestaDTO,
    GenerarConsolidadoAuditoriaComando,
)
from aplicacion.dtos.estado_tramite_dto import (
    ConsultarEstadoTramiteComando,
    EstadoTramitePracticaRespuestaDTO,
)
from aplicacion.dtos.evaluacion_desempeno_dto import (
    ConsultarFormularioEvaluacionComando,
    EvaluacionDesempenoRespuestaDTO,
    EvaluarDesempenoComando,
    FormularioEvaluacionRespuestaDTO,
)
from aplicacion.dtos.evaluacion_postulacion_dto import (
    EvaluacionPostulacionRespuestaDTO,
    EvaluarPostulacionComando,
)
from aplicacion.dtos.migracion_excel_dto import (
    MigrarPracticasExcelComando,
    MigrarPracticasExcelRespuestaDTO,
)
from aplicacion.dtos.monitoreo_practicas_dto import (
    ConsultarDetallePracticaMonitoreoComando,
    ConsultarMonitoreoPracticasComando,
    DetallePracticaMonitoreoRespuestaDTO,
    TableroMonitoreoPracticasRespuestaDTO,
)
from aplicacion.dtos.postulacion_dto import (
    PostulacionRespuestaDTO,
    PostularEstudianteComando,
)
from aplicacion.dtos.recordatorio_plazos_dto import (
    EjecutarRecordatoriosComando,
    ResultadoEnvioRecordatoriosDTO,
)
from aplicacion.dtos.registro_horas_dto import (
    RegistrarHorasComando,
    RegistroHorasRespuestaDTO,
)
from aplicacion.dtos.regla_programa_dto import (
    ActivarReglaProgramaComando,
    CrearBorradorReglaComando,
    EditarBorradorReglaComando,
    EliminarReglaProgramaComando,
    ReglaProgramaRespuestaDTO,
    SimulacionReglaProgramaRespuestaDTO,
    SimularReglaProgramaComando,
)
from aplicacion.dtos.validacion_horas_dto import (
    ValidacionHorasRespuestaDTO,
    ValidarHorasComando,
)
from aplicacion.puertos.servicio_generador_acta_pdf import (
    ServicioGeneradorActaPdfPort,
)
from aplicacion.seguridad.autorizador_rbac import AutorizadorRBAC, RolUsuario
from dominio.errores import ErrorAlmacenamientoActaPdfError
from dominio.modelos.acta_final import ActaFinal
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma
from infraestructura.adaptadores.adaptador_pdf_hash_simulado import (
    AdaptadorPdfHashSimulado,
)
from infraestructura.adaptadores.broker_memoria import InMemoryBrokerMensajes
from infraestructura.adaptadores.cliente_sia_simulado import AdaptadorSiaSimulado
from infraestructura.adaptadores.lector_plantilla_excel_simulado import (
    LectorPlantillaExcelSimulado,
)
from infraestructura.adaptadores.repositorio_memoria import (
    InMemoryRepositorioActaFinal,
    InMemoryRepositorioDocente,
    InMemoryRepositorioEvaluacionDesempeno,
    InMemoryRepositorioPractica,
    InMemoryRepositorioRegistroHoras,
    InMemoryRepositorioReglaPrograma,
    InMemoryRepositorioTokenEvaluacion,
)
from infraestructura.adaptadores.servicio_correo_simulado import AdaptadorCorreoSimulado
from infraestructura.seguridad.interceptor_identidad import InterceptorIdentidad
from infraestructura.seguridad.proveedor_identidad_simulado import (
    ProveedorIdentidadSimulado,
)


class AdaptadorPdfYHashSimulado(AdaptadorPdfHashSimulado, ServicioGeneradorActaPdfPort):
    """Adaptador determinista que unifica ServicioGeneradorActaPdfPort (CU-09) y ServicioPdfHashPort (CU-10).

    Renderiza dinámicamente la plantilla HTML/CSS (`plantillaActa`) de la `ReglaPrograma` vinculada
    a un binario PDF determinista (`%PDF-1.4 ... %%EOF`), calcula su huella criptográfica SHA-256
    de 64 caracteres hexadecimales (ADR-008) y gestiona el volumen simulado de actas PDF con soporte
    de compensación transaccional ante fallos (DT-02, Escenario 10).
    """

    def __init__(
        self,
        directorio_base: str = "/repositorio_actas",
    ) -> None:
        super().__init__()
        self._directorio_base: str = directorio_base.rstrip("/") or "/repositorio_actas"
        self._html_renderizados: dict[str, str] = {}
        self._fallo_escritura_activo: bool = False
        self._mensaje_fallo_escritura: str = (
            "Fallo simulado de entrada/salida al escribir en el repositorio de actas PDF."
        )

    def generar_y_guardar_acta_pdf(
        self,
        datos: DatosRenderizadoActaDTO,
    ) -> ResultadoRenderizadoPdfDTO:
        """Renderiza la plantilla HTML/CSS a PDF, calcula su hash SHA-256 y almacena el binario (CU-09)."""
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
        hash_sha256 = self.guardar_binario_pdf(ruta_archivo_pdf, contenido_pdf)
        self._html_renderizados[ruta_archivo_pdf] = html_renderizado

        return ResultadoRenderizadoPdfDTO(
            ruta_archivo_pdf=ruta_archivo_pdf,
            contenido_pdf=contenido_pdf,
            hash_integridad_sha256=hash_sha256,
            plantilla_utilizada=datos.plantilla_acta,
        )

    def simular_acta_pdf_en_memoria(
        self,
        datos: DatosRenderizadoActaDTO,
    ) -> ResultadoRenderizadoPdfDTO:
        """Renderiza en memoria la plantilla HTML/CSS a un binario PDF de prueba sin persistir en el repositorio oficial (CU-12).

        Garantiza 0 escrituras en `self._archivos_pdf` y en `self._html_renderizados` durante la
        simulación y previsualización de una ReglaPrograma en estado Borrador (Escenarios 3 y 10).
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

    def obtener_contenido_pdf(self, ruta_archivo_pdf: str) -> bytes | None:
        """Recupera el contenido binario de un archivo PDF almacenado o None si no existe."""
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            return None
        return self._archivos_pdf.get(ruta_archivo_pdf.strip())

    def eliminar_archivo_pdf(self, ruta_archivo_pdf: str) -> None:
        """Elimina un archivo PDF del repositorio para compensación transaccional (DT-02, Escenario 10)."""
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            return
        ruta = ruta_archivo_pdf.strip()
        self._archivos_pdf.pop(ruta, None)
        self._html_renderizados.pop(ruta, None)

    def configurar_fallo_escritura(
        self,
        activar: bool,
        mensaje: str | None = None,
    ) -> None:
        """Activa o desactiva la simulación determinista de fallo de escritura (Escenario 10, DT-02)."""
        self._fallo_escritura_activo = activar
        if mensaje is not None:
            self._mensaje_fallo_escritura = mensaje

    def obtener_html_renderizado(self, ruta_archivo_pdf: str) -> str | None:
        """Retorna el documento HTML intermedio renderizado a partir de la plantilla para inspección."""
        if not isinstance(ruta_archivo_pdf, str) or not ruta_archivo_pdf.strip():
            return None
        return self._html_renderizados.get(ruta_archivo_pdf.strip())

    def listar_rutas_archivos(self) -> list[str]:
        """Retorna la lista ordenada de todas las rutas de archivos PDF almacenados."""
        return sorted(self._archivos_pdf.keys())

    def cantidad_archivos_almacenados(self) -> int:
        """Retorna el total de archivos PDF actualmente almacenados en el repositorio."""
        return len(self._archivos_pdf)

    def limpiar(self) -> None:
        """Reinicia el almacén en memoria de archivos PDF y desactiva fallos simulados."""
        super().limpiar()
        self._html_renderizados.clear()
        self._fallo_escritura_activo = False

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


@dataclass(slots=True)
class SistemaPracticasEmpresariales:
    """Contenedor de composición de dependencias del sistema de prácticas empresariales.

    Expone los casos de uso y componentes de infraestructura configurados para
    interacción en producción, pruebas unitarias o de integración.
    """

    # Casos de uso (Capa de Aplicación)
    caso_uso_postular: PostularEstudianteCasoUso
    caso_uso_reintentar_sia: ReintentarValidacionSiaCasoUso
    caso_uso_evaluar: EvaluarPostulacionCasoUso
    caso_uso_asignar_docente: AsignarDocenteAsesorCasoUso
    caso_uso_registrar_horas: RegistrarHorasCasoUso
    caso_uso_validar_horas: ValidarHorasRegistradasCasoUso
    caso_uso_revisar_avances_horas: RevisarAvancesHorasCasoUso
    caso_uso_evaluar_desempeno: EvaluarDesempenoCasoUso
    caso_uso_enviar_recordatorios: EnviarRecordatoriosPlazosCasoUso
    caso_uso_generar_acta: GenerarActaFinalCasoUso
    caso_uso_aprobar_acta: AprobarActaElectronicamenteCasoUso
    caso_uso_consultar_estado_tramite: ConsultarEstadoTramiteCasoUso
    caso_uso_configurar_reglas: ConfigurarReglasProgramaCasoUso
    caso_uso_monitorear_practicas: MonitorearPracticasCasoUso
    caso_uso_generar_consolidados: GenerarConsolidadosAuditoriaCasoUso
    caso_uso_migrar_practicas_excel: MigrarPracticasExcelCasoUso

    # Componentes de seguridad y autorización
    autorizador_rbac: AutorizadorRBAC
    proveedor_identidad: ProveedorIdentidadSimulado
    interceptor_identidad: InterceptorIdentidad

    # Adaptadores de infraestructura
    repositorio_practica: InMemoryRepositorioPractica
    repositorio_regla: InMemoryRepositorioReglaPrograma
    repositorio_docente: InMemoryRepositorioDocente
    repositorio_registro_horas: InMemoryRepositorioRegistroHoras
    repositorio_token: InMemoryRepositorioTokenEvaluacion
    repositorio_evaluacion: InMemoryRepositorioEvaluacionDesempeno
    repositorio_acta: InMemoryRepositorioActaFinal
    repositorio_acta_final: InMemoryRepositorioActaFinal
    servicio_pdf: AdaptadorPdfYHashSimulado
    servicio_pdf_hash: AdaptadorPdfYHashSimulado
    servicio_sia: AdaptadorSiaSimulado
    broker_mensajes: InMemoryBrokerMensajes
    servicio_correo: AdaptadorCorreoSimulado
    lector_plantilla_excel: LectorPlantillaExcelSimulado


def inicializar_sistema(
    *,
    umbral_fallos_sia: int = 3,
    precargar_reglas_ejemplo: bool = True,
) -> SistemaPracticasEmpresariales:
    """Fabrica y compone todas las dependencias del sistema (Composition Root).

    Args:
        umbral_fallos_sia: Umbral de fallos consecutivos para el Circuit Breaker del SIA.
        precargar_reglas_ejemplo: Si es True, inserta reglas activas por defecto para programas modelo.

    Returns:
        Instancia de SistemaPracticasEmpresariales cableada y lista para operar.
    """
    # 1. Instanciación de adaptadores de infraestructura
    repo_practica = InMemoryRepositorioPractica()
    repo_regla = InMemoryRepositorioReglaPrograma()
    repo_docente = InMemoryRepositorioDocente()
    repo_registro_horas = InMemoryRepositorioRegistroHoras()
    repo_token = InMemoryRepositorioTokenEvaluacion()
    repo_evaluacion = InMemoryRepositorioEvaluacionDesempeno()
    repo_acta = InMemoryRepositorioActaFinal()
    servicio_pdf = AdaptadorPdfYHashSimulado()
    servicio_sia = AdaptadorSiaSimulado(umbral_fallos=umbral_fallos_sia)
    broker_mensajes = InMemoryBrokerMensajes()
    servicio_correo = AdaptadorCorreoSimulado()
    proveedor_identidad = ProveedorIdentidadSimulado()

    # 2. Componentes de seguridad de la capa de aplicación e infraestructura
    autorizador_rbac = AutorizadorRBAC()
    interceptor_identidad = InterceptorIdentidad(repositorio_token=repo_token)

    # 3. Precarga de reglas de programa vigentes (ADR-007) y tutores académicos (RT-01)
    if precargar_reglas_ejemplo:
        regla_sistemas = ReglaPrograma(
            programa_academico="Ingeniería de Sistemas",
            version="2026-1",
            horas_requeridas=320,
            criterios_rubrica={
                "dominio_tecnico": 0.40,
                "habilidades_blandas": 0.30,
                "cumplimiento_objetivos": 0.30,
            },
            plantilla_acta="plantilla_acta_sistemas_v1.html",
            estado_vigencia=EstadoVigenciaRegla.ACTIVA,
        )
        repo_regla.guardar(regla_sistemas)

        regla_industrial = ReglaPrograma(
            programa_academico="Ingeniería Industrial",
            version="2026-1",
            horas_requeridas=360,
            criterios_rubrica={"criterio_general": 1.0},
            plantilla_acta="plantilla_acta_industrial_v1.html",
            estado_vigencia=EstadoVigenciaRegla.ACTIVA,
        )
        repo_regla.guardar(regla_industrial)

        # Tutores de ejemplo conforme a los escenarios de spec.md
        tutor_1 = DocenteAsesor(
            id="doc_001",
            documento="79123456",
            nombre_completo="Prof. Carlos Gómez",
            correo_institucional="carlos.gomez@universidad.edu.co",
            cupo_maximo_practicas=10,
            practicas_activas=3,
            activo=True,
        )
        repo_docente.guardar(tutor_1)

        tutor_cupo_lleno = DocenteAsesor(
            id="doc_002",
            documento="79654321",
            nombre_completo="Prof. Ana María Ruiz",
            correo_institucional="ana.ruiz@universidad.edu.co",
            cupo_maximo_practicas=10,
            practicas_activas=10,
            activo=True,
        )
        repo_docente.guardar(tutor_cupo_lleno)

        tutor_inactivo = DocenteAsesor(
            id="doc_003",
            documento="79987654",
            nombre_completo="Prof. Roberto Pineda",
            correo_institucional="roberto.pineda@universidad.edu.co",
            cupo_maximo_practicas=10,
            practicas_activas=0,
            activo=False,
        )
        repo_docente.guardar(tutor_inactivo)

    # 4. Inyección de dependencias en casos de uso (Capa Aplicación)
    caso_uso_postular = PostularEstudianteCasoUso(
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        servicio_registro_academico=servicio_sia,
        publicador_eventos=broker_mensajes,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_reintentar_sia = ReintentarValidacionSiaCasoUso(
        repositorio_practica=repo_practica,
        servicio_registro_academico=servicio_sia,
        publicador_eventos=broker_mensajes,
        servicio_correo=servicio_correo,
    )

    caso_uso_evaluar = EvaluarPostulacionCasoUso(
        repositorio_practica=repo_practica,
        servicio_correo=servicio_correo,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_asignar_docente = AsignarDocenteAsesorCasoUso(
        repositorio_practica=repo_practica,
        repositorio_docente=repo_docente,
        servicio_correo=servicio_correo,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_registrar_horas = RegistrarHorasCasoUso(
        repositorio_practica=repo_practica,
        repositorio_registro_horas=repo_registro_horas,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_validar_horas = ValidarHorasRegistradasCasoUso(
        repositorio_practica=repo_practica,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_token_evaluacion=repo_token,
        servicio_correo=servicio_correo,
        autorizador_rbac=autorizador_rbac,
        interceptor_identidad=interceptor_identidad,
    )

    caso_uso_revisar_avances_horas = RevisarAvancesHorasCasoUso(
        repositorio_practica=repo_practica,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_regla=repo_regla,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_evaluar_desempeno = EvaluarDesempenoCasoUso(
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        repositorio_evaluacion=repo_evaluacion,
        repositorio_token_evaluacion=repo_token,
        repositorio_docente=repo_docente,
        servicio_correo=servicio_correo,
        autorizador_rbac=autorizador_rbac,
        interceptor_identidad=interceptor_identidad,
    )

    caso_uso_enviar_recordatorios = EnviarRecordatoriosPlazosCasoUso(
        repositorio_practica=repo_practica,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_token_evaluacion=repo_token,
        repositorio_docente=repo_docente,
        repositorio_regla=repo_regla,
        repositorio_evaluacion_desempeno=repo_evaluacion,
        servicio_correo=servicio_correo,
        publicador_eventos=broker_mensajes,
        autorizador_rbac=autorizador_rbac,
        interceptor_identidad=interceptor_identidad,
    )

    caso_uso_generar_acta = GenerarActaFinalCasoUso(
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        repositorio_evaluacion=repo_evaluacion,
        repositorio_acta=repo_acta,
        servicio_pdf=servicio_pdf,
        autorizador_rbac=autorizador_rbac,
        repositorio_docente=repo_docente,
    )

    caso_uso_aprobar_acta = AprobarActaElectronicamenteCasoUso(
        repositorio_practica=repo_practica,
        repositorio_acta_final=repo_acta,
        repositorio_docente=repo_docente,
        servicio_pdf_hash=servicio_pdf,
        autorizador_rbac=autorizador_rbac,
        publicador_eventos=broker_mensajes,
        servicio_correo=servicio_correo,
    )

    caso_uso_consultar_estado_tramite = ConsultarEstadoTramiteCasoUso(
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        repositorio_docente=repo_docente,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_evaluacion=repo_evaluacion,
        repositorio_acta_final=repo_acta,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_configurar_reglas = ConfigurarReglasProgramaCasoUso(
        repositorio_regla=repo_regla,
        repositorio_practica=repo_practica,
        servicio_pdf=servicio_pdf,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_monitorear_practicas = MonitorearPracticasCasoUso(
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        repositorio_docente=repo_docente,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_evaluacion=repo_evaluacion,
        repositorio_acta_final=repo_acta,
        autorizador_rbac=autorizador_rbac,
    )

    caso_uso_generar_consolidados = GenerarConsolidadosAuditoriaCasoUso(
        repositorio_practica=repo_practica,
        repositorio_acta_final=repo_acta,
        repositorio_regla=repo_regla,
        repositorio_docente=repo_docente,
        repositorio_evaluacion=repo_evaluacion,
        servicio_pdf=servicio_pdf,
        autorizador_rbac=autorizador_rbac,
    )

    lector_plantilla_excel = LectorPlantillaExcelSimulado()
    caso_uso_migrar_practicas_excel = MigrarPracticasExcelCasoUso(
        lector_plantilla=lector_plantilla_excel,
        repositorio_practica=repo_practica,
        repositorio_docente=repo_docente,
        repositorio_regla=repo_regla,
        autorizador_rbac=autorizador_rbac,
    )

    return SistemaPracticasEmpresariales(
        caso_uso_postular=caso_uso_postular,
        caso_uso_reintentar_sia=caso_uso_reintentar_sia,
        caso_uso_evaluar=caso_uso_evaluar,
        caso_uso_asignar_docente=caso_uso_asignar_docente,
        caso_uso_registrar_horas=caso_uso_registrar_horas,
        caso_uso_validar_horas=caso_uso_validar_horas,
        caso_uso_revisar_avances_horas=caso_uso_revisar_avances_horas,
        caso_uso_evaluar_desempeno=caso_uso_evaluar_desempeno,
        caso_uso_enviar_recordatorios=caso_uso_enviar_recordatorios,
        caso_uso_generar_acta=caso_uso_generar_acta,
        caso_uso_aprobar_acta=caso_uso_aprobar_acta,
        caso_uso_consultar_estado_tramite=caso_uso_consultar_estado_tramite,
        caso_uso_configurar_reglas=caso_uso_configurar_reglas,
        caso_uso_monitorear_practicas=caso_uso_monitorear_practicas,
        caso_uso_generar_consolidados=caso_uso_generar_consolidados,
        caso_uso_migrar_practicas_excel=caso_uso_migrar_practicas_excel,
        autorizador_rbac=autorizador_rbac,
        proveedor_identidad=proveedor_identidad,
        interceptor_identidad=interceptor_identidad,
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        repositorio_docente=repo_docente,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_token=repo_token,
        repositorio_evaluacion=repo_evaluacion,
        repositorio_acta=repo_acta,
        repositorio_acta_final=repo_acta,
        servicio_pdf=servicio_pdf,
        servicio_pdf_hash=servicio_pdf,
        servicio_sia=servicio_sia,
        broker_mensajes=broker_mensajes,
        servicio_correo=servicio_correo,
        lector_plantilla_excel=lector_plantilla_excel,
    )


def main() -> int:
    """Función de demostración CLI del sistema cableado."""
    print("=" * 80)
    print("  SISTEMA DE GESTIÓN DE PRÁCTICAS EMPRESARIALES (CLEAN ARCHITECTURE)")
    print("  Composition Root & Diagnóstico de Inicialización - CU-01")
    print("=" * 80)

    sistema = inicializar_sistema()
    print("[+] Dependencias cableadas e inicializadas correctamente:")
    print("    - Repositorio de Prácticas: InMemoryRepositorioPractica")
    print("    - Repositorio de Reglas:    InMemoryRepositorioReglaPrograma")
    print("    - Repositorio de Docentes:  InMemoryRepositorioDocente")
    print("    - Repositorio de Horas:     InMemoryRepositorioRegistroHoras")
    print("    - Repositorio de Tokens:    InMemoryRepositorioTokenEvaluacion")
    print("    - Repositorio Evaluaciones: InMemoryRepositorioEvaluacionDesempeno")
    print("    - Repositorio de Actas:     InMemoryRepositorioActaFinal")
    print("    - Servicio PDF y Hash:      AdaptadorPdfYHashSimulado")
    print("    - Servicio SIA:             AdaptadorSiaSimulado (Circuit Breaker activo)")
    print("    - Bróker de Mensajería:     InMemoryBrokerMensajes (Tareas + DLQ)")
    print("    - Servicio de Correo:       AdaptadorCorreoSimulado")
    print("    - Identidad y RBAC:         ProveedorIdentidadSimulado + InterceptorIdentidad + AutorizadorRBAC")
    print("    - Casos de Uso Disponibles: PostularEstudianteCasoUso (CU-01),")
    print("                                ReintentarValidacionSiaCasoUso (CU-01),")
    print("                                EvaluarPostulacionCasoUso (CU-02),")
    print("                                AsignarDocenteAsesorCasoUso (CU-03),")
    print("                                RegistrarHorasCasoUso (CU-04),")
    print("                                ValidarHorasRegistradasCasoUso (CU-05),")
    print("                                RevisarAvancesHorasCasoUso (CU-06),")
    print("                                EvaluarDesempenoCasoUso (CU-07),")
    print("                                EnviarRecordatoriosPlazosCasoUso (CU-08),")
    print("                                GenerarActaFinalCasoUso (CU-09),")
    print("                                AprobarActaElectronicamenteCasoUso (CU-10),")
    print("                                ConsultarEstadoTramiteCasoUso (CU-11),")
    print("                                ConfigurarReglasProgramaCasoUso (CU-12),")
    print("                                MonitorearPracticasCasoUso (CU-13)")

    # Demostración del Escenario 1: Postulación exitosa
    print("\n--- Demostración CU-01: Postulación exitosa (Escenario 1) ---")
    doc_demo = "1098765432"
    sistema.servicio_sia.configurar_estudiante_cumple(doc_demo, creditos_aprobados=150, porcentaje_avance=88.5)

    comando_demo = PostularEstudianteComando(
        documento=doc_demo,
        nombre_completo="Estudiante Demostración",
        correo_institucional="estudiante.demo@universidad.edu.co",
        programa_academico="Ingeniería de Sistemas",
        rol_actor=RolUsuario.ESTUDIANTE.value,
        ip_origen="192.168.1.100",
    )

    respuesta: PostulacionRespuestaDTO = sistema.caso_uso_postular(comando_demo)
    print(f"Resultado: {respuesta.estado}")
    print(f"Mensaje:   {respuesta.mensaje}")
    print(f"ID Práctica: {respuesta.practica_id}")

    practica_registrada = sistema.repositorio_practica.buscar_por_id(respuesta.practica_id or "")
    if practica_registrada:
        print(f"Estado en BD: {practica_registrada.estado_actual.value}")
        intentos = sistema.repositorio_practica.buscar_intentos_por_practica(practica_registrada.id)
        print(f"Intentos de validación registrados: {len(intentos)}")
        eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{practica_registrada.id}")
        print(f"Eventos de bitácora registrados:    {len(eventos)}")

    # Demostración CU-02: Aprobación exitosa por parte del Coordinador
    print("\n--- Demostración CU-02: Aprobación por Coordinador (Escenario 1) ---")
    comando_evaluar = EvaluarPostulacionComando(
        practica_id=respuesta.practica_id or "",
        decision="APROBAR",
        actor_id="coord_001",
        rol_actor=RolUsuario.COORDINADOR_PRACTICAS.value,
        ip_origen="192.168.1.50",
    )
    respuesta_eval: EvaluacionPostulacionRespuestaDTO = sistema.caso_uso_evaluar(comando_evaluar)
    print(f"Resultado Evaluación: {respuesta_eval.nuevo_estado}")
    print(f"Mensaje:             {respuesta_eval.mensaje}")

    practica_evaluada = sistema.repositorio_practica.buscar_por_id(respuesta.practica_id or "")
    if practica_evaluada:
        print(f"Nuevo estado en BD:  {practica_evaluada.estado_actual.value}")
        eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{practica_evaluada.id}")
        print(f"Total eventos en bitácora: {len(eventos)}")

    # Demostración CU-03: Asignación de docente asesor con cupo disponible
    print("\n--- Demostración CU-03: Asignación de Tutor Académico (Escenario 1) ---")
    docente_previo = sistema.repositorio_docente.buscar_por_id("doc_001")
    if docente_previo:
        print(f"Tutor seleccionado:  {docente_previo.nombre_completo} (Cupo previo: {docente_previo.practicas_activas}/{docente_previo.cupo_maximo_practicas})")

    comando_asignar = AsignarDocenteComando(
        practica_id=respuesta.practica_id or "",
        docente_asesor_id="doc_001",
        actor_id="coord_001",
        rol_actor=RolUsuario.COORDINADOR_PRACTICAS.value,
        ip_origen="192.168.1.50",
    )
    respuesta_asignar: AsignacionDocenteRespuestaDTO = sistema.caso_uso_asignar_docente(comando_asignar)
    print(f"Resultado Asignación:{respuesta_asignar.nuevo_estado}")
    print(f"Mensaje:             {respuesta_asignar.mensaje}")

    practica_asignada = sistema.repositorio_practica.buscar_por_id(respuesta.practica_id or "")
    if practica_asignada:
        print(f"Nuevo estado en BD:  {practica_asignada.estado_actual.value}")
        print(f"Tutor en práctica:   {practica_asignada.docente_asesor_id}")
        docente_actualizado = sistema.repositorio_docente.buscar_por_id("doc_001")
        if docente_actualizado:
            print(f"Nueva carga tutor:   {docente_actualizado.practicas_activas}/{docente_actualizado.cupo_maximo_practicas}")
        eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{practica_asignada.id}")
        print(f"Total eventos en bitácora: {len(eventos)}")

    # Demostración CU-04: Registro semanal de horas y transición formal a EnEjecucion
    print("\n--- Demostración CU-04: Registro de Horas y Transición a EnEjecucion (Escenario 2) ---")
    comando_horas_s1 = RegistrarHorasComando(
        practica_id=respuesta.practica_id or "",
        semana=1,
        cantidad_horas=40,
        descripcion_actividades="Inducción institucional e inicio de actividades técnicas de desarrollo",
        actor_id=doc_demo,
        rol_actor=RolUsuario.ESTUDIANTE.value,
        ip_origen="192.168.1.100",
    )
    respuesta_horas_s1: RegistroHorasRespuestaDTO = sistema.caso_uso_registrar_horas(comando_horas_s1)
    print(f"Resultado Horas S1:   {respuesta_horas_s1.estado_validacion}")
    print(f"Estado Práctica:     {respuesta_horas_s1.estado_practica}")
    print(f"Mensaje:             {respuesta_horas_s1.mensaje}")

    practica_en_ejecucion = sistema.repositorio_practica.buscar_por_id(respuesta.practica_id or "")
    if practica_en_ejecucion:
        print(f"Estado formal en BD: {practica_en_ejecucion.estado_actual.value}")
        reportes = sistema.repositorio_registro_horas.listar_por_practica(practica_en_ejecucion.id)
        print(f"Reportes semanales registrados: {len(reportes)}")
        eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{practica_en_ejecucion.id}")
        print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-05: Validación y aprobación de horas por supervisor con Magic Link
    print("\n--- Demostración CU-05: Validación de Horas por Supervisor con Magic Link (Escenario 1) ---")
    supervisor_demo_id = "sup_alfa_001"
    # Vincular supervisor a la práctica para pertenencia contextual (RN-01)
    if practica_en_ejecucion:
        object.__setattr__(practica_en_ejecucion, "_supervisor_empresa_id", supervisor_demo_id)
        sistema.repositorio_practica.actualizar(practica_en_ejecucion)

    token_eval = sistema.interceptor_identidad.generar_token(
        practica_id=respuesta.practica_id or "",
        supervisor_id=supervisor_demo_id,
    )
    print(f"Token efímero emitido: {token_eval.token[:35]}...")
    print(f"Vigencia del enlace:   15 días (Expira: {token_eval.fecha_expiracion.isoformat()})")

    reportes_previos = sistema.repositorio_registro_horas.listar_por_practica(respuesta.practica_id or "")
    if reportes_previos:
        rep_s1 = reportes_previos[0]
        comando_validar = ValidarHorasComando(
            practica_id=respuesta.practica_id or "",
            registro_horas_id=rep_s1.id,
            decision="Aprobar",
            token_acceso=token_eval.token,
            ip_origen="192.168.1.80",
        )
        respuesta_val: ValidacionHorasRespuestaDTO = sistema.caso_uso_validar_horas(comando_validar)
        print(f"Decisión Supervisor:  {respuesta_val.estado_validacion}")
        print(f"Horas acumuladas:     {respuesta_val.horas_acumuladas_practica} horas")
        print(f"Token consumido:      {token_eval.usado}")
        print(f"Mensaje:              {respuesta_val.mensaje}")

        eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
        print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-06: Revisión de avances de horas en modo solo lectura (DocenteAsesor y Estudiante)
    print("\n--- Demostración CU-06: Revisión de Avances de Horas en Modo Solo Lectura (Escenarios 1 y 6) ---")
    comando_avance_docente = ConsultarAvanceHorasComando(
        practica_id=respuesta.practica_id or "",
        actor_id="doc_001",
        rol_actor=RolUsuario.DOCENTE_ASESOR.value,
        ip_origen="192.168.1.60",
    )
    respuesta_avance: AvanceHorasPracticaRespuestaDTO = sistema.caso_uso_revisar_avances_horas(
        comando_avance_docente
    )
    print(f"Práctica consultada:  {respuesta_avance.practica_id} (Estado: {respuesta_avance.estado_practica})")
    print(
        f"Progreso de horas:    {respuesta_avance.horas_acumuladas_aprobadas}/"
        f"{respuesta_avance.horas_requeridas}h ({respuesta_avance.porcentaje_avance}% de avance, "
        f"{respuesta_avance.horas_restantes}h restantes)"
    )
    print(f"Reportes desglosados: {len(respuesta_avance.reportes_semanales)} reporte(s) semanal(es)")
    print(f"Mensaje:              {respuesta_avance.mensaje}")

    comando_listado_docente = ConsultarAvancesDocenteComando(
        docente_asesor_id="doc_001",
        actor_id="doc_001",
        rol_actor=RolUsuario.DOCENTE_ASESOR.value,
        ip_origen="192.168.1.60",
    )
    respuesta_listado: ListadoAvancesDocenteRespuestaDTO = (
        sistema.caso_uso_revisar_avances_horas.listar_por_docente(comando_listado_docente)
    )
    print(f"Consulta consolidada: {respuesta_listado.total_practicas_asignadas} práctica(s) asignada(s) a doc_001")

    eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
    print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-07: Evaluación de desempeño por Supervisor de Empresa mediante Magic Link
    print("\n--- Demostración CU-07: Evaluación de Desempeño del Practicante (Escenarios 1 y 2) ---")
    token_desempeno = sistema.interceptor_identidad.generar_token(
        practica_id=respuesta.practica_id or "",
        supervisor_id=supervisor_demo_id,
    )
    comando_formulario = ConsultarFormularioEvaluacionComando(
        token_acceso=token_desempeno.token,
        practica_id=respuesta.practica_id,
        ip_origen="192.168.1.80",
    )
    formulario_dto: FormularioEvaluacionRespuestaDTO = (
        sistema.caso_uso_evaluar_desempeno.obtener_formulario_evaluacion(comando_formulario)
    )
    print(
        f"Rúbrica cargada:      Regla {formulario_dto.regla_programa_id} v{formulario_dto.version_regla} "
        f"(Criterios: {list(formulario_dto.criterios_rubrica.keys())})"
    )
    print(f"Token tras consulta:  usado={token_desempeno.usado}")

    comando_evaluar_desempeno = EvaluarDesempenoComando(
        practica_id=respuesta.practica_id or "",
        calificacion_cuantitativa=4.5,
        respuestas_rubrica={
            "dominio_tecnico": 4.6,
            "habilidades_blandas": 4.5,
            "cumplimiento_objetivos": 4.4,
        },
        observaciones="Excelente desempeño técnico, cumplimiento de objetivos y trabajo en equipo",
        token_acceso=token_desempeno.token,
        supervisor_id=supervisor_demo_id,
        ip_origen="192.168.1.80",
    )
    respuesta_desempeno: EvaluacionDesempenoRespuestaDTO = sistema.caso_uso_evaluar_desempeno(
        comando_evaluar_desempeno
    )
    print(f"Evaluación ID:        {respuesta_desempeno.evaluacion_id}")
    print(f"Calificación:         {respuesta_desempeno.calificacion_cuantitativa} (Aprobatoria: {respuesta_desempeno.es_aprobatoria})")
    print(f"Nuevo estado práctica:{respuesta_desempeno.estado_practica}")
    print(f"Token consumido:      {respuesta_desempeno.token_consumido}")
    print(f"Mensaje:              {respuesta_desempeno.mensaje}")

    eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
    print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-08: Envío de recordatorios de plazos (Tarea programada SISTEMA y cooldown 1h)
    print("\n--- Demostración CU-08: Envío de Recordatorios de Plazos (Escenarios 5 y 7) ---")
    fecha_futura = datetime.now(timezone.utc) + timedelta(days=5)
    comando_recordatorios = EjecutarRecordatoriosComando(
        actor_id="SISTEMA",
        rol_actor=RolUsuario.SISTEMA.value,
        ip_origen="127.0.0.1",
        fecha_referencia=fecha_futura,
        umbral_dias_calendario=3,
        cooldown_minutos=60,
    )
    resultado_rec: ResultadoEnvioRecordatoriosDTO = sistema.caso_uso_enviar_recordatorios(
        comando_recordatorios
    )
    print(f"Prácticas evaluadas:  {resultado_rec.total_practicas_evaluadas}")
    print(f"Recordatorios env.:   {resultado_rec.total_recordatorios_enviados}")
    print(f"Mensaje:              {resultado_rec.mensaje}")

    # Segundo intento inmediato dentro de la ventana de enfriamiento de 1 hora (Escenario 7)
    resultado_cooldown: ResultadoEnvioRecordatoriosDTO = sistema.caso_uso_enviar_recordatorios(
        comando_recordatorios
    )
    print(
        f"Intento en cooldown:  enviados={resultado_cooldown.total_recordatorios_enviados}, "
        f"omitidos_cooldown={resultado_cooldown.total_omitidos_por_cooldown}"
    )

    eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
    print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-09: Generación del Acta Final en PDF con sellado criptográfico SHA-256
    print("\n--- Demostración CU-09: Generación del Acta Final en PDF con Sellado SHA-256 (Escenario 1) ---")
    practica_para_acta = sistema.repositorio_practica.buscar_por_id(respuesta.practica_id or "")
    if practica_para_acta:
        # Completar las 320 horas aprobadas requeridas por la regla del programa para la demostración
        object.__setattr__(practica_para_acta, "_horas_acumuladas_aprobadas", 320)
        sistema.repositorio_practica.actualizar(practica_para_acta)

    comando_generar_acta = GenerarActaFinalComando(
        practica_id=respuesta.practica_id or "",
        actor_id="doc_001",
        rol_actor=RolUsuario.DOCENTE_ASESOR.value,
        ip_origen="192.168.1.60",
        fecha_emision=datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc),
    )
    respuesta_acta: ActaFinalRespuestaDTO = sistema.caso_uso_generar_acta(comando_generar_acta)
    print(f"Número de Acta:       {respuesta_acta.numero_acta}")
    print(f"Plantilla aplicada:   {respuesta_acta.plantilla_acta} (v{respuesta_acta.version_regla})")
    print(f"Horas acreditadas:    {respuesta_acta.horas_acumuladas_aprobadas}/{respuesta_acta.horas_requeridas}h")
    print(f"Calificación:         {respuesta_acta.calificacion_cuantitativa} (Aprobatoria: {respuesta_acta.es_aprobatoria})")
    print(f"Ruta Archivo PDF:     {respuesta_acta.ruta_archivo_pdf}")
    print(f"Hash SHA-256:         {respuesta_acta.hash_integridad_sha256}")
    print(
        f"Firmas pendientes:    aprobadaPorDocente={respuesta_acta.aprobada_por_docente}, "
        f"aprobadaPorCoordinador={respuesta_acta.aprobada_por_coordinador}"
    )
    print(f"Estado Práctica:      {respuesta_acta.estado_practica}")
    print(f"Mensaje:              {respuesta_acta.mensaje}")

    eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
    print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-10: Aprobación electrónica secuencial del Acta Final (DocenteAsesor -> Coordinador)
    print("\n--- Demostración CU-10: Aprobación Electrónica del Acta Final (Escenarios 1 y 2) ---")
    comando_aprobar_docente = AprobarActaComando(
        practica_id=respuesta.practica_id or "",
        actor_id="doc_001",
        rol_actor=RolUsuario.DOCENTE_ASESOR.value,
        acta_id=respuesta_acta.acta_id,
        ip_origen="192.168.1.60",
    )
    respuesta_firma_docente: AprobacionActaRespuestaDTO = sistema.caso_uso_aprobar_acta(
        comando_aprobar_docente
    )
    print(
        f"Paso 1 (Docente):     aprobadaPorDocente={respuesta_firma_docente.aprobada_por_docente}, "
        f"aprobadaPorCoordinador={respuesta_firma_docente.aprobada_por_coordinador}, "
        f"estado={respuesta_firma_docente.estado_practica}"
    )
    print(f"Mensaje Paso 1:       {respuesta_firma_docente.mensaje}")

    comando_aprobar_coordinador = AprobarActaComando(
        practica_id=respuesta.practica_id or "",
        actor_id="coord_001",
        rol_actor=RolUsuario.COORDINADOR_PRACTICAS.value,
        acta_id=respuesta_acta.acta_id,
        ip_origen="192.168.1.50",
    )
    respuesta_firma_coord: AprobacionActaRespuestaDTO = sistema.caso_uso_aprobar_acta(
        comando_aprobar_coordinador
    )
    print(
        f"Paso 2 (Coordinador): aprobadaPorDocente={respuesta_firma_coord.aprobada_por_docente}, "
        f"aprobadaPorCoordinador={respuesta_firma_coord.aprobada_por_coordinador}, "
        f"actaEnFirme={respuesta_firma_coord.acta_en_firme}"
    )
    print(f"Nuevo estado práctica:{respuesta_firma_coord.estado_practica}")
    print(
        f"Cupo docente liberado:{respuesta_firma_coord.cupo_docente_liberado} "
        f"(practicasActivas={respuesta_firma_coord.practicas_activas_docente})"
    )
    eventos_acta = sistema.broker_mensajes.obtener_eventos_acta_emitida()
    print(f"Eventos ActaFinalEmitida publicados: {len(eventos_acta)}")
    print(f"Mensaje Paso 2:       {respuesta_firma_coord.mensaje}")

    eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
    print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-11: Consulta del estado del trámite en autoservicio (Estudiante titular)
    print("\n--- Demostración CU-11: Consulta del Estado del Trámite en Autoservicio (Escenario 5) ---")
    comando_estado_tramite = ConsultarEstadoTramiteComando(
        actor_id=doc_demo,
        rol_actor=RolUsuario.ESTUDIANTE.value,
        ip_origen="192.168.1.100",
    )
    respuesta_estado: EstadoTramitePracticaRespuestaDTO = sistema.caso_uso_consultar_estado_tramite(
        comando_estado_tramite
    )
    print(f"Práctica consultada:  {respuesta_estado.practica_id} (Estado: {respuesta_estado.estado_actual})")
    print(
        f"Progreso de horas:    {respuesta_estado.horas_acumuladas_aprobadas}/"
        f"{respuesta_estado.horas_requeridas}h ({respuesta_estado.porcentaje_avance_horas}% de avance)"
    )
    print(
        f"Evaluación visible:   {respuesta_estado.evaluacion.calificacion_visible} "
        f"(Calificación: {respuesta_estado.evaluacion.calificacion_cuantitativa})"
    )
    print(
        f"Acta Final en firme:  {respuesta_estado.acta_final.acta_en_firme} "
        f"(Descarga habilitada: {respuesta_estado.acta_final.descarga_habilitada}, "
        f"Acta: {respuesta_estado.acta_final.numero_acta})"
    )
    print(f"Siguiente paso:       {respuesta_estado.siguiente_paso}")
    print(f"Mensaje:              {respuesta_estado.mensaje}")

    eventos = sistema.repositorio_practica.buscar_eventos_por_entidad(f"Practica:{respuesta.practica_id}")
    print(f"Total eventos en bitácora:     {len(eventos)}")

    # Demostración CU-12: Configurar reglas y plantillas por programa (Borrador -> Edición -> Simulación -> Activación)
    print("\n--- Demostración CU-12: Configurar Reglas y Plantillas por Programa (Escenarios 1, 2, 3, 4 y 10) ---")
    comando_crear_borrador = CrearBorradorReglaComando(
        programa_academico="Ingeniería de Sistemas",
        version="2026-2",
        horas_requeridas=360,
        criterios_rubrica={
            "dominio_tecnico": 0.40,
            "trabajo_en_equipo": 0.30,
            "cumplimiento_objetivos": 0.30,
        },
        plantilla_acta="plantilla_acta_sistemas_v2.html",
        actor_id="COORD-001",
        rol_actor="Coordinador de prácticas",
        ip_origen="192.168.1.50",
    )
    borrador_creado: ReglaProgramaRespuestaDTO = (
        sistema.caso_uso_configurar_reglas.crear_borrador(comando_crear_borrador)
    )
    print(
        f"1. Borrador creado:   ID={borrador_creado.regla_id}, v{borrador_creado.version}, "
        f"estado={borrador_creado.estado_vigencia}, horas={borrador_creado.horas_requeridas}h"
    )

    comando_editar_borrador = EditarBorradorReglaComando(
        regla_id=borrador_creado.regla_id,
        actor_id="COORD-001",
        rol_actor="Coordinador de prácticas",
        horas_requeridas=380,
        criterios_rubrica=[
            "dominio_tecnico",
            "trabajo_en_equipo",
            "cumplimiento_objetivos",
            "innovacion",
        ],
        plantilla_acta="plantilla_acta_sistemas_v2_rev1.html",
        ip_origen="192.168.1.50",
    )
    borrador_editado: ReglaProgramaRespuestaDTO = (
        sistema.caso_uso_configurar_reglas.editar_borrador(comando_editar_borrador)
    )
    print(
        f"2. Borrador editado:  horas={borrador_editado.horas_requeridas}h, "
        f"criterios={list(borrador_editado.nombres_criterios)}, "
        f"plantilla={borrador_editado.plantilla_acta}"
    )

    archivos_antes_sim = sistema.servicio_pdf.cantidad_archivos_almacenados()
    comando_simular = SimularReglaProgramaComando(
        regla_id=borrador_editado.regla_id,
        actor_id="COORD-001",
        rol_actor="Coordinador de prácticas",
        ip_origen="192.168.1.50",
    )
    simulacion_dto: SimulacionReglaProgramaRespuestaDTO = (
        sistema.caso_uso_configurar_reglas.simular_previsualizacion(comando_simular)
    )
    archivos_despues_sim = sistema.servicio_pdf.cantidad_archivos_almacenados()
    print(
        f"3. Simulación PDF:    plantilla={simulacion_dto.plantilla_utilizada}, "
        f"bytes={len(simulacion_dto.contenido_pdf_simulacion)}, "
        f"persistido={simulacion_dto.persistido_en_repositorio} "
        f"(archivos repo: {archivos_antes_sim}->{archivos_despues_sim})"
    )

    comando_activar = ActivarReglaProgramaComando(
        regla_id=borrador_editado.regla_id,
        actor_id="COORD-001",
        rol_actor="Coordinador de prácticas",
        ip_origen="192.168.1.50",
    )
    regla_activada: ReglaProgramaRespuestaDTO = (
        sistema.caso_uso_configurar_reglas.activar_regla(comando_activar)
    )
    practica_previa = sistema.repositorio_practica.buscar_por_id(respuesta.practica_id or "")
    regla_practica_previa = (
        sistema.repositorio_regla.buscar_por_id(practica_previa.regla_programa_id)
        if practica_previa
        else None
    )
    print(
        f"4. Regla activada:    v{regla_activada.version} ({regla_activada.estado_vigencia}), "
        f"anterior v{regla_activada.version_anterior_inactivada} -> Inactiva"
    )
    if regla_practica_previa:
        print(
            f"5. Inmutabilidad:     Práctica previa conserva Regla v{regla_practica_previa.version} "
            f"({regla_practica_previa.horas_requeridas}h, {regla_practica_previa.plantilla_acta}) "
            f"-> 0% de alteración (EAC-01)"
        )

    # Demostración CU-13: Monitoreo general de prácticas (Tablero de control y detalle en solo lectura)
    print("\n--- Demostración CU-13: Monitoreo del Estado General de Prácticas (Escenarios 1 y 4) ---")
    comando_tablero = ConsultarMonitoreoPracticasComando(
        actor_id="COORD-001",
        rol_actor="Coordinador de prácticas",
        programa_academico_coordinador="Ingeniería de Sistemas",
        ip_origen="192.168.1.50",
    )
    tablero_dto: TableroMonitoreoPracticasRespuestaDTO = (
        sistema.caso_uso_monitorear_practicas(comando_tablero)
    )
    print(
        f"Tablero programa:     {tablero_dto.programa_academico} "
        f"(Total: {tablero_dto.total_practicas_programa}, Filtradas: {tablero_dto.total_practicas_filtradas})"
    )
    print(f"Resumen por estado:   {tablero_dto.resumen_por_estado}")
    print(f"Docentes monitoreados:{len(tablero_dto.carga_docentes)}")
    print(f"Mensaje tablero:      {tablero_dto.mensaje}")

    if respuesta.practica_id:
        comando_detalle_monitoreo = ConsultarDetallePracticaMonitoreoComando(
            practica_id=respuesta.practica_id,
            actor_id="COORD-001",
            rol_actor="Coordinador de prácticas",
            programa_academico_coordinador="Ingeniería de Sistemas",
            ip_origen="192.168.1.50",
        )
        detalle_monitoreo_dto: DetallePracticaMonitoreoRespuestaDTO = (
            sistema.caso_uso_monitorear_practicas.consultar_detalle_practica(
                comando_detalle_monitoreo
            )
        )
        print(
            f"Detalle práctica:     {detalle_monitoreo_dto.practica_id} | "
            f"Estado={detalle_monitoreo_dto.estado_actual} | "
            f"Horas={detalle_monitoreo_dto.horas_acumuladas_aprobadas}/{detalle_monitoreo_dto.horas_requeridas}h "
            f"({detalle_monitoreo_dto.porcentaje_avance_horas}%) | "
            f"ActaEnFirme={detalle_monitoreo_dto.acta_en_firme}"
        )

    print("\n--- Demo rápida CU-14: Generar consolidado para auditoría ---")
    ahora_demo = datetime.now()
    periodo_demo = f"{ahora_demo.year}-{1 if ahora_demo.month <= 6 else 2}"
    comando_consolidado = GenerarConsolidadoAuditoriaComando(
        programa_academico="Ingeniería de Sistemas",
        periodo=periodo_demo,
        actor_id="COORD-001",
        rol_actor="Coordinador de prácticas",
        ip_origen="192.168.1.50",
    )
    respuesta_consolidado: ConsolidadoAuditoriaRespuestaDTO = (
        sistema.caso_uso_generar_consolidados(comando_consolidado)
    )
    print(
        f"Consolidado PDF:      {respuesta_consolidado.nombre_archivo_pdf} | "
        f"Total={respuesta_consolidado.total_practicas} | "
        f"Completadas={respuesta_consolidado.total_completadas} | "
        f"ActasEnFirme={respuesta_consolidado.total_con_acta_en_firme}"
    )
    print(f"SHA-256 PDF:          {respuesta_consolidado.hash_sha256_pdf}")
    print(f"Mensaje consolidado:  {respuesta_consolidado.mensaje}")

    print("\n--- Demo rápida CU-15: Migrar prácticas en curso desde Excel ---")
    csv_demo_migracion = (
        "documento_estudiante,nombre_estudiante,correo_estudiante,programa_academico,"
        "nombre_empresa,nit_empresa,supervisor_nombre,supervisor_correo,docente_asesor_id,"
        "horas_acumuladas,estado_o_hito,fecha_postulacion,fecha_inicio,fecha_fin\n"
        "1053890001,Laura Méndez,laura.mendez@ucaldas.edu.co,Ingeniería de Sistemas,"
        "TechCaldas S.A.S,900111222-1,Carlos Ruiz,cruiz@techcaldas.co,doc_001,"
        "120,Aprobada,2026-02-01,,\n"
    )
    sistema.lector_plantilla_excel.registrar_lote("lote_demo_cu15", csv_demo_migracion)
    resp_dry_run: MigrarPracticasExcelRespuestaDTO = (
        sistema.caso_uso_migrar_practicas_excel(
            MigrarPracticasExcelComando(
                origen_datos="lote_demo_cu15",
                dry_run=True,
                actor_id="DBA-001",
                rol_actor="Administrador DBA",
                ip_origen="127.0.0.1",
            )
        )
    )
    print(
        f"Dry-Run CU-15:        validas={resp_dry_run.total_validas}, "
        f"importadas={resp_dry_run.total_importadas}, "
        f"rechazadas={resp_dry_run.total_rechazadas}"
    )
    resp_migracion: MigrarPracticasExcelRespuestaDTO = (
        sistema.caso_uso_migrar_practicas_excel(
            MigrarPracticasExcelComando(
                origen_datos="lote_demo_cu15",
                dry_run=False,
                actor_id="DBA-001",
                rol_actor="Administrador DBA",
                ip_origen="127.0.0.1",
            )
        )
    )
    print(
        f"Migración CU-15:      importadas={resp_migracion.total_importadas}, "
        f"omitidas={resp_migracion.total_omitidas_duplicadas}, "
        f"rechazadas={resp_migracion.total_rechazadas} | "
        f"Estado={resp_migracion.resultados_filas[0].estado_practica_asignado}"
    )

    print("\n[OK] El sistema de gestión de prácticas está listo y operativo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
