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
    datos.append({"Estudiante": nombre, "Costo (Tiempo en Tráfico)": peso, "Tiempo de Resolución (s)": round(tiempo, 2)})
    datos = sorted(datos, key=lambda x: (x["Costo (Tiempo en Tráfico)"], x["Tiempo de Resolución (s)"]))
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

if 'grafo_trafico' not in st.session_state:
    G = nx.DiGraph() 
    nodos = ["Casa", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "UDES"]
    G.add_nodes_from(nodos) 
    
    # Funciones auxiliares para clasificar las aristas y dibujarlas correctamente
    def add_two_way(u, v, w):
        G.add_edge(u, v, weight=w, edge_type='twoway')
        G.add_edge(v, u, weight=w, edge_type='twoway')

    def add_one_way(u, v, w):
        G.add_edge(u, v, weight=w, edge_type='oneway')

    # 1. Doble sentido (Sin flechas visuales, puedes ir y volver)
    add_two_way("Casa", "C1", 12)
    add_two_way("Casa", "C2", 15)
    add_two_way("C1", "C3", 10)
    add_two_way("C2", "C5", 12)
    add_two_way("C5", "C10", 20)
    add_two_way("C7", "C10", 10)
    add_two_way("C10", "C12", 15)
    
    # 2. Un solo sentido (Con flecha visual, restricciones reales)
    add_one_way("Casa", "C4", 45) # Engaño visual
    add_one_way("C1", "C4", 25)
    add_one_way("C2", "C4", 30)
    add_one_way("C3", "C6", 15)
    add_one_way("C4", "C6", 20)
    add_one_way("C4", "C7", 18)
    add_one_way("C4", "C9", 55) # Troncal colapsada
    add_one_way("C6", "C9", 25)
    add_one_way("C7", "C2", 15) # Retorno obligado
    add_one_way("C7", "C9", 22)
    add_one_way("C9", "UDES", 40)
    add_one_way("C9", "C11", 10)
    add_one_way("C9", "C12", 15)
    add_one_way("C11", "UDES", 15)
    add_one_way("C12", "UDES", 25)
    
    # 3. El Lazo / Embotellamiento
    add_one_way("C3", "C8", 5)
    add_one_way("C6", "C8", 5)
    G.add_edge("C8", "C8", weight=2, edge_type='loop')

    st.session_state.grafo_trafico = G

st.title("🚦 Optimización de Redes: Simulador de Tráfico")
st.markdown("""
**Objetivo:** Trazar la ruta computacional con el **menor costo (tiempo en tráfico)** desde la **Casa** hasta la **UDES**.
* Las aristas representan calles. Las líneas sin flechas son de doble sentido, las que tienen flechas son de un solo sentido.
* Los números sobre las aristas representan el nivel de tráfico (peso). Cuidado con los lazos.
* Analiza topológicamente el grafo antes de moverte. Los botones no te dirán el peso de la ruta.
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_trafico
    path = st.session_state.path

    fig, ax = plt.subplots(figsize=(14, 8)) 
    
    # Coordenadas estructuradas para un mapa claro
    pos = {
        "Casa": (0, 3),
        "C1": (1, 5), "C2": (1, 1),
        "C3": (3, 5), "C4": (3, 3), "C5": (3, 1),
        "C6": (5, 5), "C7": (5, 3),
        "C8": (7, 6.5), # Nodo del lazo aislado arriba
        "C9": (7, 3), "C10": (7, 1),
        "C11": (9, 4), "C12": (9, 2),
        "UDES": (11, 3)
    }

    node_colors = ['#1f2937' if node not in path else '#3b82f6' for node in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1200, ax=ax, edgecolors='white', linewidths=2)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=11, font_weight='bold', ax=ax)
    
    # --- DIBUJADO DE ARISTAS POR CATEGORÍA ---
    twoway_edges = []
    seen = set()
    for u, v, d in G.edges(data=True):
        if d['edge_type'] == 'twoway':
            if (v, u) not in seen:
                twoway_edges.append((u, v))
                seen.add((u, v))
                
    oneway_edges = [(u, v) for u, v, d in G.edges(data=True) if d['edge_type'] == 'oneway']
    loop_edges = [(u, v) for u, v, d in G.edges(data=True) if d['edge_type'] == 'loop']
    
    # 1. Dibujar Doble Sentido (Sin flechas)
    nx.draw_networkx_edges(G, pos, edgelist=twoway_edges, arrows=False, edge_color='#64748b', width=2.5, ax=ax)
    # 2. Dibujar Un Sentido (Con flechas)
    nx.draw_networkx_edges(G, pos, edgelist=oneway_edges, arrows=True, arrowstyle='-|>', arrowsize=20, edge_color='#3b82f6', width=2, ax=ax)
    # 3. Dibujar Lazos (Rojo para advertencia)
    nx.draw_networkx_edges(G, pos, edgelist=loop_edges, arrows=True, arrowstyle='-|>', arrowsize=20, edge_color='#ef4444', connectionstyle='arc3, rad=0.6', width=2.5, ax=ax)

    # Añadir los pesos evitando duplicados visuales en las vías de doble sentido
    edge_labels = {}
    for u, v, d in G.edges(data=True):
        if d['edge_type'] == 'twoway':
            if (v, u) not in edge_labels:
                edge_labels[(u, v)] = d['weight']
        else:
            edge_labels[(u, v)] = d['weight']

    nx.draw_networkx_edge_labels(
        G, pos,
        edge_labels=edge_labels,
        font_color='#b91c1c',
        font_size=11,
        font_weight='bold',
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=2)
    )

    st.pyplot(fig)
    st.divider()

    # --- LÓGICA DE NAVEGACIÓN ---
    current_node = path[-1]
    
    tiempo_transcurrido = 0
    if st.session_state.start_time is not None:
        tiempo_transcurrido = time.time() - st.session_state.start_time

    st.subheader(f"📍 Posición: {current_node} | 🚦 Tráfico Acumulado (Peso): {st.session_state.current_weight}")
    st.caption(f"⏱️ Tiempo de resolución: {round(tiempo_transcurrido, 1)} s")
    
    if current_node == "UDES":
        st.success(f"¡SISTEMA RESUELTO! Costo de ruta: {st.session_state.current_weight} | Tiempo: {round(tiempo_transcurrido, 2)} s.")
        
        with st.form("leaderboard_form"):
            nombre_jugador = st.text_input("Ingresa tu código o nombre de estudiante:")
            if st.form_submit_button("Subir al Ranking") and nombre_jugador:
                guardar_leaderboard(nombre_jugador, st.session_state.current_weight, tiempo_transcurrido)
                st.session_state.path = ["Casa"]
                st.session_state.current_weight = 0
                st.session_state.start_time = None
                st.rerun()
    else:
        out_edges = list(G.out_edges(current_node, data=True))
        
        # Validación de lazo infinito o callejón sin salida (Ej: El nodo C8)
        is_dead_end = len(out_edges) == 0 or all(u == v for u, v, d in out_edges)
        
        if is_dead_end:
            st.error("⚠️ Error de enrutamiento: Has entrado a una vía sin salida o embotellamiento total (Lazo).")
            st.warning("Debes reiniciar la ruta. Tu tiempo seguirá corriendo.")
        else:
            st.write("Intersecciones disponibles:")
            cols = st.columns(min(len(out_edges), 4))
            for i, (u, v, data) in enumerate(out_edges):
                col = cols[i % len(cols)]
                # Botón ciego: Obliga a mirar el mapa
                if col.button(f"Mover a {v}", key=f"btn_{u}_{v}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    
                    st.session_state.path.append(v)
                    st.session_state.current_weight += data['weight']
                    st.rerun()
                    
        st.write("")
        st.caption("Al reiniciar, el tráfico (peso) vuelve a 0, pero tu tiempo de resolución seguirá corriendo.")
        if st.button("🔄 Abortar y Reiniciar desde Casa", type="primary", use_container_width=True):
            st.session_state.path = ["Casa"]
            st.session_state.current_weight = 0 
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time()
            st.rerun()

with col2:
    st.subheader("🏆 Leaderboard")
    st.write("*(Clasificación por menor tráfico y tiempo)*")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin registros. Demuestra tus conocimientos de grafos.")