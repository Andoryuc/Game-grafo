import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import json
import os
import time
import pandas as pd
import numpy as np

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

NODOS_TRAMPA = {"V24", "V25", "V26"}  # Estos son los dead-ends reales, ocultos

if 'grafo_exacto' not in st.session_state:
    G = nx.MultiDiGraph()

    nodos_normales = ["Casa", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
                      "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20", "UDES"]
    # V21, V22, V23 son "cebos" — parecen nodos normales
    # V24, V25, V26 son los dead-ends reales, 2 pasos después del cebo
    nodos_trampa = ["V21", "V22", "V23", "V24", "V25", "V26"]
    G.add_nodes_from(nodos_normales + nodos_trampa)

    # === ARISTAS DIRIGIDAS (un solo sentido, con flecha) ===
    aristas_rectas = [
        ("Casa", "V1", 8),
        ("Casa", "V2", 14),
        ("Casa", "V3", 20),
        ("V1", "V4", 12),
        ("V1", "V5", 18),
        ("V2", "V5", 10),
        ("V2", "V6", 22),
        ("V3", "V6", 15),
        ("V3", "V7", 30),
        ("V4", "V8", 9),
        ("V4", "V9", 16),
        ("V5", "V9", 11),
        ("V5", "V10", 20),
        ("V6", "V10", 13),
        ("V6", "V11", 25),
        ("V7", "V11", 18),
        ("V7", "V12", 35),
        ("V8", "V13", 14),
        ("V9", "V13", 8),
        ("V9", "V14", 22),
        ("V10", "V14", 12),
        ("V10", "V15", 19),
        ("V11", "V15", 10),
        ("V11", "V16", 28),
        ("V12", "V16", 20),
        ("V13", "V17", 11),
        ("V14", "V17", 15),
        ("V14", "V18", 20),
        ("V15", "V18", 9),
        ("V15", "V19", 24),
        ("V16", "V19", 17),
        ("V16", "V20", 30),
        ("V17", "UDES", 18),
        ("V18", "UDES", 12),
        ("V19", "UDES", 22),
        ("V20", "UDES", 35),
    ]
    for u, v, w in aristas_rectas:
        G.add_edge(u, v, weight=w, edge_type='straight')

    # === ARISTAS PARALELAS ===
    G.add_edge("V12", "V7",  weight=28, edge_type='parallel', rad=0.25)
    G.add_edge("V7",  "V12", weight=35, edge_type='parallel', rad=-0.25)
    G.add_edge("V19", "V20", weight=14, edge_type='parallel', rad=0.25)
    G.add_edge("V20", "V19", weight=10, edge_type='parallel', rad=-0.25)

    # === ARISTAS BIDIRECCIONALES ===
    G.add_edge("V17", "V18", weight=6, edge_type='undirected')
    G.add_edge("V18", "V17", weight=6, edge_type='undirected_skip')
    G.add_edge("V4",  "V5",  weight=7, edge_type='undirected')
    G.add_edge("V5",  "V4",  weight=7, edge_type='undirected_skip')

    # === LAZOS ===
    G.add_edge("V9",  "V9",  weight=3, edge_type='loop')
    G.add_edge("V14", "V14", weight=4, edge_type='loop')

    # =========================================================================
    # === SISTEMA DE TRAMPAS — 2 pasos para caer, bien camufladas ===
    # =========================================================================
    #
    # TRAMPA 1: Cebo = V21 (zona media-alta), Dead-end = V24
    #   - V21 recibe de V8, V13, V4 → parece hub legítimo con 3 entradas
    #   - Desde V21 puedes ir a V22 (cebo 2) o a V24 (dead-end)
    #   - V24 recibe también de V8 para que no parezca aislado
    #
    G.add_edge("V4",  "V21", weight=10, edge_type='straight')  # entrada extra camuflaje
    G.add_edge("V8",  "V21", weight=6,  edge_type='straight')  # entrada tentadora
    G.add_edge("V13", "V21", weight=7,  edge_type='straight')  # entrada extra camuflaje
    G.add_edge("V21", "V22", weight=9,  edge_type='straight')  # salida aparente → cebo 2
    G.add_edge("V21", "V24", weight=5,  edge_type='straight')  # salida barata → TRAMPA
    G.add_edge("V9",  "V24", weight=8,  edge_type='straight')  # entrada a V24 desde nodo normal (camuflaje)
    # V24 → sin salida (dead-end real)

    #
    # TRAMPA 2: Cebo = V22 (zona media-alta), Dead-end = V25
    #   - V22 recibe de V21 (trampa 1) y de V10, V14 → parece puente natural
    #   - Desde V22 solo puedes ir a V25 (dead-end)
    #   - V25 recibe también de V15 para camuflarse
    #
    G.add_edge("V10", "V22", weight=8,  edge_type='straight')  # entrada camuflaje
    G.add_edge("V14", "V22", weight=6,  edge_type='straight')  # entrada tentadora
    G.add_edge("V22", "V25", weight=7,  edge_type='straight')  # única salida → TRAMPA
    G.add_edge("V15", "V25", weight=9,  edge_type='straight')  # entrada a V25 desde nodo normal (camuflaje)
    # V25 → sin salida (dead-end real)

    #
    # TRAMPA 3: Cebo = V23 (zona casi final), Dead-end = V26
    #   - V23 recibe de V17, V18, V19 → parece nodo de paso hacia UDES
    #   - Desde V23 solo puedes ir a V26 (dead-end)
    #   - V26 recibe también de V20 para no verse aislado
    #
    G.add_edge("V17", "V23", weight=8,  edge_type='straight')  # entrada tentadora (barato vs UDES)
    G.add_edge("V18", "V23", weight=6,  edge_type='straight')  # entrada muy tentadora
    G.add_edge("V19", "V23", weight=10, edge_type='straight')  # entrada camuflaje
    G.add_edge("V23", "V26", weight=4,  edge_type='straight')  # única salida → TRAMPA
    G.add_edge("V20", "V26", weight=7,  edge_type='straight')  # entrada a V26 desde nodo normal (camuflaje)
    # V26 → sin salida (dead-end real)

    st.session_state.grafo_exacto = G

# --- LAYOUT --- coordenadas más espaciadas
pos = {
    "Casa": (0,  10),
    "V1":  (3,  14),  "V2":  (3,  10),  "V3":  (3,   6),
    "V4":  (6,  17),  "V5":  (6,  12),  "V6":  (6,   8),  "V7":  (6,  4),
    "V8":  (9,  18),  "V9":  (9,  12),  "V10": (9,   8),  "V11": (9,  4),  "V12": (9, 1),
    "V13": (12, 16),  "V14": (12, 10),  "V15": (12,  6),  "V16": (12, 2),
    "V17": (16, 14),  "V18": (16,  9),  "V19": (16,  5),  "V20": (16, 1),
    "UDES": (20, 8),
    "V21": (10.5, 15.5),
    "V22": (14,   7.5),
    "V23": (18,  11.5),
    "V24": (10.5, 11),
    "V25": (14,   3.5),
    "V26": (20,  12),
}

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE DIBUJO DE ARISTAS PERSONALIZADO
# ──────────────────────────────────────────────────────────────────────────────
def draw_edge_label(ax, p1, p2, texto, offset_perp=0.0, color='#dc2626'):
    """Dibuja etiqueta de peso en el punto medio de una arista, con desplazamiento perpendicular."""
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = max(np.hypot(dx, dy), 1e-9)
    nx_ = -dy / length
    ny_ =  dx / length
    ax.text(mx + nx_ * offset_perp, my + ny_ * offset_perp,
            texto, color=color, fontsize=10, fontweight='bold',
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.75))


def draw_curved_no_arrow(ax, p1, p2, rad, color, linewidth=1.5):
    """Dibuja una curva sin punta de flecha usando FancyArrowPatch con arrowstyle Simple."""
    style = f"arc3,rad={rad}"
    patch = FancyArrowPatch(
        p1, p2,
        connectionstyle=style,
        arrowstyle=mpatches.ArrowStyle.Simple(head_width=0, head_length=0, tail_width=linewidth * 0.5),
        color=color,
        linewidth=linewidth,
        zorder=1
    )
    ax.add_patch(patch)


def get_curve_midpoint(p1, p2, rad):
    """Aproxima el punto medio de la curva arc3 para colocar la etiqueta."""
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = max(np.hypot(dx, dy), 1e-9)
    nx_ = -dy / length
    ny_ =  dx / length
    # El arco desplaza el punto medio rad * length/2 en la perpendicular
    bulge = rad * length * 0.5
    return mx + nx_ * bulge, my + ny_ * bulge


# ──────────────────────────────────────────────────────────────────────────────

st.title("🗺️ Optimización de Rutas: Misión UDES")
st.markdown("""
Encuentra el camino con **menor peso (costo/tiempo)** desde tu **Casa** hasta la **UDES**.
* Analiza topológicamente el grafo antes de moverte.
* Cuidado con los lazos y las vías de doble sentido con pesos distintos.
* ⚠️ Algunos caminos parecen atajos... pero pueden ser trampas sin salida.
""")

col1, col2 = st.columns([2, 1])

with col1:
    G   = st.session_state.grafo_exacto
    path = st.session_state.path

    fig, ax = plt.subplots(figsize=(22, 13))

    # ── Colores de nodos ──────────────────────────────────────────────────────
    node_colors = []
    for node in G.nodes():
        if node == "Casa":
            node_colors.append('#3b82f6')
        elif node == "UDES":
            node_colors.append('#22c55e')
        elif node == path[-1] and node not in ("Casa", "UDES"):
            node_colors.append('#f1c40f')
        else:
            node_colors.append('#1f2937')

    NODE_SIZE  = 1200
    EDGE_COLOR = '#94a3b8'
    TEXT_COLOR = '#dc2626'

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=NODE_SIZE, ax=ax,
                           edgecolors='white', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=8, font_weight='bold', ax=ax)

    # ── Dibujar aristas ───────────────────────────────────────────────────────
    for u, v, key, d in G.edges(data=True, keys=True):
        peso = d['weight']
        tipo = d['edge_type']
        p1   = pos[u]
        p2   = pos[v]

        # ---- Arista dirigida (flecha) ----------------------------------------
        if tipo == 'straight':
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)],
                arrows=True, arrowstyle='-|>', arrowsize=16,
                edge_color=EDGE_COLOR, width=1.5,
                node_size=NODE_SIZE, min_target_margin=16, ax=ax
            )
            draw_edge_label(ax, p1, p2, str(peso), offset_perp=0.35)

        # ---- Arista paralela (dos curvas arqueadas opuestas, sin flecha) -------
        elif tipo == 'parallel':
            rad = d.get('rad', 0.25)
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)],
                arrows=False,
                connectionstyle=f"arc3,rad={rad}",
                edge_color=EDGE_COLOR, width=1.5,
                node_size=NODE_SIZE, ax=ax
            )
            mx, my = get_curve_midpoint(p1, p2, rad)
            ax.text(mx, my, str(peso), color=TEXT_COLOR, fontsize=10,
                    fontweight='bold', ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.75))

        # ---- Arista no dirigida (línea simple sin flecha) --------------------
        elif tipo == 'undirected':
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)],
                arrows=False,
                edge_color=EDGE_COLOR, width=1.5,
                node_size=NODE_SIZE, ax=ax
            )
            draw_edge_label(ax, p1, p2, str(peso), offset_perp=0.35)

        # ---- Skip: el par inverso de undirected ya fue dibujado ---------------
        elif tipo == 'undirected_skip':
            pass  # No redibujar

        # ---- Lazo -------------------------------------------------------
        elif tipo == 'loop':
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)],
                arrows=True, arrowstyle='-|>', arrowsize=14,
                connectionstyle='arc3,rad=0.7',
                edge_color=EDGE_COLOR, width=1.5,
                node_size=NODE_SIZE, ax=ax
            )
            ax.text(p1[0] + 0.6, p1[1] + 0.8, str(peso),
                    color=TEXT_COLOR, fontsize=10, fontweight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.75))

    ax.axis('off')
    ax.set_xlim(-1, 22)
    ax.set_ylim(-1, 20)
    st.pyplot(fig)
    st.divider()

    # ── LÓGICA DE NAVEGACIÓN ──────────────────────────────────────────────────
    current_node = path[-1]

    tiempo_transcurrido = 0
    if st.session_state.start_time is not None:
        tiempo_transcurrido = time.time() - st.session_state.start_time

    st.subheader(f"📍 Posición: {current_node} | 🚦 Costo de Ruta: {st.session_state.current_weight}")
    st.caption(f"⏱️ Tiempo activo: {round(tiempo_transcurrido, 1)} s")

    if current_node == "UDES":
        st.success(f"¡LLEGASTE A LA UDES! Costo: {st.session_state.current_weight} | Tiempo: {round(tiempo_transcurrido, 2)} s.")
        st.balloons()

        with st.form("leaderboard_form"):
            nombre_jugador = st.text_input("Ingresa tu código o nombre:")
            if st.form_submit_button("Subir al Ranking") and nombre_jugador:
                guardar_leaderboard(nombre_jugador, st.session_state.current_weight, tiempo_transcurrido)
                st.session_state.path           = ["Casa"]
                st.session_state.current_weight = 0
                st.session_state.start_time     = None
                st.session_state.trampa_activada = False
                st.rerun()
    else:
        out_edges  = list(G.out_edges(current_node, data=True))
        # Filtrar aristas undirected_skip para que no aparezcan como botones de salida
        # (el grafo sí las tiene para que el jugador pueda moverse en ambos sentidos)
        is_dead_end = len(out_edges) == 0

        if is_dead_end:
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
        # Reiniciar: vuelve a Casa y a costo 0, pero el cronómetro NO se toca
        if st.button("🔄 Reiniciar desde Casa", type="primary", use_container_width=True):
            st.session_state.path            = ["Casa"]
            st.session_state.current_weight  = 0
            st.session_state.trampa_activada = False
            # start_time se deja intacto → el tiempo sigue corriendo
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