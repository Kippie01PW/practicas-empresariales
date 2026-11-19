# Fase 1: Especificar

## Entrada

- AGENTS.md y docs/arquitectura.md.
- docs/drivers.md: el caso de uso indicado, sus flujos alternos y los EAC que lo afectan.
- La descripción de la funcionalidad que entrega la persona.

## Produce

`specs/<NNN-nombre>/spec.md` con este formato:

```gherkin
# language: es
# Traza: <CU-xx>, <EAC-xx>, <ADR-xxx>
Característica: <nombre de la funcionalidad>
  <Rol, acción y beneficio en una o dos líneas>

  Escenario: <flujo básico>
    Dado <contexto o estado inicial>
    Cuando <acción o evento>
    Entonces <resultado observable>
    Y <otro resultado, si aplica>

  Escenario: <flujo alterno o excepción>
    ...

  Escenario: <EAC-xx con su medida>
    ...
```

## Reglas

- Un escenario para el flujo básico, uno por cada flujo alterno o excepción del caso de uso, y uno por cada EAC que lo toque, con su medida.
- Cada escenario se debe poder comprobar con un sí o un no: datos concretos, nada de "rápido", "fácil" o "adecuado".
- Usar los términos del glosario de docs/arquitectura.md.
- Describir comportamiento, no implementación: nada de clases, tablas, pantallas ni tecnologías.
- No inventar requisitos. Donde falte información, escribir en ese mismo lugar el comentario `# [NECESITA ACLARACIÓN: <pregunta concreta>]` (con `#` delante, para que siga siendo Gherkin válido) y seguir con lo demás.
- Al terminar, listar todas las marcas `[NECESITA ACLARACIÓN]` que dejó.
- No escribir código.
- Al terminar, detenerse y esperar revisión.

## Revisión de la persona

- Verificar cada escenario contra el caso de uso y completar en este mismo `spec.md` lo que falte.
- Resolver cada marca `[NECESITA ACLARACIÓN]` y borrarla. La revisión termina cuando no queda ninguna.
- Confirmar que la columna "Se especifica en" de `docs/drivers.md` enlaza a esta carpeta.
