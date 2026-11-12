# ADR-002: Estilo arquitectónico de Monolito Modular con Puertos y Adaptadores

## Estado

Aceptado

## Contexto

El sistema debe orquestar distintos dominios (postulaciones, evaluaciones, actas) sujetos a cambios en reglas y formatos (SUP-03). Se exige que la incorporación de nuevas reglas o programas modifique como máximo 2 componentes sin afectar el resto (EAC-01). Asimismo, el sistema depende fuertemente de integraciones que no controla (RT-03) y se debe definir la estructura general priorizando la mantenibilidad (PA-01).

## Alternativas consideradas

- **A) Monolito tradicional en capas (Presentación, Negocios, Datos):**
  - *Ventaja:* Patrón ampliamente conocido.
  - *Desventaja:* Alto acoplamiento; cambiar el proveedor de identidad o la API del SIA impactaría la lógica central de negocio, arriesgando EAC-01.
- **B) Monolito Modular con arquitectura hexagonal (Puertos y Adaptadores):** El núcleo de negocio define puertos (interfaces) y no depende de frameworks o BD. Las dependencias apuntan hacia adentro.
  - *Ventaja:* Cumple EAC-01, aísla completamente la lógica del negocio de los detalles de infraestructura.
  - *Desventaja:* Requiere disciplina de equipo y creación de múltiples interfaces abstractas y mapeadores de objetos (DTOs).
- **C) Arquitectura de Microservicios:**
  - *Ventaja:* Despliegue independiente por dominio.
  - *Desventaja:* Sobrecarga operativa innecesaria para un volumen fijo de 550 usuarios concurrentes, violando la restricción de infraestructura limitada institucional (RT-04).

## Decisión

Se elige la opción B porque aísla el núcleo del negocio de la inestabilidad de los sistemas externos (RT-03) y garantiza la modificabilidad focalizada exigida por EAC-01 sin incurrir en la sobrecarga de infraestructura de los microservicios.

## Consecuencias

### Positivas

- Alta capacidad de prueba unitaria del dominio sin requerir levantar la base de datos o el SIA.
- Los cambios en la API del SIA solo afectan a un adaptador específico.

### Negativas y costos aceptados

- Incremento en la verbosidad del código (más interfaces, clases y traductores).
- Curva de aprendizaje inicial para desarrolladores acostumbrados a monolitos acoplados.

### Riesgos asumidos y sus respectivas mitigaciones

- **Ruptura del aislamiento por desarrolladores inyectando repositorios directamente:** Mitigación mediante el uso de herramientas de validación de arquitectura estática (ej. ArchUnit) en la integración continua (CI) que rechacen dependencias ilegales.


## Vistas arquitectónicas afectadas

* [Vista de Procesos](../vistas/02-procesos.md) (`../diagramas/02-procesos.puml`): Contenedor único `API de prácticas` como monolito modular.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): División en capas de Clean Architecture (`infraestructura`, `aplicacion`, `dominio`, `main.py`) y vista de usos sin ciclos.
