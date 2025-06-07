import re
import pandas as pd
from PyPDF2 import PdfReader
import os
from pathlib import Path
from datetime import datetime
import unicodedata
import json

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

def process_two_column_text(text):
    """
    Procesa el texto de un PDF con formato de dos columnas.
    
    Args:
        text (str): Texto extraído del PDF
        
    Returns:
        str: Texto procesado y ordenado
    """
    # Dividir el texto en líneas
    lines = text.split('\n')
    processed_lines = []
    current_line = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Si la línea termina con guión, es parte de una palabra dividida
        if line.endswith('-'):
            current_line.append(line[:-1])
        else:
            current_line.append(line)
            # Unir la línea y agregarla a las líneas procesadas
            processed_lines.append(' '.join(current_line))
            current_line = []
    
    # Agregar la última línea si existe
    if current_line:
        processed_lines.append(' '.join(current_line))
    
    return '\n'.join(processed_lines)

def extract_document_content(text, start_index):
    """
    Extrae el contenido de un documento desde un índice inicial hasta el siguiente documento.
    
    Args:
        text (str): Texto completo del documento
        start_index (int): Índice donde comienza el documento
        
    Returns:
        tuple: (contenido, siguiente_índice)
    """
    # Patrones para identificar el inicio de diferentes tipos de documentos
    document_patterns = [
        r'DECRETO\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'RESOLUCIÓN\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'RESOLUCIÓN\s+EJECUTIVA\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'CIRCULAR\s+EXTERNA\s+CONJUNTA\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'ACUERDO\s+NÚMERO\s+\d+\s+DE\s+\d{4}'
    ]
    
    # Combinar todos los patrones
    combined_pattern = '|'.join(f'({pattern})' for pattern in document_patterns)
    
    # Buscar el siguiente documento
    next_doc = re.search(combined_pattern, text[start_index + 1:])
    
    if next_doc:
        end_index = start_index + 1 + next_doc.start()
        return text[start_index:end_index].strip(), end_index
    else:
        return text[start_index:].strip(), len(text)

def identify_document_type(title):
    """
    Identifica el tipo de documento basado en su título.
    
    Args:
        title (str): Título del documento
        
    Returns:
        str: Tipo de documento
    """
    title = title.upper()
    if re.search(r'DECRETO\s+NÚMERO\s+\d+\s+DE\s+\d{4}', title):
        return 'DECRETO'
    elif re.search(r'RESOLUCIÓN\s+EJECUTIVA\s+NÚMERO\s+\d+\s+DE\s+\d{4}', title):
        return 'RESOLUCIÓN EJECUTIVA'
    elif re.search(r'RESOLUCIÓN\s+NÚMERO\s+\d+\s+DE\s+\d{4}', title):
        return 'RESOLUCIÓN'
    elif re.search(r'CIRCULAR\s+EXTERNA\s+CONJUNTA\s+NÚMERO\s+\d+\s+DE\s+\d{4}', title):
        return 'CIRCULAR EXTERNA CONJUNTA'
    elif re.search(r'ACUERDO\s+NÚMERO\s+\d+\s+DE\s+\d{4}', title):
        return 'ACUERDO'
    return 'OTRO'

def extract_documents(pdf_path):
    """
    Extrae todos los documentos del PDF y los estructura en un DataFrame.
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        
    Returns:
        pd.DataFrame: DataFrame con la información extraída
    """
    # Leer el PDF
    reader = PdfReader(pdf_path)
    
    # Procesar cada página por separado
    processed_pages = []
    for page in reader.pages:
        if page.extract_text():
            # Procesar el texto de la página para manejar el formato de dos columnas
            page_text = process_two_column_text(page.extract_text())
            processed_pages.append(page_text)
    
    # Unir todas las páginas procesadas
    full_text = '\n'.join(processed_pages)
    
    # Patrones para identificar el inicio de diferentes tipos de documentos
    document_patterns = [
        r'DECRETO\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'RESOLUCIÓN\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'RESOLUCIÓN\s+EJECUTIVA\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'CIRCULAR\s+EXTERNA\s+CONJUNTA\s+NÚMERO\s+\d+\s+DE\s+\d{4}',
        r'ACUERDO\s+NÚMERO\s+\d+\s+DE\s+\d{4}'
    ]
    
    # Combinar todos los patrones
    combined_pattern = '|'.join(f'({pattern})' for pattern in document_patterns)
    
    # Encontrar todos los documentos
    documents = []
    current_index = 0
    
    while True:
        # Buscar el siguiente documento
        match = re.search(combined_pattern, full_text[current_index:])
        if not match:
            break
            
        # Calcular el índice real en el texto completo
        start_index = current_index + match.start()
        
        # Extraer el contenido del documento
        content, next_index = extract_document_content(full_text, start_index)
        
        # Dividir el contenido en líneas y procesar
        lines = content.split('\n')
        
        # Extraer el título (primera línea)
        title = lines[0].strip()
        
        # Extraer la fecha si existe (línea entre paréntesis)
        date = ""
        description_lines = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('(') and line.endswith(')'):
                date = line
            else:
                description_lines.append(line)
        
        # Construir la descripción completa
        description = '\n'.join(description_lines).strip()
        
        # Si hay fecha, incluirla en el título
        if date:
            title = f"{title}\n{date}"
        
        # Identificar el tipo de documento
        doc_type = identify_document_type(title)
        
        documents.append({
            'tipo_documento': doc_type,
            'titulo': title,
            'descripcion': description
        })
        
        current_index = next_index
    
    return documents

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
        documents = extract_documents(str(pdf_file))
        # Agregar el nombre del archivo a cada documento
        for doc in documents:
            doc['archivo'] = pdf_file.name
        all_data.extend(documents)
    
    if all_data:
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = resultados_dir / f'documentos_{timestamp}.json'
        
        # Guardar resultados en formato JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nResultados guardados en: {output_file}")
        print(f"Total de documentos procesados: {len(all_data)}")
        
        # Mostrar resumen por tipo de documento
        print("\nResumen por tipo de documento:")
        doc_types = {}
        for doc in all_data:
            doc_type = doc['tipo_documento']
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        for doc_type, count in doc_types.items():
            print(f"{doc_type}: {count}")
    else:
        print("No se encontraron archivos PDF en el directorio 'data'")

if __name__ == "__main__":
    main() 