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
if 'trampa_activada' not in st.session_state:
    st.session_state.trampa_activada = False

# Nodos trampa: parecen normales pero llevan a callejones sin salida
# Se añaden LEJOS del inicio para que no sea obvio
NODOS_TRAMPA = {"T1", "T2", "T3"}

if 'grafo_exacto' not in st.session_state:
    G = nx.MultiDiGraph()

    # 20 nodos normales + Casa + UDES + 3 nodos trampa ocultos
    nodos_normales = ["Casa", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
                      "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20", "UDES"]
    nodos_trampa = ["T1", "T2", "T3"]  # Nombres inofensivos en el grafo no se revelan como trampa
    G.add_nodes_from(nodos_normales + nodos_trampa)

    # === ARISTAS PRINCIPALES (rutas directas) ===
    aristas_rectas = [
        # Zona inicio (Casa → primeros nodos)
        ("Casa", "V1", 8),
        ("Casa", "V2", 14),
        ("Casa", "V3", 20),

        # Zona media-baja
        ("V1", "V4", 12),
        ("V1", "V5", 18),
        ("V2", "V5", 10),
        ("V2", "V6", 22),
        ("V3", "V6", 15),
        ("V3", "V7", 30),

        # Zona media
        ("V4", "V8", 9),
        ("V4", "V9", 16),
        ("V5", "V9", 11),
        ("V5", "V10", 20),
        ("V6", "V10", 13),
        ("V6", "V11", 25),
        ("V7", "V11", 18),
        ("V7", "V12", 35),

        # Zona media-alta
        ("V8", "V13", 14),
        ("V9", "V13", 8),
        ("V9", "V14", 22),
        ("V10", "V14", 12),
        ("V10", "V15", 19),
        ("V11", "V15", 10),
        ("V11", "V16", 28),
        ("V12", "V16", 20),

        # Zona alta
        ("V13", "V17", 11),
        ("V14", "V17", 15),
        ("V14", "V18", 20),
        ("V15", "V18", 9),
        ("V15", "V19", 24),
        ("V16", "V19", 17),
        ("V16", "V20", 30),

        # Llegada a UDES
        ("V17", "UDES", 18),
        ("V18", "UDES", 12),
        ("V19", "UDES", 22),
        ("V20", "UDES", 35),
    ]

    for u, v, w in aristas_rectas:
        G.add_edge(u, v, weight=w, edge_type='straight')

    # === ARISTAS CURVAS / BIDIRECCIONALES ===
    # V12 ↔ V7 (doble sentido, pesos distintos)
    G.add_edge("V12", "V7", weight=28, edge_type='curved', rad=0.2)
    G.add_edge("V7", "V12", weight=35, edge_type='curved', rad=0.2)

    # V17 ↔ V18 (atajo bidireccional)
    G.add_edge("V17", "V18", weight=6, edge_type='curved', rad=0.15)
    G.add_edge("V18", "V17", weight=8, edge_type='curved', rad=0.15)

    # V19 ↔ V20 (bidireccional con pesos distintos)
    G.add_edge("V19", "V20", weight=14, edge_type='curved', rad=0.2)
    G.add_edge("V20", "V19", weight=10, edge_type='curved', rad=0.2)

    # V4 ↔ V5 (atajo bidireccional)
    G.add_edge("V4", "V5", weight=7, edge_type='curved', rad=0.15)
    G.add_edge("V5", "V4", weight=9, edge_type='curved', rad=0.15)

    # === LAZOS ===
    G.add_edge("V9", "V9", weight=3, edge_type='loop')   # Lazo en nodo central
    G.add_edge("V14", "V14", weight=4, edge_type='loop')  # Lazo en zona alta

    # === TRAMPAS (callejones sin salida ocultos, accesibles desde nodos lejanos) ===
    # T1: accesible desde V12 (zona alta-derecha, lejos del inicio)
    #     parece un atajo prometedor con bajo costo, pero no tiene salida
    G.add_edge("V12", "T1", weight=5, edge_type='straight')   # Costo tentador bajo
    # T1 no tiene aristas de salida → callejón

    # T2: accesible desde V16 (zona alta), parece conectar con V20
    G.add_edge("V16", "T2", weight=8, edge_type='straight')   # Parece un buen camino
    # T2 sin salida → trampa

    # T3: accesible desde V20, muy cerca del final, cruel
    G.add_edge("V20", "T3", weight=4, edge_type='straight')   # Muy barato, tentador
    # T3 sin salida → trampa

    st.session_state.grafo_exacto = G

# --- LAYOUT / POSICIONES ---
# Distribuido en una grilla de ~5 columnas × 5 filas, más espacio
pos = {
    "Casa": (0, 6),
    "V1":  (2, 8),  "V2":  (2, 6),  "V3":  (2, 4),
    "V4":  (4, 9),  "V5":  (4, 7),  "V6":  (4, 5),  "V7":  (4, 3),
    "V8":  (6, 9),  "V9":  (6, 7),  "V10": (6, 5),  "V11": (6, 3),  "V12": (6, 1),
    "V13": (8, 8),  "V14": (8, 6),  "V15": (8, 4),  "V16": (8, 2),
    "V17": (10, 7), "V18": (10, 5), "V19": (10, 3), "V20": (10, 1),
    "UDES": (12, 4),
    # Trampas: visualmente colocadas como si fueran nodos normales
    "T1": (8, 0),    # Cerca de V12, al sur
    "T2": (10, 0),   # Sur de V16
    "T3": (12, 0),   # Sur de UDES, muy tentadora
}

st.title("🗺️ Optimización de Rutas: Misión UDES")
st.markdown("""
Encuentra el camino con **menor peso (costo/tiempo)** desde tu **Casa** hasta la **UDES**.
* Analiza topológicamente el grafo antes de moverte.
* Cuidado con los lazos y las vías de doble sentido con pesos distintos.
* ⚠️ Algunos caminos parecen atajos... pero pueden ser trampas sin salida.
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_exacto
    path = st.session_state.path

    fig, ax = plt.subplots(figsize=(16, 10))

    # Colores de nodos
    node_colors = []
    for node in G.nodes():
        if node == "Casa":
            node_colors.append('#3b82f6')       # Azul
        elif node == "UDES":
            node_colors.append('#22c55e')       # Verde
        elif node in NODOS_TRAMPA:
            node_colors.append('#1f2937')       # Igual que los demás (¡no revelar!)
        elif node == path[-1]:
            node_colors.append('#f1c40f')       # Amarillo: posición actual
        else:
            node_colors.append('#1f2937')       # Gris oscuro normal

    NODE_SIZE = 1000
    EDGE_COLOR = '#94a3b8'
    TEXT_COLOR = '#dc2626'

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=NODE_SIZE, ax=ax,
                           edgecolors='white', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=8, font_weight='bold', ax=ax)

    # Dibujar aristas por tipo
    for u, v, key, d in G.edges(data=True, keys=True):
        peso = d['weight']
        tipo = d['edge_type']

        if tipo == 'straight':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True,
                                   arrowstyle='-|>', arrowsize=16, edge_color=EDGE_COLOR,
                                   width=1.5, node_size=NODE_SIZE, min_target_margin=16, ax=ax)
            x = (pos[u][0] + pos[v][0]) / 2
            y = (pos[u][1] + pos[v][1]) / 2
            ax.text(x, y, str(peso), color=TEXT_COLOR, fontsize=9, fontweight='bold',
                    ha='center', va='center', bbox=dict(alpha=0))

        elif tipo == 'curved':
            rad = d.get('rad', 0.2)
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True,
                                   arrowstyle='-|>', arrowsize=16,
                                   connectionstyle=f"arc3,rad={rad}",
                                   edge_color=EDGE_COLOR, width=1.5,
                                   node_size=NODE_SIZE, min_target_margin=16, ax=ax)
            x = (pos[u][0] + pos[v][0]) / 2
            y = (pos[u][1] + pos[v][1]) / 2
            offset = 0.35 if rad > 0 else -0.35
            ax.text(x, y + offset, str(peso), color=TEXT_COLOR, fontsize=9, fontweight='bold',
                    ha='center', va='center', bbox=dict(alpha=0))

        elif tipo == 'loop':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True,
                                   arrowstyle='-|>', arrowsize=14,
                                   connectionstyle='arc3,rad=0.6',
                                   edge_color=EDGE_COLOR, width=1.5,
                                   node_size=NODE_SIZE, ax=ax)
            ax.text(pos[u][0] + 0.4, pos[u][1] + 0.5, str(peso),
                    color=TEXT_COLOR, fontsize=9, fontweight='bold',
                    ha='center', va='center', bbox=dict(alpha=0))

    ax.axis('off')
    ax.set_xlim(-0.5, 13.5)
    ax.set_ylim(-1, 10.5)
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
                st.session_state.path = ["Casa"]
                st.session_state.current_weight = 0
                st.session_state.start_time = None
                st.session_state.trampa_activada = False
                st.rerun()
    else:
        out_edges = list(G.out_edges(current_node, data=True))
        is_dead_end = len(out_edges) == 0

        if is_dead_end:
            # Es una trampa — revelar solo cuando ya cayó
            st.error("⚠️ ¡TRAMPA! Has entrado a una zona sin salida. Debes reiniciar desde Casa.")
            st.warning("Analiza mejor el grafo antes de moverte. Algunos nodos no tienen camino de regreso.")
            st.session_state.trampa_activada = True
        else:
            cols = st.columns(min(len(out_edges), 5))
            for i, (u, v, data) in enumerate(out_edges):
                col = cols[i % len(cols)]
                if col.button(f"→ {v}  (costo: {data['weight']})", key=f"btn_{i}_{u}_{v}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    st.session_state.path.append(v)
                    st.session_state.current_weight += data['weight']
                    st.rerun()

        st.write("")
        if st.button("🔄 Reiniciar desde Casa", type="primary", use_container_width=True):
            st.session_state.path = ["Casa"]
            st.session_state.current_weight = 0
            st.session_state.trampa_activada = False
            if st.session_state.start_time is not None:
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

    st.divider()
    st.subheader("🗺️ Ruta actual")
    if st.session_state.path:
        ruta_str = " → ".join(st.session_state.path)
        st.code(ruta_str)
    st.caption(f"Nodos visitados: {len(st.session_state.path)}")