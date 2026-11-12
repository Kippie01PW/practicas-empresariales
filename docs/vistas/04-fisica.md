# Vista Física (Diagrama de Despliegue)

## 1. Presentación principal

* **Diagrama:** `../diagramas/04-fisica.puml`
* **Propósito:** Especifica la topología de hardware, redes, contenedores de sistema operativo y volúmenes de almacenamiento sobre la infraestructura propia de la universidad (On-Premise), evidenciando el dimensionamiento para soportar la concurrencia exigida y los controles de seguridad física y lógica.
* **Público objetivo:** Ingenieros de infraestructura (Área de TI de la universidad), Administrador de base de datos (DBA) y Responsable de seguridad.

## 2. Catálogo de elementos

| Nodo Físico / Entorno | Especificación Técnica | Contenedores C4 Alojados |
| :--- | :--- | :--- |
| **Servidor de Aplicaciones Institucional** | Máquina virtual Linux Ubuntu LTS (4 vCPU, 16 GB RAM) en el Data Center de la universidad, con Docker Engine (ADR-003). | `Aplicación web`, `API de prácticas`, `Script CLI de migración`, `Broker de mensajes`, `Worker de integración` y `Repositorio de actas PDF`. |
| **Servidor de Base de Datos Institucional** | Servidor dedicado provisto y administrado por el área de TI de la universidad (SUP-04, RT-04). | `PostgreSQL` (versión 16). |
| **Volumen de Disco Cifrado (LUKS)** | Partición local montada en el contenedor de la API con respaldos diarios automatizados. | `Repositorio de actas PDF`. |
| **Infraestructura de Servicios Universitarios** | Red interna institucional donde operan los sistemas legados y transversales de la universidad. | `SIA`, `SSO Institucional`, `Servicio de correo`. |
| **Dispositivos de Usuario (Interno y Externo)** | Equipos de cómputo o móviles desde los cuales acceden los 500 estudiantes, 50 tutores y supervisores empresariales. | `Navegador Web` (ejecuta la SPA de `Aplicación web`). |

## 3. Justificación (Drivers y ADR)

* **RT-01 (Concurrencia de 500 estudiantes y 50 tutores):** El `Servidor de Aplicaciones Institucional` se dimensiona con 4 vCPU, 16 GB de RAM y 4 procesos *worker* Uvicorn detrás de Nginx, amortiguando las ráfagas de escritura mediante la cola en el contenedor `broker-mensajes` (ADR-001).
* **RT-04, RN-01, RN-05, SUP-04, RI-03 y ADR-003:** Se descarta cualquier nube pública de pago; todos los contenedores utilizan tecnologías 100% Open Source (Linux, Docker, Nginx, FastAPI, RabbitMQ, Celery, PostgreSQL) desplegadas en servidores institucionales, mitigando las demoras de configuración de TI (RI-03) gracias al empaquetamiento estándar con Docker Compose.
* **RN-01, EAC-03 y ADR-006:** El tráfico externo entra cifrado con `TLS 1.3` (puerto 443) y las conexiones hacia `PostgreSQL` usan TLS. Además, a nivel de motor de base de datos, el usuario de la aplicación (`app_practicas`) tiene revocados los permisos `UPDATE` y `DELETE` sobre la tabla `EventoBitacora`, garantizando inmutabilidad incluso ante fallos de aplicación.

## 4. Comportamiento

* El contenedor `proxy-web` (Nginx) es el único punto expuesto en la DMZ institucional (puerto 443); sirve los archivos estáticos de la `Aplicación web` y actúa como proxy reverso hacia `api-practicas` por una red interna Docker aislada.
* El contenedor `broker-mensajes` y el `Repositorio de actas PDF` montan volúmenes persistentes del sistema anfitrión para que ningún reinicio de contenedor provoque pérdida de mensajes en cola (EAC-02) ni de actas firmadas (ADR-008).

## 5. Vistas relacionadas

* **Vista de procesos (`02-procesos.md`):** Cada uno de los siete contenedores lógicos de la vista de procesos aparece mapeado 1 a 1 dentro de un nodo de este diagrama de despliegue.
* **Contexto (`../contexto.md`):** Los tres sistemas externos (`SIA`, `SSO Institucional`, `Servicio de correo`) se conectan desde el servidor de aplicaciones a través de la red interna universitaria bajo los mismos protocolos declarados en el contexto.
