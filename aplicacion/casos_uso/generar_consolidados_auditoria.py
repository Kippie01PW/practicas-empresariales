"""Caso de uso: Generar consolidados para auditoría (CU-14).

Traza: CU-14, EAC-03, OB-02, PA-03, RN-01, RN-03, ADR-002, ADR-004, ADR-005, ADR-006, ADR-008.

Implementa en el Módulo Actas la consulta histórica en modo estrictamente de solo lectura
y la exportación en formato PDF sellado con huella SHA-256 de prácticas empresariales y su
ActaFinal asociada para procesos de auditoría y acreditación académica:
1. Autorización RBAC centralizada bajo política *deny-by-default* (ADR-004, ADR-005):
   - Operación exclusiva para el rol `Coordinador de prácticas` (`Coordinador` / `CoordinadorPracticas`).
   - Todo intento no autorizado o sin sesión válida es rechazado con 0 datos expuestos y
     registro inmediato en la bitácora Append-Only (`EventoBitacora`, EAC-03, Escenario 6).
2. Validación estricta de filtros obligatorios y opcionales (Escenario 5):
   - Exige `programa_academico` y `periodo` no vacíos.
   - Valida que `fecha_inicio <= fecha_fin` y que `estado_practica` (si se indica) sea un
     `EstadoPractica` válido; de lo contrario lanza `FiltrosConsolidadoInvalidosError` sin generar PDF.
3. Proyección histórica inmutable y exportación PDF sellada con SHA-256 (Escenarios 1, 2, 3, 4):
   - Recopila el resumen histórico de prácticas y su `ActaFinal` (número oficial, fecha de emisión,
     firmas y `hashIntegridadSha256`) sin alterar ni eliminar registros históricos.
   - Genera el PDF consolidado incluso cuando el total de coincidencias es 0 (Escenario 3).
   - Registra un `EventoBitacora` inmutable de la consulta y exportación ejecutada (ADR-006).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Optional

from aplicacion.dtos.consolidado_auditoria_dto import (
    ConsolidadoAuditoriaRespuestaDTO,
    DatosRenderizadoConsolidadoPdfDTO,
    GenerarConsolidadoAuditoriaComando,
    RegistroConsolidadoPracticaDTO,
)
from aplicacion.puertos.repositorio_acta_final import RepositorioActaFinalPort
from aplicacion.puertos.repositorio_docente import RepositorioDocentePort
from aplicacion.puertos.repositorio_evaluacion_desempeno import (
    RepositorioEvaluacionDesempenoPort,
)
from aplicacion.puertos.repositorio_practica import RepositorioPracticaPort
from aplicacion.puertos.repositorio_regla import RepositorioReglaProgramaPort
from aplicacion.puertos.servicio_generador_acta_pdf import ServicioGeneradorActaPdfPort
from aplicacion.seguridad.autorizador_rbac import (
    AccesoDenegadoError,
    AutorizadorRBAC,
    ContextoUsuario,
)
from dominio.errores import FiltrosConsolidadoInvalidosError
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.evento_bitacora import EventoBitacora
from dominio.modelos.practica import EstadoPractica, Practica
from dominio.modelos.regla_programa import ReglaPrograma

_PATRON_PERIODO = re.compile(r"^\d{4}-[12]$")


class GenerarConsolidadosAuditoriaCasoUso:
    """Caso de uso del Módulo Actas para generar consolidados históricos en PDF para auditoría (CU-14)."""

    def __init__(
        self,
        *,
        repositorio_practica: RepositorioPracticaPort,
        repositorio_acta_final: RepositorioActaFinalPort,
        repositorio_regla: RepositorioReglaProgramaPort,
        repositorio_docente: RepositorioDocentePort,
        repositorio_evaluacion: RepositorioEvaluacionDesempenoPort,
        servicio_pdf: ServicioGeneradorActaPdfPort,
        autorizador_rbac: Optional[AutorizadorRBAC] = None,
    ) -> None:
        """Inicializa el caso de uso con sus puertos de lectura, renderizado PDF y autorizador RBAC."""
        self._repositorio_practica: RepositorioPracticaPort = repositorio_practica
        self._repositorio_acta_final: RepositorioActaFinalPort = repositorio_acta_final
        self._repositorio_regla: RepositorioReglaProgramaPort = repositorio_regla
        self._repositorio_docente: RepositorioDocentePort = repositorio_docente
        self._repositorio_evaluacion: RepositorioEvaluacionDesempenoPort = (
            repositorio_evaluacion
        )
        self._servicio_pdf: ServicioGeneradorActaPdfPort = servicio_pdf
        self._autorizador_rbac: AutorizadorRBAC = autorizador_rbac or AutorizadorRBAC()

    def __call__(
        self,
        comando: GenerarConsolidadoAuditoriaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ConsolidadoAuditoriaRespuestaDTO:
        """Permite invocar la instancia del caso de uso como un objeto callable."""
        return self.ejecutar(comando=comando, contexto=contexto)

    def ejecutar(
        self,
        comando: GenerarConsolidadoAuditoriaComando,
        contexto: Optional[ContextoUsuario] = None,
    ) -> ConsolidadoAuditoriaRespuestaDTO:
        """Consulta el historial de prácticas y exporta el consolidado en PDF sellado con SHA-256."""
        actor_id = (
            contexto.usuario_id if contexto is not None else comando.actor_id
        )
        rol_actor = contexto.rol if contexto is not None else comando.rol_actor
        ip_origen = (
            (
                contexto.ip_origen
                if contexto is not None and contexto.ip_origen
                else comando.ip_origen
            )
            or "127.0.0.1"
        ).strip()

        self._validar_autorizacion(
            actor_id=actor_id,
            rol_actor=rol_actor,
            ip_origen=ip_origen,
            programa_academico=comando.programa_academico,
        )

        programa_limpio, periodo_limpio, estado_filtro = self._validar_filtros(comando)

        registros_lista = self._recopilar_registros_filtrados(
            programa_academico=programa_limpio,
            periodo=periodo_limpio,
            fecha_inicio=comando.fecha_inicio,
            fecha_fin=comando.fecha_fin,
            estado_filtro=estado_filtro,
        )
        registros = tuple(registros_lista)

        total_practicas = len(registros)
        total_completadas = sum(
            1
            for item in registros
            if item.estado_actual == EstadoPractica.COMPLETADA.value
        )
        total_con_acta_en_firme = sum(
            1 for item in registros if item.acta_en_firme is True
        )

        fecha_generacion = datetime.now()
        datos_pdf = DatosRenderizadoConsolidadoPdfDTO(
            programa_academico=programa_limpio,
            periodo=periodo_limpio,
            fecha_inicio=comando.fecha_inicio,
            fecha_fin=comando.fecha_fin,
            estado_practica_filtro=estado_filtro.value if estado_filtro else None,
            total_practicas=total_practicas,
            total_completadas=total_completadas,
            total_con_acta_en_firme=total_con_acta_en_firme,
            registros=registros,
            fecha_generacion=fecha_generacion,
            actor_id=actor_id.strip(),
        )

        contenido_pdf, hash_sha256_pdf = (
            self._servicio_pdf.generar_consolidado_auditoria_pdf(datos_pdf)
        )

        nombre_archivo_pdf = (
            f"consolidado_auditoria_{self._normalizar_slug(programa_limpio)}_"
            f"{self._normalizar_slug(periodo_limpio)}.pdf"
        )

        if total_practicas == 0:
            mensaje = (
                f"No se encontraron registros históricos de prácticas para el programa "
                f"'{programa_limpio}' en el período '{periodo_limpio}'."
            )
        else:
            mensaje = (
                f"Consolidado de auditoría generado exitosamente con {total_practicas} "
                f"práctica(s) para '{programa_limpio}' en el período '{periodo_limpio}'."
            )

        evento = EventoBitacora(
            actor_identificador=actor_id.strip(),
            rol_actor=rol_actor.strip(),
            ip_origen=ip_origen,
            accion_realizada="GENERAR_CONSOLIDADO_AUDITORIA",
            entidad_afectada=f"ConsolidadoAuditoria:{programa_limpio}:{periodo_limpio}",
            fecha_hora=fecha_generacion,
            detalles={
                "programa_academico": programa_limpio,
                "periodo": periodo_limpio,
                "fecha_inicio": (
                    comando.fecha_inicio.isoformat() if comando.fecha_inicio else None
                ),
                "fecha_fin": (
                    comando.fecha_fin.isoformat() if comando.fecha_fin else None
                ),
                "estado_practica": estado_filtro.value if estado_filtro else None,
                "total_practicas": total_practicas,
                "total_completadas": total_completadas,
                "total_con_acta_en_firme": total_con_acta_en_firme,
                "hash_sha256_pdf": hash_sha256_pdf,
            },
        )
        self._repositorio_practica.guardar_evento_bitacora(evento)

        return ConsolidadoAuditoriaRespuestaDTO(
            programa_academico=programa_limpio,
            periodo=periodo_limpio,
            fecha_inicio=comando.fecha_inicio,
            fecha_fin=comando.fecha_fin,
            estado_practica_filtro=estado_filtro.value if estado_filtro else None,
            total_practicas=total_practicas,
            total_completadas=total_completadas,
            total_con_acta_en_firme=total_con_acta_en_firme,
            registros=registros,
            contenido_pdf=contenido_pdf,
            hash_sha256_pdf=hash_sha256_pdf,
            nombre_archivo_pdf=nombre_archivo_pdf,
            fecha_generacion=fecha_generacion,
            mensaje=mensaje,
        )

    def _validar_autorizacion(
        self,
        *,
        actor_id: Optional[str],
        rol_actor: Optional[str],
        ip_origen: str,
        programa_academico: Optional[str],
    ) -> None:
        """Valida sesión y rol RBAC; si falla, registra EventoBitacora de rechazo y relanza."""
        try:
            self._autorizador_rbac.validar_generacion_consolidados_auditoria(
                rol_actor=rol_actor or "",
                usuario_id=actor_id if actor_id is not None else "",
                operacion="generar_consolidados_auditoria",
            )
        except AccesoDenegadoError as exc:
            actor_seguro = (actor_id or "").strip() or "ANONIMO"
            rol_seguro = (rol_actor or "").strip() or "SIN_ROL"
            programa_seguro = (programa_academico or "").strip() or "SIN_PROGRAMA"
            evento_rechazo = EventoBitacora(
                actor_identificador=actor_seguro,
                rol_actor=rol_seguro,
                ip_origen=ip_origen,
                accion_realizada="ACCESO_DENEGADO_GENERAR_CONSOLIDADO_AUDITORIA",
                entidad_afectada=f"ConsolidadoAuditoria:{programa_seguro}",
                detalles={
                    "motivo": str(exc),
                    "operacion": "generar_consolidados_auditoria",
                },
            )
            self._repositorio_practica.guardar_evento_bitacora(evento_rechazo)
            raise

    def _validar_filtros(
        self, comando: GenerarConsolidadoAuditoriaComando
    ) -> tuple[str, str, Optional[EstadoPractica]]:
        """Valida los filtros obligatorios y opcionales sin generar archivo PDF ante error."""
        programa_limpio = (comando.programa_academico or "").strip()
        if not programa_limpio:
            raise FiltrosConsolidadoInvalidosError(campo="programaAcademico")

        periodo_limpio = (comando.periodo or "").strip()
        if not periodo_limpio:
            raise FiltrosConsolidadoInvalidosError(campo="periodo")

        if (
            comando.fecha_inicio is not None
            and comando.fecha_fin is not None
            and comando.fecha_inicio > comando.fecha_fin
        ):
            raise FiltrosConsolidadoInvalidosError(
                campo="rangoFechas",
                detalle=(
                    f"El rango de fechas indicado es inválido: fecha_inicio "
                    f"({comando.fecha_inicio.isoformat()}) es posterior a fecha_fin "
                    f"({comando.fecha_fin.isoformat()})."
                ),
            )

        estado_filtro: Optional[EstadoPractica] = None
        if comando.estado_practica is not None and comando.estado_practica.strip():
            estado_filtro = self._resolver_estado_practica(
                comando.estado_practica.strip()
            )

        return programa_limpio, periodo_limpio, estado_filtro

    @staticmethod
    def _resolver_estado_practica(valor: str) -> EstadoPractica:
        """Resuelve una cadena a EstadoPractica o lanza FiltrosConsolidadoInvalidosError."""
        normalizado = valor.strip().lower()
        for estado in EstadoPractica:
            if (
                estado.value.lower() == normalizado
                or estado.name.lower() == normalizado
            ):
                return estado
        raise FiltrosConsolidadoInvalidosError(
            campo="estadoPractica",
            detalle=(
                f"El estado de práctica '{valor}' no corresponde a un estado válido "
                f"del ciclo de vida."
            ),
        )

    def _recopilar_registros_filtrados(
        self,
        *,
        programa_academico: str,
        periodo: str,
        fecha_inicio: Optional[datetime],
        fecha_fin: Optional[datetime],
        estado_filtro: Optional[EstadoPractica],
    ) -> list[RegistroConsolidadoPracticaDTO]:
        """Consulta prácticas en solo lectura y proyecta las coincidentes junto a su ActaFinal."""
        reglas_cache: dict[str, Optional[ReglaPrograma]] = {}
        docentes_cache: dict[str, Optional[DocenteAsesor]] = {}
        registros: list[RegistroConsolidadoPracticaDTO] = []

        for practica in self._repositorio_practica.listar_todas():
            regla = self._obtener_regla_cached(practica.regla_programa_id, reglas_cache)
            programa_practica = regla.programa_academico.strip() if regla else ""
            if programa_practica.lower() != programa_academico.lower():
                continue

            periodo_practica = self._determinar_periodo_practica(practica, regla)
            if periodo_practica.lower() != periodo.lower():
                continue

            if estado_filtro is not None and practica.estado_actual != estado_filtro:
                continue

            if fecha_inicio is not None and practica.fecha_postulacion < fecha_inicio:
                continue

            if fecha_fin is not None and practica.fecha_postulacion > fecha_fin:
                continue

            registros.append(
                self._proyectar_registro(
                    practica=practica,
                    programa_academico=programa_practica,
                    periodo=periodo_practica,
                    regla=regla,
                    docentes_cache=docentes_cache,
                )
            )

        return registros

    def _obtener_regla_cached(
        self,
        regla_id: str,
        cache: dict[str, Optional[ReglaPrograma]],
    ) -> Optional[ReglaPrograma]:
        if regla_id not in cache:
            cache[regla_id] = self._repositorio_regla.buscar_por_id(regla_id)
        return cache[regla_id]

    def _obtener_docente_cached(
        self,
        docente_id: str,
        cache: dict[str, Optional[DocenteAsesor]],
    ) -> Optional[DocenteAsesor]:
        if docente_id not in cache:
            cache[docente_id] = self._repositorio_docente.buscar_por_id(docente_id)
        return cache[docente_id]

    @staticmethod
    def _determinar_periodo_practica(
        practica: Practica,
        regla: Optional[ReglaPrograma],
    ) -> str:
        """Determina el período académico asociado a la práctica desde la regla o fecha_postulacion."""
        if regla is not None and _PATRON_PERIODO.match(regla.version.strip()):
            return regla.version.strip()
        fecha = practica.fecha_postulacion
        semestre = 1 if fecha.month <= 6 else 2
        return f"{fecha.year}-{semestre}"

    def _proyectar_registro(
        self,
        *,
        practica: Practica,
        programa_academico: str,
        periodo: str,
        regla: Optional[ReglaPrograma],
        docentes_cache: dict[str, Optional[DocenteAsesor]],
    ) -> RegistroConsolidadoPracticaDTO:
        """Proyecta de forma inmutable una Practica y su ActaFinal sin alterar el estado."""
        docente = (
            self._obtener_docente_cached(practica.docente_asesor_id, docentes_cache)
            if practica.docente_asesor_id
            else None
        )
        evaluacion = self._repositorio_evaluacion.buscar_por_practica(practica.id)
        acta = self._repositorio_acta_final.buscar_por_practica(practica.id)

        return RegistroConsolidadoPracticaDTO(
            practica_id=practica.id,
            estudiante_id=practica.estudiante_id,
            programa_academico=programa_academico,
            periodo=periodo,
            estado_actual=practica.estado_actual.value,
            fecha_postulacion=practica.fecha_postulacion,
            fecha_inicio=practica.fecha_inicio,
            fecha_fin=practica.fecha_fin,
            docente_asesor_id=practica.docente_asesor_id,
            nombre_docente_asesor=docente.nombre_completo if docente else None,
            supervisor_empresa_id=practica.supervisor_empresa_id,
            horas_acumuladas_aprobadas=practica.horas_acumuladas_aprobadas,
            horas_requeridas=regla.horas_requeridas if regla else None,
            calificacion_cuantitativa=(
                evaluacion.calificacion_cuantitativa if evaluacion else None
            ),
            es_aprobatoria=evaluacion.es_aprobatoria if evaluacion else None,
            numero_acta=acta.numero_acta if acta else None,
            fecha_emision_acta=acta.fecha_emision if acta else None,
            aprobada_por_docente=acta.aprobada_por_docente if acta else None,
            aprobada_por_coordinador=acta.aprobada_por_coordinador if acta else None,
            acta_en_firme=acta.esta_en_firme if acta else None,
            hash_integridad_sha256=acta.hash_integridad_sha256 if acta else None,
        )

    @staticmethod
    def _normalizar_slug(texto: str) -> str:
        """Normaliza texto a un identificador seguro para nombres de archivo PDF."""
        sin_acentos = "".join(
            c
            for c in unicodedata.normalize("NFD", texto.strip().lower())
            if unicodedata.category(c) != "Mn"
        )
        slug = re.sub(r"[^a-z0-9]+", "_", sin_acentos).strip("_")
        return slug or "consolidado"
