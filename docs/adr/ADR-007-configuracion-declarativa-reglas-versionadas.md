# ADR-007: Configuración declarativa de reglas versionadas por programa

## Estado

Aceptado

## Contexto

Las rúbricas y reglas operativas (horas requeridas, plazos) cambian según el programa académico (SUP-03). El Coordinador necesita configurar esto a demanda (CU-12). Un atributo crítico exige que modificar reglas de un programa para un nuevo ciclo tarde menos de 16 horas y afecte máximo a 2 componentes (EAC-01), garantizando que las prácticas en curso mantengan sus condiciones vigentes intactas (OB-05).

## Alternativas consideradas

- **A) Reglas lógicas embebidas en el código (hardcoded vía condicionales):**
  - *Ventaja:* Rápido inicio para un programa base.
  - *Desventaja:* Obliga a realizar despliegues de software completos por cada modificación reglamentaria (violando EAC-01) y dificulta aislar retrospectivamente las prácticas en curso.
- **B) Parámetros versionados en base de datos evaluados por un motor de reglas interno:** Cada programa posee una configuración guardada como documento/registro con fecha de vigencia. Cuando la práctica inicia, captura el `id_regla` en ese instante.
  - *Ventaja:* El coordinador gestiona los umbrales dinámicamente (CU-12), cumple EAC-01 y garantiza retrocompatibilidad de reglas (OB-05).
  - *Desventaja:* Requiere construir la interfaz de parametrización y evaluar condicionales dinámicamente.
- **C) Motor de reglas de terceros (ej. Drools):**
  - *Ventaja:* Permite árboles de reglas altamente complejos.
  - *Desventaja:* Excesivo y sobre-diseñado para umbrales básicos.

## Decisión

Se elige la opción B porque empodera al coordinador de prácticas (CU-12) manteniendo intacta la regla para cohortes pasadas (OB-05) y elimina la necesidad de escribir código fuente frente a variaciones de formato establecidas en SUP-03.

## Consecuencias

### Positivas

- Modificar requerimientos toma horas de configuración en pantalla (Cumple EAC-01).
- Cero impactos sobre estudiantes que ya iniciaron sus horas con reglamentación previa.

### Negativas y costos aceptados

- Costo inicial de desarrollo del módulo administrativo de configuración.

### Riesgos asumidos y sus respectivas mitigaciones

- **Configuración errónea publicada en producción por error humano:** Mitigación mediante la integración de estados en la regla (Borrador -> Activo), permitiendo simular y previsualizar el impacto antes de activarla oficialmente.


## Vistas arquitectónicas afectadas

* [Vista Lógica](../vistas/01-logica.md) (`../diagramas/01-logica.puml`): Entidad `ReglaPrograma` asociada a `Practica`.
* [Vista de Desarrollo](../vistas/03-desarrollo.md) (`../diagramas/03-desarrollo.puml`): Componente `Módulo Reglas` y su relación de uso desde `Módulo Postulaciones` y `Módulo Actas`.
* [Escenario ESC-05](../diagramas/secuencias/cu12-configurar-reglas.puml): Creación en borrador, simulación y activación sin afectar cohortes en curso.
