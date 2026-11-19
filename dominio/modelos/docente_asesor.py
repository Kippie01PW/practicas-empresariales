"""Entidad de dominio DocenteAsesor.

Traza: CU-03, RT-01, ADR-002 (Clean Architecture), Vista Lógica §2.

Modela al docente asesor o tutor académico institucional responsable
del seguimiento del practicante y control de cupos de tutorías.
"""

from __future__ import annotations

import uuid
from typing import Optional

from dominio.errores import CupoDocenteExcedidoError


class DocenteAsesor:
    """Entidad de dominio que representa a un Docente Asesor o Tutor Académico.

    Atributos del diagrama UML (01-logica.puml) y del plan técnico:
        - documento: Documento de identidad del docente asesor.
        - nombreCompleto: Nombre completo del docente asesor.
        - correoInstitucional: Correo electrónico institucional.
        - cupoMaximoPracticas: Límite máximo de tutorías simultáneas permitidas (RT-01, default=10).
        - practicasActivas: Cantidad actual de prácticas activas asignadas.
        - activo: Indica si el docente se encuentra habilitado para recibir nuevas asignaciones.

    Atributos de trazabilidad técnica (plan.md):
        - id: Identificador único interno del docente asesor.
    """

    __slots__ = (
        "_id",
        "_documento",
        "_nombre_completo",
        "_correo_institucional",
        "_cupo_maximo_practicas",
        "_practicas_activas",
        "_activo",
    )

    def __init__(
        self,
        *,
        documento: str,
        nombre_completo: str,
        correo_institucional: str,
        cupo_maximo_practicas: int = 10,
        practicas_activas: int = 0,
        activo: bool = True,
        id: Optional[str] = None,
    ) -> None:
        if not documento or not documento.strip():
            raise ValueError("El documento del docente asesor no puede estar vacío.")
        if not nombre_completo or not nombre_completo.strip():
            raise ValueError("El nombre completo del docente asesor no puede estar vacío.")
        if not correo_institucional or not correo_institucional.strip():
            raise ValueError("El correo institucional del docente asesor no puede estar vacío.")
        if cupo_maximo_practicas < 0:
            raise ValueError("El cupo máximo de prácticas no puede ser negativo.")
        if practicas_activas < 0:
            raise ValueError("El número de prácticas activas no puede ser negativo.")

        self._id: str = id or str(uuid.uuid4())
        self._documento: str = documento.strip()
        self._nombre_completo: str = nombre_completo.strip()
        self._correo_institucional: str = correo_institucional.strip()
        self._cupo_maximo_practicas: int = cupo_maximo_practicas
        self._practicas_activas: int = practicas_activas
        self._activo: bool = activo

    # -- Propiedades de solo lectura ----------------------------------------

    @property
    def id(self) -> str:
        return self._id

    @property
    def documento(self) -> str:
        return self._documento

    @property
    def nombre_completo(self) -> str:
        return self._nombre_completo

    @property
    def correo_institucional(self) -> str:
        return self._correo_institucional

    @property
    def cupo_maximo_practicas(self) -> int:
        return self._cupo_maximo_practicas

    @property
    def practicas_activas(self) -> int:
        return self._practicas_activas

    @property
    def activo(self) -> bool:
        return self._activo

    # -- Métodos de dominio y control de cupos -------------------------------

    def tiene_cupo_disponible(self) -> bool:
        """Indica si el docente está habilitado y cuenta con cupo libre para asignar."""
        return self._activo and (self._practicas_activas < self._cupo_maximo_practicas)

    def cupo_disponible(self) -> int:
        """Retorna la cantidad de cupos disponibles para nuevas asignaciones."""
        if not self._activo:
            return 0
        return max(0, self._cupo_maximo_practicas - self._practicas_activas)

    def asignar_practica(self) -> None:
        """Incrementa en 1 la carga de prácticas activas asignadas.

        Raises:
            CupoDocenteExcedidoError: Si el docente alcanzó el cupo máximo o no está activo.
        """
        if not self.tiene_cupo_disponible():
            raise CupoDocenteExcedidoError(
                docente_id=self._id,
                cupo_maximo=self._cupo_maximo_practicas,
                practicas_activas=self._practicas_activas,
            )
        self._practicas_activas += 1

    def liberar_practica(self) -> None:
        """Decrementa en 1 la carga de prácticas activas ante finalización o desvinculación."""
        if self._practicas_activas > 0:
            self._practicas_activas -= 1

    # -- Representación y comparación ---------------------------------------

    def __repr__(self) -> str:
        return (
            f"DocenteAsesor(id={self._id!r}, "
            f"documento={self._documento!r}, "
            f"nombre_completo={self._nombre_completo!r}, "
            f"cupo={self._practicas_activas}/{self._cupo_maximo_practicas}, "
            f"activo={self._activo})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DocenteAsesor):
            return False
        return self._id == other._id or self._documento == other._documento

    def __hash__(self) -> int:
        return hash(self._id)
