# Contexto del Sistema (C4 - Nivel 1)

## 1. Presentación principal

* **Diagrama:** `../diagramas/contexto.puml`
* **Propósito:** Encuadra las cuatro vistas del modelo 4+1 mostrando el **Sistema de Gestión de Prácticas Empresariales** como una caja negra, delimitando qué está dentro de nuestro alcance y cómo interactúa con las personas (stakeholders) y los sistemas externos del entorno universitario.
* **Público objetivo:** Todos los stakeholders de negocio (Estudiante, Coordinador de prácticas, Docente asesor, RRHH/Supervisor) y técnicos.

## 2. Catálogo de elementos

| Elemento | Tipo | Descripción y responsabilidad |
| :--- | :--- | :--- |
| **Sistema de Gestión de Prácticas Empresariales** | Sistema de software | Caja negra central que gestiona el ciclo completo desde la postulación hasta el acta final en PDF. |
| **Estudiante** | Persona (Actor interno) | Se postula a la práctica (CU-01), registra sus horas semanales (CU-04) y consulta el estado del trámite (CU-11). |
| **Coordinador de prácticas** | Persona (Actor interno) | Aprueba postulaciones (CU-02), asigna tutores (CU-03), aprueba actas (CU-10), configura reglas (CU-12) y audita el proceso (CU-13, CU-14). |
| **Docente asesor** | Persona (Actor interno) | Revisa el avance de horas (CU-06), genera (CU-09) y aprueba electrónicamente el acta final (CU-10). |
| **Supervisor de empresa** | Persona (Actor externo) | Valida las horas semanales (CU-05) y evalúa el desempeño del practicante (CU-07) sin cuenta institucional. |
| **Administrador DBA** | Persona (Actor técnico) | Ejecuta la migración única inicial desde la plantilla normalizada de Excel (CU-15). |
| **SIA** | Sistema externo | Sistema de Información Académica que valida si el estudiante cumple los requisitos para cursar la práctica. |
| **SSO Institucional** | Sistema externo | Proveedor de identidad universitario que autentica a los actores internos (Estudiante, Coordinador, Docente). |
| **Servicio de correo** | Sistema externo | Pasarela SMTP institucional que entrega recordatorios de plazos (CU-08) y enlaces criptográficos a empresas. |

## 3. Justificación (Drivers y ADR)

* **RT-03 y SUP-01:** El `SIA` se modela como sistema externo consultado vía API REST para automatizar la verificación de requisitos en CU-01 y reducir en 90% las peticiones presenciales (OB-03).
* **RN-04, SUP-02, RI-02 y ADR-004:** El `Supervisor de empresa` interactúa directamente por HTTPS mediante enlaces efímeros enviados a través del `Servicio de correo`, mientras que los usuarios internos se autentican contra el `SSO Institucional` (PA-02).
* **RT-02, RI-01 y ADR-009:** El `Administrador DBA` interactúa por línea de comandos (CLI) para migrar la cohorte activa sin exponer módulos web desechables.

## 4. Comportamiento

* Todo flujo inicia por acción de una persona (HTTPS o CLI) o por una tarea programada interna (recordatorios CU-08).
* El sistema nunca expone sus almacenes de datos directamente al exterior; toda interacción atraviesa la frontera del sistema bajo protocolos seguros (`HTTPS`, `TLS`).

## 5. Vistas relacionadas

* **Vista de procesos (`vistas/02-procesos.md`):** Abre la caja negra del sistema para mostrar los contenedores que atienden cada flecha de este diagrama.
* **Vista física (`vistas/04-fisica.md`):** Muestra en qué nodos de red institucionales residen el sistema y las conexiones hacia `SIA`, `SSO Institucional` y `Servicio de correo`.
