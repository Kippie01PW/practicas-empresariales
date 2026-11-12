# ADR-008: Generación y preservación del acta final mediante plantillas y sellado criptográfico

## Estado

Aceptado

## Contexto

El sistema debe generar un acta de finalización oficial en PDF (CU-09) para reducir al máximo las tareas manuales (OB-01). El formato de esta acta cambia con el tiempo (SUP-03, EAC-01), y debe mantenerse la inmutabilidad legal para la universidad a través del flujo de aprobaciones (CU-10, PA-03, RN-02).

## Alternativas consideradas

- **A) Archivos de MS Word para llenado manual final:**
  - *Ventaja:* Flexibilidad para los tutores.
  - *Desventaja:* Mantiene los errores humanos, perpetuando problemas de transcripción (OB-04), y destruye el no-repudio al ser un formato editable.
- **B) Dibujo de PDF programático nativo (coordenadas x,y en código):**
  - *Ventaja:* No hay dependencias externas de librerías grandes.
  - *Desventaja:* Ante cualquier cambio mínimo de diseño solicitado (SUP-03), el desarrollador debe reprogramar, violando EAC-01.
- **C) Generación dinámica desde plantilla HTML/CSS a PDF + Cálculo de Hash de integridad:** Se usa un motor de plantillas (ej. Thymeleaf, Jinja) inyectando los datos. Al generarse y aprobarse, se calcula el Hash (SHA-256) del binario y se guarda en la base de datos junto a las aprobaciones (PA-03).
  - *Ventaja:* Cumple EAC-01 (el formato se edita como web), RN-02 y provee un PDF oficial auditable (OB-04).
  - *Desventaja:* Implica procesamiento de CPU para conversión HTML->PDF en el servidor.

## Decisión

Se elige la opción C porque automatiza integralmente la emisión (OB-01), blinda el acta ante alteraciones futuras garantizando el no-repudio (PA-03, CU-10), y desacopla la presentación de la lógica (EAC-01).

## Consecuencias

### Positivas

- Reducción drástica en errores de emisión (OB-04).
- Los formatos pueden cambiarse modificando únicamente archivos de plantilla (EAC-01).
- Respaldo criptográfico del aval otorgado por docente y coordinador (RN-02).

### Negativas y costos aceptados

- Es necesario incorporar un binario o dependencia en el servidor (como wkhtmltopdf o Puppeteer) para realizar la conversión a PDF.

### Riesgos asumidos y sus respectivas mitigaciones

- **Corrupción o pérdida del archivo PDF almacenado en disco:** Mitigación asegurando que, mientras la información de la base de datos permanezca intacta, el sistema puede regenerar el archivo, y el hash almacenado certificará que es idéntico e íntegro respecto al original emitido.
