import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import os
import time
import pandas as pd

# --- FUNCIONES DE BASE DE DATOS ---
ARCHIVO_LEADERBOARD = "ranking_final_udes.json"

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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador de Tráfico - UDES", layout="wide")

if 'path' not in st.session_state: st.session_state.path = ["Casa"]
if 'current_weight' not in st.session_state: st.session_state.current_weight = 0
if 'start_time' not in st.session_state: st.session_state.start_time = None

if 'grafo_definitivo' not in st.session_state:
    G = nx.MultiDiGraph()
    nodos = ["Casa"] + [f"C{i}" for i in range(1, 24)] + ["UDES"]
    G.add_nodes_from(nodos)

    # 1. Bidireccionales (Sin flechas, misma arista ida y vuelta implícita)
    def add_bidir(u, v, w):
        G.add_edge(u, v, weight=w, type='bidir')
        G.add_edge(v, u, weight=w, type='bidir')

    add_bidir("Casa", "C2", 15)
    add_bidir("C2", "C5", 10)
    add_bidir("C3", "C6", 12)
    add_bidir("C5", "C9", 20)
    add_bidir("C9", "C13", 10)
    add_bidir("C12", "C16", 15)
    add_bidir("C16", "C20", 12)

    # 2. Unidireccionales (Con flecha)
    def add_uni(u, v, w):
        G.add_edge(u, v, weight=w, type='uni')

    add_uni("Casa", "C1", 12); add_uni("Casa", "C3", 25)
    add_uni("C1", "C4", 15); add_uni("C1", "C5", 22)
    add_uni("C4", "C8", 10); add_uni("C8", "C11", 14)
    add_uni("C11", "C15", 25); add_uni("C15", "C18", 22)
    add_uni("C18", "C22", 18); add_uni("C22", "UDES", 55)
    add_uni("C21", "C23", 12); add_uni("C23", "UDES", 10)

    # 3. Paralelos (Curvos)
    G.add_edge("C8", "C12", weight=40, type='parallel', rad=0.2)
    G.add_edge("C8", "C12", weight=15, type='parallel', rad=-0.2)

    # 4. Lazos
    G.add_edge("C11", "C11", weight=25, type='loop')
    G.add_edge("C19", "C19", weight=5, type='loop')

    st.session_state.grafo_definitivo = G

# --- VISUALIZACIÓN ---
st.title("🗺️ Simulador de Tráfico - UDES")
col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_definitivo
    fig, ax = plt.subplots(figsize=(14, 8))
    pos = nx.spring_layout(G, seed=42, k=1.5)
    
    # Dibujar nodos
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color='#1e293b', ax=ax)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=8, ax=ax)

    # Dibujar aristas según tipo
    for u, v, k, d in G.edges(keys=True, data=True):
        rad = d.get('rad', 0) if d['type'] == 'parallel' else (0.5 if d['type'] == 'loop' else 0)
        nx.draw_networkx_edges(G, pos, edgelist=[(u,v)], 
                               arrows=(d['type'] != 'bidir'), 
                               arrowstyle='-|>', arrowsize=15,
                               connectionstyle=f'arc3,rad={rad}',
                               edge_color='#64748b', width=2, ax=ax)
        
        # Etiquetar pesos
        if d['type'] != 'bidir' or (u < v): # Evitar duplicar etiquetas en bidir
            x = (pos[u][0] + pos[v][0]) / 2 + (0.1 if rad != 0 else 0)
            y = (pos[u][1] + pos[v][1]) / 2
            ax.text(x, y, str(d['weight']), color='#ef4444', fontweight='bold', fontsize=9, bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

    ax.axis('off')
    st.pyplot(fig)

with col2:
    st.subheader("Navegación")
    current = st.session_state.path[-1]
    st.write(f"Posición: **{current}**")
    
    # Lógica de botones simplificada
    for u, v, k, d in G.out_edges(current, keys=True, data=True):
        if st.button(f"Ir a {v}", key=f"{u}_{v}_{k}"):
            st.session_state.path.append(v)
            st.session_state.current_weight += d['weight']
            st.rerun()