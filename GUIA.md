# Metodología de Desarrollo: SDD (Spec-Driven Development)

El método usado en este repositorio se llama **SDD (Spec-Driven Development / Desarrollo Guiado por Especificaciones)**. Su objetivo es evitar que el asistente alucine reglas o mezcle capas de arquitectura, asegurando que cada línea de código tenga trazabilidad estricta y matemática hacia un caso de uso, sus escenarios de calidad y sus ADRs.

---

### 1. Orden recomendado para abordar los Casos de Uso

En la vista de desarrollo (`docs/vistas/03-desarrollo.md`) se definió una cadena de dependencias estricta sin ciclos:
$$\text{Módulo Actas} \rightarrow \text{Módulo Seguimiento y Evaluación} \rightarrow \text{Módulo Postulaciones} \rightarrow \text{Módulo Reglas}$$

El orden lógico de abordaje en el sistema es:

1. **Base transversal y Reglas:** `CU-12` (Reglas por programa).
2. **Postulaciones y Asignación:** `CU-01` (Postulación), `CU-02` (Aprobar/rechazar postulación), `CU-03` (Asignar tutor), `CU-11` (Consultar estado).
3. **Seguimiento y Horas:** `CU-04` (Registrar horas), `CU-05` (Validar horas), `CU-06` (Revisar avances), `CU-08` (Recordatorios).
4. **Evaluación:** `CU-07` (Evaluar desempeño por supervisor externo).
5. **Cierre y Actas:** `CU-09` (Generar acta PDF), `CU-10` (Aprobar acta con firmas).
6. **Auditoría, Monitoreo y Migración:** `CU-13` (Monitorear estado), `CU-14` (Consolidados auditoría), `CU-15` (Migrar Excel).

---

### 2. El Ciclo de 5 Fases por Caso de Uso

Cada caso de uso se gestiona dentro de su propia carpeta `specs/<NNN-nombre-caso-uso>/` mediante 5 fases secuenciales:

```text
Fase 1: Especificar   →  crea specs/<NNN>/spec.md       (Escenarios Gherkin: Dado, Cuando, Entonces)
Fase 2: Planear       →  crea specs/<NNN>/plan.md       (Mapeo a Clean Architecture, ADRs y puertos)
Fase 3: Descomponer   →  crea specs/<NNN>/tasks.md      (Micro-tareas atómicas: T-01, T-02...)
Fase 4: Implementar   →  crea código en dominio/, aplicacion/, infraestructura/ (Una tarea a la vez)
Fase 5: Validar       →  crea specs/<NNN>/validacion.md (Matriz de evidencia y verificación)
```

---

### 3. Estrategia de Gestión de Chats y Commits

Para garantizar que el modelo de lenguaje mantenga la máxima precisión, no alucine estados intermedios ni degrade su razonamiento por saturación de contexto:

1. **Chat de Especificación (Fases 1, 2 y 3):** Se usa una sola conversación para elaborar `spec.md`, `plan.md` y `tasks.md`. Al concluir, se asienta un commit de preparación y se cierra el chat.
2. **Un Chat Nuevo por cada Tarea de Implementación (Fase 4):** Para cada tarea (`T-01`, `T-02`, etc.) se abre un chat fresco. El agente ejecuta la tarea, actualiza `tasks.md`, genera el commit atómico, hace push y se detiene. Luego se descarta ese chat y se abre uno nuevo para la siguiente tarea.
3. **Chat de Validación (Fase 5 / Última tarea):** Se abre un chat final para ejecutar las pruebas funcionales, verificar los escenarios de `spec.md`, generar `validacion.md`, hacer commit y push.

---

### 4. Guía de Prompts y Flujo de Trabajo

> **Nota:** Reemplaza `<NNN-nombre-caso-uso>` (ej. `005-validar-horas-registradas`), `<CU-XX>` (ej. `CU-05`) y `<T-XX>` por los identificadores correspondientes.

---

#### **Bloque A: Especificación (Chat 1 - Fases 1 a 3)**

Abre un **Chat Nuevo** para definir el caso de uso:

##### **Paso 1: Especificar (`spec.md`)**

```text
Antes de hacer cualquier cosa, lee estos archivos:
1. AGENTS.md
2. docs/arquitectura.md. (sección correspondiente a CU-<XX>)

Resume en tres líneas las reglas que vas a respetar.

Después ejecuta prompts/1-especificar.md para specs/<NNN-nombre-caso-uso>/ y detente al terminar.
```

* **Qué hace el agente:** Genera los escenarios formales en Gherkin cubriendo camino feliz, casos borde, reglas de negocio y atributos de calidad en `spec.md`.

##### **Paso 2: Planear (`plan.md`)**

En el mismo chat, tras revisar `spec.md`:

```text
Antes de hacer cualquier cosa, lee estos archivos:
1. AGENTS.md
2. specs/<NNN-nombre-caso-uso>/spec.md
3. docs/vistas/03-desarrollo.md y los ADRs aplicables en docs/adr/

Resume en tres líneas las reglas que vas a respetar.

Después ejecuta prompts/2-planear.md para specs/<NNN-nombre-caso-uso>/ y detente al terminar.
```

* **Qué hace el agente:** Mapea los escenarios a clases, modelos de dominio, puertos, DTOs y adaptadores en `plan.md`.

##### **Paso 3: Descomponer (`tasks.md`)**

En el mismo chat, tras revisar `plan.md`:

```text
Antes de hacer cualquier cosa, lee estos archivos:
1. AGENTS.md y docs/arquitectura.md.
2. specs/<NNN-nombre-caso-uso>/spec.md
3. specs/<NNN-caso-uso>/plan.md

Resume en tres líneas las reglas que vas a respetar.

Después ejecuta prompts/3-descomponer.md para specs/<NNN-nombre-caso-uso>/ y detente al terminar.
```

* **Qué hace el agente:** Genera la secuencia atómica de micro-tareas (`T-01` a `T-n`) en `tasks.md`, ordenadas de adentro hacia afuera (Dominio $\rightarrow$ Aplicación $\rightarrow$ Infraestructura $\rightarrow$ Main $\rightarrow$ Validación).

##### **Paso 4: Commit y Push de la Especificación**

Una vez aprobados `spec.md`, `plan.md` y `tasks.md`, realizas o solicitas el commit:

```bash
git add specs/<NNN-nombre-caso-uso>/
git commit -m "specs: Preparar spec, plan y tasks para CU-<XX>"
git push
```

*(Cierra este chat).*

---

#### **Bloque B: Implementación Tarea por Tarea (Un Chat Nuevo por cada Tarea)**

Para **CADA** tarea listada en `tasks.md` (`T-01`, `T-02`, `T-03`, etc.):

1. Abre un **Chat Nuevo**.
2. Envía el prompt de ejecución atómica:

```text
Antes de hacer cualquier cosa, lee estos archivos:
1. AGENTS.md y docs/arquitectura.md.
2. specs/<NNN-nombre-caso-uso>/spec.md
3. specs/<NNN-nombre-caso-uso>/plan.md
4. specs/<NNN-nombre-caso-uso>/tasks.md

Resume en tres líneas las reglas que vas a respetar.

Ejecuta prompts/4-implementar.md para specs/<NNN-nombre-caso-uso>/ exclusivamente para la tarea T-<XX> sin esperar validación. 
Al finalizar la tarea:
1. Marca [X] T-<XX> en specs/<NNN-nombre-caso-uso>/tasks.md.
2. Haz el commit con el formato exacto: "T-<XX>: <título de la tarea en tasks.md> (CU-<XX>)".
3. Haz el push del commit sin esperar autorización.
4. Detente al terminar.
```

* **Qué hace el agente:**
  1. Modifica o crea **únicamente** los archivos asignados a `T-<XX>`.
  2. Marca con `[X]` la tarea en `tasks.md`.
  3. Ejecuta el commit con el formato estándar del repositorio:  
     `T-<XX>: <título de la tarea> (CU-<XX>)`
  4. Ejecuta `git push`.
  5. Se detiene y reporta el resultado.

3. Cierra el chat y abre uno nuevo para la tarea `T-<XX+1>`.

---

#### **Bloque C: Validación Final (Última Tarea de `tasks.md`)**

Para la última tarea (habitualmente `T-n: Validar todos los escenarios de spec.md y generar validacion.md`):

1. Abre un **Chat Nuevo**.
2. Envía el prompt de validación:

```text
Antes de hacer cualquier cosa, lee estos archivos:
1. AGENTS.md y docs/arquitectura.md.
2. specs/<NNN-nombre-caso-uso>/spec.md
3. specs/<NNN-nombre-caso-uso>/plan.md
4. specs/<NNN-nombre-caso-uso>/tasks.md

Resume en tres líneas las reglas que vas a respetar.

Ejecuta prompts/5-validar.md para specs/<NNN-nombre-caso-uso>/ verificando el 100% de los escenarios de spec.md contra el código implementado y genera specs/<NNN-nombre-caso-uso>/validacion.md.
Al terminar:
1. Marca [X] en tasks.md para esta última tarea.
2. Haz el commit con el formato: "T-<XX>: Validar todos los escenarios de spec.md y generar validacion.md (CU-<XX>)".
3. Haz el push del commit sin esperar autorización.
4. Detente al terminar.
```

* **Qué hace el agente:**
  1. Ejecuta las pruebas deterministas de aceptación sobre cada escenario de `spec.md`.
  2. Genera `specs/<NNN-nombre-caso-uso>/validacion.md` documentando la tabla de evidencias y la verificación de reglas arquitectónicas.
  3. Marca la tarea final en `tasks.md`.
  4. Realiza el commit y push final del caso de uso.

---

### 5. Convención Uniforme de Commits del Repositorio

Para mantener el historial de Git limpio y auditable en todo el repositorio:

| Momento | Formato del Commit | Ejemplo Real |
| --- | --- | --- |
| **Fin de Fases 1, 2 y 3** | `specs: Preparar spec, plan y tasks para CU-<XX>` | `specs: Preparar spec, plan y tasks para CU-05` |
| **Por cada Tarea (Fase 4)** | `T-<XX>: <título de la tarea> (CU-<XX>)` | `T-01: Incorporar excepciones de dominio para validacion de horas y credenciales tokenizadas (CU-05)` |
| **Validación Final (Fase 5)** | `T-<última>: Validar todos los escenarios de spec.md y generar validacion.md (CU-<XX>)` | `T-12: Validar todos los escenarios de spec.md y generar validacion.md (CU-05)` |

---

### 6. Reglas de Oro para el Usuario

1. **Un chat para especificación, un chat por cada tarea de código:** Cambiar de chat en cada commit garantiza que el modelo trabaje siempre con un contexto limpio, previniendo alucinaciones, código duplicado o violaciones de capas por arrastre de contexto.
2. **Nunca saltar de fase:** Jamás se implementa código sin tener `spec.md` y `plan.md` previamente revisados y asentados.
3. **Formato estricto de commit:** Cada tarea debe tener su propio commit unitario con su push inmediato, respetando el formato `T-<XX>: <título> (CU-<XX>)`.
4. **Aislamiento por tarea:** El modelo solo debe tocar los archivos declarados en la tarea correspondiente de `tasks.md`.
