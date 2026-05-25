import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import time
import pandas as pd

# --- PERSISTENCIA DE DATOS ---
ARCHIVO_LEADERBOARD = "ranking_ingenieria_udes.json"

def cargar_leaderboard():
    if os.path.exists(ARCHIVO_LEADERBOARD):
        with open(ARCHIVO_LEADERBOARD, "r") as f:
            return json.load(f)
    return []

def guardar_leaderboard(nombre, peso, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Estudiante": nombre, "Peso Acumulado": peso, "Tiempo (s)": round(tiempo, 2)})
    # Ranking: 1. Menor Peso | 2. Menor Tiempo (Desempate)
    datos = sorted(datos, key=lambda x: (x["Peso Acumulado"], x["Tiempo (s)"]))
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Network Optimization - UDS", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = ["Casa"]
if 'current_weight' not in st.session_state:
    st.session_state.current_weight = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

if 'grafo_final' not in st.session_state:
    # DiGraph para manejar direcciones estrictas
    G = nx.DiGraph() 
    
    # Definición de topología compleja
    edges = [
        ("Casa", "C1", 12), ("Casa", "C4", 45), ("Casa", "C2", 15),
        ("C1", "C3", 10), ("C1", "C4", 25),
        ("C2", "C4", 30), ("C2", "C5", 10),
        ("C3", "C6", 15), ("C3", "C3", 5), # Lazo
        ("C4", "C6", 20), ("C4", "C7", 18), ("C4", "C9", 55),
        ("C5", "C7", 12), ("C5", "C10", 20),
        ("C6", "C3", 15), ("C6", "C9", 25), ("C6", "C11", 30),
        ("C7", "C2", 15), ("C7", "C9", 22), ("C7", "C10", 10),
        ("C8", "C8", 2), # Lazo (Embudo)
        ("C6", "C8", 5), ("C3", "C8", 5), # Hacia el embudo
        ("C9", "UDES", 40), ("C9", "C11", 10), ("C9", "C12", 15),
        ("C10", "C12", 15), ("C12", "C10", 10), # Bidireccional con pesos distintos
        ("C11", "UDES", 15), ("C12", "UDES", 25)
    ]
    
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    
    st.session_state.grafo_final = G

# --- RENDERIZADO DEL MAPA ---
st.title("🏙️ Análisis de Redes de Transporte - Proyecto UDS")
st.markdown("Identifique la ruta de costo mínimo (Dijkstra) considerando sentidos viales y pesos de tráfico.")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_final
    path = st.session_state.path
    
    # Coordenadas manuales tipo malla urbana
    pos = {
        "Casa": (0, 3), "C1": (1, 4.5), "C2": (1, 1.5),
        "C3": (2, 5.5), "C4": (2.5, 3), "C5": (2, 0.5),
        "C6": (3.5, 4), "C7": (3.5, 2), "C8": (4.5, 5.5),
        "C9": (5, 3), "C10": (5, 1), "C11": (6.5, 4),
        "C12": (6.5, 2), "UDES": (8, 3)
    }

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor('#1e293b') # Fondo oscuro para resaltar pesos
    ax.set_facecolor('#1e293b')

    # Dibujar Nodos
    node_colors = ['#3b82f6' if n == path[-1] else '#334155' for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=1600, node_color=node_colors, edgecolors='white', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=10, font_weight='bold')

    # Dibujar Aristas con Curvatura y Flechas Visibles
    for u, v, data in G.edges(data=True):
        # Si existe la arista contraria, curvamos para que se vean ambas flechas
        arc = 0.2 if G.has_edge(v, u) else 0.1
        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)],
            edge_color='#94a3b8',
            arrowsize=25, # Flechas mucho más grandes
            arrowstyle='-|>',
            connectionstyle=f'arc3,rad={arc}',
            width=1.5,
            min_target_margin=25 # Evita que la flecha se meta debajo del nodo
        )

    # Dibujar Pesos (Labels)
    edge_labels = {(u, v): f"{d['weight']}" for u, v, d in G.edges(data=True)}
    # label_pos 0.3 para alejarlo del centro y evitar solapamientos en bidireccionales
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels,
        font_color='#f87171', # Rojo claro para el peso
        font_size=11,
        font_weight='bold',
        label_pos=0.3, 
        rotate=False,
        bbox=dict(facecolor='#1e293b', edgecolor='none', alpha=0.8, pad=1)
    )

    st.pyplot(fig)
    st.divider()

    # --- NAVEGACIÓN ---
    current_node = path[-1]
    t_actual = time.time() - st.session_state.start_time if st.session_state.start_time else 0

    st.subheader(f"📍 Posición: {current_node} | ⚖️ Peso Acumulado: {st.session_state.current_weight}")
    st.caption(f"⏱️ Cronómetro de resolución: {round(t_actual, 1)} segundos")

    if current_node == "UDES":
        st.success(f"🏁 Objetivo alcanzado. Peso: {st.session_state.current_weight} | Tiempo: {round(t_actual, 2)}s")
        with st.form("ranking"):
            nombre = st.text_input("Nombre / Código Estudiante:")
            if st.form_submit_button("Registrar en Leaderboard") and nombre:
                guardar_leaderboard(nombre, st.session_state.current_weight, t_actual)
                st.session_state.path, st.session_state.current_weight, st.session_state.start_time = ["Casa"], 0, None
                st.rerun()
    else:
        opciones = list(G.out_edges(current_node, data=True))
        if not opciones or (len(opciones) == 1 and opciones[0][0] == opciones[0][1]):
            st.error("🚫 Bloqueo en la red. Sin salida viable.")
            st.info("Debe reiniciar la ruta para recalcular.")
        else:
            cols = st.columns(len(opciones))
            for i, (u, v, d) in enumerate(opciones):
                if cols[i].button(f"Mover a {v}", use_container_width=True):
                    if not st.session_state.start_time: st.session_state.start_time = time.time()
                    st.session_state.path.append(v)
                    st.session_state.current_weight += d['weight']
                    st.rerun()

    if st.button("🔄 Reiniciar Posición (Mantiene el tiempo)", type="primary"):
        st.session_state.path, st.session_state.current_weight = ["Casa"], 0
        if not st.session_state.start_time: st.session_state.start_time = time.time()
        st.rerun()

with col2:
    st.subheader("🏆 Ranking de Optimización")
    leaderboard = cargar_leaderboard()
    if leaderboard:
        st.table(pd.DataFrame(leaderboard))
    else:
        st.info("Esperando primer registro...")