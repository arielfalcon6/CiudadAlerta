# -*- coding: utf-8 -*-
"""
CiudadAlerta - árbol de decisiones y coincidencia por organismo (solo librería estándar).

Cada respuesta del vecino suma puntos a uno o más organismos y deja una razón escrita.
Al final, los puntos se convierten en porcentajes de coincidencia. La siguiente pregunta
depende de la respuesta anterior (árbol). Esta información la ven solo las autoridades.

Los porcentajes son un puntaje heurístico del prototipo, no una probabilidad estadística.
"""

ORG = ["MUNI", "SERVIU", "MOP", "CMN", "SANITARIA", "DISTRIBUIDORA"]  # orden fijo = desempate
RAIZ = "area"

# ---------------------------------------------------------------- razones (base legal / criterio)
R_ASEO = "Aseo y ornato de la comuna: función privativa de la municipalidad (Ley 18.695, art. 3 letra f)."
R_VIA_MUNI = "La municipalidad responde por el mal estado de calles y veredas de su comuna (falta de servicio, según la jurisprudencia)."
R_PAV_SERVIU = "SERVIU tiene la función de construir, reponer y conservar los pavimentos de aceras y calzadas urbanas con fondos presupuestarios."
R_MOP_VIA = "Las rutas y caminos fuera de la ciudad están a cargo del MOP (Vialidad)."
R_CONC = "Las autopistas concesionadas las gestiona el MOP (Coordinación de Concesiones) junto con la concesionaria."
R_ALUMBRADO = "La operación y mantención del alumbrado público recae en la municipalidad (la SEC ha formulado cargos a municipios por esto)."
R_SENAL = "La instalación y mantención de la señalización de tránsito es municipal, salvo en vías a cargo del MOP (Ley 18.290, art. 100)."
R_SEMAFORO = "La reparación de semáforos es responsabilidad municipal mediante contratos de mantención; la UOCT solo monitorea las fallas."
R_LLUVIAS_SERVIU = "Red secundaria de aguas lluvias (sumideros y calles): MINVU/SERVIU (Ley 19.525)."
R_LLUVIAS_MOP = "Red primaria de aguas lluvias, canales y cauces: obras hidráulicas del MOP (Ley 19.525)."
R_SAN = "El agua potable y el alcantarillado de aguas servidas los gestiona la empresa sanitaria."
R_DISTRIB = "Las líneas y postes de la red de distribución eléctrica son de la distribuidora, responsable de la seguridad de sus redes."
R_CMN = "Los Monumentos Históricos y las Zonas Típicas (Monumentos Nacionales) los supervisa el CMN."
R_ICH = "Los inmuebles y zonas de conservación histórica los define el Plan Regulador Comunal (municipio) y los supervigila la SEREMI MINVU."
R_DOM = "Construcción y urbanización: función municipal (Ley 18.695, art. 3 letra e), a través de la Dirección de Obras."
R_PRIMER = "La municipalidad suele ser el primer lugar al que acuden los vecinos, según las entrevistas a alcaldes."
R_DUDA = "No se puede saber con certeza a cuál corresponde: queda para revisión de la autoridad."


def op(texto, sig=None, ev=None, razon=None, tipo=None, lugar=None, aviso=None, incierto=False):
    return {"texto": texto, "siguiente": sig, "ev": ev or {}, "razon": razon or {},
            "tipo": tipo, "lugar": lugar, "aviso": aviso, "incierto": incierto}


def _vias(sig):
    return [op("Calle o pasaje del barrio", sig, {"MUNI": 4, "SERVIU": 1}, {"MUNI": R_VIA_MUNI, "SERVIU": R_PAV_SERVIU}, lugar="Calle o pasaje de barrio"),
            op("Avenida principal", sig, {"MUNI": 2, "SERVIU": 3}, {"MUNI": R_VIA_MUNI, "SERVIU": R_PAV_SERVIU}, lugar="Avenida principal"),
            op("Ruta o camino fuera de la ciudad", sig, {"MOP": 6}, {"MOP": R_MOP_VIA}, lugar="Ruta o camino interurbano"),
            op("Autopista con peaje", sig, {"MOP": 6}, {"MOP": R_CONC}, lugar="Ruta o camino interurbano")]


NODOS = {
    "area": {"pregunta": "¿Dónde está el problema?", "opciones": [
        op("Calle o calzada (por donde pasan los autos)", "via_calzada", tipo="Pavimento o vereda"),
        op("Vereda o acera (por donde camina la gente)", "via_vereda", tipo="Pavimento o vereda"),
        op("Plaza, parque o área verde", "verde", tipo="Plaza o área verde", lugar="Plaza o parque"),
        op("Luminaria, poste o cables", "luz", tipo="Alumbrado público"),
        op("Semáforo o señal de tránsito", "senal", tipo="Semáforos o señalización"),
        op("Agua, alcantarillado o inundación", "agua", tipo="Agua o alcantarillado"),
        op("Edificio, construcción o monumento", "edificio", tipo="Edificio o estructura"),
        op("Basura, escombros o microbasural", "basura", tipo="Basura o aseo"),
        op("Otro", "otro", tipo="Otro")]},
    "via_calzada": {"pregunta": "¿Qué tipo de vía es?", "ayuda": "Avenida principal: varias pistas y mucho tráfico.",
                    "opciones": _vias("dano_calzada")},
    "via_vereda": {"pregunta": "¿Junto a qué tipo de vía está la vereda?", "ayuda": "Avenida principal: varias pistas y mucho tráfico.",
                   "opciones": [op("Calle o pasaje del barrio", "dano_vereda", {"MUNI": 4, "SERVIU": 1}, {"MUNI": R_VIA_MUNI, "SERVIU": R_PAV_SERVIU}, lugar="Calle o pasaje de barrio"),
                                op("Avenida principal", "dano_vereda", {"MUNI": 3, "SERVIU": 3}, {"MUNI": R_VIA_MUNI, "SERVIU": R_PAV_SERVIU}, lugar="Avenida principal"),
                                op("Ruta o camino fuera de la ciudad", "dano_vereda", {"MOP": 5, "MUNI": 1}, {"MOP": R_MOP_VIA, "MUNI": R_PRIMER}, lugar="Ruta o camino interurbano")]},
    "dano_calzada": {"pregunta": "¿Qué le pasa a la calzada?", "opciones": [
        op("Hoyo o bache"),
        op("Grietas o hundimiento", "agua_visible"),
        op("Se inunda o el sumidero está tapado", None, {"SERVIU": 4, "MOP": 2, "MUNI": 1},
           {"SERVIU": R_LLUVIAS_SERVIU, "MOP": R_LLUVIAS_MOP, "MUNI": R_PRIMER}, tipo="Agua o alcantarillado"),
        op("Falta pintura, paso de cebra o señal", None, {"MUNI": 3}, {"MUNI": R_SENAL}, tipo="Semáforos o señalización")]},
    "dano_vereda": {"pregunta": "¿Qué le pasa a la vereda?", "opciones": [
        op("Baldosas rotas o sueltas"),
        op("Hoyo o hundimiento", "agua_visible"),
        op("Raíces de un árbol la levantan", None, {"MUNI": 3}, {"MUNI": R_ASEO}),
        op("Está bloqueada o falta un tramo")]},
    "agua_visible": {"pregunta": "¿Se ve agua saliendo o el suelo mojado?", "ayuda": "Un hundimiento con agua puede venir de una cañería rota.",
                     "opciones": [op("Sí, hay agua", None, {"SANITARIA": 6}, {"SANITARIA": R_SAN}, tipo="Agua o alcantarillado"),
                                  op("No"),
                                  op("No lo sé", None, {"SANITARIA": 1}, {"SANITARIA": R_DUDA})]},
    "verde": {"pregunta": "¿Qué ocurre en la plaza o área verde?", "opciones": [
        op("Falta mantención (pasto, plantas, limpieza)", None, {"MUNI": 7}, {"MUNI": R_ASEO}),
        op("Árbol caído o en riesgo de caer", None, {"MUNI": 7}, {"MUNI": R_ASEO}),
        op("Juegos o mobiliario dañado", None, {"MUNI": 7}, {"MUNI": R_ASEO})]},
    "luz": {"pregunta": "¿Qué elemento está dañado?", "opciones": [
        op("Luminaria apagada o quebrada", None, {"MUNI": 5, "DISTRIBUIDORA": 1},
           {"MUNI": R_ALUMBRADO, "DISTRIBUIDORA": "Si la luminaria está a cargo de la distribuidora por contrato con el municipio, esta podría intervenir."}),
        op("Poste inclinado o caído", "poste_cables"),
        op("Cables colgando o caídos", None, {"DISTRIBUIDORA": 6, "MUNI": 1}, {"DISTRIBUIDORA": R_DISTRIB, "MUNI": R_PRIMER},
           aviso="No te acerques ni toques los cables. Si hay riesgo, llama al 133, 132 o 131."),
        op("Tapa o caja eléctrica abierta", None, {"DISTRIBUIDORA": 4, "MUNI": 2}, {"DISTRIBUIDORA": R_DISTRIB, "MUNI": R_ALUMBRADO})]},
    "poste_cables": {"pregunta": "¿El poste lleva cables eléctricos de la red?", "opciones": [
        op("Sí, tiene cables", None, {"DISTRIBUIDORA": 5, "MUNI": 1}, {"DISTRIBUIDORA": R_DISTRIB, "MUNI": R_PRIMER}),
        op("No, solo tiene la luminaria", None, {"MUNI": 5, "DISTRIBUIDORA": 1}, {"MUNI": R_ALUMBRADO, "DISTRIBUIDORA": R_DUDA}),
        op("No lo sé", None, {"MUNI": 3, "DISTRIBUIDORA": 3}, {"MUNI": R_DUDA, "DISTRIBUIDORA": R_DUDA}, incierto=True)]},
    "senal": {"pregunta": "¿Qué ocurre?", "opciones": [
        op("Semáforo apagado o con falla", "via_senal", {"MUNI": 3}, {"MUNI": R_SEMAFORO}),
        op("Señal de tránsito dañada, caída o tapada", "via_senal", {"MUNI": 3}, {"MUNI": R_SENAL}),
        op("Falta una señal o la demarcación está borrada", "via_senal", {"MUNI": 3}, {"MUNI": R_SENAL})]},
    "via_senal": {"pregunta": "¿En qué tipo de vía está?", "opciones": [
        op("Calle o avenida de la ciudad", None, {"MUNI": 4}, {"MUNI": R_SENAL}, lugar="Calle o pasaje de barrio"),
        op("Ruta o camino fuera de la ciudad", None, {"MOP": 7}, {"MOP": R_MOP_VIA}, lugar="Ruta o camino interurbano"),
        op("No lo sé", None, {"MUNI": 1}, {"MUNI": R_DUDA}, incierto=True)]},
    "agua": {"pregunta": "¿Qué se ve?", "opciones": [
        op("Fuga de agua potable (agua limpia)", None, {"SANITARIA": 7}, {"SANITARIA": R_SAN}),
        op("Alcantarillado: olor, rebalse o tapa faltante", None, {"SANITARIA": 7}, {"SANITARIA": R_SAN}),
        op("Inundación o sumidero tapado con lluvia", None, {"SERVIU": 4, "MOP": 2, "MUNI": 1},
           {"SERVIU": R_LLUVIAS_SERVIU, "MOP": R_LLUVIAS_MOP, "MUNI": R_PRIMER}),
        op("Canal, río o cauce desbordado o tapado", None, {"MOP": 5, "MUNI": 1}, {"MOP": R_LLUVIAS_MOP, "MUNI": R_PRIMER})]},
    "edificio": {"pregunta": "¿Qué tipo de construcción es?", "opciones": [
        op("Casa o edificio común en mal estado", None, {"MUNI": 7}, {"MUNI": R_DOM}, lugar="Edificio común"),
        op("Edificio antiguo o patrimonial", "patrimonio", lugar="Edificio o monumento histórico"),
        op("Estatua, fuente o monumento en la calle", None, {"CMN": 4, "MUNI": 3},
           {"CMN": "Los monumentos públicos son Monumentos Nacionales supervisados por el CMN.",
            "MUNI": "La municipalidad suele mantener el aseo y el entorno del espacio público."}, lugar="Edificio o monumento histórico")]},
    "patrimonio": {"pregunta": "¿Tiene placa de Monumento Nacional o está en una Zona Típica?", "opciones": [
        op("Sí", None, {"CMN": 7, "MUNI": 1}, {"CMN": R_CMN, "MUNI": R_PRIMER}),
        op("No o no lo sé", None, {"CMN": 3, "MUNI": 4}, {"CMN": "Podría ser un Monumento Nacional que no se reconoce a simple vista.", "MUNI": R_ICH}, incierto=True)]},
    "basura": {"pregunta": "¿Qué hay?", "opciones": [
        op("Basura acumulada o contenedor desbordado", None, {"MUNI": 7}, {"MUNI": R_ASEO}),
        op("Escombros o microbasural", None, {"MUNI": 7}, {"MUNI": R_ASEO})]},
    "otro": {"pregunta": "¿Con qué se relaciona más?", "opciones": [
        op("Calles, caminos o veredas", None, {"MUNI": 2, "SERVIU": 1, "MOP": 1}, {"MUNI": R_PRIMER, "SERVIU": R_PAV_SERVIU, "MOP": R_MOP_VIA}, incierto=True),
        op("Agua o electricidad", None, {"SANITARIA": 2, "DISTRIBUIDORA": 2}, {"SANITARIA": R_SAN, "DISTRIBUIDORA": R_DISTRIB}, incierto=True),
        op("Edificios o patrimonio", None, {"MUNI": 2, "CMN": 2}, {"MUNI": R_ICH, "CMN": R_CMN}, incierto=True),
        op("No lo sé", None, {"MUNI": 2}, {"MUNI": R_PRIMER}, incierto=True)]},
}


# ---------------------------------------------------------------- cálculo
def _porcentajes(pts):
    total = sum(pts.values())
    crudo = {k: 100 * v / total for k, v in pts.items() if v > 0}
    pct = {k: int(v) for k, v in crudo.items()}
    resto = 100 - sum(pct.values())
    for k in sorted(crudo, key=lambda k: (-(crudo[k] - pct[k]), ORG.index(k)))[:resto]:
        pct[k] += 1
    return pct


def clasificar(ruta):
    """ruta = [(id_nodo, indice_opcion), ...]. Devuelve la clasificación completa del reporte."""
    pts, razones, resp, incierto = {k: 0 for k in ORG}, {k: [] for k in ORG}, [], False
    for nodo, i in ruta:
        info, o = NODOS[nodo], NODOS[nodo]["opciones"][i]
        resp.append({"pregunta": info["pregunta"], "respuesta": o["texto"]})
        for k, p in o["ev"].items():
            pts[k] += p
            t = o["razon"].get(k)
            if t and t not in razones[k]:
                razones[k].append(t)
        incierto = incierto or o["incierto"]
    if sum(pts.values()) == 0:
        pts["MUNI"], razones["MUNI"] = 1, [R_PRIMER]
    pct = _porcentajes(pts)
    ordenado = sorted(pct, key=lambda k: (-pct[k], ORG.index(k)))
    top = ordenado[0]
    confianza = "Baja" if incierto or pct[top] < 50 else ("Media" if pct[top] < 75 else "Alta")
    return {"organismo": top, "coincidencias": {k: pct[k] for k in ordenado},
            "razones": {k: razones[k] for k in ordenado}, "respuestas": resp, "confianza": confianza}


def tipo_de(ruta):
    tipo = None
    for nodo, i in ruta:
        tipo = NODOS[nodo]["opciones"][i]["tipo"] or tipo
    return tipo or "Otro"


def lugar_de(ruta):
    lugar = None
    for nodo, i in ruta:
        lugar = NODOS[nodo]["opciones"][i]["lugar"] or lugar
    return lugar or "Vía pública"


def _ruta(*prefijos):
    nodo, ruta = RAIZ, []
    for p in prefijos:
        ops = NODOS[nodo]["opciones"]
        i = next(k for k, o in enumerate(ops) if o["texto"].startswith(p))
        ruta.append((nodo, i))
        nodo = ops[i]["siguiente"]
        if nodo is None:
            break
    return ruta


def desde_tipo_lugar(tipo, lugar):
    """Camino equivalente para reportes antiguos o de ejemplo que solo traen tipo y lugar."""
    if lugar == "Edificio o monumento histórico":
        return _ruta("Edificio,", "Edificio antiguo", "Sí")
    if tipo == "Pavimento o vereda":
        via = {"Avenida principal": "Avenida principal", "Ruta o camino interurbano": "Ruta o camino"}.get(lugar, "Calle o pasaje")
        return _ruta("Calle o calzada", via, "Hoyo o bache")
    return _ruta({"Alumbrado público": "Luminaria,", "Plaza o área verde": "Plaza,", "Basura o aseo": "Basura,",
                  "Agua o alcantarillado": "Agua,", "Semáforos o señalización": "Semáforo o señal",
                  "Edificio o estructura": "Edificio,"}.get(tipo, "Otro"),
                 *{"Alumbrado público": ("Luminaria apagada",), "Plaza o área verde": ("Falta mantención",),
                   "Basura o aseo": ("Basura acumulada",), "Agua o alcantarillado": ("Fuga de agua",),
                   "Semáforos o señalización": ("Semáforo apagado", "Calle o avenida"),
                   "Edificio o estructura": ("Casa o edificio común",)}.get(tipo, ("No lo sé",)))
