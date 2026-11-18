# Sistema de gestión de prácticas empresariales

Repositorio de referencia del sistema para la gestión integral del ciclo de vida de prácticas empresariales (postulación, asignación de tutores, seguimiento de horas, evaluación de desempeño y generación de acta final con firmas electrónicas), desarrollado para la unidad de Arquitectura de Soluciones de Software de la Universidad de Caldas. Muestra cómo queda el caso resuelto desde la visión y drivers hasta SDD (Spec-Driven Development), con la estructura modular y de trazabilidad requerida en el proyecto.

## Integrantes
- Andrei Carro Flores
- Marita Costilla
- Juan José Hernández Velásquez
- Víctor Manuel Valencia Álvarez

---

## Cómo leerlo (en este orden)

| Paso | Archivo | Tema |
|------|---------|------|
| 1 | [docs/vision.md](docs/vision.md) | Visión: oportunidad, objetivos de negocio (OB-01 a OB-05), alcance, stakeholders, restricciones, supuestos y riesgos |
| 2 | [docs/drivers.md](docs/drivers.md) | Drivers: catálogo de casos de uso (CU-01 a CU-15), escenarios de calidad (EAC-01 a EAC-03), restricciones (RT/RN), preocupaciones (PA), matriz de priorización y escenarios (+1) |
| 3 | [docs/adr/](docs/adr/) | ADR: decisiones de arquitectura registradas (ADR-001 al ADR-010) con alternativas, contexto y consecuencias |
| 4 | [docs/contexto.md](docs/contexto.md) y [docs/vistas/](docs/vistas/) | Vistas arquitectónicas 4+1 (`01-logica.md`, `02-procesos.md`, `03-desarrollo.md`, `04-fisica.md`) |
| 5 | [docs/diagramas/](docs/diagramas/) | Diagramas como código (PlantUML): contexto, vistas C4 / UML y secuencias de los escenarios críticos (`secuencias/`) |
| 6 | [AGENTS.md](AGENTS.md) y [prompts/](prompts/) | SDD: reglas permanentes del asistente/agente y prompts guiados por cada fase (0 a 5) |
| 7 | [specs/](specs/) | SDD: carpetas por caso de uso (`001-postulacion-estudiante` a `015-migrar-practicas-excel`) con `spec.md`, `plan.md`, `tasks.md` y `validacion.md` |

## Cadena de trazabilidad

OB-01 a OB-05 (visión) → EAC-01 a EAC-03 y restricciones RT/RN (drivers) → ADR-001 a ADR-010 → Vistas 4+1 y secuencias ESC-01 a ESC-05 → Catálogo CU-01 a CU-15 (drivers.md) → specs 001 a 015 (`spec.md` → `plan.md` → `tasks.md`) → Código en `src/` → Validación (`validacion.md`).

Cada elemento cita al anterior formalmente por su identificador.

## Estructura

```text
practicas-empresariales/
├── AGENTS.md                 Reglas de contexto, arquitectura y trabajo para el agente
├── README.md                 Guía general del repositorio y orden de lectura
├── docs/
│   ├── vision.md             Documento de visión y objetivos del proyecto
│   ├── drivers.md            Catálogo de casos de uso, EAC, restricciones y matriz
│   ├── contexto.md           Diagrama y descripción del sistema en su entorno institucional
│   ├── adr/                  ADR-001 a ADR-010 (decisiones inmutables)
│   ├── vistas/               01-logica, 02-procesos, 03-desarrollo, 04-fisica (.md)
│   └── diagramas/            contexto, 01 a 04 (.puml) y secuencias/ (cu01, cu07, cu09, cu10, cu12)
├── specs/
│   ├── 001-postulacion-estudiante/        spec.md, plan.md, tasks.md, validacion.md
│   ├── 002-aprobar-rechazar-postulacion/  misma estructura
│   └── ...                                (hasta 015-migrar-practicas-excel/)
├── prompts/                  0-arranque.md y 1 a 5 (especificar, planear, descomponer, implementar, validar)
└── src/                      Código fuente del sistema (.gitkeep hasta fase 4)
```

## Cómo ver los diagramas

Los diagramas son archivos `.puml` (PlantUML, texto versionable). Se pueden ver:
- Directamente en VS Code usando la extensión **PlantUML** (con `Alt + D`).
- Pegando el contenido de los archivos en [PlantUML Editor Online](https://editor.plantuml.com) o [PlantText](https://www.planttext.com).
- Las vistas C4 utilizan la biblioteca estándar de PlantUML (`!include <C4/...>`).

## Estado

| Elemento | Estado |
|----------|--------|
| Visión, drivers, ADR (001 a 010), contexto, vistas 4+1 y secuencias (+1) | Completo |
| AGENTS.md y prompts/ (fases 0 a 5) | Completo |
| Estructura de especificaciones en `specs/` (001 a 015) | Creada |
| Spec, plan y tareas por caso de uso | En proceso según ciclo SDD |
| Validación de las specs | Pendiente (se completa durante la implementación) |
| Código en `src/` | Pendiente (Fase 4 de SDD) |

## Notas para quien consulta

- El sistema implementa un **Monolito Modular con Clean Architecture** y patrón de **Puertos y Adaptadores** (ADR-002), garantizando que las dependencias apunten estrictamente hacia el dominio.
- Resuelve desafíos críticos del ecosistema universitario: resiliencia ante caídas del Sistema de Información Académica (SIA) mediante colas asíncronas y *Circuit Breaker* (ADR-001), acceso seguro para supervisores externos sin cuenta institucional vía Magic Links firmados (ADR-004), control de acceso centralizado *deny-by-default* (ADR-005), bitácora inmutable *Append-Only* (ADR-006) y aseguramiento de integridad de actas mediante hash SHA-256 (ADR-008).
