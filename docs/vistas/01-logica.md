# Vista Lógica (Modelo de Dominio)

## 1. Presentación principal

* **Diagrama:** `../diagramas/01-logica.puml`
* **Propósito:** Representa las abstracciones clave del negocio de prácticas empresariales, sus atributos conceptuales y sus relaciones de multiplicidad, sin acoplarse a tipos de datos técnicos, métodos ni tablas SQL.
* **Público objetivo:** Analistas de dominio, usuarios finales (Coordinador de prácticas) y desarrolladores.

## 2. Catálogo de elementos

| Entidad de Dominio | Responsabilidad en el negocio |
| :--- | :--- |
| **Practica** | Entidad raíz que articula la relación entre `Estudiante`, `DocenteAsesor` y `SupervisorEmpresa`, gobernando el ciclo de vida estricto del proceso. |
| **Estudiante** | Practicante matriculado que postula y registra su avance semanal de horas. |
| **DocenteAsesor** | Tutor académico asignado según su disponibilidad dentro del cupo de los 50 tutores (CU-03). |
| **Empresa** y **SupervisorEmpresa** | Organización receptora y jefe inmediato externo encargado de validar horas y calificar el desempeño. |
| **ReglaPrograma** | Configuración versionada por programa académico (horas exigidas, rúbrica y plantilla del acta) vigente al momento de iniciar la práctica. |
| **RegistroHoras** | Reporte semanal de horas ejecutadas por el estudiante y validadas por el supervisor (CU-04, CU-05). |
| **EvaluacionDesempeno** | Concepto y calificación emitida por el supervisor externo conforme a la rúbrica de la `ReglaPrograma` vinculada (CU-07). |
| **TokenEvaluacion** | Credencial efímera de un solo uso y caducidad a 15 días emitida para que el supervisor externo acceda sin cuenta (CU-05, CU-07). |
| **ActaFinal** | Documento oficial de cierre con su huella criptográfica (`hashIntegridadSha256`) y estado de firmas de docente y coordinador (CU-09, CU-10). |
| **IntentoValidacion** | Registro de cada intento de verificación de requisitos académicos frente al SIA para asegurar trazabilidad ante caídas (CU-01). |
| **EventoBitacora** | Registro inmutable (solo inserción) de aprobaciones de actas, cambios de estado e intentos de acceso fallidos (CU-10, CU-14). |

## 3. Justificación (Drivers y ADR)

* **RN-02, CU-11 y ADR-010:** La entidad `Practica` encapsula el patrón Máquina de Estados Finitos mediante su atributo `estadoActual` (*PendienteVerificacion, Solicitada, Aprobada, Asignada, EnEjecucion, Evaluada, Completada, Rechazada*), impidiendo emitir un `ActaFinal` si las horas o la evaluación están incompletas.
* **EAC-01, SUP-03, CU-12 y ADR-007:** `ReglaPrograma` separa declarativamente las reglas y plantillas por versión. Cada `Practica` queda atada a la versión vigente cuando inició, garantizando 0% de alteración en prácticas previas (OB-05).
* **EAC-02 y ADR-001:** `IntentoValidacion` deja rastro de las validaciones asíncronas frente al SIA; ninguna postulación se pierde cuando el servicio externo falla.
* **EAC-03, RN-04 y ADR-004:** `TokenEvaluacion` modela la vigencia de 15 días y el carácter de un solo uso de los enlaces enviados a los supervisores.
* **PA-03, EAC-03, CU-10, CU-14 y ADR-006:** `EventoBitacora` y `ActaFinal` (`hashIntegridadSha256`, ADR-008) aseguran el no repudio legal de las aprobaciones y las consultas históricas de acreditación.

## 4. Comportamiento

* Al crearse una `Practica` en CU-01, nace en estado `PendienteVerificacion` o `Solicitada` y se asocia a la `ReglaPrograma` activa de su carrera.
* Cada vuelta del proceso asíncrono de verificación contra el SIA registra un `IntentoValidacion`.
* Las transiciones hacia `Evaluada` y `Completada` exigen la existencia previa de los `RegistroHoras` aprobados, una `EvaluacionDesempeno` válida y un `ActaFinal` firmada, dejando un `EventoBitacora` por cada transición.

## 5. Vistas relacionadas

* **Vista de desarrollo (`03-desarrollo.md`):** Todas estas entidades residen en la capa `dominio/` del monolito modular y no dependen de ningún componente externo.
* **Vista de procesos (`02-procesos.md`):** Las entidades se persisten transaccionalmente en `PostgreSQL`, mientras que el binario referenciado por `ActaFinal` se almacena en el `Repositorio de actas PDF`.
