"""DTOs inmutables para el caso de uso ConfigurarReglasProgramaCasoUso (CU-12).

Traza: CU-12, EAC-01, EAC-03, OB-05, PA-01, RN-01, RN-02, RN-03,
ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008.

Define los objetos de transferencia de datos inmutables (@dataclass(frozen=True, slots=True))
para la configuración declarativa de reglas y plantillas versionadas por programa académico:
- CrearBorradorReglaComando: Comando de entrada para crear una nueva versión de ReglaPrograma en estado Borrador (Escenario 1).
- EditarBorradorReglaComando: Comando de entrada para editar los atributos normativos de una ReglaPrograma mientras permanezca en estado Borrador (Escenarios 2 y 8).
- SimularReglaProgramaComando: Comando de entrada para simular y previsualizar en memoria el ActaFinal y la rúbrica de una ReglaPrograma en estado Borrador (Escenario 3).
- ActivarReglaProgramaComando: Comando de entrada para publicar y activar oficialmente una ReglaPrograma en estado Borrador, pasando la versión anterior a Inactiva (Escenario 4).
- EliminarReglaProgramaComando: Comando de entrada para solicitar la eliminación de una ReglaPrograma en estado Borrador, bloqueando versiones Activa o Inactiva (Escenario 8).
- ReglaProgramaRespuestaDTO: Respuesta formal de salida tras crear, editar o activar una ReglaPrograma.
- SimulacionReglaProgramaRespuestaDTO: Respuesta formal de salida para la previsualización en memoria del PDF del ActaFinal y la rúbrica sin persistencia oficial.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class CrearBorradorReglaComando:
    """Comando inmutable de entrada para registrar una nueva versión de ReglaPrograma en estado Borrador (CU-12, Escenario 1).

    Atributos:
        programa_academico: Nombre o identificador del programa académico (ej. 'Ingeniería de Sistemas').
        version: Identificador de la versión normativa (ej. '2026-2').
        horas_requeridas: Cantidad de horas obligatorias de práctica (entero positivo > 0).
        criterios_rubrica: Criterios de rúbrica configurados (lista simple no vacía de nombres sin peso o diccionario con ponderaciones > 0).
        plantilla_acta: Nombre o contenido de la plantilla HTML/CSS para el ActaFinal.
        actor_id: Identificador institucional del Coordinador de prácticas autenticado.
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        ip_origen: Dirección IP de origen para trazabilidad en EventoBitacora (ADR-006).
        regla_id: Identificador opcional preasignado para la nueva ReglaPrograma.
    """

    programa_academico: str
    version: str
    horas_requeridas: int
    criterios_rubrica: dict[str, Any] | list[str]
    plantilla_acta: str
    actor_id: str
    rol_actor: str = "Coordinador de prácticas"
    ip_origen: str = "127.0.0.1"
    regla_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class EditarBorradorReglaComando:
    """Comando inmutable de entrada para editar una ReglaPrograma mientras permanezca en estado Borrador (CU-12, Escenarios 2 y 8).

    Atributos:
        regla_id: Identificador único de la ReglaPrograma a editar.
        actor_id: Identificador institucional del Coordinador de prácticas autenticado.
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        horas_requeridas: Nueva cantidad opcional de horas obligatorias de práctica (entero positivo > 0).
        criterios_rubrica: Nuevos criterios de rúbrica opcionales (lista simple de criterios sin peso o diccionario con pesos > 0).
        plantilla_acta: Nueva plantilla HTML/CSS opcional para el ActaFinal.
        version: Nuevo identificador opcional de versión (validando unicidad en el mismo programa académico).
        ip_origen: Dirección IP de origen para registro en EventoBitacora (ADR-006).
    """

    regla_id: str
    actor_id: str
    rol_actor: str = "Coordinador de prácticas"
    horas_requeridas: Optional[int] = None
    criterios_rubrica: Optional[dict[str, Any] | list[str]] = None
    plantilla_acta: Optional[str] = None
    version: Optional[str] = None
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class SimularReglaProgramaComando:
    """Comando inmutable de entrada para simular y previsualizar en memoria el ActaFinal y la rúbrica de una ReglaPrograma (CU-12, Escenario 3).

    Atributos:
        regla_id: Identificador único de la ReglaPrograma en estado Borrador a simular.
        actor_id: Identificador institucional del Coordinador de prácticas autenticado.
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        estudiante_prueba_id: Identificador de estudiante de prueba para el renderizado en memoria.
        docente_prueba_id: Identificador de docente asesor de prueba para el renderizado en memoria.
        nombre_docente_prueba: Nombre completo del docente asesor de prueba.
        supervisor_prueba_id: Identificador del supervisor de empresa de prueba.
        calificacion_prueba: Calificación cuantitativa de prueba (0.0 a 5.0).
        observaciones_prueba: Observaciones cualitativas de prueba para la previsualización del acta.
        ip_origen: Dirección IP de origen para trazabilidad en bitácora si aplica.
    """

    regla_id: str
    actor_id: str
    rol_actor: str = "Coordinador de prácticas"
    estudiante_prueba_id: str = "EST-SIMULACION-001"
    docente_prueba_id: str = "DOC-SIMULACION-001"
    nombre_docente_prueba: str = "Docente Asesor Simulación"
    supervisor_prueba_id: str = "SUP-SIMULACION-001"
    calificacion_prueba: float = 4.5
    observaciones_prueba: str = (
        "Simulación de vista previa del acta final y rúbrica en estado Borrador."
    )
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class ActivarReglaProgramaComando:
    """Comando inmutable de entrada para publicar y activar oficialmente una ReglaPrograma en estado Borrador (CU-12, Escenario 4).

    Atributos:
        regla_id: Identificador único de la ReglaPrograma en estado Borrador a activar.
        actor_id: Identificador institucional del Coordinador de prácticas autenticado.
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        ip_origen: Dirección IP de origen para registro atómico en EventoBitacora (ADR-006).
        fecha_vigencia: Marca temporal opcional de entrada en vigencia oficial.
    """

    regla_id: str
    actor_id: str
    rol_actor: str = "Coordinador de prácticas"
    ip_origen: str = "127.0.0.1"
    fecha_vigencia: Optional[datetime] = None


@dataclass(frozen=True, slots=True)
class EliminarReglaProgramaComando:
    """Comando inmutable de entrada para eliminar una ReglaPrograma en estado Borrador (CU-12, Escenario 8).

    Bloquea cualquier intento de eliminación sobre reglas en estado Activa o Inactiva (histórica).

    Atributos:
        regla_id: Identificador único de la ReglaPrograma que se solicita eliminar.
        actor_id: Identificador institucional del Coordinador de prácticas autenticado.
        rol_actor: Rol del usuario autenticado para validación RBAC centralizada (ADR-005).
        ip_origen: Dirección IP de origen para trazabilidad en EventoBitacora (ADR-006).
    """

    regla_id: str
    actor_id: str
    rol_actor: str = "Coordinador de prácticas"
    ip_origen: str = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class ReglaProgramaRespuestaDTO:
    """DTO inmutable de salida tras crear, editar o activar una ReglaPrograma (CU-12, Escenarios 1, 2 y 4).

    Atributos:
        regla_id: Identificador único de la ReglaPrograma.
        programa_academico: Nombre del programa académico asociado.
        version: Versión normativa de la regla.
        horas_requeridas: Horas obligatorias exigidas por la versión de la regla.
        criterios_rubrica: Criterios de rúbrica configurados (lista simple o diccionario).
        nombres_criterios: Tupla inmutable con los nombres de los criterios de evaluación.
        plantilla_acta: Nombre o identificador de la plantilla HTML/CSS del ActaFinal.
        estado_vigencia: Estado de vigencia actual ('Borrador', 'Activa' o 'Inactiva').
        fecha_vigencia: Marca temporal de vigencia de la regla.
        regla_anterior_inactivada_id: Identificador de la versión anterior pasada a 'Inactiva' durante la activación, o None.
        version_anterior_inactivada: Versión anterior pasada a 'Inactiva' durante la activación, o None.
        mensaje: Mensaje descriptivo del resultado de la operación.
    """

    regla_id: str
    programa_academico: str
    version: str
    horas_requeridas: int
    criterios_rubrica: dict[str, Any] | list[str]
    nombres_criterios: tuple[str, ...]
    plantilla_acta: str
    estado_vigencia: str
    fecha_vigencia: datetime
    regla_anterior_inactivada_id: Optional[str]
    version_anterior_inactivada: Optional[str]
    mensaje: str


@dataclass(frozen=True, slots=True)
class SimulacionReglaProgramaRespuestaDTO:
    """DTO inmutable de salida con el resultado de la simulación en memoria del ActaFinal y rúbrica (CU-12, Escenario 3).

    Garantiza que la previsualización del PDF y de la rúbrica se genere estrictamente en memoria,
    con persistido_en_repositorio=False y manteniendo la ReglaPrograma en estado 'Borrador'.

    Atributos:
        regla_id: Identificador único de la ReglaPrograma simulada.
        programa_academico: Nombre del programa académico asociado.
        version: Versión normativa simulada.
        estado_vigencia: Estado de vigencia de la regla tras la simulación ('Borrador').
        horas_requeridas: Horas requeridas aplicadas en la vista previa del acta.
        criterios_rubrica: Criterios de rúbrica aplicados en la vista previa.
        nombres_criterios: Tupla inmutable con los nombres de los criterios de la rúbrica simulada.
        plantilla_utilizada: Plantilla HTML/CSS aplicada en la generación del PDF en memoria.
        contenido_pdf_simulacion: Binario del documento PDF generado en memoria.
        vista_previa_html: Representación HTML/CSS renderizada en memoria con los datos de prueba.
        hash_sha256_simulacion: Huella SHA-256 calculada sobre el binario PDF de previsualización.
        persistido_en_repositorio: Indica si se almacenó un ActaFinal oficial (siempre False en simulación).
        mensaje: Mensaje descriptivo del resultado de la simulación y previsualización.
    """

    regla_id: str
    programa_academico: str
    version: str
    estado_vigencia: str
    horas_requeridas: int
    criterios_rubrica: dict[str, Any] | list[str]
    nombres_criterios: tuple[str, ...]
    plantilla_utilizada: str
    contenido_pdf_simulacion: bytes
    vista_previa_html: str
    hash_sha256_simulacion: str
    persistido_en_repositorio: bool
    mensaje: str
