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

from aplicacion.casos_uso.evaluar_postulacion import EvaluarPostulacionCasoUso
from aplicacion.casos_uso.postular_estudiante import PostularEstudianteCasoUso
from aplicacion.casos_uso.reintentar_validacion_sia import ReintentarValidacionSiaCasoUso
from aplicacion.dtos.evaluacion_postulacion_dto import (
    EvaluacionPostulacionRespuestaDTO,
    EvaluarPostulacionComando,
)
from aplicacion.dtos.postulacion_dto import (
    PostulacionRespuestaDTO,
    PostularEstudianteComando,
)
from aplicacion.seguridad.autorizador_rbac import AutorizadorRBAC, RolUsuario
from dominio.modelos.regla_programa import EstadoVigenciaRegla, ReglaPrograma
from infraestructura.adaptadores.broker_memoria import InMemoryBrokerMensajes
from infraestructura.adaptadores.cliente_sia_simulado import AdaptadorSiaSimulado
from infraestructura.adaptadores.repositorio_memoria import (
    InMemoryRepositorioPractica,
    InMemoryRepositorioReglaPrograma,
)
from infraestructura.adaptadores.servicio_correo_simulado import AdaptadorCorreoSimulado
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

    # Componentes de seguridad y autorización
    autorizador_rbac: AutorizadorRBAC
    proveedor_identidad: ProveedorIdentidadSimulado

    # Adaptadores de infraestructura
    repositorio_practica: InMemoryRepositorioPractica
    repositorio_regla: InMemoryRepositorioReglaPrograma
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
    servicio_sia = AdaptadorSiaSimulado(umbral_fallos=umbral_fallos_sia)
    broker_mensajes = InMemoryBrokerMensajes()
    servicio_correo = AdaptadorCorreoSimulado()
    proveedor_identidad = ProveedorIdentidadSimulado()

    # 2. Componentes de seguridad de la capa de aplicación
    autorizador_rbac = AutorizadorRBAC()

    # 3. Precarga de reglas de programa vigentes (ADR-007)
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

    return SistemaPracticasEmpresariales(
        caso_uso_postular=caso_uso_postular,
        caso_uso_reintentar_sia=caso_uso_reintentar_sia,
        caso_uso_evaluar=caso_uso_evaluar,
        autorizador_rbac=autorizador_rbac,
        proveedor_identidad=proveedor_identidad,
        repositorio_practica=repo_practica,
        repositorio_regla=repo_regla,
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
    print("    - Servicio SIA:             AdaptadorSiaSimulado (Circuit Breaker activo)")
    print("    - Bróker de Mensajería:     InMemoryBrokerMensajes (Tareas + DLQ)")
    print("    - Servicio de Correo:       AdaptadorCorreoSimulado")
    print("    - Identidad y RBAC:         ProveedorIdentidadSimulado + AutorizadorRBAC")
    print("    - Casos de Uso Disponibles: PostularEstudianteCasoUso (CU-01),")
    print("                                ReintentarValidacionSiaCasoUso (CU-01),")
    print("                                EvaluarPostulacionCasoUso (CU-02)")

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

    print("\n[OK] El sistema de gestión de prácticas está listo y operativo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
