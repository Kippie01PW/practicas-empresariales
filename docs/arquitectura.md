# Documento de arquitectura: Sistema de gestión de prácticas empresariales

> Versión 1.0 | Estado: completo hasta SDD (la sección 9 conserva deuda técnica por registrar durante la implementación)

Este documento es el mapa del proyecto. Enlaza a los demás archivos y no los copia: un dato escrito en dos lugares termina diciendo dos cosas distintas. Su estructura es una adaptación de arc42.

---

## 1. Introducción y objetivos

El sistema automatiza la gestión integral del ciclo de vida de prácticas empresariales en la Universidad de Caldas, conectando a estudiantes, docentes asesores (tutores académicos), supervisores de empresa externos y a la Coordinación de Prácticas. Reemplaza el flujo manual basado en hojas de cálculo Excel y cadenas de correos electrónicos. Los cinco objetivos de negocio (OB-01 a OB-05) buscan reducir el tiempo total de gestión de 50 a 10 días, eliminar las pérdidas de información en un 80%, reducir las solicitudes presenciales en un 90%, disminuir las consultas de estado en un 70% y asegurar que el 90% de los estudiantes culminen con éxito su práctica obteniendo su acta final en PDF con firmas electrónicas.

Detalle: [Visión](vision.md)

Funcionalidades: [Catálogo de casos de uso](drivers.md#1-lista-de-casos-de-uso) (CU-01 a CU-15), cada uno enlazado a su carpeta de `specs/`:
- **Postulaciones y Asignación:** [CU-01](../specs/001-postulacion-estudiante/spec.md), [CU-02](../specs/002-aprobar-rechazar-postulacion/spec.md), [CU-03](../specs/003-asignar-docente-asesor/spec.md), CU-11.
- **Seguimiento y Horas:** [CU-04](../specs/004-registrar-horas-practica/spec.md), [CU-05](../specs/005-validar-horas-registradas/spec.md), [CU-06](../specs/006-revisar-avances-de-horas/spec.md), [CU-08](../specs/008-enviar-recordatorios-plazos/spec.md).
- **Evaluación de Desempeño:** [CU-07](../specs/007-evaluar-desempeno-del-practicante/spec.md).
- **Cierre y Actas:** CU-09, [CU-10](../specs/010-aprobar-acta-electronicamente/spec.md).
- **Configuración, Auditoría y Migración:** CU-12, CU-13, CU-14, CU-15.

---

## 2. Restricciones

Nueve restricciones arquitectónicas fundamentales (cuatro técnicas y cinco de negocio):
- **Técnicas:** Capacidad de concurrencia para 500 estudiantes y 50 tutores por semestre ([RT-01](drivers.md#3-tabla-de-restricciones)), obligatoriedad de migrar datos históricos y activos desde Excel ([RT-02](drivers.md#3-tabla-de-restricciones)), integración desacoplada con el SIA exclusivamente por API REST o vista de BD ([RT-03](drivers.md#3-tabla-de-restricciones)), y despliegue en infraestructura on-premise de la universidad con PostgreSQL y Docker ([RT-04](drivers.md#3-tabla-de-restricciones)).
- **Negocio:** Tratamiento estricto de datos personales conforme a la Ley 1581 ([RN-01](drivers.md#3-tabla-de-restricciones)), cumplimiento riguroso del flujo de estados hacia el acta ([RN-02](drivers.md#3-tabla-de-restricciones)), control y separación centralizada de roles RBAC ([RN-03](drivers.md#3-tabla-de-restricciones)), acceso a supervisores externos sin cuenta en el directorio activo institucional ([RN-04](drivers.md#3-tabla-de-restricciones)), y cero costos de licenciamiento comercial o suscripciones de pago ([RN-05](drivers.md#3-tabla-de-restricciones)).

Detalle: [Restricciones](drivers.md#3-tabla-de-restricciones)

---

## 3. Contexto del sistema

El sistema interactúa con cuatro roles de personas (Estudiante, Docente Asesor, Coordinador de Prácticas, Supervisor de Empresa) y cuatro sistemas externos institucionales (Sistema de Información Académica - SIA, Plataforma SSO OIDC, Servidor de Correo SMTP, y Repositorio de Actas PDF en volumen institucional).

Detalle: [Contexto](contexto.md)

---

## 4. Estrategia de solución

| Driver | Enfoque | ADR |
|--------|---------|-----|
| EAC-02, RT-01, RT-03, PA-04 | Verificación resiliente con SIA mediante Circuit Breaker, cola de reintentos RabbitMQ y Dead-Letter Queue | [ADR-001](adr/ADR-001-resiliencia-integracion-asincrona.md) |
| PA-01, RN-01, EAC-01 | Monolito modular con Clean Architecture y Puertos y Adaptadores; grafo acíclico de dependencias entre módulos | [ADR-002](adr/ADR-002-monolito-modular-puertos-adaptadores.md) |
| RT-01, RT-04, RN-05, PA-01 | Python 3.12, FastAPI, empaquetamiento en contenedores Docker y persistencia PostgreSQL transaccional | [ADR-003](adr/ADR-003-plataforma-tecnologica-empaquetamiento-despliegue.md) |
| PA-02, RN-04, EAC-03 | Autenticación híbrida: SSO OIDC para usuarios internos y Magic Links HMAC efímeros (15 días) para supervisores | [ADR-004](adr/ADR-004-autenticacion-hibrida-enlaces-criptograficos.md) |
| RN-01, RN-03, EAC-03 | Control de acceso RBAC centralizado en capa de aplicación con política *deny-by-default* y pertenencia contextual | [ADR-005](adr/ADR-005-rbac-casos-de-uso.md) |
| PA-03, EAC-03, RN-01 | Bitácora de auditoría transaccional de solo inserción (Append-Only) sellada con huella hash SHA-256 | [ADR-006](adr/ADR-006-bitacora-auditoria-append-only.md) |
| EAC-01, OB-05, PA-01 | Configuración declarativa de reglas de programa versionadas (horas exigidas, rúbricas y plantillas HTML) | [ADR-007](adr/ADR-007-configuracion-declarativa-reglas-versionadas.md) |
| PA-03, RN-02, OB-05 | Generación de acta final en PDF desde HTML/CSS y preservación inmutable con sellado hash SHA-256 | [ADR-008](adr/ADR-008-generacion-preservacion-acta-final.md) |
| RT-02, PA-05, OB-02 | Estrategia de migración inicial ETL de prácticas activas e históricas desde Excel vía herramienta CLI | [ADR-009](adr/ADR-009-estrategia-migracion-inicial.md) |
| RN-02, OB-01, OB-05 | Patrón Máquina de Estados Finitos en la entidad Practica para control estricto del ciclo de vida | [ADR-010](adr/ADR-010-maquina-estados-finitos.md) |

---

## 5. Vistas (4+1)

[Lógica](vistas/01-logica.md) | [Procesos](vistas/02-procesos.md) | [Desarrollo](vistas/03-desarrollo.md) | [Física](vistas/04-fisica.md)

Escenarios (+1): [diagramas/secuencias/](diagramas/secuencias/) y tabla de escenarios en [drivers.md](drivers.md#6-escenarios-1).

### Matriz de cobertura: drivers y ADR por vista

Ninguna fila vacía: todo driver y todo ADR se ven en al menos una vista.

| Driver o ADR | Contexto (marco) | Lógica | Procesos | Desarrollo | Física |
|--------------|:----------------:|:------:|:--------:|:----------:|:------:|
| CU-01 a CU-15 (Casos de uso del catálogo) | ✓ | ✓ | ✓ | ✓ | |
| EAC-01: modificación de reglas/plantillas ≤ 16h | | ✓ | | ✓ | |
| EAC-02: 0% postulaciones perdidas, respuesta < 3s | | ✓ | ✓ | | ✓ |
| EAC-03: 100% accesos no válidos rechazados, 0 datos expuestos | | ✓ | ✓ | ✓ | |
| RT-01: 500 estudiantes y 50 tutores concurrentes | | | ✓ | | ✓ |
| RT-02: migración obligatoria desde Excel | | | ✓ | ✓ | |
| RT-03: integración SIA por API REST / vista BD | ✓ | | ✓ | ✓ | |
| RT-04: infraestructura on-premise y PostgreSQL | | | ✓ | | ✓ |
| RN-01: tratamiento de datos Ley 1581 (RBAC y cifrado) | | ✓ | ✓ | ✓ | ✓ |
| RN-02: máquina de estados estricta hacia el acta | | ✓ | | ✓ | |
| RN-03: separación de roles RBAC | | ✓ | | ✓ | |
| RN-04: supervisores externos sin directorio activo | ✓ | ✓ | ✓ | ✓ | |
| RN-05: sin costos de licencias comerciales | | | ✓ | | ✓ |
| ADR-001 Resiliencia e integración asíncrona | | ✓ | ✓ | | ✓ |
| ADR-002 Monolito modular con Clean Architecture | | | ✓ | ✓ | |
| ADR-003 Plataforma tecnológica y PostgreSQL | | | ✓ | | ✓ |
| ADR-004 Autenticación híbrida | ✓ | ✓ | ✓ | ✓ | |
| ADR-005 Autorización RBAC centralizada | | ✓ | | ✓ | |
| ADR-006 Bitácora Append-Only | | ✓ | ✓ | ✓ | ✓ |
| ADR-007 Reglas declarativas versionadas | | ✓ | | ✓ | |
| ADR-008 Generación y sellado de actas PDF | | ✓ | ✓ | ✓ | ✓ |
| ADR-009 Migración inicial desde Excel | | | ✓ | ✓ | |
| ADR-010 Máquina de estados finitos | | ✓ | | ✓ | |

---

## 6. Conceptos transversales

| Concepto | Cómo se resuelve | Dónde se ve |
|----------|------------------|-------------|
| **Autenticación híbrida** | SSO OIDC para internos; enlaces Magic Links firmados con HMAC-SHA256, caducidad de 15 días y un solo uso para supervisores | [ADR-004](adr/ADR-004-autenticacion-hibrida-enlaces-criptograficos.md), [Desarrollo](vistas/03-desarrollo.md) |
| **Autorización y pertenencia** | `AutorizadorRBAC` en aplicación con política *deny-by-default* y control contextual de pertenencia de datos (RN-01) | [ADR-005](adr/ADR-005-rbac-casos-de-uso.md), [Desarrollo](vistas/03-desarrollo.md) |
| **Resiliencia e integración** | Circuit Breaker (timeout 5s) hacia el SIA; encolamiento RabbitMQ, reintentos asíncronos y Dead-Letter Queue | [ADR-001](adr/ADR-001-resiliencia-integracion-asincrona.md), [Procesos](vistas/02-procesos.md) |
| **Auditoría e inmutabilidad** | Tabla `EventoBitacora` Append-Only atómica en PostgreSQL sellada con hash SHA-256; permisos UPDATE/DELETE revocados | [ADR-006](adr/ADR-006-bitacora-auditoria-append-only.md), [Lógica](vistas/01-logica.md) |
| **Reglas versionadas** | Entidad `ReglaPrograma` con horas, rúbricas y plantilla; 0% alteración a prácticas activas ante cambios normativos | [ADR-007](adr/ADR-007-configuracion-declarativa-reglas-versionadas.md), [Lógica](vistas/01-logica.md) |
| **Preservación de actas** | Generación de PDF desde HTML/CSS, sellado SHA-256 en BD y almacenamiento en volumen cifrado local | [ADR-008](adr/ADR-008-generacion-preservacion-acta-final.md), [Física](vistas/04-fisica.md) |
| **Ciclo de vida de la práctica** | Máquina de estados finitos encapsulada en `Practica` (bloqueo estricto de transiciones no permitidas) | [ADR-010](adr/ADR-010-maquina-estados-finitos.md), [Lógica](vistas/01-logica.md) |
| **Despliegue y contenedores** | Contenedores Docker (API FastAPI, Worker Celery, RabbitMQ, Nginx) orquestados mediante Docker Compose | [ADR-003](adr/ADR-003-plataforma-tecnologica-empaquetamiento-despliegue.md), [Física](vistas/04-fisica.md) |
| **Migración de datos** | Script CLI independiente que reutiliza la lógica de negocio para validar e importar datos desde Excel | [ADR-009](adr/ADR-009-estrategia-migracion-inicial.md), [Procesos](vistas/02-procesos.md) |

---

## 7. Decisiones de diseño

| ADR | Decisión | Estado | Drivers |
|-----|----------|--------|---------|
| [ADR-001](adr/ADR-001-resiliencia-integracion-asincrona.md) | Integración asíncrona con SIA mediante Circuit Breaker y colas | Aceptado | EAC-02, RT-01, RT-03, PA-04 |
| [ADR-002](adr/ADR-002-monolito-modular-puertos-adaptadores.md) | Monolito modular con Clean Architecture y Puertos y Adaptadores | Aceptado | PA-01, RN-01, EAC-01 |
| [ADR-003](adr/ADR-003-plataforma-tecnologica-empaquetamiento-despliegue.md) | Python 3.12, FastAPI, PostgreSQL y Docker Compose On-Premise | Aceptado | RT-01, RT-04, RN-05, PA-01 |
| [ADR-004](adr/ADR-004-autenticacion-hibrida-enlaces-criptograficos.md) | SSO OIDC institucional y Magic Links HMAC efímeros (15 días) | Aceptado | PA-02, RN-04, EAC-03 |
| [ADR-005](adr/ADR-005-rbac-casos-de-uso.md) | Autorización RBAC centralizada deny-by-default a nivel de casos de uso | Aceptado | RN-01, RN-03, EAC-03 |
| [ADR-006](adr/ADR-006-bitacora-auditoria-append-only.md) | Bitácora de auditoría Append-Only en PostgreSQL con sellado SHA-256 | Aceptado | PA-03, EAC-03, RN-01 |
| [ADR-007](adr/ADR-007-configuracion-declarativa-reglas-versionadas.md) | Reglas normativas, rúbricas y plantillas declarativas versionadas | Aceptado | EAC-01, OB-05, PA-01 |
| [ADR-008](adr/ADR-008-generacion-preservacion-acta-final.md) | Renderizado HTML a PDF y preservación inmutable con hash SHA-256 | Aceptado | PA-03, RN-02, OB-05 |
| [ADR-009](adr/ADR-009-estrategia-migracion-inicial.md) | Herramienta CLI de migración ETL de prácticas activas e históricas | Aceptado | RT-02, PA-05, OB-02 |
| [ADR-010](adr/ADR-010-maquina-estados-finitos.md) | Control del ciclo de vida mediante Máquina de Estados Finitos | Aceptado | RN-02, OB-01, OB-05 |

---

## 8. Requisitos de calidad

| EAC | Atributo | Prioridad | ADR | Se verifica en |
|-----|----------|-----------|-----|----------------|
| **EAC-01** | Mantenibilidad (Modificabilidad) | Alta | ADR-002, ADR-007 | Modificación de regla/plantilla en menos de 16h-h afectando ≤ 2 componentes ([specs/012](../specs/012-configurar-reglas-programa/spec.md)) |
| **EAC-02** | Fiabilidad (Tolerancia a fallos e interoperabilidad) | Alta | ADR-001, ADR-003 | 0% postulaciones perdidas con SIA caído, confirmación < 3s ([specs/001](../specs/001-postulacion-estudiante/spec.md), escenario 5) |
| **EAC-03** | Seguridad (Confidencialidad y trazabilidad) | Alta | ADR-004, ADR-005, ADR-006 | 100% de accesos no válidos rechazados, 0 datos expuestos y registro en bitácora < 1 min ([specs/005](../specs/005-validar-horas-registradas/spec.md), [specs/007](../specs/007-evaluar-desempeno-supervisor/spec.md)) |

---

## 9. Riesgos y deuda técnica

| ID | Riesgo o deuda | Origen | Impacto | Respuesta |
|----|----------------|--------|---------|-----------|
| **R-01** | Caída prolongada del SIA en temporada alta de postulaciones | RT-03, EAC-02 | Acumulación de tareas en RabbitMQ | Circuit Breaker, worker con reintentos exponenciales y alertas a TI al superar umbral |
| **R-02** | Supervisor de empresa no responde la evaluación en los plazos fijados | CU-07, RI-02 | Bloqueo en la generación del acta final (OB-01, OB-05) | Tareas programadas de recordatorios automáticos (CU-08) y reenvío de Magic Links |
| **R-03** | Datos inconsistentes, duplicados o con formatos corruptos en los Excel legados | RT-02, PA-05 | Corrupción en la base de datos al importar | Script CLI con etapa de validación previa (dry-run) que reporta inconsistencias sin escribir (ADR-009) |
| **R-04** | Tutor que supera el límite de 10 prácticas asignadas por sobreasignación manual | RT-01, CU-03 | Sobrecarga docente y retraso en revisiones | Invariante estricto en la entidad `DocenteAsesor` que bloquea asignaciones adicionales |
| **DT-01** | Uso de adaptadores en memoria durante las fases tempranas de SDD | Fases iniciales | No hay persistencia duradera en disco hasta montar PostgreSQL | Repositorios diseñados bajo puertos (`Protocol`) para intercambio transparente por adaptadores SQLAlchemy/PostgreSQL |
| **DT-02** | Generación de actas PDF huérfanas si ocurre un fallo entre el renderizado y la escritura en base de datos | ADR-008 | Inconsistencia entre el volumen local de archivos y PostgreSQL | Transacción compensatoria o proceso periódico de conciliación de huellas hash SHA-256 |
| **DT-03** | Dependencia del worker asíncrono para el despacho de correos | ADR-001 | Retrasos en la notificación si RabbitMQ se detiene | Persistencia de mensajes en disco y monitoreo operativo de colas |
| **DT-04** | Prácticas importadas desde Excel que carecen de fecha de inicio formal | ADR-009 | Estado ambiguo en la máquina de estados | La migración asigna el estado formal según los hitos completados registrados en la planilla |

---

## 10. Glosario

| Término | Definición | Nombre en el código |
|---------|------------|---------------------|
| **Práctica** | Agregado raíz que representa la práctica empresarial de un estudiante, vinculando empresa, tutor y reglas. | `Practica` |
| **Estado de Práctica** | Estado formal del ciclo de vida: `PendienteVerificacion`, `Solicitada`, `Aprobada`, `Asignada`, `EnEjecucion`, `Evaluada`, `Completada`, `Rechazada`. | `EstadoPractica` |
| **Estudiante** | Estudiante regular matriculado que postula y realiza su práctica empresarial. | `Estudiante` |
| **Docente Asesor** | Docente universitario asignado como tutor académico (máximo 10 prácticas activas). | `DocenteAsesor` |
| **Supervisor de Empresa** | Jefe inmediato externo responsable de validar horas y calificar el desempeño del practicante. | `SupervisorEmpresa` |
| **Coordinador de Prácticas** | Funcionario universitario que aprueba postulaciones, asigna tutores y firma actas finales. | `RolUsuario.COORDINADOR_PRACTICAS` |
| **Regla de Programa** | Configuración declarativa versionada con horas exigidas (ej. 320h), rúbrica y plantilla HTML del acta. | `ReglaPrograma` |
| **Registro de Horas** | Reporte semanal de horas (1 a 60h) y actividades registrado por el estudiante y evaluado por el supervisor. | `RegistroHoras` |
| **Estado de Validación** | Estado del reporte semanal de horas: `Pendiente`, `Aprobado` o `Rechazado`. | `EstadoValidacionHoras` |
| **Token de Evaluación** | Credencial criptográfica efímera (Magic Link HMAC-SHA256) de un solo uso y vigencia de 15 días. | `TokenEvaluacion` |
| **Evaluación de Desempeño** | Calificación cualitativa y cuantitativa asentada por el supervisor de empresa según la rúbrica vigente. | `EvaluacionDesempeno` |
| **Acta Final** | Documento oficial de culminación renderizado en PDF con firmas electrónicas y sellado SHA-256. | `ActaFinal` |
| **Intento de Validación** | Registro de auditoría por cada consulta frente al SIA para control del Circuit Breaker y trazabilidad. | `IntentoValidacion` |
| **Evento de Bitácora** | Registro inmutable transaccional (Append-Only) de acciones auditables, cambios de estado y rechazos. | `EventoBitacora` |
