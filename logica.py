# -*- coding: utf-8 -*-
"""
CiudadAlerta - lógica del prototipo (sin interfaz, solo librería estándar).

Cada reporte se guarda como un archivo JSON dentro de la carpeta del organismo
que debe repararlo:  carpetas/MUNI/, carpetas/CMN/, carpetas/MOP/, ...
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent
CARPETAS = BASE / "carpetas"
UPLOADS = BASE / "uploads"

# ---------------------------------------------------------------- catálogos
ESTADOS = ["Pendiente", "En revisión", "En reparación", "Resuelto"]

TIPOS = ["Pavimento o vereda", "Alumbrado público", "Plaza o área verde",
         "Agua o alcantarillado", "Basura o aseo", "Edificio o estructura"]
LUGARES = ["Calle o pasaje de barrio", "Avenida principal", "Ruta o camino interurbano",
           "Plaza o parque", "Edificio común", "Edificio o monumento histórico"]
RIESGOS = ["Sin peligro", "Posible peligro", "Peligro inmediato"]

ORGANISMOS = {"MUNI": "Municipalidad", "SERVIU": "SERVIU", "MOP": "MOP (Vialidad)",
              "CMN": "CMN (Monumentos Nacionales)", "SANITARIA": "Empresa sanitaria"}

SECTORES = {  # "GPS" simulado: coordenadas aproximadas
    "Barrio Yungay": (-33.4403, -70.6720), "Barrio Brasil": (-33.4426, -70.6740),
    "Barrio Lastarria": (-33.4377, -70.6405), "Barrio Franklin": (-33.4640, -70.6540),
    "Parque Almagro": (-33.4510, -70.6495),
}

# Prioridad: pendiente (reportes/día por día) de los últimos 7 días
UMBRAL_MEDIO = 0.25
UMBRAL_ALTO = 0.60
MIN_REPORTES_SEMANA = 3


def derivar_organismo(tipo, lugar):
    """Reglas de derivación según las respuestas del ciudadano."""
    if lugar == "Edificio o monumento histórico":
        return "CMN"
    if tipo == "Agua o alcantarillado":
        return "SANITARIA"
    if tipo == "Pavimento o vereda":
        if lugar == "Avenida principal":
            return "SERVIU"
        if lugar == "Ruta o camino interurbano":
            return "MOP"
    return "MUNI"


# ---------------------------------------------------------------- almacenamiento
def cargar_todos():
    return [json.loads(p.read_text(encoding="utf-8")) for p in CARPETAS.glob("*/*.json")]


def guardar(r):
    destino = CARPETAS / r["organismo"]
    destino.mkdir(parents=True, exist_ok=True)
    for p in CARPETAS.glob(f"*/{r['id']}.json"):  # si cambió de organismo, mover
        if p.parent != destino:
            p.unlink()
    (destino / f"{r['id']}.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")


def guardar_archivo(nombre, datos):
    UPLOADS.mkdir(exist_ok=True)
    ruta = UPLOADS / f"{uuid.uuid4().hex[:8]}_{Path(nombre).name}"
    ruta.write_bytes(datos)
    return str(ruta)


def _log(r, texto, cuando=None):
    r["historial"].append(f"{(cuando or datetime.now()):%d/%m %H:%M} · {texto}")


def crear_reporte(titulo, descripcion, tipo, lugar, riesgo, sector="Ubicación en mapa",
                  media=None, fecha=None, estado="Pendiente", lat=None, lon=None):
    fecha = fecha or datetime.now()
    
    # Si no se pasan coordenadas exactas, usa la base del sector o Santiago
    if lat is None or lon is None:
        lat_base, lon_base = SECTORES.get(sector, (-33.4489, -70.6693))
        lat = lat_base + random.uniform(-0.002, 0.002)
        lon = lon_base + random.uniform(-0.002, 0.002)

    r = {
        "id": uuid.uuid4().hex[:8], "titulo": titulo.strip(), "descripcion": descripcion.strip(),
        "media": media, "tipo": tipo, "lugar": lugar, "riesgo": riesgo, "sector": sector,
        "lat": lat, "lon": lon,
        "organismo": derivar_organismo(tipo, lugar), "estado": estado,
        "fecha": fecha.isoformat(timespec="seconds"),
        "vistos": 0, "resolucion": {"si": 0, "no": 0}, "evidencias": [], "historial": [],
    }
    _log(r, f"Reporte creado y derivado a {ORGANISMOS[r['organismo']]}", fecha)
    guardar(r)
    return r


# ---------------------------------------------------------------- acciones
def cambiar_estado(r, estado=None, organismo=None):
    """Acción de la municipalidad: actualizar avance y/o reasignar organismo."""
    if estado and estado != r["estado"]:
        r["estado"] = estado
        r["resolucion"] = {"si": 0, "no": 0}  # nueva ronda de verificación ciudadana
        _log(r, f"Estado actualizado a '{estado}'")
    if organismo and organismo != r["organismo"]:
        r["organismo"] = organismo
        _log(r, f"Reasignado a {ORGANISMOS[organismo]}")
    guardar(r)


def validar_visto(r):
    r["vistos"] += 1
    guardar(r)


def votar_resolucion(r, esta_resuelto):
    r["resolucion"]["si" if esta_resuelto else "no"] += 1
    _log(r, "Un vecino " + ("confirma" if esta_resuelto else "cuestiona") + " la resolución")
    guardar(r)


def agregar_evidencia(r, comentario, media=None):
    r["evidencias"].append({"fecha": datetime.now().isoformat(timespec="seconds"),
                            "comentario": comentario.strip(), "media": media})
    _log(r, "Evidencia adicional añadida")
    guardar(r)


def cuestionada(r):
    c = r["resolucion"]
    return r["estado"] == "Resuelto" and c["no"] > c["si"] and (c["si"] + c["no"]) >= 3


# ---------------------------------------------------------------- prioridad
def pendiente_semanal(fechas, ahora=None):
    """Pendiente de la recta de regresión del nº de reportes por día (últimos 7 días)."""
    hoy = (ahora or datetime.now()).date()
    conteo = [0] * 7  # índice 0 = hace 6 días ... índice 6 = hoy
    for f in fechas:
        d = (hoy - f.date()).days
        if 0 <= d < 7:
            conteo[6 - d] += 1
    media_y = sum(conteo) / 7
    pendiente = sum((x - 3) * (y - media_y) for x, y in enumerate(conteo)) / 28
    return pendiente, sum(conteo)


def nivel_prioridad(pendiente, total):
    if total < MIN_REPORTES_SEMANA:
        return "Bajo"
    if pendiente >= UMBRAL_ALTO:
        return "Alto"
    return "Medio" if pendiente >= UMBRAL_MEDIO else "Bajo"


def prioridades(reportes, ahora=None):
    """Prioridad por 'foco' = (tipo de problema, sector), solo reportes sin resolver."""
    focos = {}
    for r in reportes:
        if r["estado"] != "Resuelto":
            focos.setdefault((r["tipo"], r["sector"]), []).append(datetime.fromisoformat(r["fecha"]))
    out = {}
    for foco, fechas in focos.items():
        pend, total = pendiente_semanal(fechas, ahora)
        out[foco] = {"pendiente": round(pend, 2), "reportes_7d": total,
                     "nivel": nivel_prioridad(pend, total)}
    return out


# ---------------------------------------------------------------- datos demo
COORD_COMUNAS = {
    "Santiago": (-33.4452, -70.6620),
    "Providencia": (-33.4273, -70.6181),
    "Las Condes": (-33.4115, -70.5702),
    "Ñuñoa": (-33.4542, -70.5971),
    "Maipú": (-33.5103, -70.7573),
    "La Florida": (-33.5221, -70.5984),
    "Puente Alto": (-33.6102, -70.5751),
    "San Miguel": (-33.4921, -70.6523),
    "Quinta Normal": (-33.4412, -70.6814),
    "Estación Central": (-33.4524, -70.6882)
}

def sembrar_demo():
    if any(CARPETAS.glob("*/*.json")):
        return
    rnd = random.Random(42)
    ahora = datetime.now()
    
    focos = [
        ("Pavimento o vereda", "Avenida principal", "Av. Bernardo O'Higgins 1450, Santiago", [0, 0, 1, 1, 2, 3, 4], "Posible peligro", "Hoyo grande en la calzada", -33.4452, -70.6620),
        ("Basura o aseo", "Plaza o parque", "Av. Nueva Providencia 2150, Providencia", [1, 0, 1, 0, 1, 0, 1], "Sin peligro", "Acumulación de microbasural", -33.4273, -70.6181),
        ("Alumbrado público", "Calle o pasaje de barrio", "Av. Apoquindo 4800, Las Condes", [0, 1, 1, 1, 2, 2, 3], "Posible peligro", "Luminarias apagadas en plaza", -33.4115, -70.5702),
        ("Pavimento o vereda", "Calle o pasaje de barrio", "Av. Irarrázaval 2400, Ñuñoa", [0, 0, 0, 1, 1, 2, 2], "Posible peligro", "Vereda levantada por raíces", -33.4542, -70.5971),
        ("Agua o alcantarillado", "Calle o pasaje de barrio", "Av. Pajaritos 3000, Maipú", [0, 0, 0, 0, 1, 1, 2], "Peligro inmediato", "Filtración de agua en vía pública", -33.5103, -70.7573),
        ("Alumbrado público", "Avenida principal", "Av. Vicuña Mackenna 7200, La Florida", [0, 1, 0, 1, 1, 2, 1], "Posible peligro", "Foco parpadeando en cruce", -33.5221, -70.5984),
        ("Basura o aseo", "Calle o pasaje de barrio", "Av. Concha y Toro 1500, Puente Alto", [1, 1, 0, 1, 0, 1, 1], "Sin peligro", "Escombros abandonados", -33.6102, -70.5751),
        ("Pavimento o vereda", "Ruta o camino interurbano", "Gran Avenida 4200, San Miguel", [0, 0, 0, 0, 0, 1, 1], "Peligro inmediato", "Bache profundo en pista bus", -33.4921, -70.6523),
        ("Edificio o estructura", "Edificio o monumento histórico", "Av. Matucana 800, Quinta Normal", [0, 0, 1, 0, 1, 0, 1], "Posible peligro", "Fachada deteriorada", -33.4412, -70.6814),
        ("Agua o alcantarillado", "Calle o pasaje de barrio", "Av. Ecuador 3500, Estación Central", [0, 0, 0, 0, 1, 1, 1], "Posible peligro", "Tapa de alcantarillado suelta", -33.4524, -70.6882),
    ]
    
    for tipo, lugar, sector, conteos, riesgo, titulo, lat, lon in focos:
        for i, n in enumerate(conteos):
            dias = 6 - i
            for _ in range(n):
                hora = rnd.randint(0, ahora.hour) if dias == 0 else rnd.randint(7, 21)
                fecha = (ahora - timedelta(days=dias)).replace(hour=hora, minute=rnd.randint(0, 59))
                estado = rnd.choice(["Pendiente", "En revisión", "En reparación"]) if dias >= 4 else "Pendiente"
                r = crear_reporte(titulo, "", tipo, lugar, riesgo, sector, fecha=fecha, estado=estado, lat=lat, lon=lon)
                r["vistos"] = rnd.randint(0, 6)
                guardar(r)

    resueltos = [
        ("Alumbrado público", "Calle o pasaje de barrio", "Manuel Montt 500, Providencia", "Luminaria reparada", 9, 6, 1, -33.4320, -70.6150),
        ("Plaza o área verde", "Plaza o parque", "Plaza de Maipú 10, Maipú", "Juegos infantiles reparados", 12, 5, 0, -33.5100, -70.7570),
        ("Pavimento o vereda", "Calle o pasaje de barrio", "Moneda 800, Santiago", "Tapa de cámara reemplazada", 15, 4, 0, -33.4420, -70.6500),
    ]
    for tipo, lugar, sector, titulo, dias, si, no, lat, lon in resueltos:
        r = crear_reporte(titulo, "", tipo, lugar, "Sin peligro", sector,
                          fecha=ahora - timedelta(days=dias), estado="Resuelto", lat=lat, lon=lon)
        r["resolucion"] = {"si": si, "no": no}
        _log(r, "Estado actualizado a 'Resuelto'")
        guardar(r)