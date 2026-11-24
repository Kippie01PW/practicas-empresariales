# Sistema de gestión de prácticas empresariales

Repositorio de referencia del sistema para la gestión integral del ciclo de vida de prácticas empresariales (postulación, evaluación administrativa, asignación de tutores, registro y validación semanal de horas, evaluación de desempeño, generación de acta final con firmas electrónicas, monitoreo centralizado y migración de datos legados), desarrollado para la unidad de Arquitectura de Soluciones de Software de la Universidad de Caldas. 

Muestra cómo queda el caso resuelto de extremo a extremo: desde la visión de negocio, requerimientos y drivers arquitectónicos hasta su especificación formal e implementación bajo **SDD (Spec-Driven Development)** con Clean Architecture y el patrón de Puertos y Adaptadores.

> **Estado del desarrollo:** El ciclo **SDD (Spec-Driven Development) se encuentra 100% completado**. Los 15 casos de uso del sistema (`CU-01` a `CU-15`) han culminado exitosamente sus 5 fases: Especificación formal Gherkin (`spec.md`), Planeación arquitectónica (`plan.md`), Descomposición de micro-tareas (`tasks.md`), Implementación modular (`dominio/`, `aplicacion/`, `infraestructura/`) y Matriz de validación reproducible (`validacion.md`).

## Integrantes
- Andrei Carro Flores
- Marita Costilla
- Juan José Hernández Velásquez
- Víctor Manuel Valencia Álvarez

---

## Cómo leerlo (en este orden)

| Paso | Archivo o Directorio | Tema |
|:---:|:---|:---|
| **1** | [docs/vision.md](docs/vision.md) | **Visión:** Problema de negocio, objetivos medibles (**OB-01 a OB-05**), alcance, stakeholders y riesgos iniciales. |
| **2** | [docs/drivers.md](docs/drivers.md) | **Drivers:** Catálogo de casos de uso (**CU-01 a CU-15**), escenarios de calidad (**EAC-01 a EAC-03**), restricciones (**RT-01 a RT-04, RN-01 a RN-05**), preocupaciones arquitectónicas (**PA-01 a PA-05**) y matriz de priorización. |
| **3** | [docs/arquitectura.md](docs/arquitectura.md) | **Mapa general de arquitectura (arc42):** Documento integrador que sintetiza objetivos, estrategia de solución, conceptos transversales, matriz de cobertura y glosario. |
| **4** | [docs/adr/](docs/adr/) | **Decisiones de arquitectura (ADRs):** Registro formal e inmutable de decisiones (**ADR-001 al ADR-010**) con contexto, alternativas evaluadas y consecuencias. |
| **5** | [docs/contexto.md](docs/contexto.md) y [docs/vistas/](docs/vistas/) | **Vistas arquitectónicas 4+1:** Modelo formal de Kruchten compuesto por la vista [Lógica](docs/vistas/01-logica.md), de [Procesos](docs/vistas/02-procesos.md), de [Desarrollo](docs/vistas/03-desarrollo.md) y [Física](docs/vistas/04-fisica.md). |
| **6** | [docs/diagramas/](docs/diagramas/) | **Diagramas como código (PlantUML):** Diagrama de contexto, vistas C4 (niveles 1 a 3), diagrama de despliegue y secuencias de los escenarios críticos en `secuencias/`. |
| **7** | [AGENTS.md](AGENTS.md), [GUIA.md](GUIA.md) y [prompts/](prompts/) | **Gobierno SDD:** Reglas permanentes del asistente, guía metodológica de prompts y flujos de trabajo por fases (0 a 5) con estrategia de cambio de contexto. |
| **8** | [specs/](specs/) | **Especificaciones de casos de uso:** Carpetas individuales para cada funcionalidad (`001-postulacion-estudiante` a `015-migrar-practicas-en-curso-desde-excel`), cada una con su ciclo completo: `spec.md`, `plan.md`, `tasks.md` y `validacion.md`. |
| **9** | [dominio/](dominio/), [aplicacion/](aplicacion/), [infraestructura/](infraestructura/) y [main.py](main.py) | **Código fuente y composición:** Implementación modular en Python 3.12 bajo Clean Architecture y Composition Root ejecutable. |

---

## Cadena de trazabilidad

El proyecto mantiene una cadena de trazabilidad bidireccional y rigurosa en la que cada artefacto cita formalmente a sus predecesores:

$$\text{OB-01..05 (Visión)} \longrightarrow \begin{matrix} \text{EAC-01..03} \\ \text{RT/RN (Drivers)} \end{matrix} \longrightarrow \text{ADR-001..010} \longrightarrow \begin{matrix} \text{Vistas 4+1} \\ \text{Secuencias (+1)} \end{matrix} \longrightarrow \text{CU-01..15} \longrightarrow \text{specs/ (001..015)} \longrightarrow \begin{matrix} \text{Código} \\ \text{(dominio/aplicacion/infra)} \end{matrix} \longrightarrow \text{validacion.md}$$

---

## Estructura del repositorio

```text
practicas-empresariales/
├── AGENTS.md                 # Reglas canónicas del proyecto, fuentes de verdad y convenciones Clean Architecture
├── GUIA.md                   # Guía paso a paso de la metodología SDD, gestión de prompts y formato de commits
├── README.md                 # Mapa general del repositorio, orden de lectura y estado del sistema
├── main.py                   # Composition Root del sistema: inyección de dependencias y CLI de demostración
├── docs/                     # Documentación arquitectónica formal
│   ├── arquitectura.md       # Mapa general de arquitectura adaptado de arc42
│   ├── vision.md             # Visión del producto, objetivos de negocio (OB-01 a OB-05) y stakeholders
│   ├── drivers.md            # Catálogo CU-01 a CU-15, escenarios de atributos de calidad, restricciones y matriz
│   ├── contexto.md           # Diagrama de contexto del sistema y límites institucionales
│   ├── adr/                  # Decisiones arquitectónicas registradas (ADR-001 al ADR-010)
│   ├── vistas/               # Vistas del modelo 4+1 (01-logica, 02-procesos, 03-desarrollo, 04-fisica)
│   └── diagramas/            # Diagramas PlantUML (.puml) y escenarios de secuencia en secuencias/
├── dominio/                  # Capa interna de Dominio (pura, sin dependencias externas)
│   ├── errores.py            # Jerarquía unificada de excepciones de negocio
│   └── modelos/              # Entidades del agregado: Practica, Estudiante, DocenteAsesor, ReglaPrograma,
│                             # RegistroHoras, TokenEvaluacion, EvaluacionDesempeno, ActaFinal, EventoBitacora...
├── aplicacion/               # Capa de Aplicación (Casos de uso, orquestación y contratos)
│   ├── casos_uso/            # Implementación de los 15 casos de uso (CU-01 a CU-15) y worker SIA
│   ├── dtos/                 # DTOs inmutables de entrada y salida (@dataclass frozen)
│   ├── puertos/              # Interfaces abstractas (typing.Protocol) de repositorios y servicios externos
│   └── seguridad/            # AutorizadorRBAC centralizado con política deny-by-default y control contextual
├── infraestructura/          # Capa de Infraestructura (Adaptadores y tecnologías concretas)
│   ├── adaptadores/          # Repositorios en memoria deterministas, adaptadores simulados de SIA con
│                             # Circuit Breaker, bróker RabbitMQ con DLQ, correo SMTP y generador PDF/hash
│   └── seguridad/            # InterceptorIdentidad (Magic Links HMAC-SHA256) y ProveedorIdentidadSimulado (OIDC)
├── prompts/                  # Plantillas de prompts guiados para el flujo SDD (fases 0 a 5)
│   ├── 0-arranque.md         # Prompt de arranque e inducción de sesión
│   ├── 1-especificar.md      # Fase 1: Redacción de escenarios Gherkin (spec.md)
│   ├── 2-planear.md          # Fase 2: Mapeo arquitectónico y diseño técnico (plan.md)
│   ├── 3-descomponer.md      # Fase 3: Lista ordenada de micro-tareas atómicas (tasks.md)
│   ├── 4-implementar.md      # Fase 4: Implementación de código tarea por tarea
│   └── 5-validar.md          # Fase 5: Matriz de verificación funcional y arquitectónica (validacion.md)
└── specs/                    # Especificaciones completas de los 15 casos de uso del catálogo
    ├── 001-postulacion-estudiante/
    ├── 002-aprobar-rechazar-postulacion/
    ├── 003-asignar-docente-asesor/
    ├── 004-registrar-horas-practica/
    ├── 005-validar-horas-registradas/
    ├── 006-revisar-avances-de-horas/
    ├── 007-evaluar-desempeno-del-practicante/
    ├── 008-enviar-recordatorios-plazos/
    ├── 009-generar-acta-final-de-la-practica/
    ├── 010-aprobar-acta-electronicamente/
    ├── 011-consultar-estado-del-tramite/
    ├── 012-configurar-reglas-plantillas-programa/
    ├── 013-monitorear-estado-general-de-practicas/
    ├── 014-generar-consolidados-auditoria/
    └── 015-migrar-practicas-en-curso-desde-excel/
```

---

## Cómo ver los diagramas

Los diagramas están escritos en PlantUML (`.puml`, texto versionable). Se pueden visualizar mediante:
- **Visual Studio Code:** Instalando la extensión **PlantUML** y presionando `Alt + D` sobre cualquier archivo `.puml`.
- **Visores en línea:** Copiando el contenido del archivo en [PlantUML Editor Online](https://editor.plantuml.com) o [PlantText](https://www.planttext.com).
- **Librería C4:** Los diagramas de contenedores y componentes consumen la librería estándar C4 de PlantUML (`!include <C4/...>`).

---

## Estado del proyecto

> **Estado general:** **SDD (Spec-Driven Development) 100% Completado**. Se ejecutaron y cerraron las 5 fases metodológicas para los 15 casos de uso (`CU-01` a `CU-15`), asegurando trazabilidad matemática desde los objetivos de negocio y drivers hasta la suite de validación en memoria y Composition Root.

| Componente / Dimensión | Estado | Cobertura y Detalle |
|:---|:---:|:---|
| **Metodología SDD (Fases 1 a 5)** | **100% Completado** | Las 5 fases (`spec.md`, `plan.md`, `tasks.md`, implementación en `src/` y `validacion.md`) culminadas al 100% para los 15 casos de uso (`CU-01` a `CU-15`). |
| **Visión y Drivers** | **Completo** | Documento de visión ([vision.md](docs/vision.md)), objetivos OB-01 a OB-05, catálogo CU-01 a CU-15, EAC-01 a EAC-03 y restricciones en [drivers.md](docs/drivers.md). |
| **Arquitectura arc42 y Vistas 4+1** | **Completo** | [docs/arquitectura.md](docs/arquitectura.md), vistas Lógica, Procesos, Desarrollo y Física, más 5 diagramas de secuencias críticas en [docs/diagramas/](docs/diagramas/). |
| **Decisiones Arquitectónicas (ADRs)** | **Completo** | 10 decisiones registradas formalmente ([ADR-001 al ADR-010](docs/adr/)), sin pendientes abiertos. |
| **Especificaciones SDD (`specs/`)** | **Completo** | 15 de 15 casos de uso cuentan con su ciclo SDD completo: `spec.md`, `plan.md`, `tasks.md` y `validacion.md`. |
| **Código Fuente (Clean Architecture)** | **Completo** | Implementado al 100% en `dominio/`, `aplicacion/` e `infraestructura/`, respetando la regla de dependencia estricta. |
| **Validación y Pruebas de Aceptación** | **Completo** | 100% de los escenarios de aceptación (camino feliz, casos borde, concurrencia y seguridad) verificados y documentados en sus respectivos `validacion.md`. |
| **Composition Root y CLI de Demostración** | **Completo** | `main.py` integra los 15 casos de uso y ejecuta una demostración fluida y reproducible de extremo a extremo con código de salida 0. |

---

## Ejecución del sistema

El sistema está desarrollado en **Python 3.12+** con tipado estático estricto (`typing`, `from __future__ import annotations`). No requiere instalación de bases de datos externas pesadas ni configuraciones adicionales para su ejecución y validación inicial, gracias a la suite de adaptadores deterministas en memoria:

```bash
# Ejecutar la demostración integral de los 15 casos de uso
python main.py
```

Al ejecutarse, `main.py` compone todas las dependencias e interactúa secuencialmente con el ciclo de vida completo de la práctica:
1. **CU-01:** Postulación de estudiante con verificación de requisitos académicos (SIA).
2. **CU-02:** Aprobación administrativa por parte del Coordinador de Prácticas.
3. **CU-03:** Asignación de docente asesor respetando el cupo reglamentario de tutorías (RT-01).
4. **CU-04:** Registro semanal de horas y transición formal a estado `EnEjecucion`.
5. **CU-05:** Validación de horas por supervisor de empresa externo mediante Magic Link criptográfico (ADR-004).
6. **CU-06:** Consulta de avances y acumulados en modo solo lectura por el docente asesor.
7. **CU-07:** Evaluación cualitativa y cuantitativa de desempeño según la rúbrica versionada.
8. **CU-08:** Tarea programada de recordatorios y alertas por proximidad de plazos.
9. **CU-09:** Renderizado del Acta Final en PDF desde plantilla HTML/CSS y sellado hash SHA-256 (ADR-008).
10. **CU-10:** Firma electrónica del docente asesor y del coordinador, formalizando la práctica en estado `Completada`.
11. **CU-11:** Consulta de autoservicio del estado del trámite y descarga del acta oficial por el estudiante.
12. **CU-12:** Configuración declarativa, edición y activación de nuevas versiones de reglas sin alterar prácticas previas (EAC-01).
13. **CU-13:** Tablero de control de monitoreo general de prácticas para la coordinación.
14. **CU-14:** Exportación de consolidados históricos de auditoría y acreditación académica en PDF.
15. **CU-15:** Proceso ETL de migración masiva de prácticas en curso desde archivos Excel normalizados.

---

## Aspectos arquitectónicos clave

- **Monolito Modular con Clean Architecture y Puertos y Adaptadores ([ADR-002](docs/adr/ADR-002-monolito-modular-puertos-adaptadores.md)):** La lógica de negocio (`dominio/`) es agnóstica de frameworks y bases de datos. Los casos de uso (`aplicacion/`) definen sus puertos como `Protocol` y la infraestructura (`infraestructura/`) provee los adaptadores concretos.
- **Resiliencia e integración desacoplada ([ADR-001](docs/adr/ADR-001-resiliencia-integracion-asincrona.md)):** La consulta al SIA cuenta con timeout de 5s y *Circuit Breaker*. Si el servicio falla, la postulación queda en `PendienteVerificacion`, se publica en RabbitMQ y un worker asíncrono con Dead-Letter Queue (DLQ) gestiona los reintentos (**EAC-02**).
- **Autenticación híbrida ([ADR-004](docs/adr/ADR-004-autenticacion-hibrida-enlaces-criptograficos.md)):** SSO institucional (OIDC) para usuarios internos (estudiantes, docentes, coordinadores) y enlaces efímeros firmados criptográficamente (Magic Links HMAC-SHA256 con vigencia de 15 días y carácter de un solo uso) para supervisores de empresa externos (**EAC-03, RN-04**).
- **Autorización RBAC centralizada y pertenencia contextual ([ADR-005](docs/adr/ADR-005-rbac-casos-de-uso.md)):** Política *deny-by-default* a nivel de casos de uso, validando tanto el rol como la pertenencia contextual de los datos (un estudiante solo accede a su práctica; un docente solo a sus practicantes asignados, dando cumplimiento a la Ley 1581 / **RN-01**).
- **Bitácora de auditoría Append-Only ([ADR-006](docs/adr/ADR-006-bitacora-auditoria-append-only.md)):** Registro inmutable y de solo inserción para cada cambio de estado, aprobación de actas o accesos denegados, sellados criptográficamente con hash SHA-256.
- **Reglas declarativas versionadas por programa ([ADR-007](docs/adr/ADR-007-configuracion-declarativa-reglas-versionadas.md)):** Horas requeridas, rúbricas de evaluación y plantillas HTML atadas inmutablemente a la práctica al momento de iniciar, garantizando 0% de alteración a prácticas activas o históricas ante reformas curriculares (**EAC-01**).
- **Generación y preservación de actas ([ADR-008](docs/adr/ADR-008-generacion-preservacion-acta-final.md)):** Renderizado de actas PDF oficiales y preservación con huella digital SHA-256 en base de datos y volumen de almacenamiento local.
- **Máquina de estados finitos formal ([ADR-010](docs/adr/ADR-010-maquina-estados-finitos.md)):** La entidad `Practica` encapsula y gobierna estrictamente sus transiciones de estado (*PendienteVerificacion $\rightarrow$ Solicitada $\rightarrow$ Aprobada $\rightarrow$ Asignada $\rightarrow$ EnEjecucion $\rightarrow$ Evaluada $\rightarrow$ Completada* o *Rechazada*), impidiendo la culminación del trámite sin el cumplimiento total de los requisitos.
