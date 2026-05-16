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

def guardar_leaderboard(nombre, pasos, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Hacker": nombre, "Pasos": pasos, "Tiempo (seg)": round(tiempo, 2)})
    # Ordenar PRIMERO por menos pasos, SEGUNDO por menor tiempo
    datos = sorted(datos, key=lambda x: (x["Pasos"], x["Tiempo (seg)"]))
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cyber-Maze: Infiltración", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = [1] # Siempre empezamos en el nodo 1
if 'steps_taken' not in st.session_state:
    st.session_state.steps_taken = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'graph' not in st.session_state:
    G = nx.Graph()
    # Grafo laberíntico de 25 nodos. Inicio: 1, Fin: 25.
    # Diseñado con callejones sin salida y rutas engañosas.
    edges = [
        (1,2), (1,6), (2,3), (2,7), (3,4), (4,5), (5,10), (6,11), (7,12),
        (8,9), (8,13), (9,10), (9,14), (10,15), (11,16), (12,17), (13,18),
        (14,19), (16,21), (17,22), (18,23), (19,24), (20,25), (21,22),
        (22,23), (23,24), (24,25), (15,20), (14,15), (3,8), (16,17)
    ]
    # Quitamos enlaces obvios para forzar un camino complejo
    edges_to_remove = [(15,20), (24,25), (22,23)]
    for e in edges_to_remove:
        if e in edges: edges.remove(e)
    
    G.add_edges_from(edges)
    # Agregamos la conexión final escondida
    G.add_edges_from([(20, 24), (19, 20), (20, 25)])
    st.session_state.graph = G

st.title("👾 Cyber-Maze: Enrutamiento Óptimo")
st.markdown("""
**Misión:** Lleva el paquete de datos desde el **Nodo 1 (INICIO)** hasta el **Nodo 25 (MAINFRAME)**.
Reglas del cortafuegos: NO puedes repetir nodos. Si te quedas atrapado, deberás retroceder, lo cual suma pasos a tu penalización. **¡Gana el que llegue con MENOS PASOS en el menor tiempo!**
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.graph
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO ---
    fig, ax = plt.subplots(figsize=(7, 5))
    # Usamos kamada_kawai para un look orgánico de red neuronal/hacker
    pos = nx.kamada_kawai_layout(G) 

    node_colors = []
    for node in G.nodes():
        if node == 1:
            node_colors.append('#f1c40f') # Amarillo (Inicio)
        elif node == 25:
            node_colors.append('#9b59b6') # Morado (Meta)
        elif path and node == path[-1]:
            node_colors.append('#3498db') # Azul (Posición Actual)
        elif node in path:
            node_colors.append('#2ecc71') # Verde (Rastro)
        else:
            node_colors.append('#34495e') # Gris oscuro (Desconocido)
            
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=600, 
            font_color='white', font_weight='bold', edge_color='#7f8c8d', ax=ax)

    if len(path) > 1:
        path_edges = list(zip(path, path[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='#2ecc71', width=4, ax=ax)

    st.pyplot(fig)

    # --- LÓGICA DEL JUEGO ---
    st.divider()
    current_node = path[-1]
    
    # Iniciar cronómetro al dar el primer paso
    if len(path) == 1 and st.session_state.start_time is None:
         st.info("Esperando tu primer movimiento para arrancar el cronómetro...")
    
    st.subheader(f"📡 Posición: Nodo {current_node} | 👣 Pasos consumidos: {st.session_state.steps_taken}")
    
    # Condición de Victoria
    if current_node == 25:
        tiempo_total = time.time() - st.session_state.start_time
        st.success(f"¡MAINFRAME HACKEADO! Pasos: {st.session_state.steps_taken} | Tiempo: {round(tiempo_total, 2)} seg.")
        st.balloons()
        
        with st.form("leaderboard_form"):
            st.write("¡Inmortaliza tu récord en la base de datos!")
            nombre_jugador = st.text_input("Ingresa tu alias:")
            submit_btn = st.form_submit_button("Guardar Puntaje")
            
            if submit_btn and nombre_jugador:
                guardar_leaderboard(nombre_jugador, st.session_state.steps_taken, tiempo_total)
                st.success("¡Puntaje guardado!")
                st.session_state.path = [1]
                st.session_state.steps_taken = 0
                st.session_state.start_time = None
                st.rerun()
                
        if st.button("Jugar de nuevo (Sin guardar)"):
            st.session_state.path = [1]
            st.session_state.steps_taken = 0
            st.session_state.start_time = None
            st.rerun()
    else:
        # Movimientos válidos (nodos adyacentes no visitados)
        neighbors = list(G.neighbors(current_node))
        unvisited = [n for n in neighbors if n not in path]
        
        # Condición de Atrapado
        if not unvisited:
            st.error("⚠️ ¡CALLEJÓN SIN SALIDA! El cortafuegos te bloqueó. Debes retroceder.")
        else:
            st.write("Rutas descubiertas (Nodos conectados):")
            cols = st.columns(len(unvisited))
            for i, neighbor in enumerate(unvisited):
                if cols[i].button(f"Mover al {neighbor}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    st.session_state.path.append(neighbor)
                    st.session_state.steps_taken += 1
                    st.rerun()
                    
        st.write("")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if len(path) > 1:
                if st.button("⬅️ Deshacer paso (Penalización: +1 paso)"):
                    st.session_state.path.pop()
                    st.session_state.steps_taken += 1 # Penalidad por equivocarse
                    st.rerun()
        with col_btn2:
            if st.button("🛑 Abortar misión (Reinicio total)", type="secondary"):
                st.session_state.path = [1]
                st.session_state.steps_taken = 0
                st.session_state.start_time = None
                st.rerun()

with col2:
    # --- TABLA DE CLASIFICACIÓN ---
    st.subheader("🏆 Top Hackers (Menos pasos ganan)")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("El servidor está limpio. ¡Sé el primero en infiltrarte!")