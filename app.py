# -*- coding: utf-8 -*-
"""
CiudadAlerta - prototipo de interfaz.

Instalar:  pip install streamlit folium streamlit-folium geopy pandas
Ejecutar:  streamlit run app.py
"""
from datetime import datetime
from pathlib import Path

import folium
from folium.plugins import LocateControl
from geopy.geocoders import Nominatim
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import logica as L

# 1. Configuración de página siempre al inicio de Streamlit
st.set_page_config(page_title="CiudadAlerta (prototipo)", page_icon="🏙️", layout="centered")

L.sembrar_demo()
st.session_state.setdefault("ver", 0)       # para limpiar el formulario tras enviar
st.session_state.setdefault("votos", set())  # evita votar dos veces en la sesión

COLOR_ESTADO = {"Pendiente": "#E67E22", "En revisión": "#2E86C1",
                "En reparación": "#8E44AD", "Resuelto": "#27AE60"}
ICONO_NIVEL = {"Alto": "🔴 Alto", "Medio": "🟠 Medio", "Bajo": "🟢 Bajo"}
ORDEN_NIVEL = {"Alto": 0, "Medio": 1, "Bajo": 2}

# Lista oficial de comunas de la Región Metropolitana con buscador
COMUNAS_OFICIALES = [
    "Cerrillos", "Cerro Navia", "Conchalí", "El Bosque", "Estación Central",
    "Huechuraba", "Independencia", "La Cisterna", "La Florida", "La Granja",
    "La Pintana", "La Reina", "Las Condes", "Lo Barnechea", "Lo Espejo",
    "Lo Prado", "Macul", "Maipú", "Ñuñoa", "Pedro Aguirre Cerda",
    "Peñalolén", "Providencia", "Pudahuel", "Quilicura", "Quinta Normal",
    "Recoleta", "Renca", "San Joaquín", "San Miguel", "San Ramón",
    "Santiago", "Vitacura", "Puente Alto", "Pirque", "San José de Maipo",
    "Colina", "Lampa", "Tiltil", "San Bernardo", "Buin", "Paine", "Calera de Tango",
    "Melipilla", "Talagante", "Padre Hurtado", "Peñaflor"
]

# ---------------------------------------------------------------- COMPONENTES Y AUXILIARES
def recargar_app():
    """Recarga la app de manera compatible con cualquier versión de Streamlit."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def titulo_pregunta(texto):
    """Aplica formato grande y destacado ÚNICAMENTE a las 5 preguntas del formulario."""
    st.markdown(
        f'<div style="font-size: 1.35rem; font-weight: 800; color: #0284C7; margin-top: 1.4rem; margin-bottom: 0.4rem;">{texto}</div>', 
        unsafe_allow_html=True
    )


def badge(texto, color):
    return (f'<span style="background:{color};color:white;padding:2px 9px;'
            f'border-radius:10px;font-size:12px">{texto}</span>')


def stepper(estado):
    """Indicador de avance: Pendiente → En revisión → En reparación → Resuelto."""
    actual = L.ESTADOS.index(estado)
    html = '<div style="display:flex;gap:6px;margin:6px 0 4px">'
    for k, e in enumerate(L.ESTADOS):
        on = k <= actual
        html += (f'<div style="flex:1;text-align:center;padding:6px 2px;border-radius:6px;'
                 f'font-size:12px;font-weight:{600 if k == actual else 400};'
                 f'background:{COLOR_ESTADO[estado] if on else "#E5E7E9"};'
                 f'color:{"white" if on else "#7F8C8D"}">{e}</div>')
    st.markdown(html + "</div>", unsafe_allow_html=True)


def mostrar_media(ruta):
    if ruta and Path(ruta).exists():
        if ruta.lower().endswith((".mp4", ".mov")):
            st.video(ruta)
        else:
            st.image(ruta, width=320)


def fecha_corta(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")


def extraer_comuna_estricta(direccion_texto):
    """Extrae únicamente el nombre de la comuna ignorando barrios y calles."""
    if not direccion_texto:
        return "Santiago"
    for comuna in COMUNAS_OFICIALES:
        if comuna.lower() in direccion_texto.lower():
            return comuna
    if "," in direccion_texto:
        return direccion_texto.split(",")[-1].strip()
    return direccion_texto.strip()


@st.cache_data(ttl=3600)
def obtener_direccion_calle_comuna(lat, lon):
    """Convierte coordenadas a Nombre de calle y Comuna (sin barrios)."""
    try:
        geolocator = Nominatim(user_agent="ciudadalerta_app_v3")
        location = geolocator.reverse((lat, lon), timeout=5)
        if location and location.raw.get("address"):
            addr = location.raw["address"]
            calle = addr.get("road") or addr.get("pedestrian") or addr.get("footway") or "Calle sin nombre"
            numero = addr.get("house_number", "")
            
            comuna_raw = (addr.get("city") or 
                          addr.get("town") or 
                          addr.get("municipality") or 
                          addr.get("county") or 
                          addr.get("city_district") or 
                          "Santiago")
            
            comuna = extraer_comuna_estricta(comuna_raw)
            direccion_completa = f"{calle} {numero}".strip()
            return f"{direccion_completa}, {comuna}"
    except Exception:
        pass
    return "Ubicación seleccionada, Santiago"

# ---------------------------------------------------------------- VISIÓN CIUDADANO


def selector_mapa_interactivo():
    st.caption("El mapa detectará tu ubicación automáticamente al cargar. Si deseas cambiar el punto, haz clic en el lugar exacto.")

    if "lat_sel" not in st.session_state:
        st.session_state.lat_sel = -33.4452
        st.session_state.lon_sel = -70.6620

    m = folium.Map(
        location=[st.session_state.lat_sel, st.session_state.lon_sel],
        zoom_start=15
    )

    LocateControl(
        auto_start=True,
        flyTo=True,
        keepCurrentZoomLevel=False,
        strings={"title": "Mi ubicación actual", "popup": "Te encuentras aquí"},
        locateOptions={"enableHighAccuracy": True}
    ).add_to(m)

    folium.Marker(
        [st.session_state.lat_sel, st.session_state.lon_sel],
        popup="Ubicación seleccionada",
        tooltip="Punto del reporte",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    map_data = st_folium(
        m,
        width="100%",
        height=350,
        key="mapa_selector_ciudadano",
        returned_objects=["last_clicked"]
    )

    if map_data and map_data.get("last_clicked"):
        click_lat = map_data["last_clicked"]["lat"]
        click_lon = map_data["last_clicked"]["lng"]
        
        if click_lat != st.session_state.lat_sel or click_lon != st.session_state.lon_sel:
            st.session_state.lat_sel = click_lat
            st.session_state.lon_sel = click_lon
            recargar_app()


def render_resumen_reporte(r):
    st.success("¡Su reporte ha sido realizado con éxito!")
    st.markdown("---")
    st.markdown("### 📋 Resumen del reporte")
    st.write(f"**ID del reporte:** `{r['id']}`")
    st.write(f"**Título:** {r['titulo']}")
    st.write(f"**Tipo de problema:** {r['tipo']}")
    st.write(f"**Lugar:** {r['lugar']}")
    st.write(f"**Nivel de riesgo:** {r['riesgo']}")
    st.write(f"**Ubicación:** {r['sector']}")
    st.write(f"**Organismo asignado:** {L.ORGANISMOS.get(r['organismo'], r['organismo'])}")
    if r.get("descripcion"):
        st.write(f"**Descripción:** {r['descripcion']}")
    else:
        st.write("**Descripción:** _Sin descripción_")
    if r.get("media"):
        st.markdown("**Evidencia adjunta:**")
        mostrar_media(r["media"])
    st.markdown("---")
    if st.button("Aceptar / Cerrar", type="primary"):
        st.session_state.pop("reporte_exito", None)
        recargar_app()


def popup_confirmacion(r):
    if hasattr(st, "dialog"):
        @st.dialog("✅ Reporte realizado con éxito")
        def _dialog_impl():
            render_resumen_reporte(r)
        _dialog_impl()
    else:
        render_resumen_reporte(r)


def formulario():
    v = st.session_state.ver

    if "reporte_exito" in st.session_state:
        popup_confirmacion(st.session_state["reporte_exito"])

    # 📍 MAPA INTERACTIVO AL PRINCIPIO
    titulo_pregunta("📍 Ubicación del problema")
    selector_mapa_interactivo()

    # 1. ¿Qué tipo de problema es?
    titulo_pregunta("1. ¿Qué tipo de problema es?")
    tipo = st.radio("Tipo de problema", L.TIPOS, index=None, key=f"tipo_{v}", label_visibility="collapsed")

    # 2. ¿Dónde está?
    titulo_pregunta("2. ¿Dónde está?")
    lugar = st.radio("Lugar del problema", L.LUGARES, index=None, key=f"lugar_{v}", label_visibility="collapsed")

    # 3. ¿Hay peligro para las personas?
    titulo_pregunta("3. ¿Hay peligro para las personas?")
    riesgo = st.radio("Nivel de riesgo", L.RIESGOS, index=None, horizontal=True, key=f"riesgo_{v}", label_visibility="collapsed")
    
    # 4. Cuéntanos más (solo el título es obligatorio)
    titulo_pregunta("4. Cuéntanos más (solo el título es obligatorio)")
    titulo = st.text_input("Título *", max_chars=60, key=f"titulo_{v}")
    descripcion = st.text_area("Descripción (opcional)", max_chars=300, key=f"desc_{v}")
    
    # 5. ADJUNTAR EVIDENCIA (CONTROL TOTAL DE CÁMARA BAJO DEMANDA)
    titulo_pregunta("5. Adjuntar evidencia (opcional)")
    
    key_foto_cam = f"foto_camara_guardada_{v}"
    key_mostrar_cam = f"mostrar_camara_{v}"

    if key_mostrar_cam not in st.session_state:
        st.session_state[key_mostrar_cam] = False

    c_galeria, c_camara = st.columns(2)

    with c_galeria:
        media_file = st.file_uploader(
            "📁 Subir desde la galería", 
            type=["jpg", "jpeg", "png", "mp4", "mov"], 
            key=f"media_file_{v}"
        )

    with c_camara:
        st.write("**📷 Foto con la cámara**")
        
        # OPORTUNIDAD 1: Si ya tomó la foto, muestra miniatura y apaga la cámara
        if st.session_state.get(key_foto_cam):
            st.image(st.session_state[key_foto_cam], caption="Foto capturada", width=180)
            if st.button("🗑️ Quitar / Volver a tomar", key=f"btn_del_cam_{v}"):
                st.session_state[key_foto_cam] = None
                st.session_state[key_mostrar_cam] = False
                recargar_app()

        # OPORTUNIDAD 2: Solo si presionó encender, renderiza el visor e inicia la cámara
        elif st.session_state.get(key_mostrar_cam):
            cam_capture = st.camera_input("Capturar foto", key=f"cam_input_{v}", label_visibility="collapsed")
            if cam_capture:
                st.session_state[key_foto_cam] = cam_capture
                st.session_state[key_mostrar_cam] = False  # Apaga la cámara inmediatamente
                recargar_app()
            
            if st.button("❌ Cancelar / Apagar cámara", key=f"btn_cancel_cam_{v}"):
                st.session_state[key_mostrar_cam] = False
                recargar_app()

        # OPORTUNIDAD 3: Estado por defecto al cargar (Cámara totalmente desactivada)
        else:
            if st.button("📸 Solicitar y encender cámara", key=f"btn_start_cam_{v}"):
                st.session_state[key_mostrar_cam] = True
                recargar_app()

    st.markdown("<br>", unsafe_allow_html=True)
    enviar = st.button("Enviar reporte", type="primary", use_container_width=True, key=f"btn_send_{v}")

    if enviar:
        if not (tipo and lugar and riesgo and titulo.strip()):
            st.error("Por favor responde las 3 primeras preguntas y escribe un título.")
            return
        
        foto_camara = st.session_state.get(key_foto_cam)
        media = foto_camara if foto_camara is not None else media_file
        
        ruta = None
        if media:
            nombre_archivo = getattr(media, "name", f"foto_camara_{v}.png")
            ruta = L.guardar_archivo(nombre_archivo, media.getvalue())
            
        dir_final = st.session_state.get("direccion_texto", "Ubicación Mapa")
        
        r = L.crear_reporte(
            titulo, descripcion, tipo, lugar, riesgo, 
            sector=dir_final, media=ruta,
            lat=st.session_state.lat_sel, lon=st.session_state.lon_sel
        )
        
        st.session_state[key_foto_cam] = None
        st.session_state[key_mostrar_cam] = False
        st.session_state.reporte_exito = r
        st.session_state.ver += 1
        recargar_app()


def tarjeta_ciudadano(r):
    votos = st.session_state.votos
    with st.container(border=True):
        st.markdown(f"**{r['titulo']}**")
        st.markdown(badge(r["estado"], COLOR_ESTADO[r["estado"]]) + " "
                    + badge(L.ORGANISMOS[r["organismo"]], "#5D6D7E"), unsafe_allow_html=True)
        stepper(r["estado"])
        st.caption(f"{r['tipo']} · {r['lugar']} · {fecha_corta(r['fecha'])} · "
                   f"{r['vistos']} vecinos lo ven")

        if r["estado"] == "Resuelto":
            c = r["resolucion"]
            st.info("La municipalidad dice que esto fue resuelto. **¿Es así?**")
            st.caption(f"{c['si']} vecinos lo confirman · {c['no']} dicen que no")
            b1, b2 = st.columns(2)
            ya = (r["id"], "res") in votos
            if b1.button("Sí, está resuelto", key=f"si_{r['id']}", disabled=ya):
                L.votar_resolucion(r, True); votos.add((r["id"], "res")); recargar_app()
            if b2.button("No, sigue el problema", key=f"no_{r['id']}", disabled=ya):
                L.votar_resolucion(r, False); votos.add((r["id"], "res")); recargar_app()
        elif st.button("👁 Yo también lo veo", key=f"v_{r['id']}",
                       disabled=(r["id"], "v") in votos):
            L.validar_visto(r); votos.add((r["id"], "v")); recargar_app()

        with st.expander("Detalles y evidencia"):
            st.write(r["descripcion"] or "_Sin descripción._")
            mostrar_media(r["media"])
            for e in r["evidencias"]:
                st.markdown(f"**Evidencia ({fecha_corta(e['fecha'])}):** {e['comentario'] or '—'}")
                mostrar_media(e["media"])
            st.markdown("**Historial**")
            for h in r["historial"]:
                st.caption(h)
            k = f"{r['id']}_{len(r['evidencias'])}"
            com = st.text_input("Añadir evidencia (comentario)", key=f"ec_{k}", max_chars=200)
            arch = st.file_uploader("Foto o video", key=f"ef_{k}",
                                    type=["jpg", "jpeg", "png", "mp4", "mov"])
            if st.button("Guardar evidencia", key=f"eg_{k}") and (com.strip() or arch):
                ruta = L.guardar_archivo(arch.name, arch.getvalue()) if arch else None
                L.agregar_evidencia(r, com, ruta); recargar_app()


def vista_ciudadano():
    if "tab_ciudadano" not in st.session_state:
        st.session_state.tab_ciudadano = "reportar"

    col1, col2 = st.columns(2)
    
    with col1:
        activo_1 = st.session_state.tab_ciudadano == "reportar"
        if st.button(
            "📢 1. REPORTAR UN PROBLEMA",
            key="btn_nav_reportar",
            use_container_width=True,
            type="primary" if activo_1 else "secondary"
        ):
            st.session_state.tab_ciudadano = "reportar"
            recargar_app()

    with col2:
        activo_2 = st.session_state.tab_ciudadano == "ver"
        if st.button(
            "🗺️ 2. VER Y VALIDAR REPORTES",
            key="btn_nav_ver",
            use_container_width=True,
            type="primary" if activo_2 else "secondary"
        ):
            st.session_state.tab_ciudadano = "ver"
            recargar_app()

    st.divider()

    if st.session_state.tab_ciudadano == "reportar":
        formulario()
    else:
        reps = sorted(L.cargar_todos(), key=lambda r: r["fecha"], reverse=True)
        if not reps:
            st.info("No hay reportes todavía.")
        for r in reps:
            tarjeta_ciudadano(r)

# ---------------------------------------------------------------- VISIÓN AUTORIDAD
def tarjeta_municipal(r, nivel):
    with st.container(border=True):
        st.markdown(f"**{r['titulo']}**  ·  {ICONO_NIVEL[nivel]}" if r["estado"] != "Resuelto"
                    else f"**{r['titulo']}**")
        stepper(r["estado"])
        st.caption(f"{r['tipo']} · {r['lugar']} · {r['sector']} · {r['riesgo']} · "
                   f"{fecha_corta(r['fecha'])} · {r['vistos']} validaciones")
        if L.cuestionada(r):
            c = r["resolucion"]
            st.error(f"Los vecinos cuestionan esta resolución ({c['si']} sí / {c['no']} no). "
                     "Considera reabrir el reporte.")
        c1, c2, c3 = st.columns([2, 2, 1])
        estado = c1.selectbox("Estado", L.ESTADOS, index=L.ESTADOS.index(r["estado"]),
                              key=f"e_{r['id']}")
        orgs = list(L.ORGANISMOS)
        org = c2.selectbox("Organismo", orgs, index=orgs.index(r["organismo"]),
                           format_func=L.ORGANISMOS.get, key=f"o_{r['id']}")
        c3.write("")
        if c3.button("Aplicar", key=f"a_{r['id']}"):
            L.cambiar_estado(r, estado, org); recargar_app()
        with st.expander("Descripción y evidencia"):
            st.write(r["descripcion"] or "_Sin descripción._")
            mostrar_media(r["media"])
            for e in r["evidencias"]:
                st.markdown(f"**Evidencia ({fecha_corta(e['fecha'])}):** {e['comentario'] or '—'}")
                mostrar_media(e["media"])


def vista_municipalidad():
    reps = L.cargar_todos()
    prio = L.prioridades(reps)
    nivel = lambda r: prio.get((r["tipo"], r["sector"]), {}).get("nivel", "Bajo")
    abiertos = [r for r in reps if r["estado"] != "Resuelto"]

    # 1. Métricas generales
    m = st.columns(4)
    m[0].metric("Reportes totales", len(reps))
    m[1].metric("Abiertos", len(abiertos))
    m[2].metric("Focos prioridad alta", sum(v["nivel"] == "Alto" for v in prio.values()))
    m[3].metric("Resoluciones cuestionadas", sum(L.cuestionada(r) for r in reps))

    # 2. Prioridad por foco
    st.subheader("Prioridad por foco")
    st.caption(f"Foco = tipo de problema + ubicación. Prioridad según la pendiente de reportes por día "
               f"en 7 días: Bajo < {L.UMBRAL_MEDIO} · Medio {L.UMBRAL_MEDIO}–{L.UMBRAL_ALTO} · "
               f"Alto ≥ {L.UMBRAL_ALTO} (mínimo {L.MIN_REPORTES_SEMANA} reportes).")
    filas = sorted(prio.items(), key=lambda kv: (ORDEN_NIVEL[kv[1]["nivel"]], -kv[1]["pendiente"]))
    st.dataframe(pd.DataFrame([{"Prioridad": ICONO_NIVEL[v["nivel"]], "Problema": t, "Ubicación/Sector": s,
                                "Reportes (7 días)": v["reportes_7d"], "Pendiente": v["pendiente"]}
                               for (t, s), v in filas]), hide_index=True)

    # 3. Carpetas por organismo y filtro dinámico
    st.subheader("Carpetas por organismo")
    claves = list(L.ORGANISMOS)
    tabs = st.tabs([f"{L.ORGANISMOS[k]} ({sum(r['organismo'] == k for r in reps)})" for k in claves])

    for tab, k in zip(tabs, claves):
        with tab:
            items = sorted((r for r in reps if r["organismo"] == k),
                           key=lambda r: (r["estado"] == "Resuelto", ORDEN_NIVEL[nivel(r)], r["fecha"]))

            comuna_sel = "Santiago"
            if k == "MUNI":
                comuna_sel = st.selectbox(
                    "🔍 Busca o selecciona la comuna de la Municipalidad:",
                    options=COMUNAS_OFICIALES,
                    index=COMUNAS_OFICIALES.index("Santiago"),
                    key="filtro_comuna_muni",
                    help="Haz clic y escribe el nombre de la comuna para buscar"
                )
                items = [r for r in items if extraer_comuna_estricta(r.get("sector", "")) == comuna_sel]
                
                if items:
                    st.info(f"Mostrando reportes asignados a la **Municipalidad de {comuna_sel}** ({len(items)} reportes)")
                else:
                    st.warning(f"No hay reportes registrados actualmente para la **Municipalidad de {comuna_sel}**.")

            st.caption(f"Carpeta: carpetas/{k}/" + ("" if k == "MUNI" else
                       f" · se envía a {L.ORGANISMOS[k]}; la autoridad registra el avance informado."))

            # 🗺️ MAPA INTERACTIVO CON COLORES SEGÚN ESTADO DE REPARACIÓN
            abiertos_filtrados = [r for r in items if r["estado"] != "Resuelto"]
            
            with st.expander(f"🗺️ Mapa de reportes abiertos ({len(abiertos_filtrados)})", expanded=True):
                st.markdown(
                    "**Leyenda de estados:** "
                    "🟠 **Pendiente** &nbsp;&nbsp;|&nbsp;&nbsp; "
                    "🔵 **En revisión** &nbsp;&nbsp;|&nbsp;&nbsp; "
                    "🟣 **En reparación**",
                    unsafe_allow_html=True
                )
                
                if abiertos_filtrados:
                    lats = [r["lat"] for r in abiertos_filtrados if "lat" in r]
                    lons = [r["lon"] for r in abiertos_filtrados if "lon" in r]
                    
                    if lats and lons:
                        centro_lat = sum(lats) / len(lats)
                        centro_lon = sum(lons) / len(lons)
                        
                        m_muni = folium.Map(location=[centro_lat, centro_lon], zoom_start=13)
                        
                        for r in abiertos_filtrados:
                            if "lat" in r and "lon" in r:
                                col = COLOR_ESTADO.get(r["estado"], "#E67E22")
                                folium.CircleMarker(
                                    location=[r["lat"], r["lon"]],
                                    radius=9,
                                    color=col,
                                    fill=True,
                                    fill_color=col,
                                    fill_opacity=0.85,
                                    popup=f"<b>{r['titulo']}</b><br>Estado: {r['estado']}<br>Sector: {r['sector']}",
                                    tooltip=f"{r['titulo']} ({r['estado']})"
                                ).add_to(m_muni)
                        
                        st_folium(m_muni, width="100%", height=350, key=f"mapa_muni_{k}_{comuna_sel if k=='MUNI' else 'all'}")
                else:
                    st.info("No hay reportes abiertos para mostrar en el mapa de esta selección.")

            if not items:
                continue

            df = pd.DataFrame([{"id": r["id"], "titulo": r["titulo"], "tipo": r["tipo"],
                                "lugar": r["lugar"], "riesgo": r["riesgo"], "ubicacion": r["sector"],
                                "estado": r["estado"], "prioridad": nivel(r), "fecha": r["fecha"]}
                               for r in items])
            st.download_button("Exportar carpeta (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"reportes_{k}_{comuna_sel if k=='MUNI' else ''}.csv", 
                               mime="text/csv", key=f"dl_{k}")
            for r in items:
                tarjeta_municipal(r, nivel(r))

    # 4. Herramientas de demostración
    st.divider()
    with st.expander("🧰 Herramientas de demostración"):
        st.caption("Borra TODOS los reportes (incluidos los de prueba y sus fotos) y vuelve a "
                   "generar los reportes de ejemplo.")
        confirmar = st.checkbox("Entiendo que se borrarán todos los reportes", key="confirmar_reinicio")
        if st.button("🔄 Reiniciar demo", disabled=not confirmar, key="btn_reiniciar_demo"):
            L.reiniciar_demo()
            st.session_state.votos = set()
            recargar_app()

# ---------------------------------------------------------------- DESCRIPCIÓN
DESCRIPCION = f"""
### ¿Qué es CiudadAlerta?
Una aplicación móvil para **reportar y dar seguimiento a daños en infraestructura pública**.
Los vecinos reportan en pocos toques; el sistema ordena la información, la deriva al organismo
responsable y entrega a la municipalidad una lista priorizada. Los vecinos pueden ver el avance
y verificar si lo que se declara como resuelto realmente lo está.

### Problema que aborda
Los reportes ciudadanos suelen llegar desordenados (texto libre, sin categoría, sin saber a quién
corresponde) y los vecinos no saben si su reporte avanza. Esto hace lenta la gestión y baja la confianza.

### Usuarios
- **Ciudadano:** reporta, valida reportes de otros ("yo también lo veo"), añade evidencia y verifica resoluciones.
- **Municipalidad / Autoridad:** controla el avance de cada reporte, revisa prioridades y gestiona las carpetas por organismo.

### Flujo del ciudadano (rápido e intuitivo)
1. **Tres preguntas con alternativas:** tipo de problema, lugar y nivel de peligro. Esto permite categorizar automáticamente.
2. **Título** (único campo obligatorio), **descripción** y **foto o video** opcionales. Estos datos son informativos para otros vecinos y para la municipalidad; no se usan para categorizar.
3. La ubicación se selecciona interactivamente mediante GPS o marcador en mapa.

### Seguimiento de avance
Cada reporte tiene cuatro estados: **Pendiente → En revisión → En reparación → Resuelto**.
**Solo la municipalidad cambia el estado.** Cuando un reporte pasa a *Resuelto*, los vecinos ven la
pregunta *"La municipalidad dice que esto fue resuelto, ¿es así?"* y responden Sí/No. Si hay al menos
3 respuestas y predominan los "No", la municipalidad recibe una alerta de **resolución cuestionada**.

### Derivación automática por organismo
Según las respuestas, cada reporte se guarda en la carpeta del organismo que debe repararlo:

| Condición | Organismo |
|---|---|
| Lugar = edificio o monumento histórico | CMN |
| Problema = agua o alcantarillado | Empresa sanitaria |
| Pavimento en avenida principal | SERVIU |
| Pavimento en ruta o camino interurbano | MOP (Vialidad) |
| Cualquier otro caso | Municipalidad |

La municipalidad puede reasignar un reporte si la derivación automática no fue correcta.

### Prioridad (visión municipalidad)
Se agrupan los reportes sin resolver en **focos** (mismo tipo de problema en el mismo sector). Para cada foco se
cuenta cuántos reportes llegaron cada día en los últimos 7 días y se calcula la **pendiente** de la tendencia.
"""

# ---------------------------------------------------------------- PÁGINA PRINCIPAL
st.title("🏙️ CiudadAlerta")
c1, c2 = st.columns(2)
with c1:
    st.caption("Visión:  Ciudadano  ◂▸  Autoridad")
    es_muni = st.toggle("Visión", key="vision", label_visibility="collapsed")
with c2:
    st.caption("Mostrar:  App  ◂▸  Descripción")
    ver_desc = st.toggle("Descripción", key="desc", label_visibility="collapsed")
st.divider()

if ver_desc:
    st.markdown(DESCRIPCION)
elif es_muni:
    st.markdown("#### Panel de la Autoridad")
    vista_municipalidad()
else:
    st.markdown("#### Visión del ciudadano")
    vista_ciudadano()