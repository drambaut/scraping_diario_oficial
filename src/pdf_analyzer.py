import re
import pandas as pd
from PyPDF2 import PdfReader
import os
from pathlib import Path
from datetime import datetime

def extract_purpose(text):
    """
    Extrae el propósito del decreto o resolución.
    
    Args:
        text (str): Texto completo del decreto o resolución
        
    Returns:
        str: Propósito extraído o cadena vacía si no se encuentra
    """
    # Buscar el propósito que comienza con "por la cual" y termina con "ACUERDO"
    match = re.search(r'por la cual.*?(?=ACUERDO)', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ""

def analyze_pdf(pdf_path):
    """
    Analiza un archivo PDF y extrae información sobre decretos y resoluciones.
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        
    Returns:
        pd.DataFrame: DataFrame con la información extraída
    """
    # Leer el PDF
    reader = PdfReader(pdf_path)
    full_text = '\n'.join(page.extract_text() for page in reader.pages if page.extract_text())

    # Dividir por ministerio
    sections = re.split(r"(Ministerio[^\n]+)", full_text)
    data = []

    for i in range(1, len(sections), 2):
        ministry = sections[i].strip()
        content = sections[i+1]
        
        # Extraer decretos
        decrees = re.findall(
            r"(DECRETO NÚMERO.*?)(?=(?:DECRETO NÚMERO|RESOLUCIÓ?N NÚMERO|$))",
            content, flags=re.S
        )
        for dec in decrees:
            dec = dec.strip()
            # Extraer el título (primera línea)
            title = dec.split('\n')[0].strip()
            # Extraer el propósito
            purpose = extract_purpose(dec)
            # El resto del contenido
            remaining_text = dec[len(title):].strip()
            
            data.append({
                'ministerio': ministry,
                'tipo_documento': 'DECRETO',
                'titulo': title,
                'proposito': purpose,
                'contenido': remaining_text
            })
            
        # Extraer resoluciones
        resolutions = re.findall(
            r"(RESOLUCIÓ?N NÚMERO.*?)(?=(?:DECRETO NÚMERO|RESOLUCIÓ?N NÚMERO|$))",
            content, flags=re.S
        )
        for res in resolutions:
            res = res.strip()
            # Extraer el título (primera línea)
            title = res.split('\n')[0].strip()
            # Extraer el propósito
            purpose = extract_purpose(res)
            # El resto del contenido
            remaining_text = res[len(title):].strip()
            
            data.append({
                'ministerio': ministry,
                'tipo_documento': 'RESOLUCIÓN',
                'titulo': title,
                'proposito': purpose,
                'contenido': remaining_text
            })

    # Crear DataFrame
    df = pd.DataFrame(data)
    return df

def main():
    # Obtener la ruta del directorio actual
    current_dir = Path(__file__).parent.parent
    data_dir = current_dir / 'data'
    resultados_dir = current_dir / 'resultados'
    
    # Crear directorios si no existen
    data_dir.mkdir(exist_ok=True)
    resultados_dir.mkdir(exist_ok=True)
    
    # Procesar todos los PDFs en el directorio data
    all_data = []
    for pdf_file in data_dir.glob('*.pdf'):
        print(f"Procesando {pdf_file.name}...")
        df = analyze_pdf(str(pdf_file))
        df['archivo'] = pdf_file.name
        all_data.append(df)
    
    if all_data:
        # Combinar todos los DataFrames
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = resultados_dir / f'resultados_{timestamp}.csv'
        
        # Guardar resultados
        final_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nResultados guardados en: {output_file}")
        print(f"Total de registros procesados: {len(final_df)}")
    else:
        print("No se encontraron archivos PDF en el directorio 'data'")

if __name__ == "__main__":
    main() 