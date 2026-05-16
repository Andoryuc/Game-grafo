import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import time
import pandas as pd

# --- FUNCIONES DE BASE DE DATOS (LEADERBOARD) ---
ARCHIVO_LEADERBOARD = "leaderboard.json"

def cargar_leaderboard():
    if os.path.exists(ARCHIVO_LEADERBOARD):
        with open(ARCHIVO_LEADERBOARD, "r") as f:
            return json.load(f)
    return []

def guardar_leaderboard(nombre, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Hacker": nombre, "Tiempo (segundos)": round(tiempo, 2)})
    # Ordenar por el menor tiempo
    datos = sorted(datos, key=lambda x: x["Tiempo (segundos)"])
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cyber-Router: IA Hacker", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'graph' not in st.session_state:
    G = nx.Graph()
    # Grafo más interesante para la competencia
    G.add_edges_from([(1,2), (1,3), (1,4), (2,3), (3,4), (4,5), (2,5), (3,5), (5,6), (4,6)])
    st.session_state.graph = G
    st.session_state.target_nodes = len(G.nodes)

st.title("👾 Cyber-Router: El Protocolo Hamilton")
st.markdown("**Misión:** Visita todos los servidores (vértices) exactamente **UNA VEZ** sin quedarte atrapado. ¡El menor tiempo gana!")

# --- DISEÑO A DOS COLUMNAS ---
col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.graph
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO ---
    fig, ax = plt.subplots(figsize=(6, 4))
    pos = nx.spring_layout(G, seed=42) 

    node_colors = []
    for node in G.nodes():
        if path and node == path[-1]:
            node_colors.append('#3498db') # Azul (Actual)
        elif node in path:
            node_colors.append('#2ecc71') # Verde (Visitado)
        else:
            node_colors.append('#e74c3c') # Rojo (No visitado)
            
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=800, 
            font_color='white', font_weight='bold', edge_color='gray', ax=ax)

    if len(path) > 1:
        path_edges = list(zip(path, path[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='#2ecc71', width=4, ax=ax)

    st.pyplot(fig)

    # --- LÓGICA DEL JUEGO ---
    st.divider()
    if not path:
        st.subheader("📍 Fase 1: Punto de Inserción")
        st.write("Selecciona el servidor de inicio para arrancar el cronómetro:")
        cols = st.columns(len(G.nodes()))
        for i, node in enumerate(G.nodes()):
            if cols[i].button(f"Nodo {node}"):
                st.session_state.path.append(node)
                st.session_state.start_time = time.time()
                st.rerun()
    else:
        current_node = path[-1]
        st.subheader(f"📡 Estás en el servidor: {current_node}")
        
        # Condición de Victoria
        if len(path) == st.session_state.target_nodes:
            tiempo_total = time.time() - st.session_state.start_time
            st.success(f"¡HACKEO COMPLETADO en {round(tiempo_total, 2)} segundos!")
            st.balloons()
            
            # Formulario para guardar puntaje
            with st.form("leaderboard_form"):
                st.write("¡Guarda tu puntaje en el sistema central!")
                nombre_jugador = st.text_input("Ingresa tu alias / nombre:")
                submit_btn = st.form_submit_button("Guardar Puntaje")
                
                if submit_btn and nombre_jugador:
                    guardar_leaderboard(nombre_jugador, tiempo_total)
                    st.success("¡Puntaje guardado!")
                    st.session_state.path = []
                    st.session_state.start_time = None
                    st.rerun()
                    
            if st.button("Jugar de nuevo (Sin guardar)"):
                st.session_state.path = []
                st.session_state.start_time = None
                st.rerun()
        else:
            # Movimientos válidos
            neighbors = list(G.neighbors(current_node))
            unvisited = [n for n in neighbors if n not in path]
            
            # Condición de Derrota
            if not unvisited:
                st.error("¡SISTEMA BLOQUEADO! Te quedaste sin rutas[cite: 285].")
                if st.button("Reintentar Intrusión"):
                    st.session_state.path = []
                    st.session_state.start_time = None
                    st.rerun()
            else:
                st.write("Rutas disponibles:")
                cols = st.columns(len(unvisited))
                for i, neighbor in enumerate(unvisited):
                    if cols[i].button(f"Mover al {neighbor}"):
                        st.session_state.path.append(neighbor)
                        st.rerun()
                        
            st.write("")
            if st.button("🛑 Abortar misión (Reiniciar)", type="secondary"):
                st.session_state.path = []
                st.session_state.start_time = None
                st.rerun()

with col2:
    # --- TABLA DE CLASIFICACIÓN (LEADERBOARD) ---
    st.subheader("🏆 Top Hackers (Leaderboard)")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        # Hacemos que el índice empiece en 1
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aún no hay registros. ¡Sé el primero en hackear la red!")