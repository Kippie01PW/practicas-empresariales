# Documento de visión: Sistema de gestión de prácticas empresariales

**Integrantes:**
- Andrei Carro Flores
- Marita Costilla
- Juan José Hernández Velásquez
- Víctor Manuel Valencia Álvarez

> **Enunciado.** Actualmente la gestión para conectar a estudiantes, tutores y empresas para las prácticas se realiza por medio de un archivo Excel y correo electrónico, lo que genera retrasos, pérdidas de información y falta de comunicación transversal entre los stakeholders debido a este proceso manual y repetitivo (alrededor de 500 estudiantes por semestre y 50 tutores legales). Se requiere un sistema de software que automatice la gestión del ciclo de postulaciones, asignación de tutores, seguimiento de horas y generación del acta final en PDF.

## 1. Problema u oportunidad

Actualmente la gestión para conectar a estudiantes, tutores y empresas para las prácticas se realiza por medio de un excel y correo electrónico, lo que genera una gran cantidad de retrasos, pérdidas de información, falta de una comunicación transversal entre todos los stakeholders de negocio interesados debido a este proceso manual, repetitivo y con una inmensa cantidad de personas relacionadas con este proceso de las prácticas (alrededor de 500 estudiantes por semestre y 50 tutores legales). Esto puede ser perfectamente manejado por un sistema de software.

## 2. Objetivos de negocio

| ID | Objetivo de negocio (medible) | Atributo de calidad que implica |
|----|-------------------------------|---------------------------------|
| **OB-01** | Reducir el tiempo de la gestión de las prácticas de 50 días a un máximo de 10 días. | Desempeño (comportamiento temporal) y Eficiencia operativa |
| **OB-02** | Reducir las pérdidas de información en un 80% para los estudiantes por el uso de una hoja de excel y mensajes por correo electrónico. | Fiabilidad (integridad de la información) y Trazabilidad |
| **OB-03** | Reducir en un 90% las peticiones presenciales para las prácticas de estudiantes que las desean hacer. | Capacidad de interacción (usabilidad) y Disponibilidad |
| **OB-04** | Reducir en un 70% las consultas sobre el estado de aceptación de las prácticas. | Capacidad de interacción (autoservicio) |
| **OB-05** | Lograr que el 90% de los estudiantes completen sus prácticas y obtengan su acta de finalización. | Fiabilidad y Mantenibilidad |

## 3. Alcance

### Qué SÍ incluye

- Gestión del ciclo de las postulaciones de estudiantes.
- Conexión y asignación con alguno de los 50 tutores disponibles.
- Consideración y gestión de empresas disponibles.
- Unión y vinculación transversal entre estudiantes, tutor y empresa.
- Envío de información y notificaciones sobre el estado de la práctica.
- Seguimiento y registro de horas de práctica.
- Generación automática de un acta de finalización en PDF sobre las prácticas.

### Qué NO incluye (o no se asegura)

- No se asegura que se tengan vacantes para los estudiantes.
- No se asegura que todos los estudiantes sean aceptados por las empresas.
- No incluye la gestión de la cantidad ni los acuerdos monetarios del contrato de práctica.

## 4. Stakeholders

### Stakeholders de negocio

| Rol | Preocupaciones | Poder | Interés |
|-----|----------------|-------|---------|
| **Estudiante** | Ser informado rápido de su aceptación, fácil registro de horas y obtener su acta a tiempo. | Bajo | Alto |
| **Coordinador de prácticas** | Automatizar asignaciones, centralizar datos (eliminar excel) y agilizar la emisión de actas. | Alto | Alto |
| **Tutor** | Interfaz intuitiva, alertas automáticas de revisión y no sumar carga administrativa extra. | Medio | Alto |
| **RHH de la empresa** | Ser informado para ver su aceptación, fácil gestión con la evaluación del desempeño del estudiante. | Bajo | Medio |

### Stakeholders técnicos

| Rol | Preocupaciones | Poder | Interés |
|-----|----------------|-------|---------|
| **Arquitecto de software** | Integración segura con el sistema actual y arquitectura escalable. | Alto | Alto |
| **Administrador de base de datos** | Integridad de la información, backups y correcta migración desde excel. | Medio | Medio |
| **Responsable de seguridad** | Protección de datos y prevención de vulnerabilidades. | Alto | Alto |

## 5. Restricciones

| ID | Restricción | Tipo | Origen | Impacto arquitectónico |
|----|-------------|------|--------|------------------------|
| **RT-01** | El sistema debe de soportar los 500 alumnos y a los 50 tutores de forma simultánea. | Técnica | Visión (RT-01) | Sizing y dimensionamiento de infraestructura interna para manejar picos de concurrencia al inicio y fin de semestre. |
| **RT-02** | El sistema debe de ser capaz de soportar la migración de datos obtenidos en las hojas de cálculo de excel. | Técnica | Visión (RT-02) | Diseño de un componente de importación/ETL con reglas de validación y limpieza de datos (PA-05, RI-01). |
| **RN-01** | El sistema debe de estar propiamente en los servidores de la universidad; los datos personales deben ser tratados conforme a las leyes y reglas impuestas por la universidad. | Negocio / Legal | Visión (RN-01) | Alojamiento on-premise, cifrado de datos sensibles en tránsito (TLS) y reposo; control estricto RBAC. |
| **RN-02** | El sistema debe de cumplir de forma estricta el flujo de las prácticas empresariales para generar el acta final. | Negocio | Visión (RN-02) | Implementación de una máquina de estados finitos que impida transiciones ilegales en el proceso. |
| **RN-03** | El sistema debe de tener roles bien definidos. | Negocio | Visión (RN-03) | Mecanismo centralizado de autorización que valida permisos y pertenencia en cada endpoint/caso de uso. |

## 6. Supuestos y riesgos iniciales

### 6.1 Supuestos

| ID | Supuesto adoptado | Validar con / Implicación |
|----|-------------------|---------------------------|
| **SUP-01** | La oficina de Registro Académico o TI proporcionará una API o una vista en base de datos para validar que el estudiante cumple con los requisitos previos para matricular la práctica sin necesidad de validación manual. | Registro Académico / TI |
| **SUP-02** | Las empresas externas cuentan con acceso a internet y correo electrónico para diligenciar el formulario de evaluación del estudiante sin requerir una cuenta corporativa en el directorio activo de la universidad. | Supervisores de empresa |
| **SUP-03** | El formato del acta final de práctica y las rúbricas de evaluación de las empresas están previamente estandarizados por la Facultad de Ingenierías y no sufrirán modificaciones durante el tiempo de desarrollo. | Facultad de Ingenierías |
| **SUP-04** | La universidad proveerá los servidores de pruebas y producción con el motor de base de datos listo, sin que el equipo de desarrollo deba asumir costos de hosting o licencias de software de terceros. | Área de TI institucional |
| **SUP-05** | Las personas encargadas de la gestión de las prácticas recibirán una inducción inicial de máximo 1 hora para adoptar la nueva herramienta abandonando el uso de plantillas en Excel. | Coordinación y Tutores |

### 6.2 Riesgos iniciales

| ID | Riesgo inicial | Impacto | Probabilidad | Mitigación / Efecto |
|----|----------------|---------|--------------|---------------------|
| **RI-01** | Inconsistencia, duplicidad o formato no estructurado en las hojas de cálculo de Excel actuales, lo que puede retrasar o dificultar la migración inicial de la cohorte activa a la nueva base de datos. | Alto | Alta | Plantilla oficial estandarizada y script CLI de importación con validación previa en modo Dry Run (ADR-009). |
| **RI-02** | Que los evaluadores de las empresas externas prefieran enviar las evaluaciones escaneadas por correo en lugar de usar la plataforma web, generando reprocesos manuales para el tutor o coordinador. | Medio | Media | Esquema de enlaces criptográficos efímeros (Magic Links) por correo con acceso directo sin registro (ADR-004). |
| **RI-03** | Demoras administrativas en la asignación o configuración de los ambientes de despliegue/servidores por parte del área de TI de la universidad durante la fase final del proyecto. | Alto | Media | Empaquetamiento en contenedores Docker autogestionados y escalamiento de requerimientos desde la semana 1 (ADR-003). |
