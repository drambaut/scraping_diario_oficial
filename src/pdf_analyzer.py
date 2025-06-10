import re
import pandas as pd
from PyPDF2 import PdfReader
import os
from pathlib import Path
from datetime import datetime
import unicodedata
import json
from dateutil import parser

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
        list: Lista de diccionarios con entidad y línea completa de cada decreto/resolución
    """
    reader = PdfReader(pdf_path)
    full_text = '\n'.join(page.extract_text() for page in reader.pages if page.extract_text())
    lines = full_text.split('\n')

    # Buscar el inicio de la tabla de contenido
    toc_start = -1
    for i, line in enumerate(lines):
        if re.search(r'C\s*o\s*n\s*t\s*e\s*n\s*i\s*d\s*o', line, re.IGNORECASE):
            toc_start = i
            break
    if toc_start == -1:
        return []

    # Buscar el final de la tabla de contenido (puede ser heurístico)
    toc_end = len(lines)
    for i in range(toc_start+1, len(lines)):
        if re.search(r'P[áa]gina|^\d+$', lines[i], re.IGNORECASE):
            toc_end = i
            break
    toc_lines = lines[toc_start:toc_end]

    data = []
    current_entity = None
    entity_pattern = re.compile(r'^(MINISTERIO|DEPARTAMENTO|ENTIDAD|ORGANISMO)[^\n]*', re.IGNORECASE)
    for line in toc_lines:
        line = line.strip()
        if not line:
            continue
        entity_match = entity_pattern.match(line)
        if entity_match:
            current_entity = line.strip()
            continue
        # Guardar cada línea de decreto/resolución junto con la entidad actual
        if current_entity:
            data.append({
                'entidad': current_entity,
                'linea': line
            })
    return data

def clean_entity_name(entity):
    """
    Extrae solo el nombre puro de la entidad colombiana.
    """
    if not entity:
        return entity
    # Solo toma hasta el primer salto de línea o punto
    entity = entity.split('\n')[0].split('.')[0]
    # Lista de palabras que NO son parte del nombre de la entidad (pero permite preposiciones/conjunciones comunes)
    stopwords = [
        'COMUNICAR', 'POR', 'DECRETO', 'RESOLUCIÓN', 'RESOLUCION', 'ACUERDO', 'CIRCULAR', 'CONTENIDO', 'PRESENTE', 'DOCTORES'
    ]
    # Buscar el patrón de entidad al inicio
    match = re.match(r'((MINISTERIO|DEPARTAMENTO|ORGANISMO|ENTIDAD)[A-ZÁÉÍÓÚÑ\s]+)', entity.strip(), re.IGNORECASE)
    if match:
        nombre = match.group(1).strip()
        # Cortar en la primera stopword encontrada
        nombre_split = nombre.split()
        nombre_final = []
        for word in nombre_split:
            if word.upper() in stopwords:
                break
            nombre_final.append(word)
        if nombre_final:
            return ' '.join(nombre_final).title()
        return nombre.title()
    # Si no encuentra patrón, devuelve solo las primeras 8 palabras (por seguridad)
    return ' '.join(entity.strip().split()[:8]).title()

def normalize_text(text):
    # Quita tildes y pasa a mayúsculas
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').upper() if text else ''

def find_entity_fuzzy(toc_data, tipo, numero, anio):
    tipo = normalize_text(tipo)
    numero = normalize_text(numero)
    anio = normalize_text(anio)
    last_entity = None

    # 1. Coincidencia completa
    for entry in toc_data:
        linea = normalize_text(entry['linea'])
        if tipo in linea and numero in linea and anio in linea:
            return clean_entity_name(entry['entidad'])
        if entry['entidad']:
            last_entity = entry['entidad']

    # 2. Coincidencia por número y año
    for entry in toc_data:
        linea = normalize_text(entry['linea'])
        if numero in linea and anio in linea:
            return clean_entity_name(entry['entidad'])

    # 3. Coincidencia solo por año
    for entry in toc_data:
        linea = normalize_text(entry['linea'])
        if anio in linea:
            return clean_entity_name(entry['entidad'])

    # 4. Si no hay coincidencia, devolver la última entidad conocida
    if last_entity:
        return clean_entity_name(last_entity)

    # 5. Si no hay ninguna, devolver un valor por defecto
    return "INSTITUCIÓN DESCONOCIDA"

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

def extract_publication_date(text):
    """
    Extrae la fecha de publicación del encabezado del PDF.
    
    Args:
        text (str): Texto completo del PDF
        
    Returns:
        str: Fecha de publicación en formato YYYY-MM-DD o cadena vacía si no se encuentra
    """
    # Buscar el patrón de fecha en el encabezado
    date_pattern = r'Bogotá, D\. C\., [^,]+,\s+(\d{1,2})\s+de\s+([a-zA-Z]+)\s+de\s+(\d{4})'
    match = re.search(date_pattern, text)
    
    if match:
        try:
            day = match.group(1)
            month = match.group(2)
            year = match.group(3)
            # Convertir el mes de texto a número
            month_map = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }
            month_num = month_map.get(month.lower(), '01')
            # Formatear la fecha como YYYY-MM-DD
            return f"{year}-{month_num}-{day.zfill(2)}"
        except:
            return ""
    return ""

def extract_institution(text):
    """
    Extrae la institución del documento.
    
    Args:
        text (str): Texto del documento
        
    Returns:
        str: Nombre de la institución o cadena vacía si no se encuentra
    """
    # Buscar el patrón de institución al inicio del documento
    institution_pattern = r'^(Ministerio|Departamento|Entidad|Organismo)[^\n]+'
    match = re.search(institution_pattern, text, re.MULTILINE)
    
    if match:
        return match.group(0).strip()
    return ""

def extract_documents(pdf_path):
    """
    Extrae todos los documentos del PDF y los estructura en un DataFrame.
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        
    Returns:
        pd.DataFrame: DataFrame con la información extraída
    """
    reader = PdfReader(pdf_path)
    processed_pages = []
    for page in reader.pages:
        if page.extract_text():
            page_text = process_two_column_text(page.extract_text())
            processed_pages.append(page_text)
    full_text = '\n'.join(processed_pages)
    publication_date = extract_publication_date(full_text)

    # Extraer la tabla de contenido como lista de dicts
    toc_data = extract_table_of_contents(pdf_path)

    document_patterns = [
        r'(DECRETO)\s+N[ÚU]MERO\s+(\d+)\s+DE\s+(\d{4})',
        r'(RESOLUCIÓN)\s+N[ÚU]MERO\s+(\d+)\s+DE\s+(\d{4})',
        r'(RESOLUCIÓN EJECUTIVA)\s+N[ÚU]MERO\s+(\d+)\s+DE\s+(\d{4})',
        r'(CIRCULAR EXTERNA CONJUNTA)\s+N[ÚU]MERO\s+(\d+)\s+DE\s+(\d{4})',
        r'(ACUERDO)\s+N[ÚU]MERO\s+(\d+)\s+DE\s+(\d{4})'
    ]
    combined_pattern = '|'.join(document_patterns)

    documents = []
    current_index = 0
    while True:
        match = re.search(combined_pattern, full_text[current_index:], re.IGNORECASE)
        if not match:
            break
        start_index = current_index + match.start()
        content, next_index = extract_document_content(full_text, start_index)
        lines = content.split('\n')
        title = lines[0].strip()
        # Buscar tipo, número y año en el título
        doc_match = re.match(r'(DECRETO|RESOLUCIÓN|RESOLUCIÓN EJECUTIVA|CIRCULAR EXTERNA CONJUNTA|ACUERDO)\s+N[ÚU]MERO\s+(\d+)\s+DE\s+(\d{4})', title, re.IGNORECASE)
        tipo = doc_match.group(1).upper() if doc_match else ''
        numero = doc_match.group(2) if doc_match else ''
        anio = doc_match.group(3) if doc_match else ''
        date = ""
        description_lines = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('(') and line.endswith(')'):
                date = line
            else:
                description_lines.append(line)
        description = '\n'.join(description_lines).strip()
        if date:
            title = f"{title}\n{date}"
        doc_type = identify_document_type(title)
        # Buscar la entidad usando fuzzy
        institution = find_entity_fuzzy(toc_data, tipo, numero, anio)
        documents.append({
            'tipo_documento': doc_type,
            'titulo': title,
            'descripcion': description,
            'fecha_publicacion': publication_date,
            'institucion': institution
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