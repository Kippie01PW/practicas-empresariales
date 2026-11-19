"""Entidad de dominio Estudiante.

Traza: CU-01, ADR-002 (Clean Architecture), Vista Lógica §2.

Modela al estudiante o practicante matriculado que postula e interactúa
con el sistema de prácticas empresariales.
"""

from __future__ import annotations

import uuid


class Estudiante:
    """Entidad de dominio que representa a un estudiante universitario.

    Atributos del diagrama UML (01-logica.puml):
        - documento: Documento de identificación del estudiante.
        - nombreCompleto: Nombre completo del estudiante.
        - correoInstitucional: Correo institucional del estudiante.
        - programaAcademico: Programa académico al que pertenece.

    Atributos de trazabilidad técnica (plan.md):
        - id: Identificador único interno del estudiante.
    """

    __slots__ = (
        "_id",
        "_documento",
        "_nombre_completo",
        "_correo_institucional",
        "_programa_academico",
    )

    def __init__(
        self,
        *,
        documento: str,
        nombre_completo: str,
        correo_institucional: str,
        programa_academico: str,
        id: str | None = None,
    ) -> None:
        if not documento or not documento.strip():
            raise ValueError("El documento del estudiante no puede estar vacío.")
        if not nombre_completo or not nombre_completo.strip():
            raise ValueError("El nombre completo del estudiante no puede estar vacío.")
        if not correo_institucional or not correo_institucional.strip():
            raise ValueError("El correo institucional del estudiante no puede estar vacío.")
        if not programa_academico or not programa_academico.strip():
            raise ValueError("El programa académico del estudiante no puede estar vacío.")

        self._id: str = id or str(uuid.uuid4())
        self._documento: str = documento.strip()
        self._nombre_completo: str = nombre_completo.strip()
        self._correo_institucional: str = correo_institucional.strip()
        self._programa_academico: str = programa_academico.strip()

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
    def programa_academico(self) -> str:
        return self._programa_academico

    def __repr__(self) -> str:
        return (
            f"Estudiante(id={self._id!r}, "
            f"documento={self._documento!r}, "
            f"nombre_completo={self._nombre_completo!r}, "
            f"programa_academico={self._programa_academico!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Estudiante):
            return False
        return self._id == other._id or self._documento == other._documento

    def __hash__(self) -> int:
        return hash(self._id)
