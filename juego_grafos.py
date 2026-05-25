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

NODOS_TRAMPA = {"V21", "V22", "V23"}

if 'grafo_exacto' not in st.session_state:
    G = nx.MultiDiGraph()

    nodos_normales = ["Casa", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
                      "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20", "UDES"]
    nodos_trampa = ["V21", "V22", "V23"]
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

    # === ARISTAS PARALELAS (doble sentido con pesos DISTINTOS → dos curvas opuestas, sin flecha) ===
    # V12 ↔ V7
    G.add_edge("V12", "V7", weight=28, edge_type='parallel', rad=0.25)
    G.add_edge("V7",  "V12", weight=35, edge_type='parallel', rad=-0.25)

    # V19 ↔ V20
    G.add_edge("V19", "V20", weight=14, edge_type='parallel', rad=0.25)
    G.add_edge("V20", "V19", weight=10, edge_type='parallel', rad=-0.25)

    # === ARISTAS BIDIRECCIONALES (mismo peso o tratadas como no dirigidas → una sola línea sin flecha) ===
    # V17 ↔ V18 (atajo)
    G.add_edge("V17", "V18", weight=6,  edge_type='undirected')
    G.add_edge("V18", "V17", weight=6,  edge_type='undirected_skip')  # skip: no redibujar

    # V4 ↔ V5 (atajo)
    G.add_edge("V4",  "V5",  weight=7,  edge_type='undirected')
    G.add_edge("V5",  "V4",  weight=7,  edge_type='undirected_skip')

    # === LAZOS ===
    G.add_edge("V9",  "V9",  weight=3, edge_type='loop')
    G.add_edge("V14", "V14", weight=4, edge_type='loop')

    # === TRAMPAS CAMUFLADAS (V21, V22, V23 — nombres inocentes, posición central, sin salida) ===
    # V21: accesible desde V5 y V9 (zona media, parece un hub legítimo con dos entradas)
    G.add_edge("V5",  "V21", weight=6,  edge_type='straight')   # Costo bajo desde V5
    G.add_edge("V9",  "V21", weight=4,  edge_type='straight')   # Muy tentador desde V9 — sin salida

    # V22: accesible desde V10 y V14 (zona media-alta, parece puente hacia V18)
    G.add_edge("V10", "V22", weight=7,  edge_type='straight')   # Parece atajo a zona alta
    G.add_edge("V14", "V22", weight=5,  edge_type='straight')   # Costo irresistible — sin salida

    # V23: accesible desde V15 y V16 (zona alta, a un paso de la UDES)
    G.add_edge("V15", "V23", weight=8,  edge_type='straight')   # Parece ruta rápida final
    G.add_edge("V16", "V23", weight=6,  edge_type='straight')   # Costo tentador — sin salida

    st.session_state.grafo_exacto = G

# --- LAYOUT ---
pos = {
    "Casa": (0, 6),
    "V1":  (2, 8),  "V2":  (2, 6),  "V3":  (2, 4),
    "V4":  (4, 9),  "V5":  (4, 7),  "V6":  (4, 5),  "V7":  (4, 3),
    "V8":  (6, 9),  "V9":  (6, 7),  "V10": (6, 5),  "V11": (6, 3),  "V12": (6, 1),
    "V13": (8, 8),  "V14": (8, 6),  "V15": (8, 4),  "V16": (8, 2),
    "V17": (10, 7), "V18": (10, 5), "V19": (10, 3), "V20": (10, 1),
    "UDES": (12, 4),
    # Trampas en medio del grafo, posiciones naturales entre nodos reales
    "V21": (6,  8.2),   # Entre V8 y V13, zona alta-media — parece nodo de paso
    "V22": (9,  5.5),   # Entre V14/V15 y V17/V18 — parece puente natural
    "V23": (10, 2.5),   # Entre V19 y V20 — parece nodo hacia UDES
}

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE DIBUJO DE ARISTAS PERSONALIZADO
# ──────────────────────────────────────────────────────────────────────────────
def draw_edge_label(ax, p1, p2, texto, offset_perp=0.0, color='#dc2626'):
    """Dibuja etiqueta de peso en el punto medio de una arista, con desplazamiento perpendicular."""
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    # Vector perpendicular
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = max(np.hypot(dx, dy), 1e-9)
    nx_ = -dy / length
    ny_ =  dx / length
    ax.text(mx + nx_ * offset_perp, my + ny_ * offset_perp,
            texto, color=color, fontsize=9, fontweight='bold',
            ha='center', va='center', bbox=dict(alpha=0))


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

    fig, ax = plt.subplots(figsize=(16, 10))

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

    NODE_SIZE  = 1000
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
            draw_edge_label(ax, p1, p2, str(peso), offset_perp=0.18)

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
            ax.text(mx, my, str(peso), color=TEXT_COLOR, fontsize=9,
                    fontweight='bold', ha='center', va='center', bbox=dict(alpha=0))

        # ---- Arista no dirigida (línea simple sin flecha) --------------------
        elif tipo == 'undirected':
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)],
                arrows=False,
                edge_color=EDGE_COLOR, width=1.5,
                node_size=NODE_SIZE, ax=ax
            )
            draw_edge_label(ax, p1, p2, str(peso), offset_perp=0.18)

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
            ax.text(p1[0] + 0.45, p1[1] + 0.55, str(peso),
                    color=TEXT_COLOR, fontsize=9, fontweight='bold',
                    ha='center', va='center', bbox=dict(alpha=0))

    ax.axis('off')
    ax.set_xlim(-0.8, 13.5)
    ax.set_ylim(-1.2, 10.5)
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