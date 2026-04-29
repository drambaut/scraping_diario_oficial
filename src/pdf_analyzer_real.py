import re
import pandas as pd
from PyPDF2 import PdfReader
import os
from pathlib import Path
from datetime import datetime
import unicodedata
import json
from dateutil import parser


# Expresión regular 
document_patterns = [
    r'\s*DECRETO(?:[^\S\n\r]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,3}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*RESOLUCI[ÓO]N(?:[^\S\n\r]+EJECUTIVA)(?:[^\S\n\r]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,2}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*RESOLUCI[ÓO]N(?:[^\S\n\r]+(?!N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,4}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*CIRCULAR(?:[^\S\n\r]+EXTERNA(?:[^\S\n\r]+CONJUNTA))(?:[^\S\n\r]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,2}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*CIRCULAR(?:[^\S\n\r]+EXTERNA)(?:[^\S\n\r]+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,2}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*CIRCULAR(?:[^\S\n\r]+(?!N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,3}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*ACUERDO(?:[^\S\n\r]+(?!N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,3}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*DIRECTIVA(?:[^\S\n\r]+(?!N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,3}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*LEY(?:[^\S\n\r]+)(\d+)(?:[^\S\n\r]+)DE(?:[^\S\n\r]+)(19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]?\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre)[^\)]*\))',
    r'\s*AVISO(?:[^\S\n\r]+(?!N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\.\-]{1,}){0,3}?(?:[^\S\n\r]+)(?:N[^\S\n\r]*[ÚUu]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\n\r]+)[A-Z0-9]+(?:[ \.\-_/][A-Z0-9]+)*(?:[^\S\n\r]+)\bDE\b(?:[^\S\n\r]+)(?:19\d{2}|20\d{2})(?=[^\S\n\r]*[\r\n]\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))',
    r'\s*RESOLUCI[ÓO]N(?:[^\S\r\n]+[A-ZÁÉÍÓÚÑ]{2,}(?:[^\S\r\n]+[A-ZÁÉÍÓÚÑ]{1,})?)(?:[^\S\r\n]+)(?:N[^\S\r\n]*[ÚU]MERO|NUMERO|N[O°]\.?|No\.?)?(?:[^\S\r\n]+)\d+(?:[ \.\-_/]\d+)*(?:[^\S\r\n]+)DE(?:[^\S\r\n]+)(?:19\d{2}|20\d{2})(?=[^\S\r\n]*[\r\n]?\s*\((?:ene|enero|feb|febrero|mar|marzo|abr|abril|may|mayo|jun|junio|jul|julio|ago|agosto|sep|sept|septiembre|set|setiembre|oct|octubre|nov|noviembre|dic|diciembre))'
]


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
    Extrae el contenido de un documento desde su encabezado hasta el inicio del siguiente.
    Evita autosolapes saltando el encabezado actual completo antes de buscar el próximo.
    """
    combined_pattern = '|'.join(f'({pattern})' for pattern in document_patterns)

    # Detecta el encabezado actual en start_index y calcula su largo
    head_match = re.match(combined_pattern, text[start_index:], re.IGNORECASE)
    skip = head_match.end(0) if head_match else 1  # salta TODO el encabezado actual

    # Busca el siguiente documento DESPUÉS del encabezado actual
    search_from = start_index + skip
    next_doc = re.search(combined_pattern, text[search_from:], re.IGNORECASE)

    # Delimita el bloque y devuelve
    end_index = (search_from + next_doc.start()) if next_doc else len(text)
    chunk = text[start_index:end_index].strip()
    return chunk, end_index

def identify_document_type(title: str) -> str:
    t = title.upper()
    if re.search(r'\bDECRETO\b', t):
        return 'DECRETO'
    if re.search(r'\bRESOLUCI[ÓO]N\b', t):
        return 'RESOLUCIÓN'
    if re.search(r'\bACUERDO\b', t):
        return 'ACUERDO'
    if re.search(r'\bCIRCULAR\b', t):
        return 'CIRCULAR'
    if re.search(r'\bDIRECTIVA\b', t):
        return 'DIRECTIVA'
    if re.search(r'\bLEY\b', t):
        return 'LEY'
    if re.search(r'\bAVISO\b', t):
        return 'AVISO'
    return ''

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
    # Modificar en caso de ser necesario
    current_dir = Path(__file__).parent.parent
    data_dir = current_dir / 'data' / '2025'
    resultados_dir = current_dir / 'resultados' / '2025'
    
    # Crear directorios si no existen
    data_dir.mkdir(parents=True, exist_ok=True)
    resultados_dir.mkdir(parents=True, exist_ok=True)
    
    # Obtener lista de PDFs
    pdf_files = list(data_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("❌ No se encontraron archivos PDF en el directorio 'data/2025'")
        return
    
    print(f"📁 Procesando {len(pdf_files)} archivo(s) PDF de 2025...")
    print("=" * 50)
    
    # Procesar cada PDF por separado
    total_documents = 0
    processed_files = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"📄 [{i}/{len(pdf_files)}] Procesando: {pdf_file.name}")
        
        try:
            documents = extract_documents(str(pdf_file))
            
            if documents:
                # Agregar el nombre del archivo a cada documento
                for doc in documents:
                    doc['archivo'] = pdf_file.name
                
                # Generar nombre de archivo único para este PDF
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # Usar el nombre del PDF (sin extensión) en el nombre del archivo JSON
                pdf_name = pdf_file.stem
                output_file = resultados_dir / f'documentos_{timestamp}_{pdf_name}.json'
                
                # Guardar resultados en formato JSON
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(documents, f, ensure_ascii=False, indent=2)
                
                total_documents += len(documents)
                processed_files += 1
                
                print(f"   ✅ {len(documents)} documento(s) extraído(s)")
                print(f"   💾 Guardado en: {output_file.name}")
                
                # Mostrar resumen por tipo de documento para este PDF
                doc_types = {}
                for doc in documents:
                    doc_type = doc['tipo_documento']
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                print(f"   📋 Tipos: {', '.join([f'{k}({v})' for k, v in doc_types.items()])}")
                
            else:
                print(f"   ⚠️  No se encontraron documentos en este PDF")
                
        except Exception as e:
            print(f"   ❌ Error procesando {pdf_file.name}: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"🎉 Procesamiento completado!")
    print(f"📊 Total de archivos procesados: {processed_files}/{len(pdf_files)}")
    print(f"📄 Total de documentos extraídos: {total_documents}")
    print(f"💾 Archivos JSON generados en: {resultados_dir}")
    
    if processed_files == 0:
        print("\n❌ No se extrajeron documentos de ningún archivo PDF")

if __name__ == "__main__":
    main() 