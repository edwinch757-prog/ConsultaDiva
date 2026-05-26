import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Consulta DIVA", page_icon="✨", layout="wide")

# --- ESTILOS VISUALES (Smart Casual) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #1E3A8A; color: white; border-radius: 6px; width: 100%; }
    .total-box { background-color: #E0E7FF; padding: 15px; border-radius: 8px; text-align: right; font-size: 20px; font-weight: bold; color: #1E3A8A; }
    </style>
""", unsafe_index=True)

# --- 1. FUNCIÓN PARA LIMPIAR Y PROCESAR EL EXCEL ---
def procesar_excel(file):
    # Lee el archivo respetando las columnas de la A a la K
    df = pd.read_excel(file)
    
    # Renombramos internamente para que coincida con tu estructura de la A a la K
    # A=Tipo, B=Rango_Ancho, C=Rango_Alto, D=Descripcion, E=Coleccion, F=Color, G=SKU, J=Precio
    df.columns = ['Tipo', 'Rango_Ancho', 'Rango_Alto', 'Descripcion', 'Coleccion', 'Color', 'SKU', 'EAN', 'Costo', 'Precio_Venta', 'Nombre_Completo']
    
    # Limpieza de rangos con guion (ej: "80-100" -> Min: 80, Max: 100)
    df[['Ancho_Min', 'Ancho_Max']] = df['Rango_Ancho'].astype(str).str.split('-', expand=True).astype(float)
    df[['Alto_Min', 'Alto_Max']] = df['Rango_Alto'].astype(str).str.split('-', expand=True).astype(float)
    
    # Estandarizar texto a minúsculas y sin espacios para evitar errores de digitación
    df['Coleccion_Clean'] = df['Coleccion'].astype(str).str.lower().str.strip()
    df['Tipo_Clean'] = df['Tipo'].astype(str).str.lower().str.strip()
    
    return df

# --- 2. MOTOR DE BÚSQUEDA MATEMÁTICA ---
def buscar_producto(df, termino_busqueda, ancho, alto):
    termino = str(termino_busqueda).lower().strip()
    # Soporta abreviaturas comunes
    if termino == 'bo': termino = 'blackout'
    if termino == 'panl': termino = 'panel'
    if termino == 'alu': termino = 'aluminio'
    
    # Filtro por texto en tipo o colección, y coincidencia matemática de rangos
    resultado = df[
        ((df['Coleccion_Clean'].str.contains(termino)) | (df['Tipo_Clean'].str.contains(termino))) &
        (df['Ancho_Min'] <= ancho) & (df['Ancho_Max'] >= ancho) &
        (df['Alto_Min'] <= alto) & (df['Alto_Max'] >= alto)
    ]
    return resultado

# --- 3. INTERFAZ DE USUARIO ---
st.title("✨ Consulta DIVA")
st.caption("Sistema Inteligente de Cotización y Consulta de Cortinas")

# Inicializar base de datos en la sesión
if 'base_datos' not in st.session_state:
    st.session_state['base_datos'] = None

tab1, tab2 = st.tabs(["🔍 Módulo de Consulta", "🗄️ Base de Datos e IA"])

# --- TAB 2: BASE DE DATOS (Primero para cargar el archivo) ---
with tab2:
    st.subheader("Carga de Matriz de Precios")
    archivo = st.file_uploader("Sube tu archivo de Excel (Columnas A a la K)", type=["xlsx"])
    
    if archivo:
        try:
            st.session_state['base_datos'] = procesar_excel(archivo)
            st.success("¡Base de datos cargada y normalizada con éxito!")
        except Exception as e:
            st.error(f"Error al procesar el archivo. Asegúrate de que tenga las columnas desde la A hasta la K. Detalles: {e}")
            
    st.write("---")
    st.subheader("🤖 Asistente IA de Modificación")
    comando_ia = st.text_input("Escribe un comando para alterar la base de datos (Ej: 'Subir 5% a Prado')")
    if comando_ia:
        if st.session_state['base_datos'] is not None:
            # Aquí se conectará el modelo de lenguaje en el despliegue final
            st.info(f"Comando recibido: '{comando_ia}'. Modificando base de datos en memoria...")
        else:
            st.warning("Primero debes subir un archivo de Excel para poder hacer modificaciones.")

# --- TAB 1: CONSULTA Y RESPUESTA ---
with tab1:
    if st.session_state['base_datos'] is None:
        st.info("👋 ¡Bienvenido a Consulta DIVA! Por favor, ve a la pestaña 'Base de Datos' y sube tu archivo de Excel para empezar a cotizar.")
    else:
        df_APP = st.session_state['base_datos']
        
        st.subheader("Nueva Cotización")
        metodo_busqueda = sk = st.radio("Selecciona el método de entrada:", ["Escribir texto corrido (Rápido)", "Celdas independientes (Preciso)"])
        
        productos_a_cotizar = []
        
        if metodo_busqueda == "Celdas independientes (Preciso)":
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                col_seleccionada = st.selectbox("Colección / Tipo", df_APP['Coleccion'].unique())
            with col2:
                ancho_num = st.number_input("Ancho solicitado (cm)", min_value=0.0, step=1.0, value=100.0)
            with col3:
                alto_num = st.number_input("Alto solicitado (cm)", min_value=0.0, step=1.0, value=200.0)
                
            if st.button("Agregar a la Cotización"):
                res = buscar_producto(df_APP, col_seleccionada, ancho_num, alto_num)
                if not res.empty:
                    productos_a_cotizar.append(res.iloc[0])
                    st.success(f"Agregado: {res.iloc[0]['SKU']} - ${res.iloc[0]['Precio_Venta']:,}")
                else:
                    st.error("No se encontró un rango de medidas que coincida.")
                    
        else:
            # MODO RÁPIDO: Escribir corrido "prado 100*200, blackout 120*150"
            entrada_rapida = st.text_area("Entrada rápida", placeholder="Ejemplo: prado 100*200, bo 120*150, panel 250*100")
            
            if st.button("Procesar Líneas"):
                # Separamos por comas las distintas cortinas
                items = entrada_rapida.split(",")
                for item in items:
                    if '*' in item:
                        try:
                            # Extraer las medidas usando expresiones regulares
                            partes_texto = item.split()
                            # El último elemento suele tener las medidas (ej: 100*200)
                            medidas = partes_texto[-1]
                            ancho_r, alto_r = map(float, medidas.split('*'))
                            
                            # El resto del texto es la colección (ej: "roles duo prado")
                            coleccion_r = " ".join(partes_texto[:-1])
                            
                            res = buscar_producto(df_APP, coleccion_r, ancho_r, alto_r)
                            if not res.empty:
                                productos_a_cotizar.append(res.iloc[0])
                        except:
                            st.error(f"No pude entender el formato de: '{item}'. Recuerda usar Ancho*Alto.")

        # --- TABLA DE RESULTADOS TOTALES ---
        if productos_a_cotizar:
            st.write("### Resumen del Proyecto")
            df_resumen = pd.DataFrame(productos_a_cotizar)
            
            # Mostramos solo lo que necesitas ver frente al cliente
            st.table(df_resumen[['SKU', 'Tipo', 'Coleccion', 'Color', 'Rango_Ancho', 'Rango_Alto', 'Precio_Venta']])
            
            total_proyecto = df_resumen['Precio_Venta'].sum()
            st.markdown(f"<div class='total-box'>TOTAL PROYECTO: ${total_proyecto:,.0f} COP</div>", unsafe_allow_html=True)