import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import time
import pandas as pd

# --- FUNCIONES DE BASE DE DATOS (LEADERBOARD) ---
ARCHIVO_LEADERBOARD = "leaderboard_oficial.json"

def cargar_leaderboard():
    if os.path.exists(ARCHIVO_LEADERBOARD):
        with open(ARCHIVO_LEADERBOARD, "r") as f:
            return json.load(f)
    return []

def guardar_leaderboard(nombre, pasos, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Hacker": nombre, "Pasos Totales": pasos, "Tiempo (seg)": round(tiempo, 2)})
    datos = sorted(datos, key=lambda x: (x["Pasos Totales"], x["Tiempo (seg)"]))
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cyber-Maze: Nivel 40", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = [1]
if 'steps_taken' not in st.session_state:
    st.session_state.steps_taken = 0
if 'penalties' not in st.session_state:
    st.session_state.penalties = 0  
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

if 'grafo_40_v4' not in st.session_state:
    G = nx.MultiDiGraph() 
    G.add_nodes_from(range(1, 41)) 
    
    def add_bidi(u, v, label="Bidireccional"):
        G.add_edge(u, v, label=label)
        G.add_edge(v, u, label=label)

    def add_uni(u, v, label="Unidireccional"):
        G.add_edge(u, v, label=label)

    # --- LA RUTA MAESTRA ---
    add_bidi(1, 4)
    add_bidi(4, 8)
    add_bidi(8, 13)
    add_uni(13, 17, "Unidireccional") 
    add_bidi(17, 21)
    add_bidi(21, 26)
    add_bidi(26, 30)
    add_uni(30, 34, "Unidireccional") 
    add_bidi(34, 37)
    add_bidi(37, 39)
    add_bidi(39, 40)

    # --- TRAMPAS, CALLEJONES Y BUCLES ---
    add_uni(1, 2)
    add_bidi(2, 3)
    add_uni(3, 3, "Loop Mortal") 
    add_bidi(1, 6)
    add_uni(6, 7)
    add_uni(7, 2, "Trampa Retorno") 

    add_bidi(4, 9)
    add_bidi(9, 10)
    add_bidi(10, 11)
    add_uni(11, 11, "Loop Mortal")
    add_bidi(8, 12)
    add_uni(12, 16)
    add_bidi(16, 20)
    add_uni(20, 24)
    add_uni(24, 24, "Loop Mortal")

    add_bidi(13, 14)
    add_bidi(14, 15)
    add_uni(15, 13, "Retorno Oculto")

    add_bidi(21, 22)
    add_uni(22, 17, "Caída libre")
    add_uni(21, 25)
    add_bidi(25, 29)
    add_uni(29, 33) 
    add_bidi(26, 27)
    add_bidi(27, 28)
    add_uni(28, 23)
    add_uni(23, 18)
    add_uni(18, 19)
    add_uni(19, 13, "Trampa Retorno Masivo")

    add_bidi(30, 31)
    add_bidi(31, 32)
    add_uni(32, 26, "Retorno")
    add_bidi(34, 35)
    add_bidi(38, 35)
    add_uni(35, 36)
    add_uni(36, 36, "Loop Mortal")
    add_uni(39, 38)
    
    add_uni(17, 21, "Cable Secundario")

    st.session_state.grafo_40_v4 = G

st.title("La Pesadilla de Dijkstra")
st.markdown("""
**Misión:** Lleva el paquete desde el **Nodo 1** hasta el **Nodo 40**.
⚠️ **REGLAS DEL SISTEMA:** * Existen enlaces **Bidireccionales** (puedes ir y volver) y **Unidireccionales** (solo ida).
* **ATENCIÓN:** En este sistema no existe el "Ctrl+Z". Si te metes en un callejón sin salida, tu única opción es **Reiniciar** el sistema. Al hacerlo, vuelves al Nodo 1 y se te suma un castigo directo de **+5 pasos** a tu marcador final. ¡Piensa antes de moverte!
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_40_v4
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO ---
    fig, ax = plt.subplots(figsize=(18, 12)) 
    pos = nx.spring_layout(G, seed=150, k=2.8, iterations=300) 

    node_colors = []
    for node in G.nodes():
        if node == 1: node_colors.append('#f1c40f') 
        elif node == 40: node_colors.append('#9b59b6') 
        elif path and node == path[-1]: node_colors.append('#3498db') 
        elif node in path: node_colors.append('#2ecc71') 
        else: node_colors.append('#34495e') 
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=320, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=8, font_weight='bold', ax=ax)
    
    nx.draw_networkx_edges(
        G, pos, 
        edge_color='#bdc3c7', 
        arrows=True, 
        arrowstyle='-|>', 
        arrowsize=16, 
        connectionstyle='arc3,rad=0.25', 
        ax=ax
    )

    st.pyplot(fig)
    st.divider()

    # --- LÓGICA DEL JUEGO ---
    current_node = path[-1]
    
    total_pasos = st.session_state.steps_taken + st.session_state.penalties
    
    if len(path) == 1 and st.session_state.start_time is None and total_pasos == 0:
         st.info("El reloj está en cero. Analiza las flechas antes de tu primer movimiento...")
    
    st.subheader(f"📡 Terminal: Nodo {current_node} | 👣 Pasos Acumulados: {total_pasos} (Penalidades: {st.session_state.penalties})")
    
    if current_node == 40:
        tiempo_total = time.time() - st.session_state.start_time
        st.success(f"¡SISTEMA HACKEADO! Pasos Totales: {total_pasos} | Tiempo: {round(tiempo_total, 2)} s.")
        st.balloons()
        
        with st.form("leaderboard_form"):
            nombre_jugador = st.text_input("Ingresa tu alias de Hacker:")
            if st.form_submit_button("Guardar Récord") and nombre_jugador:
                guardar_leaderboard(nombre_jugador, total_pasos, tiempo_total)
                st.success("¡Base de datos actualizada!")
                st.session_state.path = [1]
                st.session_state.steps_taken = 0
                st.session_state.penalties = 0
                st.session_state.start_time = None
                st.rerun()
    else:
        out_edges = list(G.out_edges(current_node, data=True))
        
        valid_moves = []
        for u, v, data in out_edges:
            valid_moves.append((v, data.get('label', f"Enlace estándar")))
                
        if not valid_moves:
            st.error("⚠️ FATAL ERROR: Nodo sin salida. Te bloqueaste a ti mismo. Tu única opción es reiniciar el sistema.")
        else:
            st.write("Puertos abiertos descubiertos (Sigue las flechas):")
            cols = st.columns(min(len(valid_moves), 4))
            for i, (target, label) in enumerate(valid_moves):
                col = cols[i % len(cols)]
                if col.button(f"Mover al {target}\n({label})", key=f"btn_{i}_{target}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    
                    if target == current_node:
                        st.warning("¡Bucle detectado! Hiciste ping a ti mismo.")
                    
                    st.session_state.path.append(target)
                    st.session_state.steps_taken += 1
                    st.rerun()
                    
        st.write("")
        # ÚNICO BOTÓN RESTANTE: REINICIAR
        if st.button("🛑 Reinicio de Sistema (Castigo: +5 pasos)", type="primary", use_container_width=True):
            st.session_state.path = [1]
            st.session_state.steps_taken = 0 
            st.session_state.penalties += 5 
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time()
            st.rerun()

with col2:
    st.subheader("🏆 Elite Global")
    st.write("*(Ordenado por MENOS pasos totales)*")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin registros.")