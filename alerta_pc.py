"""
Alerta "MAMÁ TE ESTÁ LLAMANDO" - versión por internet
------------------------------------------------------
Se ejecuta en cada PC. Se conecta a ntfy.sh (un servicio gratuito de avisos)
y se queda escuchando. Cuando el móvil manda una alerta a este PC, muestra
el popup y le confirma al móvil que lo ha recibido y cuando se ha cerrado.

obJmcTFJloJ1WmcvYxTy8Q

Requisitos: Windows + Python 3 + requests  (pip install requests)
"""
import ctypes
import json
import os
import sys
import threading
import time

import requests

# ================== CONFIGURACIÓN ==================
CLAVE = "obJmcTFJloJ1WmcvYxTy8Q"   # el MISMO en los 2 PCs y en el móvil
NOMBRE = "Juan"                       # "santi" en el PC de Santi, "juan" en el de Juan
SERVIDOR = "https://ntfy.sh"
MENSAJE = "MAMA TE ESTA LLAMANDO"
MAX_ANTIGUEDAD = 120  # segundos: ignora alertas viejas (p. ej. si el PC estaba sin red)
# ===================================================

# Si se ejecuta sin consola (pythonw / .pyw), evita errores al imprimir
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

TEMA_ALERTAS = f"{CLAVE}-{NOMBRE}"   # aquí escucha este PC
TEMA_CONFIRMAR = f"{CLAVE}-ok"       # aquí responde al móvil

popup_abierto = threading.Event()


def confirmar(estado):
    """Avisa al móvil: 'recibido' (popup mostrado) o 'visto' (popup cerrado)."""
    try:
        requests.post(f"{SERVIDOR}/{TEMA_CONFIRMAR}",
                      data=f"{NOMBRE}:{estado}".encode(), timeout=10)
    except requests.RequestException as e:
        print("No se pudo confirmar:", e)


def mostrar_popup():
    # MB_ICONEXCLAMATION | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST
    flags = 0x30 | 0x1000 | 0x10000 | 0x40000
    ctypes.windll.user32.MessageBoxW(0, MENSAJE, "Aviso de mamá", flags)  # espera al OK
    popup_abierto.clear()
    confirmar("visto")


def recibir_alerta():
    if not popup_abierto.is_set():
        popup_abierto.set()
        threading.Thread(target=mostrar_popup, daemon=True).start()
    threading.Thread(target=confirmar, args=("recibido",), daemon=True).start()


def escuchar():
    ultimo_id = None        # último mensaje procesado
    ultimo_contacto = None  # última vez que el servidor dio señales de vida

    while True:
        params = {}
        if ultimo_id:
            params["since"] = ultimo_id            # recupera lo que llegó durante un corte
        elif ultimo_contacto:
            params["since"] = str(int(ultimo_contacto))

        try:
            with requests.get(f"{SERVIDOR}/{TEMA_ALERTAS}/json", params=params,
                              stream=True, timeout=(10, 90)) as r:
                r.raise_for_status()
                print(f"Conectado. Escuchando alertas para '{NOMBRE}'...")
                for linea in r.iter_lines():
                    if not linea:
                        continue
                    ultimo_contacto = time.time()
                    msg = json.loads(linea)
                    if msg.get("event") != "message" or msg.get("id") == ultimo_id:
                        continue
                    ultimo_id = msg["id"]
                    if time.time() - msg.get("time", 0) > MAX_ANTIGUEDAD:
                        continue  # alerta demasiado vieja, no la mostramos
                    print("¡Alerta recibida!")
                    recibir_alerta()
        except (requests.RequestException, ValueError) as e:
            print("Conexión perdida, reintento en 5 s:", e)
        time.sleep(5)


if __name__ == "__main__":
    if CLAVE.startswith("PON-AQUI"):
        print("Primero cambia CLAVE en la configuración del archivo.")
        sys.exit(1)
    escuchar()
