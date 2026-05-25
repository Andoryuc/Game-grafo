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

if 'grafo_trafico_25' not in st.session_state:
    G = nx.MultiDiGraph() 
    # Exactamente 25 nodos: Casa (1) + C1-C23 (23) + UDES (1)
    nodos = ["Casa"] + [f"C{i}" for i in range(1, 24)] + ["UDES"]
    G.add_nodes_from(nodos) 
    
    # --- FUNCIONES DE TOPOLOGÍA ---
    def add_twoway(u, v, w):
        G.add_edge(u, v, weight=w, edge_type='twoway')
        G.add_edge(v, u, weight=w, edge_type='twoway')

    def add_oneway(u, v, w):
        G.add_edge(u, v, weight=w, edge_type='oneway')

    def add_parallel(u, v, w1, w2):
        G.add_edge(u, v, weight=w1, edge_type='parallel', rad=0.2)
        G.add_edge(u, v, weight=w2, edge_type='parallel', rad=-0.2)
        
    def add_loop(u, w):
        G.add_edge(u, u, weight=w, edge_type='loop')

    # --- ESTRUCTURA DE LA RED ---
    # 1. Doble Sentido (Líneas grises, sin flechas)
    add_twoway("Casa", "C2", 15)
    add_twoway("C2", "C5", 10)
    add_twoway("C3", "C6", 12)
    add_twoway("C5", "C9", 20)
    add_twoway("C6", "C10", 18)
    add_twoway("C9", "C13", 10)
    add_twoway("C12", "C16", 15)
    add_twoway("C16", "C20", 12)
    add_twoway("C17", "C21", 20)
    add_twoway("C22", "UDES", 55) # Camino directo pero muy costoso

    # 2. Un Solo Sentido (Líneas azules con flecha)
    add_oneway("Casa", "C1", 12)
    add_oneway("Casa", "C3", 25)
    add_oneway("C1", "C4", 15)
    add_oneway("C1", "C5", 22)
    add_oneway("C4", "C8", 10)
    add_oneway("C7", "C10", 30)
    add_oneway("C8", "C11", 14)
    add_oneway("C10", "C14", 18)
    add_oneway("C11", "C15", 25)
    add_oneway("C14", "C17", 15)
    add_oneway("C15", "C18", 22)
    add_oneway("C17", "C20", 10)
    add_oneway("C18", "C22", 18)
    add_oneway("C21", "C23", 12)
    add_oneway("C19", "C23", 15)
    add_oneway("C23", "UDES", 10)
    add_oneway("C18", "C19", 8)
    add_oneway("C15", "C19", 14)

    # 3. Paralelos (Rutas alternativas entre los mismos puntos)
    add_parallel("C8", "C12", 40, 15) # Ojo clínico aquí
    add_parallel("C13", "C17", 35, 12)

    # 4. Lazos (Trampas mortales)
    add_loop("C11", 25) # Lazo en nodo de paso
    add_loop("C19", 5)  # Lazo justo antes del final
    
    # Callejón sin salida
    add_oneway("C16", "C19", 10)
    add_oneway("C20", "C23", 50) # Engaño de peso alto

    st.session_state.grafo_trafico_25 = G

st.title("🗺️ Optimización de Rutas: Misión UDES")
st.markdown("""
Encuentra el camino con **menor peso (costo/tiempo)** desde tu **Casa** hasta la **UDES**. 
* **Líneas sólidas sin flecha:** Calles de doble sentido.
* **Líneas con flecha:** Calles de un solo sentido.
* **Líneas curvas dobles:** Vías paralelas (tienen diferente costo, elige bien).
* Evalúa bien tus opciones. El tiempo sigue corriendo aunque te equivoques. 
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_trafico_25
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO (NUEVO LAYOUT DIAMANTE) ---
    fig, ax = plt.subplots(figsize=(16, 10)) 
    
    # Coordenadas calculadas matemáticamente para una matriz perfecta de 25 nodos
    pos = {
        "Casa": (0, 3),
        "C1": (2, 5), "C2": (2, 3), "C3": (2, 1),
        "C4": (4, 6), "C5": (4, 4), "C6": (4, 2), "C7": (4, 0),
        "C8": (6, 5), "C9": (6, 3), "C10": (6, 1),
        "C11": (8, 6), "C12": (8, 4), "C13": (8, 2), "C14": (8, 0),
        "C15": (10, 5), "C16": (10, 3), "C17": (10, 1),
        "C18": (12, 6), "C19": (12, 4), "C20": (12, 2), "C21": (12, 0),
        "C22": (14, 5), "C23": (14, 1),
        "UDES": (16, 3)
    }

    node_colors = ['#bdc3c7' if node not in path else '#f1c40f' for node in G.nodes()]
    node_colors[0] = '#3498db' if 'Casa' not in path[-1:] else '#f1c40f'
    node_colors[-1] = '#2ecc71' 
    
    # Tamaño de nodo fijo y constante
    NODE_SIZE = 1000
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=NODE_SIZE, ax=ax, edgecolors='black', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='black', font_size=9, font_weight='bold', ax=ax)
    
    # --- DIBUJADO DE ARISTAS CON MÁRGENES CORREGIDOS ---
    drawn_twoway = set()
    edge_labels = {}

    for u, v, key, d in G.edges(data=True, keys=True):
        peso = d['weight']
        tipo = d['edge_type']

        if tipo == 'twoway':
            if (v, u) not in drawn_twoway:
                nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=False, edge_color='#7f8c8d', width=2.5, node_size=NODE_SIZE, ax=ax)
                drawn_twoway.add((u, v))
                edge_labels[(u, v)] = peso
                
        elif tipo == 'oneway':
            # min_target_margin asegura que la flecha quede FUERA del círculo
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=18, edge_color='#2980b9', width=2, node_size=NODE_SIZE, min_target_margin=18, ax=ax)
            edge_labels[(u, v)] = peso
            
        elif tipo == 'parallel':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=15, connectionstyle=f"arc3,rad={d['rad']}", edge_color='#8e44ad', width=2, node_size=NODE_SIZE, min_target_margin=18, ax=ax)
            x = (pos[u][0] + pos[v][0]) / 2
            y = (pos[u][1] + pos[v][1]) / 2
            offset = 0.25 if d['rad'] > 0 else -0.25
            ax.text(x, y + offset, str(peso), color='#8e44ad', fontsize=10, fontweight='bold', ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1))
            
        elif tipo == 'loop':
            # Delegamos el loop a NetworkX pero lo estilizamos para que resalte
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=15, edge_color='#e74c3c', width=2.5, node_size=NODE_SIZE, ax=ax)
            # Dibujamos el texto del peso explícitamente arriba del nodo con un cuadro rojo
            ax.text(pos[u][0] + 0.3, pos[u][1] + 0.5, str(peso), color='white', fontsize=10, fontweight='bold', ha='center', va='center', bbox=dict(facecolor='#e74c3c', edgecolor='none', boxstyle='circle,pad=0.3'))

    # Etiquetas de aristas normales (oneway y twoway)
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, font_color='#2c3e50', font_size=10, font_weight='bold', label_pos=0.35,
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1)
    )

    # Eliminar bordes de la gráfica para un look más limpio
    ax.axis('off')
    st.pyplot(fig)
    st.divider()

    # --- LÓGICA DE NAVEGACIÓN ---
    current_node = path[-1]
    
    tiempo_transcurrido = 0
    if st.session_state.start_time is not None:
        tiempo_transcurrido = time.time() - st.session_state.start_time

    st.subheader(f"📍 Posición: {current_node} | 🚦 Tráfico Acumulado: {st.session_state.current_weight}")
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
                st.rerun()
    else:
        out_edges = list(G.out_edges(current_node, data=True))
        is_dead_end = len(out_edges) == 0
        
        if is_dead_end:
            st.error("⚠️ Error Crítico: Has entrado a un callejón sin salida.")
            st.warning("Reinicia la ruta para intentarlo de nuevo.")
        else:
            st.write("Intersecciones disponibles:")
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
        st.caption("Si te equivocas, puedes reiniciar. El peso volverá a 0, pero tu tiempo seguirá corriendo.")
        if st.button("🔄 Reiniciar desde Casa", type="primary", use_container_width=True):
            st.session_state.path = ["Casa"]
            st.session_state.current_weight = 0 
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time()
            st.rerun()

with col2:
    st.subheader("🏆 Leaderboard Dijkstra")
    st.write("*(Desempate por tiempo)*")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin registros. Sé el primero en encontrar la ruta óptima.")