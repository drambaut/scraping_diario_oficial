# Analizador de PDFs del Diario Oficial

Este proyecto analiza archivos PDF del Diario Oficial para extraer información sobre decretos y resoluciones, organizándola en un DataFrame y exportándola a CSV.

## Estructura del Proyecto

```
.
├── data/               # Directorio para los archivos PDF
├── resultados/         # Directorio para los archivos CSV generados
├── src/               # Código fuente
│   └── pdf_analyzer.py
├── requirements.txt   # Dependencias del proyecto
└── README.md         # Este archivo
```

## Configuración

1. Crear y activar el entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Coloca los archivos PDF que deseas analizar en el directorio `data/`
2. Ejecuta el script:
```bash
python src/pdf_analyzer.py
```

El script procesará todos los PDFs en el directorio `data/` y generará un archivo CSV en el directorio `resultados/` con un nombre que incluye la fecha y hora de la ejecución.

## Resultados

Los archivos CSV generados se guardarán en el directorio `resultados/` con el formato `resultados_YYYYMMDD_HHMMSS.csv` y contendrán las siguientes columnas:

- ministerio: El ministerio al que pertenece el documento
- tipo_documento: Tipo de documento (DECRETO o RESOLUCIÓN)
- titulo: Título completo del documento (primera línea)
- proposito: Propósito del documento (texto entre "por la cual" y "ACUERDO")
- contenido: Resto del contenido del documento
- archivo: Nombre del archivo PDF de origen