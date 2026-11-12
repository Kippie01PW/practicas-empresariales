# ADR-003: Plataforma tecnológica y empaquetamiento de despliegue On-Premise

## Estado

Aceptado

## Contexto

Por políticas universitarias (RN-01), los datos deben residir en servidores propios y usar motores de bases de datos del catálogo institucional (RT-04, SUP-04). Está estrictamente prohibido incurrir en costos de licenciamiento de terceros o suscripciones en la nube (RN-05). Se requiere empaquetar la solución para que el área de TI la despliegue fácilmente a tiempo (RI-03).

## Alternativas consideradas

- **A) Servicios gestionados en Nube Pública (PaaS / Serverless AWS/Azure):**
  - *Ventaja:* Escalado automático para los picos de inicio de semestre.
  - *Desventaja:* Totalmente incompatible con RT-04 y RN-05.
- **B) Despliegue tradicional directo sobre Sistema Operativo:**
  - *Ventaja:* Uso nativo de los recursos del servidor local.
  - *Desventaja:* Dependencia de versiones específicas de librerías en el servidor, aumentando el riesgo de demoras por TI (RI-03) y diferencias entre entornos.
- **C) Contenedores autogestionados (Docker) con software Open Source:** La aplicación y sus dependencias se empaquetan en contenedores libres de costo, conectándose a la BD local provista por TI.
  - *Ventaja:* Cumple RT-04 y RN-05, elimina el "funciona en mi máquina" y agiliza el despliegue de TI (RI-03).
  - *Desventaja:* Requiere que la infraestructura de TI soporte ejecución de contenedores.

## Decisión

Se elige la opción C porque respeta las restricciones presupuestales (RN-05) y de infraestructura (RT-04) mientras minimiza el riesgo de fricción y demoras operativas (RI-03) al entregar artefactos portables.

## Consecuencias

### Positivas

- Eliminación completa de costos de licenciamiento (RN-05).
- Homologación idéntica entre entornos de desarrollo, pruebas y producción.

### Negativas y costos aceptados

- La escalabilidad queda limitada a los recursos de hardware físicos asignados por la universidad.

### Riesgos asumidos y sus respectivas mitigaciones

- **El equipo de TI institucional no soporta Docker de forma nativa:** Mitigación mediante el escalamiento del requerimiento técnico en la semana 1 del proyecto y provisión de documentación de despliegue directo alternativo en caso de ser rechazado.
