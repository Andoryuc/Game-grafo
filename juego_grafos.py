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
    datos.append({"Estudiante": nombre, "Costo (Tráfico)": peso, "Tiempo de Resolución (s)": round(tiempo, 2)})
    datos = sorted(datos, key=lambda x: (x["Costo (Tráfico)"], x["Tiempo de Resolución (s)"]))
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
    
    pos = {
        "Casa": (0, 3),
        "C1": (2, 5), "C2": (2, 1),
        "C3": (4, 7), "C4": (4, 3), "C5": (4, -1),
        "C6": (6, 5), "C7": (6, 1),
        "C8": (8, 7), "C9": (8, 3), "C10": (8, -1),
        "C11": (10, 5), "C12": (10, 1),
        "UDES": (12, 3)
    }

    node_colors = []
    for node in G.nodes():
        if node == "Casa": node_colors.append('#3b82f6')
        elif node == path[-1] and node != "Casa": node_colors.append('#f1c40f')
        else: node_colors.append('#1f2937')
            
    NODE_SIZE = 1200
    EDGE_COLOR = '#94a3b8'
    TEXT_COLOR = '#dc2626'
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=NODE_SIZE, ax=ax, edgecolors='white', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=10, font_weight='bold', ax=ax)
    
    for u, v, key, d in G.edges(data=True, keys=True):
        peso = d['weight']
        tipo = d['edge_type']
        
        # Lógica para detectar si es bidireccional (hay vuelta)
        is_bidir = G.has_edge(v, u)
        arrow_style = '<->' if is_bidir else '-|>'

        if tipo == 'straight':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle=arrow_style, arrowsize=18, edge_color=EDGE_COLOR, width=1.5, node_size=NODE_SIZE, min_target_margin=18, ax=ax)
            x, y = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            ax.text(x, y, str(peso), color=TEXT_COLOR, fontsize=11, fontweight='bold', ha='center', va='center')
            
        elif tipo == 'curved':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle=arrow_style, arrowsize=18, connectionstyle=f"arc3,rad={d['rad']}", edge_color=EDGE_COLOR, width=1.5, node_size=NODE_SIZE, min_target_margin=18, ax=ax)
            x, y = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
            offset = 0.3 if d['rad'] > 0 else -0.3
            ax.text(x, y + offset, str(peso), color=TEXT_COLOR, fontsize=11, fontweight='bold', ha='center', va='center')
            
        elif tipo == 'loop':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=15, connectionstyle='arc3, rad=0.5', edge_color=EDGE_COLOR, width=1.5, node_size=NODE_SIZE, ax=ax)
            ax.text(pos[u][0] + 0.3, pos[u][1] + 0.5, str(peso), color=TEXT_COLOR, fontsize=11, fontweight='bold', ha='center', va='center')

    ax.axis('off')
    st.pyplot(fig)
    st.divider()

    current_node = path[-1]
    tiempo_transcurrido = time.time() - st.session_state.start_time if st.session_state.start_time else 0

    st.subheader(f"📍 Posición: {current_node} | 🚦 Costo de Ruta: {st.session_state.current_weight}")
    
    if current_node == "UDES":
        st.success(f"¡LLEGASTE! Costo: {st.session_state.current_weight} | Tiempo: {round(tiempo_transcurrido, 2)} s.")
        if st.form_submit_button("Subir al Ranking"): pass # Placeholder
    else:
        out_edges = list(G.out_edges(current_node, data=True))
        cols = st.columns(min(len(out_edges), 4))
        for i, (u, v, data) in enumerate(out_edges):
            if cols[i % 4].button(f"Mover a {v}", key=f"btn_{i}_{u}_{v}"):
                if st.session_state.start_time is None: st.session_state.start_time = time.time()
                st.session_state.path.append(v)
                st.session_state.current_weight += data['weight']
                st.rerun()

    if st.button("🔄 Reiniciar desde Casa"):
        st.session_state.path, st.session_state.current_weight, st.session_state.start_time = ["Casa"], 0, None
        st.rerun()