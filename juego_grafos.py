import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import time
import pandas as pd

# --- FUNCIONES DE BASE DE DATOS (LEADERBOARD) ---
ARCHIVO_LEADERBOARD = "ranking_dijkstra_udes.json"

def cargar_leaderboard():
    if os.path.exists(ARCHIVO_LEADERBOARD):
        with open(ARCHIVO_LEADERBOARD, "r") as f:
            return json.load(f)
    return []

def guardar_leaderboard(nombre, peso, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Estudiante": nombre, "Costo (Tráfico)": peso, "Tiempo (s)": round(tiempo, 2)})
    datos = sorted(datos, key=lambda x: (x["Costo (Tráfico)"], x["Tiempo (s)"]))
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador de Tráfico - UDES", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = ["Casa"]
if 'current_weight' not in st.session_state:
    st.session_state.current_weight = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

if 'grafo_exacto' not in st.session_state:
    G = nx.MultiDiGraph() 
    nodos = ["Casa", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "UDES"]
    G.add_nodes_from(nodos) 
    
    # 1. Rutas rectas estándar (Un solo sentido)
    aristas_rectas = [
        ("Casa", "C1", 12), ("Casa", "C4", 45), ("Casa", "C2", 15),
        ("C1", "C3", 10), ("C1", "C4", 25),
        ("C2", "C4", 30), ("C2", "C7", 15), ("C2", "C5", 10),
        ("C3", "C6", 15), ("C3", "C8", 5),
        ("C4", "C6", 20), ("C4", "C9", 55), ("C4", "C7", 18),
        ("C5", "C7", 12), ("C5", "C10", 20),
        ("C6", "C8", 5), ("C6", "C11", 30), ("C6", "C9", 25),
        ("C7", "C9", 22), ("C7", "C10", 10),
        ("C9", "C11", 10), ("C9", "UDES", 40), ("C9", "C12", 15),
        ("C11", "UDES", 15),
        ("C12", "UDES", 25)
    ]
    for u, v, w in aristas_rectas:
        G.add_edge(u, v, weight=w, edge_type='straight')

    # 2. Rutas paralelas/bidireccionales (C10 y C12)
    G.add_edge("C10", "C12", weight=15, edge_type='curved', rad=0.15)
    G.add_edge("C12", "C10", weight=10, edge_type='curved', rad=0.15)

    # 3. Lazo en C8
    G.add_edge("C8", "C8", weight=2, edge_type='loop')

    st.session_state.grafo_exacto = G

st.title("🗺️ Optimización de Rutas: Misión UDES")
st.markdown("""
Encuentra el camino con **menor peso (costo/tiempo)** desde tu **Casa** hasta la **UDES**. 
* Analiza topológicamente el grafo antes de moverte. 
* Cuidado con los lazos y las vías de doble sentido con pesos distintos.
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_exacto
    path = st.session_state.path

    fig, ax = plt.subplots(figsize=(14, 8)) 
    
    # Coordenadas exactas para replicar el layout de tu imagen
    pos = {
        "Casa": (0, 3),
        "C1": (2, 5), "C2": (2, 1),
        "C3": (4, 7), "C4": (4, 3), "C5": (4, -1),
        "C6": (6, 5), "C7": (6, 1),
        "C8": (8, 7), "C9": (8, 3), "C10": (8, -1),
        "C11": (10, 5), "C12": (10, 1),
        "UDES": (12, 3)
    }

    # Colores: Azul para Casa, Gris Oscuro para el resto, Amarillo para la ruta actual
    node_colors = []
    for node in G.nodes():
        if node == "Casa":
            node_colors.append('#3b82f6')
        elif node == path[-1] and node != "Casa":
            node_colors.append('#f1c40f')
        else:
            node_colors.append('#1f2937')
            
    NODE_SIZE = 1200
    EDGE_COLOR = '#94a3b8' # Gris claro de la imagen
    TEXT_COLOR = '#dc2626' # Rojo para los pesos
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=NODE_SIZE, ax=ax, edgecolors='white', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=10, font_weight='bold', ax=ax)
    
    # Dibujar aristas según su tipo para replicar la imagen
    for u, v, key, d in G.edges(data=True, keys=True):
        peso = d['weight']
        tipo = d['edge_type']

        if tipo == 'straight':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=18, edge_color=EDGE_COLOR, width=1.5, node_size=NODE_SIZE, min_target_margin=18, ax=ax)
            x, y = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            ax.text(x, y, str(peso), color=TEXT_COLOR, fontsize=11, fontweight='bold', ha='center', va='center', bbox=dict(alpha=0)) # bbox transparente como en tu imagen
            
        elif tipo == 'curved':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=18, connectionstyle=f"arc3,rad={d['rad']}", edge_color=EDGE_COLOR, width=1.5, node_size=NODE_SIZE, min_target_margin=18, ax=ax)
            x, y = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            offset = 0.3 if d['rad'] > 0 else -0.3
            ax.text(x, y + offset, str(peso), color=TEXT_COLOR, fontsize=11, fontweight='bold', ha='center', va='center', bbox=dict(alpha=0))
            
        elif tipo == 'loop':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=15, connectionstyle='arc3, rad=0.5', edge_color=EDGE_COLOR, width=1.5, node_size=NODE_SIZE, ax=ax)
            ax.text(pos[u][0] + 0.3, pos[u][1] + 0.5, str(peso), color=TEXT_COLOR, fontsize=11, fontweight='bold', ha='center', va='center', bbox=dict(alpha=0))

    ax.axis('off')
    st.pyplot(fig)
    st.divider()

    # --- LÓGICA DE NAVEGACIÓN ---
    current_node = path[-1]
    
    tiempo_transcurrido = 0
    if st.session_state.start_time is not None:
        tiempo_transcurrido = time.time() - st.session_state.start_time

    st.subheader(f"📍 Posición: {current_node} | 🚦 Costo de Ruta: {st.session_state.current_weight}")
    st.caption(f"⏱️ Tiempo activo: {round(tiempo_transcurrido, 1)} s")
    
    if current_node == "UDES":
        st.success(f"¡LLEGASTE A LA UDES! Costo de ruta: {st.session_state.current_weight} | Tiempo: {round(tiempo_transcurrido, 2)} s.")
        st.balloons()
        
        with st.form("leaderboard_form"):
            nombre_jugador = st.text_input("Ingresa tu código o nombre:")
            if st.form_submit_button("Subir al Ranking") and nombre_jugador:
                guardar_leaderboard(nombre_jugador, st.session_state.current_weight, tiempo_transcurrido)
                st.session_state.path, st.session_state.current_weight, st.session_state.start_time = ["Casa"], 0, None
                st.rerun()
    else:
        out_edges = list(G.out_edges(current_node, data=True))
        is_dead_end = len(out_edges) == 0
        
        if is_dead_end:
            st.error("⚠️ Error Crítico: Has entrado a un callejón sin salida.")
            st.warning("From error one learns, each error brings me closer to my dreams. Reinicia la ruta para intentarlo de nuevo.")
        else:
            cols = st.columns(min(len(out_edges), 4))
            for i, (u, v, data) in enumerate(out_edges):
                col = cols[i % len(cols)]
                if col.button(f"Mover a {v}", key=f"btn_{i}_{u}_{v}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    
                    st.session_state.path.append(v)
                    st.session_state.current_weight += data['weight']
                    st.rerun()
                    
        st.write("")
        if st.button("🔄 Reiniciar desde Casa", type="primary", use_container_width=True):
            st.session_state.path, st.session_state.current_weight = ["Casa"], 0 
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time()
            st.rerun()

with col2:
    st.subheader("🏆 Leaderboard Dijkstra")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sé el primero en encontrar la ruta óptima.")