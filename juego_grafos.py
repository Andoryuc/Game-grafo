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
    # Desempate: 1ro menor costo de ruta, 2do menor tiempo pensando
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
    # Usamos DiGraph estándar (ideal para representar calles de 1 o 2 vías sin aristas múltiples en la misma dirección)
    G = nx.DiGraph() 
    nodos = ["Casa", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "UDES"]
    G.add_nodes_from(nodos) 
    
    # --- DEFINICIÓN DE RUTAS Y TRÁFICO (PESOS) ---
    # Rutas iniciales
    G.add_edge("Casa", "C1", weight=12)
    G.add_edge("Casa", "C2", weight=15)
    G.add_edge("Casa", "C4", weight=45) # Camino que parece directo pero tiene mucho tráfico
    
    # Red central (Mezcla de un solo sentido y doble sentido con diferentes pesos)
    G.add_edge("C1", "C3", weight=10)
    G.add_edge("C1", "C4", weight=25)
    
    G.add_edge("C2", "C5", weight=10)
    G.add_edge("C2", "C4", weight=30)
    
    G.add_edge("C3", "C6", weight=15)
    G.add_edge("C3", "C8", weight=5) # Entrada a un embotellamiento sin salida
    
    G.add_edge("C4", "C6", weight=20)
    G.add_edge("C4", "C7", weight=18)
    G.add_edge("C4", "C9", weight=55) # Troncal colapsada
    
    G.add_edge("C5", "C7", weight=12)
    G.add_edge("C5", "C10", weight=20)
    
    G.add_edge("C6", "C8", weight=5) # Otra entrada al embotellamiento
    G.add_edge("C6", "C9", weight=25)
    G.add_edge("C6", "C11", weight=30)
    
    G.add_edge("C7", "C2", weight=15) # Retorno de 1 vía
    G.add_edge("C7", "C9", weight=22)
    G.add_edge("C7", "C10", weight=10)
    
    # El nodo C8 es un callejón sin salida / rotonda infinita
    G.add_edge("C8", "C8", weight=2)
    
    G.add_edge("C9", "UDES", weight=40)
    G.add_edge("C9", "C11", weight=10)
    G.add_edge("C9", "C12", weight=15)
    
    G.add_edge("C10", "C12", weight=15)
    G.add_edge("C12", "C10", weight=10) # Doble vía con distinto tráfico de bajada
    
    G.add_edge("C11", "UDES", weight=15)
    G.add_edge("C12", "UDES", weight=25)

    st.session_state.grafo_trafico = G

st.title("🚦 Optimización de Redes: Simulador de Tráfico")
st.markdown("""
**Objetivo:** Trazar la ruta computacional con el **menor costo (tiempo en tráfico)** desde la **Casa** hasta la **UDES**.
* Las aristas representan calles. Las flechas indican el sentido vial permitido.
* Los números sobre las aristas representan el nivel de tráfico (peso).
* Analiza topológicamente el grafo antes de moverte. **No hay ayudas visuales.**
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_trafico
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO (MAPA URBANO) ---
    fig, ax = plt.subplots(figsize=(14, 8)) 
    
    # Coordenadas estructuradas para obligarlos a leer las líneas
    pos = {
        "Casa": (0, 3),
        "C1": (1, 4), "C2": (1, 2),
        "C3": (2, 5), "C4": (2, 3), "C5": (2, 1),
        "C6": (3, 4), "C7": (3, 2),
        "C8": (4, 5), "C9": (4, 3), "C10": (4, 1),
        "C11": (5, 4), "C12": (5, 2),
        "UDES": (6, 3)
    }

    # Todos los nodos son uniformes para no dar pistas, solo resaltamos el camino actual
    node_colors = ['#1f2937' if node not in path else '#3b82f6' for node in G.nodes()]
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1200, ax=ax, edgecolors='white', linewidths=2)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=11, font_weight='bold', ax=ax)
    
    # Dibujar aristas curvadas para evitar colisiones visuales
    nx.draw_networkx_edges(
        G, pos, 
        edge_color='#9ca3af', 
        arrows=True, 
        arrowstyle='-|>', 
        arrowsize=18, 
        connectionstyle='arc3,rad=0.1', 
        ax=ax
    )

    # Añadir los pesos directamente en las líneas
    edge_weights = {(u, v): d['weight'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(
        G, pos,
        edge_labels=edge_weights,
        font_color='#b91c1c',
        font_size=10,
        font_weight='bold',
        label_pos=0.3, # Coloca el número más cerca del nodo de origen para evitar que se pisen en vías de doble sentido
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=2)
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
        
        # Validar si están en un nodo sin salida o bucle infinito (como el C8)
        is_dead_end = len(out_edges) == 0 or all(u == v for u, v, d in out_edges)
        
        if is_dead_end:
            st.error("⚠️ Error de enrutamiento: Has entrado a una vía sin salida o embotellamiento total.")
            st.warning("De los errores se aprende, cada error me acerca más a mis sueños. Debes reiniciar la ruta.")
        else:
            st.write("Intersecciones disponibles:")
            cols = st.columns(min(len(out_edges), 4))
            for i, (u, v, data) in enumerate(out_edges):
                col = cols[i % len(cols)]
                # El botón ya no dice el peso, tienen que mirar el grafo
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