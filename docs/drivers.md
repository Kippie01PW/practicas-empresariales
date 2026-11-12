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
