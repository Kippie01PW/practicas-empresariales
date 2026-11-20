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

from aplicacion.casos_uso.asignar_docente_asesor import AsignarDocenteAsesorCasoUso
from aplicacion.casos_uso.evaluar_postulacion import EvaluarPostulacionCasoUso
from aplicacion.casos_uso.postular_estudiante import PostularEstudianteCasoUso
from aplicacion.casos_uso.registrar_horas import RegistrarHorasCasoUso
from aplicacion.casos_uso.reintentar_validacion_sia import ReintentarValidacionSiaCasoUso
from aplicacion.casos_uso.revisar_avances_horas import RevisarAvancesHorasCasoUso
from aplicacion.casos_uso.validar_horas_registradas import ValidarHorasRegistradasCasoUso
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
from aplicacion.dtos.evaluacion_postulacion_dto import (
    EvaluacionPostulacionRespuestaDTO,
    EvaluarPostulacionComando,
)
from aplicacion.dtos.postulacion_dto import (
    PostulacionRespuestaDTO,
    PostularEstudianteComando,
)
from aplicacion.dtos.registro_horas_dto import (
    RegistrarHorasComando,
    RegistroHorasRespuestaDTO,
)
from aplicacion.dtos.validacion_horas_dto import (
    ValidacionHorasRespuestaDTO,
    ValidarHorasComando,
)
from aplicacion.seguridad.autorizador_rbac import AutorizadorRBAC, RolUsuario
from dominio.modelos.docente_asesor import DocenteAsesor
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma
from infraestructura.adaptadores.broker_memoria import InMemoryBrokerMensajes
from infraestructura.adaptadores.cliente_sia_simulado import AdaptadorSiaSimulado
from infraestructura.adaptadores.repositorio_memoria import (
    InMemoryRepositorioDocente,
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
    servicio_sia: AdaptadorSiaSimulado
    broker_mensajes: InMemoryBrokerMensajes
    servicio_correo: AdaptadorCorreoSimulado


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

    return SistemaPracticasEmpresariales(
        caso_uso_postular=caso_uso_postular,
        caso_uso_reintentar_sia=caso_uso_reintentar_sia,
        caso_uso_evaluar=caso_uso_evaluar,
        caso_uso_asignar_docente=caso_uso_asignar_docente,
        caso_uso_registrar_horas=caso_uso_registrar_horas,
        caso_uso_validar_horas=caso_uso_validar_horas,
        caso_uso_revisar_avances_horas=caso_uso_revisar_avances_horas,
        autorizador_rbac=autorizador_rbac,
        proveedor_identidad=proveedor_identidad,
        interceptor_identidad=interceptor_identidad,
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
        repositorio_docente=repo_docente,
        repositorio_registro_horas=repo_registro_horas,
        repositorio_token=repo_token,
        servicio_sia=servicio_sia,
        broker_mensajes=broker_mensajes,
        servicio_correo=servicio_correo,
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
    print("                                RevisarAvancesHorasCasoUso (CU-06)")

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

    print("\n[OK] El sistema de gestión de prácticas está listo y operativo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
