import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import time
import pandas as pd

# --- FUNCIONES DE BASE DE DATOS (LEADERBOARD) ---
ARCHIVO_LEADERBOARD = "leaderboard.json"

def cargar_leaderboard():
    if os.path.exists(ARCHIVO_LEADERBOARD):
        with open(ARCHIVO_LEADERBOARD, "r") as f:
            return json.load(f)
    return []

def guardar_leaderboard(nombre, pasos, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Hacker": nombre, "Pasos": pasos, "Tiempo (seg)": round(tiempo, 2)})
    datos = sorted(datos, key=lambda x: (x["Pasos"], x["Tiempo (seg)"]))
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cyber-Maze: Pseudografo Dirigido", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = [1]
if 'steps_taken' not in st.session_state:
    st.session_state.steps_taken = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'graph' not in st.session_state:
    # Usamos MultiDiGraph: Permite direcciones, aristas paralelas y lazos.
    G = nx.MultiDiGraph() 
    
    # --- CONSTRUCCIÓN DEL GRAFO DEL TERROR ---
    # Enlaces unidireccionales normales (origen, destino)
    normal_edges = [
        (1, 2), (1, 5), (1, 8), (2, 3), (3, 4), (4, 11), 
        (5, 6), (6, 7), (7, 12), (8, 9), (9, 10), (10, 15),
        (11, 16), (12, 16), (15, 14), (14, 13), (13, 18),
        (16, 17), (17, 22), (22, 23), (23, 24), (24, 25),
        (25, 20), (20, 19), (19, 28), (28, 29), (29, 30)
    ]
    G.add_edges_from(normal_edges)
    
    # 1. Enlaces Trampa Unidireccionales (Te dejan sin salida)
    G.add_edges_from([(4, 5), (12, 11), (17, 18), (24, 29)]) # 24 a 29 parece un atajo, pero 29 es unidireccional y bloquea.
    
    # 2. Lazos (Self-loops - Errores de routing)
    G.add_edges_from([(3, 3), (9, 9), (16, 16), (22, 22)])
    
    # 3. Aristas Paralelas (Múltiples puertos entre dos nodos)
    # Entre el 7 y el 8 hay dos cables. Uno va de 7->8, otro de 8->7.
    G.add_edge(7, 8, label="Puerto 80")
    G.add_edge(8, 7, label="Puerto 443")
    # Entre 25 y 26 hay dos aristas en la MISMA dirección (Paralelas puras)
    G.add_edge(25, 26, label="Cable A")
    G.add_edge(25, 26, label="Cable B")
    G.add_edge(26, 27)
    G.add_edge(27, 30) # Ruta alterna escondida
    
    st.session_state.graph = G

st.title("☠️ Protocolo Pseudografo: El Laberinto de un Solo Sentido")
st.markdown("""
**Misión:** Lleva el paquete desde el **Nodo 1** hasta el **Nodo 30**.
⚠️ **ADVERTENCIA TÉCNICA:** * **Grafo Dirigido:** Las flechas indican el ÚNICO sentido permitido.
* **Lazos:** Si te haces ping a ti mismo (ej. 3->3), pierdes un paso.
* **Cables Paralelos:** Algunos nodos tienen múltiples conexiones al mismo destino o en contravía.
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.graph
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO MULTIDIRIGIDO ---
    fig, ax = plt.subplots(figsize=(9, 7))
    pos = nx.spring_layout(G, seed=123, k=0.6) 

    node_colors = []
    for node in G.nodes():
        if node == 1: node_colors.append('#f1c40f') # Inicio
        elif node == 30: node_colors.append('#9b59b6') # Meta
        elif path and node == path[-1]: node_colors.append('#3498db') # Actual
        elif node in path: node_colors.append('#2ecc71') # Rastro
        else: node_colors.append('#34495e') # Desconocido
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=10, font_weight='bold', ax=ax)
    
    # Dibujar aristas con flechas y curvas para notar las paralelas y lazos
    nx.draw_networkx_edges(
        G, pos, 
        edge_color='#bdc3c7', 
        arrows=True, 
        arrowstyle='-|>', 
        arrowsize=18, 
        connectionstyle='arc3,rad=0.2', # Esta curva es magia, permite ver aristas paralelas y bidireccionales
        ax=ax
    )

    st.pyplot(fig)
    st.divider()

    # --- LÓGICA DEL JUEGO ---
    current_node = path[-1]
    
    if len(path) == 1 and st.session_state.start_time is None:
         st.info("El reloj está en cero. Analiza las flechas antes de moverte...")
    
    st.subheader(f"📡 Terminal: Nodo {current_node} | 👣 Pasos: {st.session_state.steps_taken}")
    
    if current_node == 30:
        tiempo_total = time.time() - st.session_state.start_time
        st.success(f"¡SISTEMA HACKEADO! Pasos: {st.session_state.steps_taken} | Tiempo: {round(tiempo_total, 2)} s.")
        st.balloons()
        
        with st.form("leaderboard_form"):
            nombre_jugador = st.text_input("Ingresa tu alias de Hacker:")
            if st.form_submit_button("Guardar Código") and nombre_jugador:
                guardar_leaderboard(nombre_jugador, st.session_state.steps_taken, tiempo_total)
                st.success("¡Base de datos actualizada!")
                st.session_state.path = [1]
                st.session_state.steps_taken = 0
                st.session_state.start_time = None
                st.rerun()
                
        if st.button("Reinicio rápido"):
            st.session_state.path = [1]
            st.session_state.steps_taken = 0
            st.session_state.start_time = None
            st.rerun()
    else:
        # Obtener los puertos de salida (Out-edges en un grafo dirigido)
        out_edges = list(G.out_edges(current_node, data=True))
        
        # Filtrar destinos válidos (no repetir nodos a menos que sea un lazo engañoso)
        valid_moves = []
        for u, v, data in out_edges:
            # Puedes caer en un lazo, o ir a un nodo no visitado
            if v not in path or v == current_node:
                valid_moves.append((v, data.get('label', f"Enlace estándar")))
                
        if not valid_moves:
            st.error("⚠️ FATAL ERROR: Llegaste a un nodo sin salidas válidas. Cortafuegos activado. ¡Retrocede!")
        else:
            st.write("Puertos abiertos descubiertos (Sigue las flechas):")
            cols = st.columns(min(len(valid_moves), 4))
            for i, (target, label) in enumerate(valid_moves):
                # Distribuir botones en columnas
                col = cols[i % len(cols)]
                if col.button(f"Mover al Nodo {target}\n({label})", key=f"btn_{i}_{target}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    
                    if target == current_node:
                        st.warning("¡Bucle detectado! Hiciste ping a ti mismo. Pierdes 1 paso.")
                        st.session_state.steps_taken += 1
                    else:
                        st.session_state.path.append(target)
                        st.session_state.steps_taken += 1
                    st.rerun()
                    
        st.write("")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if len(path) > 1:
                if st.button("⬅️ Inyectar código de retroceso (+1 paso penalización)"):
                    st.session_state.path.pop()
                    st.session_state.steps_taken += 1
                    st.rerun()
        with col_btn2:
            if st.button("🛑 Formatear (Reinicio total)", type="secondary"):
                st.session_state.path = [1]
                st.session_state.steps_taken = 0
                st.session_state.start_time = None
                st.rerun()

with col2:
    st.subheader("🏆 Elite Global")
    st.write("*(Ordenado por menos pasos)*")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin registros.")