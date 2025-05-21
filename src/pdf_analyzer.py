import re
import pandas as pd
from PyPDF2 import PdfReader
import os
from pathlib import Path
from datetime import datetime
import unicodedata

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

def clean_text(text):
    """
    Limpia el texto de caracteres especiales y normaliza el formato.
    
    Args:
        text (str): Texto a limpiar
        
    Returns:
        str: Texto limpio
    """
    # Normalizar caracteres especiales
    text = unicodedata.normalize('NFKD', text)
    
    # Reemplazar caracteres específicos
    replacements = {
        '√ö': 'ó',
        '√≥': 'ó',
        '√∫': 'ú',
        '√≠': 'í',
        '√°': 'á',
        '√©': 'é',
        '√±': 'ñ',
        '√º': 'ü'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Eliminar texto no deseado al final
    text = re.sub(r'\s*El Presidente de la Rep.*$', '', text)
    
    # Eliminar guiones al final de línea
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # Eliminar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_table_of_contents(pdf_path):
    """
    Extrae la tabla de contenido de un PDF con formato de dos columnas.
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        
    Returns:
        pd.DataFrame: DataFrame con la información extraída de la tabla de contenido
    """
    # Leer el PDF
    reader = PdfReader(pdf_path)
    full_text = '\n'.join(page.extract_text() for page in reader.pages if page.extract_text())
    
    # Dividir el texto en líneas
    lines = full_text.split('\n')
    
    data = []
    current_entity = None
    current_title = []
    collecting_title = False
    
    # Patrón para identificar entidades (ministerios u organismos)
    entity_pattern = re.compile(r'^(Ministerio|Departamento|Entidad|Organismo)[^\n]+', re.IGNORECASE)
    
    # Patrón para identificar el inicio de un decreto o resolución
    decree_start_pattern = re.compile(r'^(DECRETO|RESOLUCIÓN)\s+NÚMERO\s+\d+', re.IGNORECASE)
    
    # Patrón para identificar el final de un título (generalmente termina con un número de página)
    page_number_pattern = re.compile(r'\s+\d+$')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Si la línea está vacía, continuar con la siguiente
        if not line:
            i += 1
            continue
            
        # Verificar si la línea es una entidad
        entity_match = entity_pattern.search(line)
        if entity_match:
            # Si estábamos recolectando un título, guardarlo antes de cambiar de entidad
            if collecting_title and current_title and current_entity:
                full_title = ' '.join(current_title)
                data.append({
                    'nombre_decreto': full_title,
                    'entidad': current_entity
                })
                current_title = []
                collecting_title = False
            
            current_entity = line.strip()
            i += 1
            continue
            
        # Verificar si la línea es el inicio de un decreto
        decree_match = decree_start_pattern.search(line)
        if decree_match and current_entity:
            # Si estábamos recolectando un título anterior, guardarlo
            if collecting_title and current_title:
                full_title = ' '.join(current_title)
                data.append({
                    'nombre_decreto': full_title,
                    'entidad': current_entity
                })
            
            current_title = [line]
            collecting_title = True
            i += 1
            
            # Continuar recolectando líneas hasta encontrar el número de página
            while i < len(lines):
                next_line = lines[i].strip()
                
                # Si encontramos una nueva entidad o decreto, terminar la recolección
                if entity_pattern.search(next_line) or decree_start_pattern.search(next_line):
                    break
                    
                # Si encontramos un número de página, terminar la recolección
                if page_number_pattern.search(next_line):
                    # Remover el número de página
                    next_line = page_number_pattern.sub('', next_line).strip()
                    current_title.append(next_line)
                    break
                
                # Si la línea no está vacía, agregarla al título
                if next_line:
                    current_title.append(next_line)
                
                i += 1
            
            # Guardar el título completo
            if current_title:
                full_title = ' '.join(current_title)
                data.append({
                    'nombre_decreto': full_title,
                    'entidad': current_entity
                })
                current_title = []
                collecting_title = False
        else:
            i += 1
    
    return pd.DataFrame(data)

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
        df = extract_table_of_contents(str(pdf_file))
        df['archivo'] = pdf_file.name
        all_data.append(df)
    
    if all_data:
        # Combinar todos los DataFrames
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = resultados_dir / f'tabla_contenido_{timestamp}.csv'
        
        # Guardar resultados
        final_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nResultados guardados en: {output_file}")
        print(f"Total de registros procesados: {len(final_df)}")
    else:
        print("No se encontraron archivos PDF en el directorio 'data'")

if __name__ == "__main__":
    main() 