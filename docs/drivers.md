# Drivers arquitectónicos: Sistema de prácticas empresariales

**Integrantes:**
- Andrei Carro Flores
- Marita Costilla
- Juan José Hernández Velásquez
- Víctor Manuel Valencia Álvarez

> **Enunciado.** Partiendo del [Documento de visión](vision.md), se extraen los drivers que moldean la arquitectura del sistema de gestión de prácticas empresariales: casos de uso primarios, escenarios de atributos de calidad, restricciones técnicas y de negocio, preocupaciones arquitectónicas y la matriz de priorización.

## 1. Lista de casos de uso

| ID | Caso de uso | Actor | ¿Primario? | Justificación y trazabilidad al Doc. de Visión |
|----|-------------|-------|------------|------------------------------------------------|
| **CU-01** | Postulación de estudiante a la práctica | Estudiante | Sí | **(2) Complejidad técnica:** Verifica automáticamente los requisitos académicos invocando la API de Registro Académico (SUP-01, OB-03). |
| **CU-02** | Aprobar o rechazar postulación | Coordinador de prácticas | No | Evaluación administrativa basada en las validaciones previas de CU-01. |
| **CU-03** | Asignar docente asesor / tutor | Coordinador de prácticas | No | Asignación directa consultando la carga actual de los 50 tutores disponibles. |
| **CU-04** | Registrar horas de práctica semanales | Estudiante | No | Formulario transaccional de alta frecuencia (500 estudiantes, RT-01), pero de baja complejidad. |
| **CU-05** | Validar horas registradas | Supervisor de empresa | No | Aprobación rápida reutilizando la infraestructura de acceso por enlace seguro. |
| **CU-06** | Revisar avances de horas | Docente asesor | No | Consulta de lecturas sobre los acumulados de horas validados. |
| **CU-07** | Evaluar desempeño del practicante | Supervisor de empresa | Sí | **(4) Riesgo:** Depende de un actor externo sin cuenta corporativa (SUP-02, RI-02); si no responde en el plazo, bloquea la generación del acta (OB-01, OB-05). |
| **CU-08** | Enviar recordatorios de plazos | Sistema (Tarea programada) | No | Notificaciones automáticas por correo para mitigar retrasos y cumplir el objetivo de 10 días (OB-01). |
| **CU-09** | Generar acta final de la práctica | Sistema / Docente | Sí | **(1) Importancia de negocio:** Entregable oficial en PDF que formaliza la culminación de la práctica (OB-01, OB-05, RN-02). |
| **CU-10** | Aprobar el acta electrónicamente | Docente y Coordinador | Sí | **(5) Atado a atributo crítico:** Seguridad, trazabilidad e inmutabilidad legal de las firmas sobre el acta final. |
| **CU-11** | Consultar estado del trámite | Estudiante | No | Consulta de autoservicio que reduce en un 70% las solicitudes de información (OB-04). |
| **CU-12** | Configurar reglas y plantillas por programa | Coordinador de prácticas | Sí | **(5) Atado a atributo crítico:** Mantenibilidad. Permite ajustar rúbricas y formatos del acta sin modificar el código fuente (SUP-03). |
| **CU-13** | Monitorear estado general de prácticas | Coordinador de prácticas | No | Tablero de control centralizado para eliminar el uso de archivos manuales (OB-02). |
| **CU-14** | Generar consolidados para auditoría | Coordinador de prácticas | No | Exportación de datos históricos con fines de acreditación académica. |
| **CU-15** | Migrar prácticas en curso desde Excel | DBA / Administrador | No | Proceso ETL ejecutado una única vez en el despliegue inicial (RT-02, RI-01). |

---

## 2. Escenarios de atributos de calidad

### EAC-01: Mantenibilidad (Modificabilidad)

| Parte | Pregunta | Contenido |
|-------|----------|-----------|
| **1. Fuente del estímulo** | ¿Quién o qué lo provoca? | Coordinador de prácticas o Decanatura |
| **2. Estímulo** | ¿Qué ocurre? | Solicita cambiar la estructura, criterios de evaluación o formato visual del acta final en PDF (SUP-03) |
| **3. Artefacto** | ¿Sobre qué parte? | Módulo de reglas de práctica y motor de plantillas de actas |
| **4. Entorno** | ¿En qué condiciones? | Tiempo de mantenimiento, con el sistema desplegado en producción y prácticas activas |
| **5. Respuesta** | ¿Qué debe hacer el sistema? | El desarrollador actualiza la plantilla y reglas de configuración sin modificar la lógica de negocio ni la estructura de la base de datos |
| **6. Medida de respuesta** | ¿Cómo se verifica? | **Modificación completada y desplegada en menos de 16 horas-hombre, afectando como máximo 2 componentes y con 0% de alteración en actas emitidas previamente** |

**Escenario redactado.** El Coordinador de prácticas o Decanatura solicita cambiar la estructura, criterios de evaluación o formato visual del acta final en PDF en tiempo de mantenimiento (con el sistema desplegado en producción y prácticas activas). El desarrollador actualiza la plantilla y reglas de configuración en el módulo de reglas de práctica y motor de plantillas de actas sin modificar la lógica de negocio ni la estructura de la base de datos, completando y desplegando el cambio en menos de 16 horas-hombre, afectando como máximo 2 componentes y con 0% de alteración en actas emitidas previamente.

**Trazabilidad:** OB-05, SUP-03, RN-02, CU-12.

---

### EAC-02: Fiabilidad (Tolerancia a fallos e interoperabilidad)

| Parte | Pregunta | Contenido |
|-------|----------|-----------|
| **1. Fuente del estímulo** | ¿Quién o qué lo provoca? | Servicio Web / API de Registro Académico (SUP-01) |
| **2. Estímulo** | ¿Qué ocurre? | La API externa no responde (timeout > 5s) o arroja error durante el registro masivo de postulaciones |
| **3. Artefacto** | ¿Sobre qué parte? | Adaptador de integración con Registro Académico en CU-01 |
| **4. Entorno** | ¿En qué condiciones? | Pico de carga al inicio del semestre (hasta 500 estudiantes concurrentes, RT-01) |
| **5. Respuesta** | ¿Qué debe hacer el sistema? | El sistema activa un patrón Circuit Breaker, almacena la postulación en estado "Pendiente de verificación", confirma al estudiante en pantalla y reintenta la validación de forma asíncrona |
| **6. Medida de respuesta** | ¿Cómo se verifica? | **0% de postulaciones perdidas, tiempo de respuesta al estudiante menor a 3 segundos (en el 95% de casos) y verificación finalizada en menos de 30 minutos tras el restablecimiento del servicio** |

**Escenario redactado.** Durante el pico de carga al inicio del semestre con hasta 500 estudiantes concurrentes, la API externa de Registro Académico no responde (timeout > 5s) o arroja error durante el registro de postulaciones. El adaptador de integración activa un patrón Circuit Breaker, almacena la postulación en estado "Pendiente de verificación", confirma al estudiante en pantalla en menos de 3 segundos (en el 95% de casos) asegurando 0% de postulaciones perdidas, y finaliza la verificación de forma asíncrona en menos de 30 minutos tras el restablecimiento del servicio de Registro Académico.

**Trazabilidad:** OB-03, RT-01, SUP-01, CU-01.

---

### EAC-03: Seguridad (Confidencialidad y Trazabilidad)

| Parte | Pregunta | Contenido |
|-------|----------|-----------|
| **1. Fuente del estímulo** | ¿Quién o qué lo provoca? | Usuario no autorizado o tercero ajeno a la empresa evaluadora |
| **2. Estímulo** | ¿Qué ocurre? | Intenta acceder a un formulario de evaluación o validación mediante un enlace alterado, reenviado o con más de 15 días de emisión |
| **3. Artefacto** | ¿Sobre qué parte? | Componente de autenticación tokenizada sin cuenta previa (SUP-02) |
| **4. Entorno** | ¿En qué condiciones? | Operación normal en producción |
| **5. Respuesta** | ¿Qué debe hacer el sistema? | El sistema deniega el acceso, oculta cualquier información del estudiante y registra el evento en la bitácora de auditoría |
| **6. Medida de respuesta** | ¿Cómo se verifica? | **100% de accesos no válidos rechazados, 0 datos expuestos y registro inmediato en la bitácora de seguridad (con IP, fecha y hora) en menos de 1 minuto** |

**Escenario redactado.** En operación normal en producción, un usuario no autorizado o tercero ajeno intenta acceder a un formulario de evaluación o validación mediante un enlace alterado, reenviado o con más de 15 días de emisión. El componente de autenticación tokenizada deniega el acceso, oculta cualquier información del estudiante y registra de inmediato el evento en la bitácora de auditoría (con IP, fecha y hora en menos de 1 minuto), logrando el 100% de accesos no válidos rechazados y 0 datos expuestos.

**Trazabilidad:** RN-01, SUP-02, RI-02, CU-05, CU-07.

---

## 3. Tabla de restricciones

| ID | Restricción | Tipo | Origen | Impacto arquitectónico esperado |
|----|-------------|------|--------|---------------------------------|
| **RT-01** | Soporte de carga simultánea de 500 estudiantes y 50 tutores. | Técnica | Visión (RT-01) | Sizing de infraestructura interna para manejar concurrencia en picos de inicio y fin de semestre. |
| **RT-02** | Obligatoriedad de migrar datos almacenados en hojas de cálculo Excel. | Técnica | Visión (RT-02) | Diseño de un componente de importación/ETL con reglas de validación y limpieza de datos (PA-05, RI-01). |
| **RT-03** | Integración exclusiva con Registro Académico a través de API o vista de BD. | Técnica | Visión (SUP-01) | Implementación de un patrón de arquitectura hexagonal (puertos y adaptadores) para desacoplar el sistema del SIA. |
| **RT-04** | Despliegue en infraestructura propia y uso de motores de BD provistos por la universidad. | Técnica | Visión (RN-01, SUP-04) | Descarta servicios cloud administrados (serverless, PaaS comercial). Requiere empaquetamiento en contenedores o servidores locales. |
| **RN-01** | Tratamiento de datos personales conforme a las leyes y políticas institucionales. | Negocio / Legal | Visión (RN-01) | Cifrado de datos sensibles en tránsito (TLS) y reposo; control estricto de acceso basado en roles (RBAC). |
| **RN-02** | Cumplimiento estricto del flujo de estados para la emisión del acta final. | Negocio | Visión (RN-02) | Implementación de una máquina de estados finitos que impida saltar pasos en el proceso. |
| **RN-03** | Separación y control estricto de roles de usuario. | Negocio | Visión (RN-03) | Mecanismo centralizado de autorización que valida permisos en cada endpoint de la aplicación. |
| **RN-04** | Permitir acceso a supervisores externos sin cuenta en el directorio activo de la universidad. | Negocio | Visión (SUP-02) | Creación de un esquema de tokens temporales de un solo uso con caducidad por correo electrónico. |
| **RN-05** | No incurrir en costos de licencias de terceros ni servicios de suscripción de pago. | Negocio | Visión (SUP-04) | Requisito de selección de software basado en tecnologías open source y componentes propios. |

---

## 4. Preocupaciones arquitectónicas

| ID | Preocupación | Justificación arquitectónica |
|----|--------------|------------------------------|
| **PA-01** | Estructura general y modularidad | Con un volumen medio (500 usuarios) y reglas de negocio cambiantes (SUP-03), se opta por un monolito modular con capas claramente separadas para priorizar la Mantenibilidad sin añadir la complejidad operativa de microservicios. |
| **PA-02** | Gestión de autenticación y accesos híbridos | Convivencia de dos esquemas de seguridad: SSO institucional para usuarios internos (Estudiante, Coordinador, Tutor) y tokens firmados sin contraseña para supervisores externos (SUP-02). |
| **PA-03** | Trazabilidad y no repudio del acta final | Garantizar la inmutabilidad y auditoría de la aprobación del acta (CU-10, OB-05) registrando huellas digitales, fechas y responsables del flujo. |
| **PA-04** | Estrategia de resiliencia en integraciones externas | Definir un manejo unificado de fallas ante caídas de la API de Registro Académico o la pasarela de correos, evitando la inconsistencia de datos (SUP-01, EAC-02). |
| **PA-05** | Proceso de migración y depuración de datos desde Excel | Diseñar una estrategia de validación previa que maneje la inconsistencia o duplicidad en las hojas de cálculo actuales sin corromper la nueva base de datos (RT-02, RI-01). |

---

## 5. Matriz de priorización

| Importancia / Dificultad | Alta Dificultad Técnica | Baja Dificultad Técnica |
|---|---|---|
| **Alta Importancia para el Negocio** | **Atender primero (Zona de riesgo):**<br>- CU-01<br>- CU-12<br>- EAC-01<br>- EAC-02<br>- RT-01<br>- RT-03<br>- PA-02 | **Hacer ya (Valor rápido):**<br>- CU-07<br>- CU-09<br>- CU-10<br>- EAC-03<br>- RN-01<br>- RN-02<br>- RN-03<br>- RN-04<br>- PA-01<br>- PA-03<br>- PA-04 |
| **Baja Importancia para el Negocio** | **Cuestionar o reevaluar:**<br>- RT-02<br>- PA-05 | **Hacer si sobra tiempo:**<br>- RT-04<br>- RN-05 |

### Detalle por cuadrante

#### 1. Alta importancia, alta dificultad: Atender primero (Zona de riesgo)
- **CU-01**: Postulación de estudiante a la práctica.
- **CU-12**: Configurar reglas y plantillas por programa.
- **EAC-01**: Mantenibilidad (Modificabilidad de plantillas y reglas).
- **EAC-02**: Fiabilidad (Tolerancia a fallos e interoperabilidad con Registro Académico).
- **RT-01**: Soporte de carga concurrente (500 estudiantes, 50 tutores).
- **RT-03**: Integración desacoplada con Registro Académico.
- **PA-02**: Gestión de autenticación y accesos híbridos.

#### 2. Alta importancia, baja dificultad: Hacer ya (Valor rápido)
- **CU-07**: Evaluar desempeño del practicante por supervisor externo.
- **CU-09**: Generar acta final de la práctica en PDF.
- **CU-10**: Aprobar el acta electrónicamente con firmas docentes y coordinador.
- **EAC-03**: Seguridad (Confidencialidad y trazabilidad de accesos).
- **RN-01**: Tratamiento de datos personales y alojamiento on-premise.
- **RN-02**: Cumplimiento estricto del flujo de estados hacia el acta.
- **RN-03**: Separación y control estricto de roles de usuario.
- **RN-04**: Acceso a supervisores externos sin credenciales institucionales.
- **PA-01**: Estructura general como monolito modular.
- **PA-03**: Trazabilidad y no repudio del acta final.
- **PA-04**: Estrategia de resiliencia en integraciones externas.

#### 3. Baja importancia, baja dificultad: Hacer si sobra tiempo
- **RT-04**: Despliegue en servidores y BD de la universidad.
- **RN-05**: Uso exclusivo de software libre / Open Source.

#### 4. Baja importancia, alta dificultad: Cuestionar o reevaluar
- **RT-02**: Obligatoriedad de migrar datos de hojas de Excel heterogéneas.
- **PA-05**: Proceso de migración y depuración de datos desde Excel.


---

## 6. Escenarios (+1)

Inventario de escenarios que se diagraman. Cada escenario cubre al menos un caso de uso primario y evidencia uno o más EAC/ADR.

| ID | Escenario | Origen | Por qué es escenario | Archivo en secuencias/ |
|----|-----------|--------|----------------------|------------------------|
| **ESC-01** | Postulación de estudiante a la práctica | CU-01 y EAC-02 | Caso de uso primario de complejidad técnica (integración con SIA, RT-03). Evidencia ADR-001 y EAC-02: cuando el SIA no responde en 5 s, se encola asíncronamente, responde al estudiante en menos de 3 s y no se pierde ninguna postulación bajo carga de 500 usuarios (RT-01). | [cu01-postularse.puml](diagramas/secuencias/cu01-postularse.puml) |
| **ESC-02** | Evaluar desempeño del practicante | CU-07 y EAC-03 | Caso de uso primario de alto riesgo (actor externo sin cuenta corporativa, RN-04, SUP-02). Evidencia ADR-004, ADR-006 y EAC-03: acceso mediante enlace criptográfico efímero y rechazo inmediato con registro en bitácora (< 1 min) si el enlace fue alterado o tiene más de 15 días. | [cu07-evaluar-desempeno.puml](diagramas/secuencias/cu07-evaluar-desempeno.puml) |
| **ESC-03** | Generar acta final de la práctica | CU-09 | Caso de uso primario de importancia de negocio (OB-01, OB-05, RN-02). Evidencia ADR-008 y ADR-010: validación de la máquina de estados, renderizado dinámico desde la plantilla HTML/CSS de la ReglaPrograma vinculada y sellado con hash SHA-256. | [cu09-generar-acta.puml](diagramas/secuencias/cu09-generar-acta.puml) |
| **ESC-04** | Aprobar el acta electrónicamente | CU-10 y EAC-03 | Caso de uso primario atado a seguridad y no repudio legal (PA-03, RN-02, RN-03). Evidencia ADR-005, ADR-006 y ADR-010: control RBAC estricto para Docente asesor y Coordinador de prácticas, verificación de integridad SHA-256 y escritura atómica Append-Only en bitácora. | [cu10-aprobar-acta.puml](diagramas/secuencias/cu10-aprobar-acta.puml) |
| **ESC-05** | Configurar reglas y plantillas por programa | CU-12 y EAC-01 | Caso de uso primario atado a mantenibilidad (SUP-03). Evidencia ADR-007 y EAC-01: actualización declarativa de una nueva versión de regla/plantilla en caliente sin alterar el código fuente ni afectar las prácticas activas o actas emitidas previamente (0% alteración). | [cu12-configurar-reglas.puml](diagramas/secuencias/cu12-configurar-reglas.puml) |

Los tres EAC quedan cubiertos: EAC-02 en ESC-01, EAC-03 en ESC-02 y ESC-04, y EAC-01 en ESC-05. No queda ningún EAC huérfano.

---

## 7. Recorrido de validación por las vistas

Cada escenario recorre las 4 vistas del modelo 4+1 sin elementos faltantes:

| Escenario | Elementos tocados en Contexto | Elementos tocados en Vista Lógica | Elementos tocados en Vista de Procesos | Elementos tocados en Vista de Desarrollo | Elementos tocados en Vista Física |
|-----------|-------------------------------|-----------------------------------|----------------------------------------|------------------------------------------|-----------------------------------|
| **ESC-01** (cu01-postularse.puml) | Estudiante, SSO Institucional, SIA, Servicio de correo. | Estudiante, Practica, ReglaPrograma, IntentoValidacion, EventoBitacora. | Aplicación web, API de prácticas, PostgreSQL, Broker de mensajes, Worker de integración. | Controlador REST, Interceptor de Identidad, Autorizador RBAC, Módulo Postulaciones, Módulo Reglas, Adaptador SIA, Publicador de Eventos, Adaptador PostgreSQL. | Dispositivo de Usuario Interno, Servidor de Aplicaciones Institucional (dk_web, dk_api, dk_broker, dk_worker), Servidor de Base de Datos Institucional. |
| **ESC-02** (cu07-evaluar-desempeno.puml) | Supervisor de empresa, Servicio de correo. | SupervisorEmpresa, TokenEvaluacion, Practica, ReglaPrograma, EvaluacionDesempeno, EventoBitacora. | Aplicación web, API de prácticas, PostgreSQL, Broker de mensajes, Worker de integración. | Controlador REST, Interceptor de Identidad, Módulo Seguimiento y Evaluación, Adaptador PostgreSQL, Publicador de Eventos. | Dispositivo de Supervisor Externo, Servidor de Aplicaciones Institucional (dk_web, dk_api, dk_broker, dk_worker), Servidor de Base de Datos Institucional. |
| **ESC-03** (cu09-generar-acta.puml) | Docente asesor, SSO Institucional. | DocenteAsesor, Practica, ReglaPrograma, RegistroHoras, EvaluacionDesempeno, ActaFinal, EventoBitacora. | Aplicación web, API de prácticas, PostgreSQL, Repositorio de actas PDF. | Controlador REST, Interceptor de Identidad, Autorizador RBAC, Módulo Actas, Módulo Seguimiento y Evaluación, Módulo Reglas, Adaptador PDF y Hash, Adaptador PostgreSQL. | Dispositivo de Usuario Interno, Servidor de Aplicaciones Institucional (dk_web, dk_api, vol_pdf), Servidor de Base de Datos Institucional. |
| **ESC-04** (cu10-aprobar-acta.puml) | Docente asesor, Coordinador de prácticas, SSO Institucional, Servicio de correo. | DocenteAsesor, Practica, ActaFinal, EventoBitacora. | Aplicación web, API de prácticas, PostgreSQL, Repositorio de actas PDF, Broker de mensajes, Worker de integración. | Controlador REST, Interceptor de Identidad, Autorizador RBAC, Módulo Actas, Adaptador PDF y Hash, Adaptador PostgreSQL, Publicador de Eventos. | Dispositivo de Usuario Interno, Servidor de Aplicaciones Institucional (dk_web, dk_api, vol_pdf, dk_broker, dk_worker), Servidor de Base de Datos Institucional. |
| **ESC-05** (cu12-configurar-reglas.puml) | Coordinador de prácticas, SSO Institucional. | ReglaPrograma, EventoBitacora. | Aplicación web, API de prácticas, PostgreSQL. | Controlador REST, Interceptor de Identidad, Autorizador RBAC, Módulo Reglas, Adaptador PDF y Hash, Adaptador PostgreSQL. | Dispositivo de Usuario Interno, Servidor de Aplicaciones Institucional (dk_web, dk_api), Servidor de Base de Datos Institucional. |

---

## 8. Matriz de cobertura de drivers y ADR por vista

| Driver / ADR | Contexto (contexto.puml) | Vista Lógica (01-logica.puml) | Vista de Procesos (02-procesos.puml) | Vista de Desarrollo (03-desarrollo.puml) | Vista Física (04-fisica.puml) | Escenarios +1 (secuencias/) |
|---|---|---|---|---|---|---|
| **CU-01** (Postulación estudiante) | X | X (Practica, IntentoValidacion) | X (API de prácticas, Broker de mensajes) | X (Módulo Postulaciones, Adaptador SIA) | X | X (cu01-postularse.puml) |
| **CU-07** (Evaluar desempeño externo) | X | X (EvaluacionDesempeno, TokenEvaluacion) | X (Aplicación web, API de prácticas) | X (Módulo Seguimiento y Evaluación) | X | X (cu07-evaluar-desempeno.puml) |
| **CU-09** (Generar acta final PDF) | | X (ActaFinal) | X (API de prácticas, Repositorio de actas PDF) | X (Módulo Actas, Adaptador PDF y Hash) | X | X (cu09-generar-acta.puml) |
| **CU-10** (Aprobar acta electrónicamente) | X | X (ActaFinal, EventoBitacora) | X (API de prácticas, PostgreSQL) | X (Módulo Actas, Autorizador RBAC) | X | X (cu10-aprobar-acta.puml) |
| **CU-12** (Configurar reglas por programa) | X | X (ReglaPrograma) | X (API de prácticas, PostgreSQL) | X (Módulo Reglas) | | X (cu12-configurar-reglas.puml) |
| **EAC-01** (Mantenibilidad < 16h, máx 2 comp.) | | X (ReglaPrograma) | | X (Módulo Reglas, Adaptador PDF y Hash) | | X (cu12-configurar-reglas.puml) |
| **EAC-02** (Fiabilidad y resiliencia ante caída SIA) | X | X (IntentoValidacion) | X (Broker de mensajes, Worker de integración) | X (Adaptador SIA, Publicador de Eventos) | X | X (cu01-postularse.puml) |
| **EAC-03** (Seguridad, rechazo enlaces > 15d y bitácora) | X | X (TokenEvaluacion, EventoBitacora) | X (API de prácticas, PostgreSQL) | X (Interceptor de Identidad, Autorizador RBAC) | X | X (cu07-evaluar-desempeno.puml) |
| **RT-01** (500 estudiantes y 50 tutores simultáneos) | | | X (Broker de mensajes) | | X (4 vCPU, 16 GB RAM, 4 workers) | X (cu01-postularse.puml) |
| **RT-02 / PA-05** (Migración desde Excel) | X | | X (Script CLI de migración) | X (Módulo Postulaciones) | X (c_cli) | |
| **RT-03 / PA-04** (Integración desacoplada SIA) | X | X (IntentoValidacion) | X (Worker de integración) | X (Puertos de Salida, Adaptador SIA) | X | X (cu01-postularse.puml) |
| **RT-04 / RN-01 / RN-05** (On-Premise, Ley 1581, Open Source) | | | X (PostgreSQL) | X (Autorizador RBAC) | X (Data Center Univ., Docker, TLS 1.3, LUKS) | |
| **RN-02** (Flujo estricto para emitir acta) | | X (Practica.estadoActual) | | X (Núcleo de Dominio - State Machine) | | X (cu09-generar-acta.puml) |
| **RN-03 / PA-02** (Separación de roles y acceso híbrido) | X | X (TokenEvaluacion) | X (SSO Institucional) | X (Interceptor de Identidad, Autorizador RBAC) | X | X (cu07-evaluar-desempeno.puml, cu10-aprobar-acta.puml) |
| **RN-04** (Supervisores sin cuenta en directorio activo) | X | X (TokenEvaluacion) | X (Servicio de correo) | X (Interceptor de Identidad) | X | X (cu07-evaluar-desempeno.puml) |
| **[ADR-001](adr/ADR-001-resiliencia-integracion-asincrona.md)** (Cola asíncrona + Worker para SIA/Correo) | | X (IntentoValidacion) | X (Broker de mensajes, Worker de integración) | X (Adaptador SIA, Publicador de Eventos) | X (dk_broker, dk_worker) | X (cu01-postularse.puml) |
| **[ADR-002](adr/ADR-002-monolito-modular-puertos-adaptadores.md)** (Monolito modular + Puertos y Adaptadores) | | | X (API de prácticas) | X (Capas Clean Architecture y vista de usos) | X (dk_api) | |
| **[ADR-003](adr/ADR-003-plataforma-tecnologica-empaquetamiento-despliegue.md)** (Despliegue On-Premise con Docker Open Source) | | | | | X (Servidor de Aplicaciones Institucional + Docker) | |
| **[ADR-004](adr/ADR-004-autenticacion-hibrida-enlaces-criptograficos.md)** (Autenticación híbrida SSO + Magic Links) | X | X (TokenEvaluacion) | X (SSO Institucional, Servicio de correo) | X (Interceptor de Identidad) | X | X (cu07-evaluar-desempeno.puml) |
| **[ADR-005](adr/ADR-005-rbac-casos-de-uso.md)** (RBAC centralizado en capa de Aplicación) | | | | X (Autorizador RBAC) | | X (cu10-aprobar-acta.puml, cu12-configurar-reglas.puml) |
| **[ADR-006](adr/ADR-006-bitacora-auditoria-append-only.md)** (Bitácora transaccional Append-Only) | | X (EventoBitacora) | X (PostgreSQL) | X (Adaptador PostgreSQL) | X (Permisos SQL INSERT en PostgreSQL) | X (cu07-evaluar-desempeno.puml, cu10-aprobar-acta.puml) |
| **[ADR-007](adr/ADR-007-configuracion-declarativa-reglas-versionadas.md)** (Reglas declarativas versionadas por programa) | | X (ReglaPrograma) | X (PostgreSQL) | X (Módulo Reglas) | | X (cu12-configurar-reglas.puml) |
| **[ADR-008](adr/ADR-008-generacion-preservacion-acta-final.md)** (Acta PDF desde plantilla HTML + Hash SHA-256) | | X (ActaFinal) | X (Repositorio de actas PDF) | X (Módulo Actas, Adaptador PDF y Hash) | X (vol_pdf) | X (cu09-generar-acta.puml, cu10-aprobar-acta.puml) |
| **[ADR-009](adr/ADR-009-estrategia-migracion-inicial.md)** (Migración inicial vía plantilla Excel y CLI) | X (Administrador DBA) | | X (Script CLI de migración) | X (Módulo Postulaciones) | X (c_cli) | |
| **[ADR-010](adr/ADR-010-maquina-estados-finitos.md)** (Máquina de Estados Finitos en entidad Practica) | | X (Practica) | | X (Núcleo de Dominio) | | X (cu09-generar-acta.puml, cu10-aprobar-acta.puml) |
