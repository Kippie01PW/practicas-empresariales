# Vista de Procesos (Diagrama de Contenedores - C4 Nivel 2)

## 1. Presentación principal

* **Diagrama:** `../diagramas/02-procesos.puml`
* **Propósito:** Hace zoom dentro del sistema para mostrar las unidades de ejecución independientes (procesos y almacenes de datos), las tecnologías seleccionadas sin costo de licenciamiento (RN-05) y los protocolos de comunicación síncronos y asíncronos entre ellos.
* **Público objetivo:** Integradores de sistemas, arquitectos y desarrolladores.

## 2. Catálogo de elementos

| Contenedor | Tipo y Tecnología | Descripción y responsabilidad |
| :--- | :--- | :--- |
| **Aplicación web** | Contenedor (SPA React / TypeScript) | Interfaz de usuario en el navegador para los roles internos y para el formulario sin cuenta del supervisor externo. |
| **API de prácticas** | Contenedor (Python / FastAPI, Monolito modular) | Proceso principal que expone los endpoints REST, aplica RBAC (ADR-005), ejecuta la máquina de estados (ADR-010) y genera actas desde plantillas HTML a PDF (ADR-008). |
| **Broker de mensajes** | Contenedor (RabbitMQ) | Cola de mensajes con persistencia en disco que desacopla la recepción de postulaciones de la disponibilidad del `SIA` y del `Servicio de correo` (ADR-001). |
| **Worker de integración** | Contenedor (Python / Celery) | Proceso en segundo plano que consume del `Broker de mensajes`, aplica reintentos con retroceso exponencial hacia el `SIA` y ejecuta la tarea programada de recordatorios (CU-08). |
| **Script CLI de migración** | Contenedor (Python CLI) | Herramienta de línea de comandos de un solo uso que valida la plantilla Excel normalizada e inyecta las prácticas activas reutilizando la lógica de negocio (ADR-009). |
| **PostgreSQL** | Base de datos (Relacional institucional) | Motor provisto por la universidad (RT-04) que almacena las tablas transaccionales, las reglas versionadas (ADR-007) y la tabla `EventoBitacora` de solo inserción (ADR-006). |
| **Repositorio de actas PDF** | Almacenamiento de archivos (Volumen local) | Almacén en disco institucional para preservar los PDFs oficiales generados y verificados mediante su hash SHA-256 (ADR-008). |

## 3. Justificación (Drivers y ADR)

* **EAC-02, RT-01, PA-04 y ADR-001:** Para garantizar respuesta al estudiante en menos de 3 segundos durante picos de 500 usuarios simultáneos y 0% de pérdida de postulaciones si el `SIA` tarda más de 5 segundos o cae, la `API de prácticas` abre el Circuit Breaker, guarda la postulación en `PostgreSQL` y publica el evento en el `Broker de mensajes` para que el `Worker de integración` reintente asíncronamente.
* **PA-01, EAC-01 y ADR-002:** La lógica reside en un único contenedor `API de prácticas` estructurado como monolito modular, evitando la complejidad operativa de microservicios sobre la infraestructura local (RT-04).
* **PA-03, EAC-03 y ADR-006:** La auditoría reside dentro del mismo `PostgreSQL` como tabla `EventoBitacora` Append-Only para asegurar atomicidad transaccional entre la aprobación del acta y su rastro de auditoría.
* **RT-02, PA-05, RI-01 y ADR-009:** El `Script CLI de migración` está separado de la `Aplicación web` para no contaminar la interfaz de producción con pantallas de carga que quedarían obsoletas tras el día 1.

## 4. Comportamiento

* **Flujo síncrono:** Las peticiones de los actores entran desde la `Aplicación web` hacia la `API de prácticas` por `JSON / HTTPS`, la cual opera transaccionalmente sobre `PostgreSQL`.
* **Flujo asíncrono y tolerancia a fallos:** Cuando una operación requiere notificar por correo (CU-08, Magic Links ADR-004) o cuando el `SIA` falla en CU-01, la `API de prácticas` publica un mensaje `AMQP` en el `Broker de mensajes` y responde inmediatamente al usuario. El `Worker de integración` procesa la cola y, si agota los reintentos, mueve el mensaje a una *Dead-Letter Queue* (ADR-001).

## 5. Vistas relacionadas

* **Contexto (`../contexto.md`):** Conserva exactamente los mismos cinco actores y tres sistemas externos con sus protocolos.
* **Vista de desarrollo (`03-desarrollo.md`):** Hace zoom dentro del contenedor `API de prácticas` para detallar sus módulos y capas.
* **Vista física (`04-fisica.md`):** Asigna cada uno de estos siete contenedores a su respectivo nodo y contenedor Docker en los servidores de la universidad.
* **Escenarios (`../drivers.md` y `../diagramas/secuencias/`):** Los participantes de todos los diagramas de secuencia son exactamente los contenedores de esta vista.
