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

if 'grafo_trafico_pro' not in st.session_state:
    # MultiDiGraph permite multiples aristas entre los mismos nodos (Paralelos)
    G = nx.MultiDiGraph() 
    nodos = ["Casa", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", 
             "C10", "C11", "C12", "C13", "C14", "C15", "C16", "UDES"]
    G.add_nodes_from(nodos) 
    
    # --- FUNCIONES DE TOPOLOGÍA ---
    def add_twoway(u, v, w):
        G.add_edge(u, v, weight=w, edge_type='twoway')
        G.add_edge(v, u, weight=w, edge_type='twoway')

    def add_oneway(u, v, w):
        G.add_edge(u, v, weight=w, edge_type='oneway')

    def add_parallel(u, v, w1, w2):
        G.add_edge(u, v, weight=w1, edge_type='parallel', rad=0.2, pos=0.3)
        G.add_edge(u, v, weight=w2, edge_type='parallel', rad=-0.2, pos=0.7)
        
    def add_loop(u, w):
        G.add_edge(u, u, weight=w, edge_type='loop')

    # 1. Rutas de doble sentido (Sin flechas, puedes ir y volver)
    add_twoway("Casa", "C2", 12)
    add_twoway("C2", "C5", 10)
    add_twoway("C3", "C6", 15)
    add_twoway("C5", "C8", 8)
    add_twoway("C7", "C10", 12)
    add_twoway("C11", "C14", 15)
    add_twoway("C13", "C16", 10)

    # 2. Rutas de un solo sentido (Con flechas)
    add_oneway("Casa", "C1", 18)
    add_oneway("Casa", "C3", 25)
    add_oneway("C1", "C4", 15)
    add_oneway("C2", "C4", 20)
    add_oneway("C4", "C7", 10)
    add_oneway("C6", "C9", 22)
    add_oneway("C8", "C11", 14)
    add_oneway("C9", "C12", 20)
    add_oneway("C10", "C13", 18)
    add_oneway("C12", "C15", 25)
    add_oneway("C14", "UDES", 30)
    add_oneway("C16", "UDES", 22)

    # 3. Enlaces Paralelos (Dos opciones para ir del mismo nodo A al B)
    # Ejemplo: Una troncal rápida pero congestionada vs un callejón
    add_parallel("C4", "C6", 40, 15) 
    add_parallel("C7", "C9", 35, 12)
    add_parallel("C10", "C14", 55, 18)

    # 4. Trampas y Lazos (Loops camuflados en el mapa)
    # Trampa 1: C15 parece estar pegado a la UDES, pero no tiene salida a ella.
    add_oneway("C11", "C15", 5) # Atractivo por el bajo peso
    add_loop("C15", 10) # Te quedas dando vueltas
    add_oneway("C15", "C12", 30) # Única salida te devuelve atrás con mucho peso
    
    # Trampa 2: Lazo en medio de una intersección concurrida
    add_loop("C9", 5)

    st.session_state.grafo_trafico_pro = G

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
    G = st.session_state.grafo_trafico_pro
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO (MAPA URBANO) ---
    fig, ax = plt.subplots(figsize=(14, 9)) 
    
    # Coordenadas estructuradas para que parezca un mapa de ciudad denso
    pos = {
        "Casa": (0, 2),
        "C1": (1, 4), "C2": (1, 2), "C3": (1, 0),
        "C4": (2, 3), "C5": (2, 1),
        "C6": (3, 4), "C7": (3, 2), "C8": (3, 0),
        "C9": (4, 3), "C10": (4, 1),
        "C11": (5, 4), "C12": (5, 2), "C13": (5, 0),
        "C14": (6, 3), "C15": (6, 4), "C16": (6, 1),
        "UDES": (7, 2)
    }

    node_colors = ['#bdc3c7' if node not in path else '#f1c40f' for node in G.nodes()]
    node_colors[0] = '#3498db' if 'Casa' not in path[-1:] else '#f1c40f' # Casa azul
    node_colors[-1] = '#2ecc71' # Udes verde
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1000, ax=ax, edgecolors='black', linewidths=1.5)
    nx.draw_networkx_labels(G, pos, font_color='black', font_size=9, font_weight='bold', ax=ax)
    
    # Dibujado por capas para respetar las reglas visuales
    drawn_twoway = set()
    edge_labels = {}

    for u, v, key, d in G.edges(data=True, keys=True):
        peso = d['weight']
        tipo = d['edge_type']

        if tipo == 'twoway':
            if (v, u) not in drawn_twoway:
                nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=False, edge_color='#7f8c8d', width=2.5, ax=ax)
                drawn_twoway.add((u, v))
                edge_labels[(u, v)] = peso
                
        elif tipo == 'oneway':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=18, edge_color='#2980b9', width=2, ax=ax)
            edge_labels[(u, v)] = peso
            
        elif tipo == 'parallel':
            # Paralelos usan curvatura y se guardan en el dict con posiciones diferentes
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=15, connectionstyle=f"arc3,rad={d['rad']}", edge_color='#8e44ad', width=2, ax=ax)
            # Para que nx.draw_networkx_edge_labels no sobreescriba paralelos, lo dibujamos directo con matplotlib o usamos un truco de offset
            x = (pos[u][0] + pos[v][0]) / 2
            y = (pos[u][1] + pos[v][1]) / 2
            offset = 0.15 if d['rad'] > 0 else -0.15
            ax.text(x, y + offset, str(peso), color='#c0392b', fontsize=10, fontweight='bold', ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1))
            
        elif tipo == 'loop':
            nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], arrows=True, arrowstyle='-|>', arrowsize=15, connectionstyle='arc3, rad=0.6', edge_color='#e74c3c', width=2, ax=ax)
            ax.text(pos[u][0], pos[u][1] + 0.3, str(peso), color='#c0392b', fontsize=10, fontweight='bold', ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1))

    # Dibujar labels estandar (ignora paralelos y loops que ya se dibujaron manual)
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, font_color='#c0392b', font_size=10, font_weight='bold',
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1)
    )

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
            st.warning("From error one learns, each error brings me closer to my dreams. Reinicia la ruta para intentarlo de nuevo.")
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