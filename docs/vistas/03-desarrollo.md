# Vista de Desarrollo (Componentes C4 Nivel 3 y Vista de Usos)

## 1. Presentación principal

* **Diagrama:** `../diagramas/03-desarrollo.puml`
* **Propósito:** Muestra la estructura interna del contenedor principal **`API de prácticas`** combinando las tres capas de **Clean Architecture / Puertos y Adaptadores** (`infraestructura`, `aplicacion`, `dominio` más `main.py` de composición) con la **vista de usos entre módulos de negocio sin ciclos** (grafo acíclico dirigido).
* **Público objetivo:** Desarrolladores y arquitecto de software.

## 2. Catálogo de elementos

| Componente / Paquete | Capa | Responsabilidad |
| :--- | :--- | :--- |
| **main.py** | Composición | Único archivo que conoce todas las capas; instancia los adaptadores y los inyecta en los casos de uso. |
| **Controlador REST** | Infraestructura | Adaptador primario HTTP que recibe peticiones desde la `Aplicación web` y formatea respuestas JSON. |
| **Interceptor de Identidad** | Infraestructura | Verifica el token OIDC del `SSO Institucional` para usuarios internos o valida la firma HMAC y caducidad de 15 días del Magic Link para externos (ADR-004). |
| **Adaptador PostgreSQL** | Infraestructura | Implementa los puertos de repositorio SQL y escribe de forma atómica en la tabla `EventoBitacora` (ADR-006). |
| **Adaptador SIA** | Infraestructura | Cliente HTTP hacia el `SIA` instrumentado con timeout de 5s y patrón *Circuit Breaker* (ADR-001, RT-03). |
| **Publicador de Eventos** | Infraestructura | Publica mensajes persistentes en el `Broker de mensajes` cuando falla el SIA o se requieren notificaciones. |
| **Adaptador PDF y Hash** | Infraestructura | Toma la plantilla HTML/CSS configurada, inyecta los datos de la práctica, genera el PDF y calcula su hash SHA-256 (ADR-008). |
| **Autorizador RBAC** | Aplicación | Punto centralizado que verifica rol y pertenencia de datos (*Context-Based RBAC*, ej. que un docente solo vea sus practicantes) bajo política *deny-by-default* (ADR-005). |
| **Módulo Actas** | Aplicación | Orquesta la generación (CU-09), aprobación electrónica (CU-10) y consolidados de auditoría (CU-14). |
| **Módulo Seguimiento y Evaluación** | Aplicación | Gestiona el registro y validación de horas (CU-04, CU-05, CU-06), evaluación de desempeño (CU-07) y recordatorios (CU-08). |
| **Módulo Postulaciones** | Aplicación | Gestiona postulaciones (CU-01), aprobación (CU-02), asignación de tutor (CU-03), consulta de estado (CU-11), monitoreo (CU-13) y carga desde el CLI (CU-15). |
| **Módulo Reglas** | Aplicación | Gestiona el versionamiento declarativo de horas requeridas, rúbricas y plantillas por programa académico (CU-12, ADR-007). |
| **Puertos de Salida** | Aplicación | Interfaces abstractas definidas por la capa de aplicación que los adaptadores de infraestructura implementan. |
| **Núcleo de Dominio** | Dominio | Entidades del negocio y la Máquina de Estados Finitos dentro de `Practica` (ADR-010), libres de dependencias de frameworks o bases de datos. |

## 3. Justificación (Drivers y ADR)

* **PA-01, EAC-01, RT-03 y ADR-002:** La arquitectura hexagonal (Puertos y Adaptadores) garantiza que cualquier cambio en la API del `SIA` solo afecte al `Adaptador SIA` (1 componente), y que un cambio en el formato o rúbrica del acta solo toque el `Módulo Reglas` y el `Adaptador PDF y Hash` (máximo 2 componentes, en menos de 16 horas-hombre, cumpliendo estrictamente **EAC-01**).
* **RN-01, RN-03 y ADR-005:** El `Autorizador RBAC` vive en la capa de Aplicación y no en anotaciones sueltas del controlador HTTP; así, tanto el `Controlador REST` como el `Script CLI de migración` y el `Worker de integración` pasan por las mismas reglas de seguridad y dominio.
* **Vista de usos sin ciclos:** La cadena de dependencias entre módulos es estrictamente jerárquica y acíclica:
  $$\text{Módulo Actas} \rightarrow \text{Módulo Seguimiento y Evaluación} \rightarrow \text{Módulo Postulaciones} \rightarrow \text{Módulo Reglas}$$
  Esto permite construir y entregar el sistema por incrementos (primero Reglas y Postulaciones, luego Seguimiento y finalmente Actas) sin deuda técnica por dependencias circulares.

## 4. Comportamiento

* **Regla de dependencia:** Todas las flechas de uso cruzan las capas apuntando hacia adentro (hacia `dominio`). Los adaptadores de `infraestructura` dependen de `aplicacion` (implementando los `Puertos de Salida`), nunca al revés. Para impedir violaciones accidentales, el pipeline de integración continua valida las importaciones con pruebas de arquitectura estática (ADR-002).

## 5. Vistas relacionadas

* **Vista de procesos (`02-procesos.md`):** Este diagrama detalla el interior del contenedor `API de prácticas`; además, el `Worker de integración` y el `Script CLI de migración` reutilizan directamente la capa de `aplicacion` y `dominio` de este mismo código base.
* **Vista lógica (`01-logica.md`):** El componente `Núcleo de Dominio` contiene exactamente las entidades definidas en el modelo de dominio UML.
