# ADR-001: Resiliencia e integración asíncrona con Registro Académico

## Estado

Aceptado

## Contexto

Durante los picos de inicio de semestre, hasta 500 estudiantes (RT-01) intentan postularse simultáneamente (CU-01). El sistema debe validar los requisitos consumiendo la API externa del SIA (RT-03), la cual puede presentar intermitencias. Se exige confirmar al estudiante en menos de 3 segundos (95% de los casos), asegurar 0% de pérdidas de postulaciones y reintentar si el SIA falla, completando el proceso en máximo 30 minutos tras su recuperación (EAC-02). Adicionalmente, se busca estandarizar el manejo de fallos para todas las integraciones, incluyendo el correo (PA-04).

## Alternativas consideradas

- **A) Invocación síncrona bloqueante:** Se llama a la API en tiempo real y, si falla, se muestra un error al usuario.
  - *Ventaja:* Desarrollo rápido.
  - *Desventaja:* Se pierden postulaciones si el SIA cae, incumpliendo rotundamente EAC-02 y bloqueando el acceso masivo.
- **B) Cola de peticiones asíncrona con persistencia durable y reintentos (Message Broker + Worker):** La solicitud se guarda de inmediato y se despacha a una cola de mensajes persistente; un proceso en segundo plano (worker) gestiona el envío al SIA y los reintentos con retraso exponencial.
  - *Ventaja:* Desacopla la disponibilidad del SIA (RT-03) y cumple EAC-02 al 100%.
  - *Desventaja:* Introduce un componente adicional de infraestructura y complejidad en la gestión de estados.

## Decisión

Se elige la opción B porque satisface integralmente la necesidad de respuesta y tolerancia a fallos requerida por EAC-02, y proporciona un mecanismo unificado para gestionar integraciones inestables según PA-04.

## Consecuencias

### Positivas

- Cumplimiento estricto de EAC-02 (0% pérdidas, respuesta < 3s).
- Amortigua la carga de 500 solicitudes simultáneas (RT-01).
- Unifica la estrategia de resiliencia para el SIA y para notificaciones (PA-04, CU-08).

### Negativas y costos aceptados

- Introduce estados transitorios en la UI ("Pendiente de verificación").
- Aumenta la carga operativa al requerir la instalación y monitoreo de un bróker de mensajes en los servidores institucionales.

### Riesgos asumidos y sus respectivas mitigaciones

- **Acumulación masiva de mensajes si el SIA cae por varios días:** Mitigación mediante la configuración de alertas de longitud de cola y límite de reintentos derivando a una "Dead-Letter Queue" (cola de mensajes fallidos) para revisión del administrador.


## Vistas arquitectónicas afectadas

* [Vista Lógica](../vistas/01-logica.md) (`../diagramas/01-logica.puml`): Entidad `IntentoValidacion`.
* [Vista de Procesos](../vistas/02-procesos.md) (`../diagramas/02-procesos.puml`): Contenedores `Broker de mensajes` y `Worker de integración`.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): Componentes `Adaptador SIA` (con Circuit Breaker) y `Publicador de Eventos`.
* [Vista Física](../vistas/04-fisica.md) (`../diagramas/04-fisica.puml`): Contenedores Docker `broker-mensajes` y `worker-integracion`.
* [Escenario ESC-01](../diagramas/secuencias/cu01-postularse.puml): Flujo alterno ante timeout o caída del SIA.
