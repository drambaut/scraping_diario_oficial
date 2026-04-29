# -*- coding: utf-8 -*-
"""
Analizador normativo: Lectura de JSONs + PKL (Diario Oficial)
Autor: mflagosv + ajustes por ChatGPT
"""

import pandas as pd
import pickle as pk
import re
from pandas import ExcelWriter
import os
import json
import glob

#PATH_INTEGRANTES = "data/Integrantes.csv"
PATH_INTEGRANTES = #r'\Integrantes.csv'  # modificar
PATH_JSON = #r'\data\2025'               # modificar
# --------------------------- Funciones auxiliares ---------------------------
def find_parag(texto, patron, pat_inst):
    parag_lst, inst_l = [], []
    fi = re.finditer(patron, texto)
    for match in fi:
        ini = int(match.start())
        fin = texto.find(". ", ini)
        paragraph = texto[ini:fin]
        l_palabras = paragraph.replace(",", "").split(" ")[:9]
        sub_parag = " ".join(l_palabras)
        bus = re.findall(pat_inst, sub_parag)
        if bus:
            parag_lst.append(paragraph)
            inst_l += bus
    parag_txt = " || ".join(parag_lst) if parag_lst else " "
    ist_txt = "; ".join(inst_l) if inst_l else " "
    return parag_txt, ist_txt

def get_patt(listado):
    return "|".join([i.lower().strip() for i in listado.split(",")])

def get_patt_inst(listado):
    return "| ".join([i.lower().strip() for i in listado.split(",")])

def get_epig(texto):
    epigrafe = re.search(r"^[^.]+", texto)
    return epigrafe.group(0) if epigrafe else " "

def get_date(texto):
    patrones = [
        r"\(\w+ \d+\)", r"\(\d+ \w+ \w+\)", r"\(\d+ \w+\)",
        r"\(\w+\. \d+\)", r"\(\d+\. \w+\)", r"\(\w+ \w+ \d+\)"
    ]
    for pat in patrones:
        match = re.search(pat, texto)
        if match:
            return match.group(0)[1:-1]
    return 0

def detectAct(texto, patron):
    bus = re.findall(patron, texto)
    return "; ".join(bus) if bus else " "

def get_txt(texto, nombre):
    os.makedirs('./reportes/Documentos', exist_ok=True)
    with open(f"./reportes/Documentos/{nombre}.txt", "w", encoding='utf-8-sig') as f:
        f.write(texto)

def load_json_files(input_folder):
    json_files = glob.glob(os.path.join(input_folder, "*.json"))
    all_data = []
    print(f"Cargando {len(json_files)} archivos JSON desde {input_folder}")
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    entry['archivo'] = os.path.basename(json_file)
                    all_data.append(entry)
        except Exception as e:
            print(f"Error en archivo {json_file}: {e}")
    return all_data

def clasification(df):
    condiciones = [
        (df["Párrafos_Encontrados"]!=" ") & (df["Integrantes_Encontrados"]==" "),
        (df["Párrafos_Encontrados"]==" ") & (df["Integrantes_Encontrados"]!=" "),
        (df["Párrafos_Encontrados"]!=" ") & (df["Integrantes_Encontrados"]!=" ")
    ]
    categorias = ["Instancia", "Integrantes", "Instancias-Integrantes"]
    df["Categoria"] = "Otros"
    for cond, cat in zip(condiciones, categorias):
        df.loc[cond, "Categoria"] = cat
    return df

def clean_excel_string(value):
    if isinstance(value, str):
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    return value

# ----------------------------- Flujo principal ------------------------------
print("Preparando patrones de búsqueda...")
t = "Créase el , Créase él, Creáse el, Creáse él, Créase la, Créase los, Créase una, Créase un, Conformará una, Conformará un, Se conforma, Creará un, Creará una, Créase ella, Se crea, Se reglamenta, Establecimiento de una, Establecimiento de un, Confórmese una, Confórmese un"
y = "Instancias, instancia, Comisión, Comisiones, Comité, Comités, Consejo, Consejos, Junta, Juntas, Mesa, Mesas, Plataforma, Plataformas, Red, Redes, Subcomités, Subcomité, Sistema, Sistemas, mecanismo, mecanismos"
pat_tot = get_patt(t)
pat_inst = get_patt_inst(y)
df_integ = pd.read_csv(PATH_INTEGRANTES, sep=';')
l_actores = [i.lower().strip() for i in df_integ.iloc[:, 0].tolist()]
pat_actores = "|".join(l_actores)

print("Cargando archivos JSON 2024")
data = load_json_files(PATH_JSON)
df = pd.DataFrame.from_dict(data)
if 'titulo' in df.columns and 'descripcion' in df.columns:
    df['Nombre'] = df['titulo']
    df['Texto'] = df['descripcion'].fillna("").str.lower()
else:
    raise ValueError("Columnas 'titulo' y 'descripcion' requeridas no encontradas.")
df['ids'] = "(...)"
df['anio'] = pd.to_datetime(df['fecha_publicacion'], errors='coerce').dt.year.astype('Int64')

# Procesamiento de texto
df['pagra_inst'] = df['Texto'].apply(find_parag, patron=pat_tot, pat_inst=pat_inst)
df['Párrafos_Encontrados'] = df['pagra_inst'].apply(lambda x: x[0])
df['Tipo Instancias'] = df['pagra_inst'].apply(lambda x: x[1])
df['Epigrafe'] = df['Texto'].apply(get_epig)
df['mes_dia'] = df['Epigrafe'].apply(get_date)
df['Fecha'] = df['mes_dia'].astype(str) + ' de ' + df['anio'].astype(str)
df['Integrantes_Encontrados'] = df['Texto'].apply(detectAct, patron=pat_actores)
df = clasification(df)
df_2025 = df[["ids", "Nombre", "anio", "Fecha", "Texto", "Epigrafe", "Categoria",
              "Párrafos_Encontrados", "Tipo Instancias", "Integrantes_Encontrados", "archivo"]].copy()

print("Cargando archivos .pkl 2023–2024")
df_tot = df_2025.copy()
for anio in range(2023, 2025):
    path = f"./data/{anio}-data_all.pkl"
    if not os.path.exists(path):
        continue
    data = pk.load(open(path, "rb"))
    df = pd.DataFrame.from_dict(data)
    df_fin = df[['ids', 'type', 'year', 'texts']].copy()
    df_fin.rename(columns={'type': 'Nombre', 'year': 'anio', 'texts': 'Texto'}, inplace=True)
    df_fin['Texto'] = df_fin['Texto'].str.lower()

    df_fin['pagra_inst'] = df_fin['Texto'].apply(find_parag, patron=pat_tot, pat_inst=pat_inst)
    df_fin['Párrafos_Encontrados'] = df_fin['pagra_inst'].apply(lambda x: x[0])
    df_fin['Tipo Instancias'] = df_fin['pagra_inst'].apply(lambda x: x[1])
    df_fin['Epigrafe'] = df_fin['Texto'].apply(get_epig)
    df_fin['mes_dia'] = df_fin['Epigrafe'].apply(get_date)
    df_fin['Fecha'] = df_fin['mes_dia'].astype(str) + ' de ' + df_fin['anio'].astype(str)
    df_fin['Integrantes_Encontrados'] = df_fin['Texto'].apply(detectAct, patron=pat_actores)
    df_fin['archivo'] = os.path.basename(path)
    df_fin = clasification(df_fin)
    df_fin = df_fin[["ids", "Nombre", "anio", "Fecha", "Texto", "Epigrafe", "Categoria",
                     "Párrafos_Encontrados", "Tipo Instancias", "Integrantes_Encontrados", "archivo"]]
    df_tot = pd.concat([df_tot, df_fin], ignore_index=True)

print("Exportando a Excel por año")
os.makedirs("./reportes", exist_ok=True)
with ExcelWriter("./reportes/Reporte_ClicParticipativo-2025.xlsx", engine="openpyxl") as writer:
    for anio in sorted(df_tot['anio'].dropna().unique()):
        df_anio = df_tot[df_tot['anio'] == anio].copy()
        # Reemplazo de applymap (obsoleto) por apply + map
        df_anio = df_anio.apply(lambda col: col.map(clean_excel_string))
        df_anio.to_excel(writer, sheet_name=str(anio), index=False)

print("Exportación finalizada")