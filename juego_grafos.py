import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import time
import pandas as pd

# --- FUNCIONES DE BASE DE DATOS (LEADERBOARD) ---
ARCHIVO_LEADERBOARD = "ranking_udes.json"

def cargar_leaderboard():
    if os.path.exists(ARCHIVO_LEADERBOARD):
        with open(ARCHIVO_LEADERBOARD, "r") as f:
            return json.load(f)
    return []

def guardar_leaderboard(nombre, peso, tiempo):
    datos = cargar_leaderboard()
    datos.append({"Estudiante": nombre, "Peso Total": peso, "Tiempo (seg)": round(tiempo, 2)})
    # Desempate: 1ro menor peso, 2do menor tiempo
    datos = sorted(datos, key=lambda x: (x["Peso Total"], x["Tiempo (seg)"]))
    with open(ARCHIVO_LEADERBOARD, "w") as f:
        json.dump(datos, f)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ruta Óptima a la UDES", layout="wide")

# --- ESTADO DE LA SESIÓN ---
if 'path' not in st.session_state:
    st.session_state.path = ["Casa"]
if 'current_weight' not in st.session_state:
    st.session_state.current_weight = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

if 'grafo_udes' not in st.session_state:
    G = nx.MultiDiGraph() 
    nodos = ["Casa", "A", "B", "C", "D", "E", "Trampa 1", "Trampa 2", "UDES"]
    G.add_nodes_from(nodos) 
    
    def add_edge_data(u, v, weight, tipo, desc=""):
        # Se añade un pequeño identificador visual al label para la UI
        G.add_edge(u, v, weight=weight, label=f"{tipo}", desc=desc)

    # 1. Camino Directo (Unidireccional pero peso altísimo)
    add_edge_data("Casa", "UDES", 120, "Unidireccional", "Ruta directa (Tráfico pesado)")

    # 2. Caminos Bidireccionales (Ida y vuelta)
    add_edge_data("Casa", "A", 10, "Doble vía", "Calle principal")
    add_edge_data("A", "Casa", 10, "Doble vía", "Calle principal")
    
    add_edge_data("A", "B", 5, "Doble vía", "Conexión barrial")
    add_edge_data("B", "A", 5, "Doble vía", "Conexión barrial")

    add_edge_data("C", "D", 10, "Doble vía", "Avenida central")
    add_edge_data("D", "C", 10, "Doble vía", "Avenida central")

    # 3. Caminos Unidireccionales
    add_edge_data("Casa", "B", 25, "Unidireccional", "Bajada de un solo sentido")
    add_edge_data("B", "E", 15, "Unidireccional", "Vía rápida")
    add_edge_data("E", "UDES", 30, "Unidireccional", "Subida a la universidad")
    add_edge_data("D", "UDES", 15, "Unidireccional", "Entrada principal")

    # 4. Enlaces Paralelos (Dos formas de ir de A a C)
    add_edge_data("A", "C", 25, "Paralelo", "Ruta Segura y pavimentada")
    add_edge_data("A", "C", 5, "Paralelo", "Atajo de tierra (Peligroso)")

    # 5. Lazos (Loops)
    add_edge_data("A", "A", 3, "Lazo", "Te perdiste en la rotonda")

    # 6. Trampas y Encierros (Callejones sin salida hacia UDES)
    add_edge_data("C", "Trampa 1", 2, "Unidireccional", "Se ve muy corto...")
    add_edge_data("Trampa 1", "Trampa 1", 1, "Lazo", "Dando vueltas en el mismo lugar") 
    
    add_edge_data("E", "Trampa 2", 5, "Unidireccional", "Desvío engañoso")

    st.session_state.grafo_udes = G

st.title("🗺️ Optimización de Rutas: Misión UDES")
st.markdown("""
Encuentra el camino con **menor peso (costo/distancia)** desde tu **Casa** hasta la **UDES**. 
* Evalúa bien tus opciones: hay enlaces paralelos, rotondas (lazos) y callejones sin salida.
* El tiempo sigue corriendo aunque te equivoques. 
""")

col1, col2 = st.columns([2, 1])

with col1:
    G = st.session_state.grafo_udes
    path = st.session_state.path

    # --- RENDERIZADO DEL GRAFO (POSICIONES FIJAS) ---
    fig, ax = plt.subplots(figsize=(12, 6)) 
    
    # Coordenadas manuales para que el grafo parezca un mapa lógico
    pos = {
        "Casa": (0, 0),
        "A": (2, 1),
        "B": (2, -1),
        "C": (4, 1),
        "E": (4, -1),
        "D": (6, 1),
        "Trampa 1": (5, 2),
        "Trampa 2": (5, -2),
        "UDES": (8, 0)
    }

    node_colors = []
    for node in G.nodes():
        if node == "Casa": node_colors.append('#3498db') # Azul
        elif node == "UDES": node_colors.append('#2ecc71') # Verde
        elif path and node == path[-1]: node_colors.append('#f1c40f') # Amarillo (Actual)
        elif node in path: node_colors.append('#bdc3c7') # Gris (Visitados)
        elif "Trampa" in node: node_colors.append('#e74c3c') # Rojo
        else: node_colors.append('#95a5a6') 
            
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2000, ax=ax, edgecolors='black')
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=10, font_weight='bold', ax=ax)
    
    # Dibujar aristas con curvatura para poder ver los paralelos y bidireccionales
    for u, v, data in G.edges(data=True):
        style = 'arc3,rad=0.15' if u != v else 'arc3,rad=0' # Curvar a menos que sea un lazo
        nx.draw_networkx_edges(
            G, pos, 
            edgelist=[(u,v)],
            edge_color='#2c3e50', 
            arrows=True, 
            arrowstyle='-|>', 
            arrowsize=15, 
            connectionstyle=style, 
            ax=ax
        )

    st.pyplot(fig)
    st.divider()

    # --- LÓGICA DEL JUEGO ---
    current_node = path[-1]
    
    # Cronómetro visual
    tiempo_transcurrido = 0
    if st.session_state.start_time is not None:
        tiempo_transcurrido = time.time() - st.session_state.start_time

    st.subheader(f"📍 Ubicación Actual: {current_node} | ⚖️ Peso Acumulado: {st.session_state.current_weight}")
    st.caption(f"⏱️ Tiempo activo: {round(tiempo_transcurrido, 1)} segundos")
    
    if current_node == "UDES":
        st.success(f"¡LLEGASTE A LA UDES! Peso Final: {st.session_state.current_weight} | Tiempo: {round(tiempo_transcurrido, 2)} s.")
        st.balloons()
        
        with st.form("leaderboard_form"):
            nombre_jugador = st.text_input("Ingresa tu nombre para el ranking:")
            if st.form_submit_button("Guardar Récord") and nombre_jugador:
                guardar_leaderboard(nombre_jugador, st.session_state.current_weight, tiempo_transcurrido)
                st.success("¡Base de datos actualizada!")
                # Reset total tras ganar
                st.session_state.path = ["Casa"]
                st.session_state.current_weight = 0
                st.session_state.start_time = None
                st.rerun()
    else:
        out_edges = list(G.out_edges(current_node, data=True, keys=True))
        
        if not out_edges or all(u == v for u, v, k, d in out_edges):
            st.error("⚠️ Caíste en una trampa sin salida o en un bucle infinito.")
            st.markdown(">*De los errores se aprende, cada error me acerca más a mis sueños.*")
        else:
            st.write("Caminos disponibles:")
            for u, v, key, data in out_edges:
                peso = data.get('weight', 0)
                tipo = data.get('label', '')
                desc = data.get('desc', '')
                
                # Etiqueta del botón
                btn_text = f"Ir a {v} (Peso: {peso})\n[{tipo}] {desc}"
                
                if st.button(btn_text, key=f"btn_{u}_{v}_{key}"):
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    
                    st.session_state.path.append(v)
                    st.session_state.current_weight += peso
                    st.rerun()
                    
        st.write("")
        # BOTÓN DE REINICIO TÁCTICO
        st.caption("Si te equivocaste de ruta, puedes reiniciar la posición. El peso volverá a 0, pero el tiempo seguirá corriendo.")
        if st.button("🔄 Reiniciar desde Casa", type="primary", use_container_width=True):
            st.session_state.path = ["Casa"]
            st.session_state.current_weight = 0 
            # NO reseteamos start_time para penalizar en el desempate
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time()
            st.rerun()

with col2:
    st.subheader("🏆 Ranking Dijkstra")
    st.write("*(Desempate por tiempo)*")
    datos_leaderboard = cargar_leaderboard()
    
    if datos_leaderboard:
        df = pd.DataFrame(datos_leaderboard)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sé el primero en encontrar la ruta óptima.")