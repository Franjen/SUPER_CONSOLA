import os
import re
import difflib
import unicodedata
import json
import time
import ctypes
import threading
import subprocess
import shutil
import hashlib
import urllib.request
import urllib.parse
from ctypes import wintypes

import tkinter as tk
from tkinter import messagebox, simpledialog

from PIL import Image, ImageTk


# ============================================================
# MI BIBLIOTECA DE JUEGOS - V3.7 (PERFILES WII Y FULLSCREEN)
# ============================================================
# NUEVO:
# - IGDB
# - Descarga automática de portadas
# - Caché local de metadatos
# - Consultas en segundo plano
# - Las portadas existentes NO se vuelven a descargar
#
# CONSERVA:
# - Interfaz tipo consola
# - Pillow
# - Mando
# - Teclado
# - Azahar
# - F11 automático
# - Regreso automático a Biblioteca
# ============================================================


# ============================================================
# CARPETAS
# ============================================================

CARPETA_ROMS = r"C:\Juegos\ROMS"
CARPETA_BIBLIOTECA = r"C:\Juegos\Biblioteca"

CARPETA_PORTADAS = os.path.join(
    CARPETA_BIBLIOTECA,
    "portadas"
)

CARPETA_CACHE = os.path.join(
    CARPETA_BIBLIOTECA,
    "cache"
)

ARCHIVO_CONFIG = os.path.join(
    CARPETA_BIBLIOTECA,
    "config_igdb.json"
)

ARCHIVO_CACHE = os.path.join(
    CARPETA_CACHE,
    "biblioteca.json"
)

os.makedirs(
    CARPETA_PORTADAS,
    exist_ok=True
)

os.makedirs(
    CARPETA_CACHE,
    exist_ok=True
)


# ============================================================
# SISTEMAS
# ============================================================

SISTEMAS = {

    "3DS": {
        "exe": r"C:\Program Files\Azahar\azahar.exe",

        "extensiones": [
            ".3ds",
            ".cci",
            ".cxi",
            ".app"
        ],

        "igdb": [
            "Nintendo 3DS"
        ],
    },

    "N64": {
        "exe": r"C:\Juegos\Emuladores\N64\Project64.exe",

        "extensiones": [
            ".z64",
            ".n64",
            ".v64"
        ],

        "igdb": [
            "Nintendo 64"
        ],
    },

    "NDS": {
        "exe": r"C:\Juegos\Emuladores\NDS\melonDS.exe",

        "extensiones": [
            ".nds"
        ],

        "igdb": [
            "Nintendo DS"
        ],
    },

    "GBA": {
        "exe": r"C:\Juegos\Emuladores\GBA\mGBA.exe",

        "extensiones": [
            ".gba"
        ],

        "igdb": [
            "Game Boy Advance"
        ],
    },

    "SNES": {
        "exe": r"C:\Juegos\Emuladores\SNES\snes9x-x64.exe",

        "extensiones": [
            ".sfc",
            ".smc"
        ],

        "igdb": [
            "Super Nintendo Entertainment System"
        ],
    },

    "NES": {
        "exe": "",

        "extensiones": [
            ".nes"
        ],

        "igdb": [
            "Nintendo Entertainment System"
        ],
    },

    "GameCube": {
        "exe": "",

        "extensiones": [
            ".iso",
            ".gcm",
            ".rvz"
        ],

        "igdb": [
            "Nintendo GameCube"
        ],
    },

    "Wii": {
        "exe": "",

        "extensiones": [
            ".iso",
            ".wbfs",
            ".rvz"
        ],

        "igdb": [
            "Wii"
        ],
    },

    "PSP": {
        "exe": "",

        "extensiones": [
            ".iso",
            ".cso"
        ],

        "igdb": [
            "PlayStation Portable"
        ],
    },

    "PS1": {
        "exe": "",

        "extensiones": [
            ".cue",
            ".chd"
        ],

        "igdb": [
            "PlayStation"
        ],
    },
}


# ============================================================
# DETECCION DE mGBA (sin alterar otros emuladores)
# ============================================================
def localizar_mgba():
    """Busca mGBA en ubicaciones habituales y en PATH."""
    candidatos = [
        SISTEMAS["GBA"]["exe"],
        r"C:\Juegos\Emuladores\GBA\mGBA-0.10.5-win64\mGBA.exe",
        r"C:\Juegos\Emuladores\mGBA\mGBA.exe",
        r"C:\Program Files\mGBA\mGBA.exe",
        r"C:\Program Files (x86)\mGBA\mGBA.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "mGBA", "mGBA.exe"),
        shutil.which("mGBA.exe"),
    ]
    for ruta in candidatos:
        if ruta and os.path.isfile(ruta):
            return ruta
    return None


# ============================================================
# DOLPHIN: detección sin modificar su configuración de mandos
# ============================================================
def localizar_dolphin():
    candidatos = [
        r"C:\Juegos\Emuladores\Wii\Dolphin.exe",
        r"C:\Juegos\Emuladores\Dolphin\Dolphin.exe",
        r"C:\Juegos\Emuladores\GameCube\Dolphin.exe",
        r"C:\Juegos\Emuladores\Dolphin-x64\Dolphin.exe",
        r"C:\Program Files\Dolphin\Dolphin.exe",
        r"C:\Program Files (x86)\Dolphin\Dolphin.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Dolphin", "Dolphin.exe"),
        shutil.which("Dolphin.exe"),
    ]
    for ruta in candidatos:
        if ruta and os.path.isfile(ruta):
            return ruta
    # Permite encontrar instalaciones portables dentro de Emuladores.
    raiz = r"C:\Juegos\Emuladores"
    if os.path.isdir(raiz):
        for carpeta, subcarpetas, archivos in os.walk(raiz):
            subcarpetas[:] = [d for d in subcarpetas if d.lower() not in ("roms", "games", "cache")]
            for archivo in archivos:
                if archivo.lower() == "dolphin.exe":
                    return os.path.join(carpeta, archivo)
    return None


# ============================================================
# PERFILES WII AUTOMATICOS - V3.7
# No cambia Dolphin.ini: Fullscreen = True ya está configurado.
# ============================================================
CONFIG_DOLPHIN = os.path.join(os.environ.get("APPDATA", ""), "Dolphin Emulator", "Config")
ARCHIVO_WIIMOTE = os.path.join(CONFIG_DOLPHIN, "WiimoteNew.ini")
ARCHIVO_PERFILES_WII = os.path.join(CARPETA_BIBLIOTECA, "perfiles_wii.json")


def tipo_mando_wii(juego):
    """Devuelve Classic o Nunchuk; guarda decisiones para otros títulos."""
    nombre = normalizar_titulo_igdb(juego["nombre"])
    if "super mario galaxy" in nombre:
        return "Nunchuk"
    if "budokai tenkaichi" in nombre:
        return "Classic"
    try:
        with open(ARCHIVO_PERFILES_WII, encoding="utf-8") as f:
            guardados = json.load(f)
        valor = guardados.get(os.path.basename(juego["ruta"]).casefold())
        if valor in ("Classic", "Nunchuk"):
            return valor
    except (OSError, ValueError, TypeError):
        pass
    return None


def guardar_tipo_mando_wii(juego, tipo):
    try:
        with open(ARCHIVO_PERFILES_WII, encoding="utf-8") as f:
            guardados = json.load(f)
            if not isinstance(guardados, dict):
                guardados = {}
    except (OSError, ValueError, TypeError):
        guardados = {}
    guardados[os.path.basename(juego["ruta"]).casefold()] = tipo
    with open(ARCHIVO_PERFILES_WII, "w", encoding="utf-8") as f:
        json.dump(guardados, f, ensure_ascii=False, indent=2)


def configurar_mandos_wii(tipo):
    """Cambia solo Extension de Wii Remote 1 y 2, conserva todos los botones."""
    if tipo not in ("Classic", "Nunchuk"):
        raise ValueError("Tipo de mando Wii no válido")
    if not os.path.isfile(ARCHIVO_WIIMOTE):
        raise FileNotFoundError("No se encontró la configuración de Dolphin: " + ARCHIVO_WIIMOTE)
    with open(ARCHIVO_WIIMOTE, "rb") as f:
        original = f.read()
    # Respaldo original una sola vez; nunca sobreescribirlo.
    respaldo = ARCHIVO_WIIMOTE + ".biblioteca_respaldo"
    if not os.path.exists(respaldo):
        with open(respaldo, "wb") as f:
            f.write(original)
    contenido = original.decode("utf-8-sig")
    fin_linea = "\r\n" if b"\r\n" in original else "\n"
    for numero in (1, 2):
        patron = r"(?ms)(^\[Wiimote" + str(numero) + r"\]\s*\r?\n)(.*?)(?=^\[|\Z)"
        def reemplazar(seccion):
            cabecera, cuerpo = seccion.group(1), seccion.group(2)
            if re.search(r"(?m)^Extension\s*=.*$", cuerpo):
                cuerpo = re.sub(r"(?m)^Extension\s*=.*$", "Extension = " + tipo, cuerpo, count=1)
            else:
                cuerpo += "Extension = " + tipo + fin_linea
            return cabecera + cuerpo
        contenido, cuenta = re.subn(patron, reemplazar, contenido, count=1)
        if cuenta != 1:
            raise RuntimeError("No se encontró Wiimote" + str(numero) + " en WiimoteNew.ini")
    if contenido != original.decode("utf-8-sig"):
        temporal = ARCHIVO_WIIMOTE + ".biblioteca_tmp"
        with open(temporal, "wb") as f:
            f.write((b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b"") + contenido.encode("utf-8"))
        os.replace(temporal, ARCHIVO_WIIMOTE)


# ============================================================
# COLORES
# ============================================================

COLOR_FONDO = "#090e15"
COLOR_PANEL = "#111827"
COLOR_TARJETA = "#182131"
COLOR_TARJETA_SELECCIONADA = "#293b56"

COLOR_AZUL = "#3b82f6"
COLOR_AZUL_CLARO = "#60a5fa"

COLOR_TEXTO = "#ffffff"
COLOR_TEXTO_SECUNDARIO = "#9ca3af"

COLOR_VERDE = "#22c55e"
COLOR_AMARILLO = "#fbbf24"
COLOR_ROJO = "#ef4444"


# ============================================================
# JOYSTICK WINDOWS
# ============================================================

winmm = ctypes.WinDLL("winmm")

JOY_RETURNX = 0x00000001
JOY_RETURNY = 0x00000002
JOY_RETURNZ = 0x00000004
JOY_RETURNR = 0x00000008
JOY_RETURNPOV = 0x00000040
JOY_RETURNBUTTONS = 0x00000080

JOY_RETURNALL = (
    JOY_RETURNX |
    JOY_RETURNY |
    JOY_RETURNZ |
    JOY_RETURNR |
    JOY_RETURNPOV |
    JOY_RETURNBUTTONS
)


class JOYINFOEX(ctypes.Structure):

    _fields_ = [

        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),

        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),

        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),

        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),

        ("dwPOV", wintypes.DWORD),

        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


# ============================================================
# UTILIDADES
# ============================================================

def limpiar_nombre(nombre):

    nombre = os.path.splitext(nombre)[0]

    etiquetas = [

        "3DS",
        "N64",
        "NDS",
        "GBA",
        "SNES",
        "NES",
        "GAMECUBE",
        "WII",
        "PSP",
        "PS1"
    ]

    for etiqueta in etiquetas:

        nombre = re.sub(
            rf"\[{re.escape(etiqueta)}\]",
            "",
            nombre,
            flags=re.IGNORECASE
        )

    # --------------------------------------------------------
    # Quitar etiquetas comunes de ROM
    # --------------------------------------------------------

    nombre = re.sub(
        r"\((USA|EUR|EUROPE|JAPAN|JPN|WORLD|SPAIN|ES|EN|FR|DE|ITALY)\)",
        "",
        nombre,
        flags=re.IGNORECASE
    )

    nombre = re.sub(
        r"\s+",
        " ",
        nombre
    )

    return nombre.strip()


def nombre_limpio_nds(nombre):
    """Quita prefijos de dumps y etiquetas de grupos, sin tocar el archivo real."""
    nombre = os.path.splitext(os.path.basename(nombre))[0]
    nombre = re.sub(r"^\s*\d{3,5}\s*[-_.]\s*", "", nombre)
    nombre = re.sub(r"\([^)]*(?:XenoPhobia|EXiMiUS|USA|Europe|Spain|E\)|U\)|J\))[^)]*\)", " ", nombre, flags=re.I)
    nombre = re.sub(r"\[(?:NDS|DS)\]", " ", nombre, flags=re.I)
    nombre = re.sub(r"\b(?:Español|Spanish)\b", " ", nombre, flags=re.I)
    nombre = re.sub(r"\s+", " ", nombre).strip(" -_.")
    return nombre


def limpiar_nombre_busqueda_igdb(nombre):
    """Quita etiquetas de ROM sin eliminar números importantes del título."""
    nombre = nombre_limpio_nds(nombre)
    # Etiquetas de región/idiomas de Wii: (Europe, Australia) (En,Fr,De,Es,It).
    nombre = re.sub(r"\([^)]*(?:Europe|Australia|USA|Japan|En,Fr|En,De|Fr,De|Es,It)[^)]*\)", " ", nombre, flags=re.I)
    nombre = re.sub(r"\[(?:3DS|N64|NDS|GBA|SNES|NES|GAMECUBE|WII|PSP|PS1)\]", " ", nombre, flags=re.I)
    nombre = re.sub(r"\b(?:Español|Spanish|English|Ingl[eé]s)\b", " ", nombre, flags=re.I)
    nombre = re.sub(r"\((?:USA|U|E|EUR|EUROPE|JAPAN|JPN|WORLD|SPAIN|ES|EN|FR|DE|ITALY|M\d+|V\d+(?:\.\d+)*|REV[^)]*)\)", " ", nombre, flags=re.I)
    nombre = re.sub(r"\[(?:USA|EUR|EUROPE|JAPAN|JPN|WORLD|SPAIN|ES|EN|FR|DE|ITALY|REV[^]]*)\]", " ", nombre, flags=re.I)
    nombre = nombre.replace("[", " ").replace("]", " ")
    nombre = re.sub(r"^(.+?),\s*The\s*-\s*(.+)$", r"The \1: \2", nombre, flags=re.I)
    nombre = nombre.replace(" - ", ": ")
    nombre = re.sub(r"\s+", " ", nombre).strip(" -_:")
    nombre = re.sub(r"\bTri\s*Force\b", "Triforce", nombre, flags=re.I)
    return nombre


def normalizar_titulo_igdb(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def nombres_alternativos_igdb(nombre):
    base = limpiar_nombre_busqueda_igdb(nombre)
    variantes = [base]
    # Títulos localizados de Nintendo DS: IGDB suele indexarlos en inglés.
    clave = normalizar_titulo_igdb(base)
    if "pokemon" in clave and ("platino" in clave or "platinum" in clave):
        variantes.insert(0, "Pokemon Platinum Version")
        variantes.append("Pokemon Platinum")
    if "pokemon" in clave and ("heartgold" in clave or "oro" in clave):
        variantes.insert(0, "Pokemon HeartGold Version")
        variantes.append("Pokemon HeartGold")
    # Ediciones en español de GBA que IGDB indexa con títulos internacionales.
    if "megaman" in clave and "zero" in clave and not re.search(r"\b[2-4]\b", clave):
        variantes.insert(0, "Mega Man Zero")
        variantes.append("Megaman Zero")
    if "pokemon" in clave and ("mundo misterioso" in clave or "mystery dungeon" in clave):
        variantes.insert(0, "Pokemon Mystery Dungeon Red Rescue Team")
        variantes.append("Pokémon Mystery Dungeon: Red Rescue Team")
    # Algunas ediciones de IGDB separan «Tri Force» y otras usan «Triforce».
    variantes.append(re.sub(r"triforce", "Tri Force", base, flags=re.I))
    variantes.append(base.replace(":", " ").replace("-", " "))
    # Una búsqueda más corta sirve como respaldo, sin sacrificar la validación final.
    palabras = base.split()
    if len(palabras) >= 4:
        variantes.append(" ".join(palabras[:4]))
    resultado = []
    vistos = set()
    for variante in variantes:
        variante = " ".join(variante.split()).strip()
        clave = normalizar_titulo_igdb(variante)
        if clave and clave not in vistos:
            resultado.append(variante)
            vistos.add(clave)
    return resultado


def preparar_rom_nds(ruta):
    """Alias ASCII para ROM NDS: evita fallos de argumentos Unicode de melonDS.

    Mantiene la ROM original y copia temporalmente el guardado al alias.
    Devuelve (ruta_para_abrir, datos_para_limpieza). Solo crea un alias si
    hay caracteres no ASCII en el nombre o en la ruta.
    """
    ruta = os.path.abspath(ruta)
    if not os.path.isfile(ruta):
        raise FileNotFoundError("No se encuentra la ROM: " + ruta)
    try:
        ruta.encode("ascii")
        return ruta, None
    except UnicodeEncodeError:
        pass

    carpeta = os.path.dirname(ruta)
    # Primero intentamos la ruta corta de Windows, que evita crear archivos.
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        kernel32.GetShortPathNameW.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        n = kernel32.GetShortPathNameW(ruta, buffer, len(buffer))
        if 0 < n < len(buffer) and os.path.isfile(buffer.value):
            try:
                buffer.value.encode("ascii")
                return buffer.value, None
            except UnicodeEncodeError:
                pass
    except Exception:
        pass

    # Alias estable dentro de la misma carpeta: hardlink sin duplicar la ROM.
    # Si la carpeta también tiene caracteres no ASCII, se necesita otra ruta.
    try:
        carpeta.encode("ascii")
    except UnicodeEncodeError:
        raise RuntimeError("La carpeta de la ROM contiene caracteres especiales. "
                           "Mueve el juego a C:\\Juegos\\ROMS\\NDS y pulsa F5.")
    identificador = hashlib.sha256(ruta.encode("utf-8")).hexdigest()[:12]
    alias = os.path.join(carpeta, "_biblioteca_nds_" + identificador + ".nds")
    creado = False
    if not os.path.exists(alias):
        os.link(ruta, alias)
        creado = True
    elif not os.path.samefile(ruta, alias):
        raise RuntimeError("El alias de la ROM está ocupado por otro archivo: " + alias)
    original_sav = os.path.splitext(ruta)[0] + ".sav"
    alias_sav = os.path.splitext(alias)[0] + ".sav"
    # Evitar sobrescribir un guardado del alias que aún no se haya recuperado.
    if os.path.isfile(alias_sav):
        if os.path.isfile(original_sav) and os.path.getmtime(alias_sav) > os.path.getmtime(original_sav):
            respaldo = original_sav + ".biblioteca_backup"
            if not os.path.exists(respaldo):
                shutil.copy2(original_sav, respaldo)
            shutil.copy2(alias_sav, original_sav)
    if os.path.isfile(original_sav):
        shutil.copy2(original_sav, alias_sav)
    return alias, (alias, original_sav, alias_sav, creado)


def finalizar_rom_nds(datos):
    if not datos:
        return
    alias, original_sav, alias_sav, creado = datos
    try:
        if os.path.isfile(alias_sav):
            if not os.path.isfile(original_sav) or os.path.getmtime(alias_sav) > os.path.getmtime(original_sav):
                if os.path.isfile(original_sav):
                    respaldo = original_sav + ".biblioteca_backup"
                    if not os.path.exists(respaldo):
                        shutil.copy2(original_sav, respaldo)
                shutil.copy2(alias_sav, original_sav)
            os.remove(alias_sav)
    finally:
        if creado and os.path.isfile(alias):
            os.remove(alias)


def nombre_seguro(nombre):

    nombre = limpiar_nombre(nombre)

    nombre = re.sub(
        r'[<>:"/\\|?*]',
        "",
        nombre
    )

    return nombre.strip()


def clave_cache(juego):

    return (
        juego["sistema"]
        + "|"
        + juego["nombre"]
    ).lower()


# ============================================================
# CONFIGURACIÓN IGDB
# ============================================================

def cargar_config_igdb():

    if not os.path.isfile(
        ARCHIVO_CONFIG
    ):

        return None

    try:

        with open(
            ARCHIVO_CONFIG,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(
                archivo
            )

        client_id = (
            datos.get(
                "client_id",
                ""
            ).strip()
        )

        client_secret = (
            datos.get(
                "client_secret",
                ""
            ).strip()
        )

        if not client_id:
            return None

        if not client_secret:
            return None

        return {
            "client_id": client_id,
            "client_secret": client_secret
        }

    except Exception as error:

        print(
            "Error leyendo config_igdb.json:",
            error
        )

        return None


# ============================================================
# CACHE
# ============================================================

def cargar_cache():

    if not os.path.isfile(
        ARCHIVO_CACHE
    ):

        return {}

    try:

        with open(
            ARCHIVO_CACHE,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(
                archivo
            )

        if isinstance(
            datos,
            dict
        ):

            return datos

    except Exception as error:

        print(
            "Error leyendo caché:",
            error
        )

    return {}


def guardar_cache(cache):

    try:

        temporal = (
            ARCHIVO_CACHE
            + ".tmp"
        )

        with open(
            temporal,
            "w",
            encoding="utf-8"
        ) as archivo:

            json.dump(
                cache,
                archivo,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            temporal,
            ARCHIVO_CACHE
        )

    except Exception as error:

        print(
            "Error guardando caché:",
            error
        )


# ============================================================
# PORTADAS LOCALES
# ============================================================

def buscar_portada(juego):

    nombre = nombre_seguro(
        juego["archivo"]
    )

    sistema = juego["sistema"]

    candidatos = [

        nombre,

        f"{sistema}_{nombre}",

        juego["nombre"],
        nombre_limpio_nds(juego["archivo"]),
        nombre_seguro(nombre_limpio_nds(juego["archivo"]))
    ]

    extensiones = [

        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    ]

    for candidato in candidatos:

        for extension in extensiones:

            ruta = os.path.join(
                CARPETA_PORTADAS,
                candidato + extension
            )

            if os.path.isfile(
                ruta
            ):

                return ruta

    # --------------------------------------------------------
    # Ignorar mayúsculas/minúsculas
    # --------------------------------------------------------

    try:

        archivos = os.listdir(
            CARPETA_PORTADAS
        )

        for archivo in archivos:

            base = os.path.splitext(
                archivo
            )[0]

            extension = os.path.splitext(
                archivo
            )[1].lower()

            if extension not in extensiones:
                continue

            for candidato in candidatos:

                if (
                    base.lower().strip()
                    ==
                    candidato.lower().strip()
                ):

                    return os.path.join(
                        CARPETA_PORTADAS,
                        archivo
                    )

    except Exception:
        pass

    return None


# ============================================================
# ESCANEAR ROMS
# ============================================================

def buscar_juegos():

    encontrados = []

    for sistema, datos in SISTEMAS.items():

        carpeta = os.path.join(
            CARPETA_ROMS,
            sistema
        )

        if not os.path.isdir(
            carpeta
        ):

            continue

        for raiz, carpetas, archivos in os.walk(
            carpeta
        ):

            for archivo in archivos:

                extension = os.path.splitext(
                    archivo
                )[1].lower()

                if extension not in datos["extensiones"]:
                    continue

                juego = {

                    "nombre":
                        limpiar_nombre(
                            archivo
                        ),

                    "archivo":
                        archivo,

                    "ruta":
                        os.path.join(
                            raiz,
                            archivo
                        ),

                    "sistema":
                        sistema,
                }

                juego["portada"] = (
                    buscar_portada(
                        juego
                    )
                )

                encontrados.append(
                    juego
                )

    encontrados.sort(
        key=lambda juego:
            juego["nombre"].lower()
    )

    return encontrados


# ============================================================
# IMÁGENES PILLOW
# ============================================================

def cargar_imagen(
    ruta,
    ancho_maximo,
    alto_maximo
):

    if not ruta:
        return None

    if not os.path.isfile(
        ruta
    ):

        return None

    try:

        with Image.open(
            ruta
        ) as original:

            imagen = original.convert(
                "RGBA"
            )

            imagen.thumbnail(
                (
                    ancho_maximo,
                    alto_maximo
                ),
                Image.Resampling.LANCZOS
            )

            copia = imagen.copy()

        return ImageTk.PhotoImage(
            copia
        )

    except Exception as error:

        print(
            "No se pudo cargar portada:",
            ruta
        )

        print(
            "Detalle:",
            error
        )

        return None


# ============================================================
# CLIENTE IGDB
# ============================================================

class ClienteIGDB:

    def __init__(
        self,
        config
    ):

        self.client_id = (
            config["client_id"]
        )

        self.client_secret = (
            config["client_secret"]
        )

        self.token = None

        self.token_expira = 0


    # ========================================================
    # TOKEN
    # ========================================================

    def obtener_token(
        self
    ):

        ahora = time.time()

        if (
            self.token
            and
            ahora < self.token_expira
        ):

            return self.token

        parametros = urllib.parse.urlencode({

            "client_id":
                self.client_id,

            "client_secret":
                self.client_secret,

            "grant_type":
                "client_credentials"
        })

        url = (
            "https://id.twitch.tv/oauth2/token?"
            + parametros
        )

        request = urllib.request.Request(
            url,
            method="POST"
        )

        with urllib.request.urlopen(
            request,
            timeout=15
        ) as respuesta:

            datos = json.loads(
                respuesta.read().decode(
                    "utf-8"
                )
            )

        self.token = (
            datos["access_token"]
        )

        duracion = int(
            datos.get(
                "expires_in",
                3600
            )
        )

        self.token_expira = (
            time.time()
            + duracion
            - 60
        )

        return self.token


    # ========================================================
    # CONSULTA
    # ========================================================

    def consultar(
        self,
        endpoint,
        cuerpo
    ):

        token = (
            self.obtener_token()
        )

        url = (
            "https://api.igdb.com/v4/"
            + endpoint
        )

        datos = cuerpo.encode(
            "utf-8"
        )

        request = urllib.request.Request(
            url,
            data=datos,
            method="POST"
        )

        request.add_header(
            "Client-ID",
            self.client_id
        )

        request.add_header(
            "Authorization",
            "Bearer "
            + token
        )

        request.add_header(
            "Content-Type",
            "text/plain"
        )

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as respuesta:

            return json.loads(
                respuesta.read().decode(
                    "utf-8"
                )
            )


    # ========================================================
    # BUSCAR JUEGO
    # ========================================================

    def buscar_juego(self, nombre, sistema):
        """Busca títulos alternativos y evita confundir secuelas y plataformas."""
        esperado = normalizar_titulo_igdb(limpiar_nombre_busqueda_igdb(nombre))
        if sistema == "NDS" and "pokemon" in esperado:
            if "platino" in esperado:
                esperado = "pokemon platinum version"
            elif "heartgold" in esperado or "oro" in esperado:
                esperado = "pokemon heartgold version"
        if sistema == "Wii" and "super mario galaxy" in esperado:
            esperado = "super mario galaxy"
        if sistema == "GBA":
            if "megaman" in esperado and "zero" in esperado and not re.search(r"\b[2-4]\b", esperado):
                esperado = "mega man zero"
            elif "pokemon" in esperado and ("mundo misterioso" in esperado or "mystery dungeon" in esperado):
                esperado = "pokemon mystery dungeon red rescue team"
        plataformas = {p.casefold() for p in SISTEMAS[sistema]["igdb"]}
        candidatos = []
        for intento, consulta in enumerate(nombres_alternativos_igdb(nombre)):
            consulta_segura = consulta.replace('"', "").replace("\\", "")
            cuerpo = (
                'search "' + consulta_segura + '"; '
                'fields name,cover.image_id,platforms.name,first_release_date,summary; limit 40;'
            )
            resultados = self.consultar("games", cuerpo)
            for posicion, juego in enumerate(resultados or []):
                nombres_plataforma = {
                    p.get("name", "").casefold() for p in juego.get("platforms", [])
                }
                if not (plataformas & nombres_plataforma):
                    continue
                nombre_igdb = normalizar_titulo_igdb(juego.get("name", ""))
                if not nombre_igdb:
                    continue
                # Las diferencias de puntuación y de «Tri Force» no afectan la coincidencia.
                a = esperado.replace("tri force", "triforce")
                b = nombre_igdb.replace("tri force", "triforce")
                semejanza = difflib.SequenceMatcher(None, a, b).ratio()
                if a == b:
                    semejanza = 1.0
                # No aceptar coincidencias dudosas ni secuelas equivocadas.
                if semejanza < 0.78:
                    continue
                portada = bool((juego.get("cover") or {}).get("image_id"))
                candidatos.append((semejanza, portada, -intento, -posicion, juego))
            if candidatos and max(c[0] for c in candidatos) >= 0.98 and any(c[1] for c in candidatos):
                break
        if not candidatos:
            return None
        candidatos.sort(key=lambda c: (c[0], c[1], c[2], c[3]), reverse=True)
        return candidatos[0][4]


# ============================================================
# BIBLIOTECA
# ============================================================

class Biblioteca:

    def __init__(
        self,
        root
    ):

        self.root = root

        self.root.title(
            "Mi Biblioteca de Juegos"
        )

        self.root.configure(
            bg=COLOR_FONDO
        )

        self.root.attributes(
            "-fullscreen",
            True
        )

        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        self.cache = (
            cargar_cache()
        )

        self.lock_cache = (
            threading.Lock()
        )

        # ----------------------------------------------------
        # IGDB
        # ----------------------------------------------------

        self.config_igdb = (
            cargar_config_igdb()
        )

        self.igdb = None

        if self.config_igdb:

            self.igdb = ClienteIGDB(
                self.config_igdb
            )

        # ----------------------------------------------------

        self.juegos = (
            buscar_juegos()
        )

        self.juegos_visibles = []

        self.filtro_actual = "TODOS"

        self.indice = 0

        self.tarjetas = []

        self.imagenes_tarjetas = []

        self.imagen_detalle_actual = None

        self.juego_ejecutandose = False

        self.proceso_emulador = None
        self.salida_solicitada = threading.Event()
        self.combinacion_inicio = {}

        self.descarga_activa = False

        # ----------------------------------------------------
        # MANDO
        # ----------------------------------------------------

        self.mando_activo = None

        # Estado independiente para cada mando USB.
        self.estados_mandos = {}
        self.ultimo_escaneo_mandos = 0
        self.ultimo_movimiento = 0

        self.bloqueo_movimiento = 0.20

        self.ultimo_cambio_sistema = 0

        # ----------------------------------------------------

        self.crear_interfaz()

        self.configurar_teclado()

        self.mostrar_juegos()

        self.detectar_mando()

        self.root.after(
            100,
            self.leer_mando
        )

        # ----------------------------------------------------
        # INICIAR METADATOS DESPUÉS DE MOSTRAR LA INTERFAZ
        # ----------------------------------------------------

        self.root.after(
            1200,
            self.iniciar_actualizacion_metadatos
        )


    # ========================================================
    # INTERFAZ
    # ========================================================

    def crear_interfaz(
        self
    ):

        # ====================================================
        # CABECERA
        # ====================================================

        cabecera = tk.Frame(
            self.root,
            bg=COLOR_FONDO,
            height=72
        )

        cabecera.pack(
            fill="x",
            padx=28,
            pady=(10, 0)
        )

        cabecera.pack_propagate(
            False
        )

        titulo = tk.Label(
            cabecera,
            text="MI BIBLIOTECA",
            font=(
                "Segoe UI",
                25,
                "bold"
            ),
            fg=COLOR_TEXTO,
            bg=COLOR_FONDO
        )

        titulo.pack(
            side="left"
        )

        subtitulo = tk.Label(
            cabecera,
            text="JUEGOS",
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            fg=COLOR_AZUL_CLARO,
            bg=COLOR_FONDO
        )

        subtitulo.pack(
            side="left",
            padx=(15, 0),
            pady=(10, 0)
        )

        self.estado_mando_label = tk.Label(
            cabecera,
            text="🎮 Buscando mando...",
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            fg=COLOR_AMARILLO,
            bg=COLOR_FONDO
        )

        self.estado_mando_label.pack(
            side="right",
            padx=10
        )

        self.contador = tk.Label(
            cabecera,
            text="",
            font=(
                "Segoe UI",
                11
            ),
            fg=COLOR_TEXTO_SECUNDARIO,
            bg=COLOR_FONDO
        )

        self.contador.pack(
            side="right",
            padx=15
        )

        self.estado_biblioteca = tk.Label(
            cabecera,
            text="",
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            fg=COLOR_VERDE,
            bg=COLOR_FONDO
        )

        self.estado_biblioteca.pack(
            side="right",
            padx=15
        )

        # ====================================================
        # SISTEMAS
        # ====================================================

        barra_sistemas = tk.Frame(
            self.root,
            bg=COLOR_FONDO,
            height=50
        )

        barra_sistemas.pack(
            fill="x",
            padx=28
        )

        barra_sistemas.pack_propagate(
            False
        )

        sistemas_menu = [

            "TODOS",
            "3DS",
            "N64",
            "NDS",
            "GBA",
            "SNES",
            "NES",
            "GameCube",
            "Wii",
            "PSP",
            "PS1"
        ]

        self.botones_sistema = {}

        for sistema in sistemas_menu:

            boton = tk.Button(
                barra_sistemas,
                text=sistema,
                font=(
                    "Segoe UI",
                    9,
                    "bold"
                ),
                fg=COLOR_TEXTO,
                bg=COLOR_PANEL,
                activebackground=COLOR_AZUL,
                activeforeground="white",
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda s=sistema:
                    self.cambiar_filtro(s)
            )

            boton.pack(
                side="left",
                padx=(0, 6),
                pady=6,
                ipadx=7,
                ipady=4
            )

            self.botones_sistema[
                sistema
            ] = boton

        # ====================================================
        # CENTRAL
        # ====================================================

        central = tk.Frame(
            self.root,
            bg=COLOR_FONDO
        )

        central.pack(
            fill="both",
            expand=True,
            padx=28,
            pady=(5, 8)
        )

        # ====================================================
        # LISTA
        # ====================================================

        lista_frame = tk.Frame(
            central,
            bg=COLOR_FONDO
        )

        lista_frame.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.canvas = tk.Canvas(
            lista_frame,
            bg=COLOR_FONDO,
            highlightthickness=0,
            bd=0
        )

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = tk.Scrollbar(
            lista_frame,
            orient="vertical",
            command=self.canvas.yview,
            width=13
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.canvas.configure(
            yscrollcommand=
                scrollbar.set
        )

        self.zona_juegos = tk.Frame(
            self.canvas,
            bg=COLOR_FONDO
        )

        self.ventana_canvas = (
            self.canvas.create_window(
                (0, 0),
                window=self.zona_juegos,
                anchor="nw"
            )
        )

        self.zona_juegos.bind(
            "<Configure>",
            self.actualizar_scrollregion
        )

        self.canvas.bind(
            "<Configure>",
            self.ajustar_ancho_canvas
        )

        # ====================================================
        # PANEL DERECHO
        # ====================================================

        self.panel_detalle = tk.Frame(
            central,
            bg=COLOR_PANEL,
            width=260
        )

        self.panel_detalle.pack(
            side="right",
            fill="y",
            padx=(18, 0)
        )

        self.panel_detalle.pack_propagate(
            False
        )

        tk.Label(
            self.panel_detalle,
            text="SELECCIONADO",
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            fg=COLOR_AZUL_CLARO,
            bg=COLOR_PANEL
        ).pack(
            pady=(15, 8)
        )

        self.detalle_portada_frame = tk.Frame(
            self.panel_detalle,
            bg="#0b1220",
            width=180,
            height=270
        )

        self.detalle_portada_frame.pack(
            pady=(0, 8)
        )

        self.detalle_portada_frame.pack_propagate(
            False
        )

        self.detalle_portada = tk.Label(
            self.detalle_portada_frame,
            text="🎮",
            font=(
                "Segoe UI Emoji",
                45
            ),
            fg=COLOR_AZUL_CLARO,
            bg="#0b1220"
        )

        self.detalle_portada.pack(
            fill="both",
            expand=True
        )

        self.detalle_nombre = tk.Label(
            self.panel_detalle,
            text="",
            font=(
                "Segoe UI",
                14,
                "bold"
            ),
            fg=COLOR_TEXTO,
            bg=COLOR_PANEL,
            wraplength=225,
            justify="center"
        )

        self.detalle_nombre.pack(
            padx=15,
            pady=(5, 3)
        )

        self.detalle_sistema = tk.Label(
            self.panel_detalle,
            text="",
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            fg=COLOR_AZUL_CLARO,
            bg=COLOR_PANEL
        )

        self.detalle_sistema.pack(
            pady=2
        )

        self.detalle_estado = tk.Label(
            self.panel_detalle,
            text="LISTO PARA JUGAR",
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
            fg=COLOR_VERDE,
            bg=COLOR_PANEL
        )

        self.detalle_estado.pack(
            pady=(5, 8)
        )

        self.boton_jugar_grande = tk.Button(
            self.panel_detalle,
            text="▶  JUGAR",
            font=(
                "Segoe UI",
                13,
                "bold"
            ),
            fg="white",
            bg=COLOR_AZUL,
            activebackground=COLOR_AZUL_CLARO,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.jugar_seleccionado
        )

        self.boton_jugar_grande.pack(
            fill="x",
            padx=25,
            pady=(0, 15),
            ipady=8
        )

        # ====================================================
        # BARRA INFERIOR
        # ====================================================

        inferior = tk.Frame(
            self.root,
            bg=COLOR_PANEL,
            height=45
        )

        inferior.pack(
            side="bottom",
            fill="x"
        )

        inferior.pack_propagate(
            False
        )

        tk.Label(
            inferior,
            text=(
                "🎮 STICK  Mover     "
                "LB/RB  Consolas     "
                "A/START  Jugar     "
                "START+Z (2s)  Salir del juego     "
                "F5  Actualizar"
            ),
            font=(
                "Segoe UI",
                10
            ),
            fg="#cbd5e1",
            bg=COLOR_PANEL
        ).pack(
            side="left",
            padx=28,
            pady=12
        )


    # ========================================================
    # CANVAS
    # ========================================================

    def actualizar_scrollregion(
        self,
        event=None
    ):

        self.canvas.configure(
            scrollregion=
                self.canvas.bbox("all")
        )


    def ajustar_ancho_canvas(
        self,
        event
    ):

        self.canvas.itemconfig(
            self.ventana_canvas,
            width=event.width
        )


    # ========================================================
    # MOSTRAR JUEGOS
    # ========================================================

    def mostrar_juegos(
        self
    ):

        for widget in (
            self.zona_juegos.winfo_children()
        ):

            widget.destroy()

        self.tarjetas = []

        self.imagenes_tarjetas = []

        if self.filtro_actual == "TODOS":

            self.juegos_visibles = (
                self.juegos
            )

        else:

            self.juegos_visibles = [

                juego

                for juego in self.juegos

                if juego["sistema"]
                == self.filtro_actual
            ]

        self.contador.config(
            text=(
                f"{len(self.juegos_visibles)} "
                "JUEGO(S)"
            )
        )

        self.actualizar_botones_sistemas()

        if not self.juegos_visibles:

            tk.Label(
                self.zona_juegos,
                text=(
                    "NO HAY JUEGOS\n"
                    "INSTALADOS"
                ),
                font=(
                    "Segoe UI",
                    20,
                    "bold"
                ),
                fg=COLOR_TEXTO_SECUNDARIO,
                bg=COLOR_FONDO,
                justify="center"
            ).pack(
                pady=100
            )

            return

        if self.indice >= len(
            self.juegos_visibles
        ):

            self.indice = 0

        columnas = 3

        for i, juego in enumerate(
            self.juegos_visibles
        ):

            tarjeta = tk.Frame(
                self.zona_juegos,
                bg=COLOR_TARJETA,
                width=215,
                height=345,
                cursor="hand2"
            )

            tarjeta.grid(
                row=i // columnas,
                column=i % columnas,
                padx=10,
                pady=10,
                sticky="nsew"
            )

            tarjeta.grid_propagate(
                False
            )

            portada_frame = tk.Frame(
                tarjeta,
                bg="#0b1220",
                width=160,
                height=240
            )

            portada_frame.pack(
                pady=(12, 5)
            )

            portada_frame.pack_propagate(
                False
            )

            imagen_portada = (
                cargar_imagen(
                    juego.get(
                        "portada"
                    ),
                    158,
                    238
                )
            )

            if imagen_portada:

                self.imagenes_tarjetas.append(
                    imagen_portada
                )

                label_portada = tk.Label(
                    portada_frame,
                    image=imagen_portada,
                    bg="#0b1220"
                )

            else:

                label_portada = tk.Label(
                    portada_frame,
                    text=(
                        "🎮\n\n"
                        + juego["sistema"]
                    ),
                    font=(
                        "Segoe UI",
                        20,
                        "bold"
                    ),
                    fg=COLOR_AZUL_CLARO,
                    bg="#0b1220",
                    justify="center"
                )

            label_portada.pack(
                fill="both",
                expand=True
            )

            nombre = tk.Label(
                tarjeta,
                text=juego["nombre"],
                font=(
                    "Segoe UI",
                    11,
                    "bold"
                ),
                fg=COLOR_TEXTO,
                bg=COLOR_TARJETA,
                wraplength=185,
                justify="center"
            )

            nombre.pack(
                padx=8,
                pady=(5, 2),
                expand=True
            )

            sistema = tk.Label(
                tarjeta,
                text=juego["sistema"],
                font=(
                    "Segoe UI",
                    9,
                    "bold"
                ),
                fg=COLOR_AZUL_CLARO,
                bg=COLOR_TARJETA
            )

            sistema.pack(
                pady=(0, 8)
            )

            widgets_click = [

                tarjeta,
                portada_frame,
                label_portada,
                nombre,
                sistema
            ]

            for widget in widgets_click:

                widget.bind(
                    "<Button-1>",
                    lambda event,
                    indice=i:
                        self.seleccionar_con_mouse(
                            indice
                        )
                )

                widget.bind(
                    "<Double-Button-1>",
                    lambda event,
                    indice=i:
                        self.jugar_indice(
                            indice
                        )
                )

            self.tarjetas.append(
                tarjeta
            )

        for columna in range(
            columnas
        ):

            self.zona_juegos.grid_columnconfigure(
                columna,
                weight=1
            )

        self.actualizar_seleccion()


    # ========================================================
    # METADATOS AUTOMÁTICOS
    # ========================================================

    def iniciar_actualizacion_metadatos(
        self
    ):

        if self.descarga_activa:
            return

        faltantes = [

            juego

            for juego in self.juegos

            if not juego.get(
                "portada"
            )
        ]

        if not faltantes:

            self.estado_biblioteca.config(
                text="✓ BIBLIOTECA ACTUALIZADA",
                fg=COLOR_VERDE
            )

            return

        if not self.igdb:

            self.estado_biblioteca.config(
                text="IGDB NO CONFIGURADO",
                fg=COLOR_AMARILLO
            )

            return

        self.descarga_activa = True

        self.estado_biblioteca.config(
            text="⟳ BUSCANDO PORTADAS...",
            fg=COLOR_AMARILLO
        )

        hilo = threading.Thread(
            target=
                self.actualizar_metadatos_hilo,
            daemon=True
        )

        hilo.start()


    def actualizar_metadatos_hilo(
        self
    ):

        cambios = False

        errores = 0

        try:

            for juego in self.juegos:

                if juego.get(
                    "portada"
                ):

                    continue

                try:

                    resultado = (
                        self.obtener_metadatos_juego(
                            juego
                        )
                    )

                    if resultado:

                        cambios = True

                except Exception as error:

                    errores += 1

                    print(
                        "Error obteniendo metadatos para:",
                        juego["nombre"]
                    )

                    print(
                        error
                    )

                    time.sleep(1)

        finally:

            self.descarga_activa = False

            self.root.after(
                0,
                lambda:
                    self.finalizar_actualizacion_metadatos(
                        cambios,
                        errores
                    )
            )


    def obtener_metadatos_juego(
        self,
        juego
    ):

        clave = clave_cache(
            juego
        )

        # ----------------------------------------------------
        # Revisar caché
        # ----------------------------------------------------

        with self.lock_cache:

            datos_cache = (
                self.cache.get(
                    clave
                )
            )

        if datos_cache:

            archivo_portada = (
                datos_cache.get(
                    "portada"
                )
            )

            if archivo_portada:

                ruta_portada = (
                    os.path.join(
                        CARPETA_PORTADAS,
                        archivo_portada
                    )
                )

                if os.path.isfile(ruta_portada):
                    nombre_esperado = normalizar_titulo_igdb(nombre_seguro(juego["nombre"]))
                    nombre_guardado = normalizar_titulo_igdb(os.path.splitext(archivo_portada)[0])
                    if nombre_esperado == nombre_guardado:
                        juego["portada"] = ruta_portada
                        return True
                    print("Portada de caché no coincide; buscando nuevamente:", juego["nombre"])

        # ----------------------------------------------------
        # Buscar en IGDB
        # ----------------------------------------------------

        resultado = (
            self.igdb.buscar_juego(
                nombre_limpio_nds(juego["archivo"]) if juego["sistema"] == "NDS" else juego["nombre"],
                juego["sistema"]
            )
        )

        if not resultado:

            with self.lock_cache:

                self.cache[
                    clave
                ] = {

                    "nombre":
                        juego["nombre"],

                    "sistema":
                        juego["sistema"],

                    "encontrado":
                        False
                }

                guardar_cache(
                    self.cache
                )

            return False

        portada = (
            resultado.get(
                "cover",
                {}
            )
        )

        image_id = (
            portada.get(
                "image_id"
            )
        )

        nombre_igdb = (
            resultado.get(
                "name",
                juego["nombre"]
            )
        )

        archivo_portada = None

        if image_id:

            archivo_portada = (
                nombre_seguro(juego["nombre"])
                + ".jpg"
            )

            destino = os.path.join(
                CARPETA_PORTADAS,
                archivo_portada
            )

            if not os.path.isfile(
                destino
            ):

                url_imagen = (
                    "https://images.igdb.com/"
                    "igdb/image/upload/"
                    "t_cover_big/"
                    + image_id
                    + ".jpg"
                )

                self.descargar_archivo(
                    url_imagen,
                    destino
                )

            if os.path.isfile(
                destino
            ):

                juego["portada"] = (
                    destino
                )

        # ----------------------------------------------------
        # Guardar metadatos
        # ----------------------------------------------------

        fecha = (
            resultado.get(
                "first_release_date"
            )
        )

        resumen = (
            resultado.get(
                "summary",
                ""
            )
        )

        plataformas = [

            plataforma.get(
                "name",
                ""
            )

            for plataforma in resultado.get(
                "platforms",
                []
            )
        ]

        with self.lock_cache:

            self.cache[
                clave
            ] = {

                "igdb_id":
                    resultado.get(
                        "id"
                    ),

                "nombre":
                    nombre_igdb,

                "sistema":
                    juego["sistema"],

                "plataformas":
                    plataformas,

                "fecha":
                    fecha,

                "resumen":
                    resumen,

                "portada":
                    archivo_portada,

                "encontrado":
                    True
            }

            guardar_cache(
                self.cache
            )

        return bool(
            juego.get(
                "portada"
            )
        )


    def descargar_archivo(
        self,
        url,
        destino
    ):

        temporal = (
            destino
            + ".tmp"
        )

        try:

            request = (
                urllib.request.Request(
                    url,
                    headers={
                        "User-Agent":
                            "MiBibliotecaJuegos/2.4.2"
                    }
                )
            )

            with urllib.request.urlopen(
                request,
                timeout=20
            ) as respuesta:

                datos = respuesta.read()

            with open(
                temporal,
                "wb"
            ) as archivo:

                archivo.write(
                    datos
                )

            # ------------------------------------------------
            # Validar que realmente sea una imagen
            # ------------------------------------------------

            with Image.open(
                temporal
            ) as imagen:

                imagen.verify()

            os.replace(
                temporal,
                destino
            )

        except Exception:

            if os.path.isfile(
                temporal
            ):

                try:
                    os.remove(
                        temporal
                    )

                except Exception:
                    pass

            raise


    def finalizar_actualizacion_metadatos(
        self,
        cambios,
        errores
    ):

        if cambios:

            # ------------------------------------------------
            # Volver a detectar portadas
            # ------------------------------------------------

            for juego in self.juegos:

                juego["portada"] = (
                    buscar_portada(
                        juego
                    )
                )

            self.mostrar_juegos()

        if errores:

            self.estado_biblioteca.config(
                text=(
                    "⚠ ACTUALIZACIÓN "
                    "INCOMPLETA"
                ),
                fg=COLOR_AMARILLO
            )

        else:
            pendientes = sum(1 for juego in self.juegos if not juego.get("portada"))
            self.estado_biblioteca.config(
                text=(f"⚠ {pendientes} PORTADA(S) PENDIENTE(S)" if pendientes else "✓ BIBLIOTECA ACTUALIZADA"),
                fg=(COLOR_AMARILLO if pendientes else COLOR_VERDE)
            )


    # ========================================================
    # BOTONES DE SISTEMA
    # ========================================================

    def actualizar_botones_sistemas(
        self
    ):

        for sistema, boton in (
            self.botones_sistema.items()
        ):

            if sistema == self.filtro_actual:

                boton.config(
                    bg=COLOR_AZUL,
                    fg="white"
                )

            else:

                boton.config(
                    bg=COLOR_PANEL,
                    fg="white"
                )


    # ========================================================
    # SELECCIÓN
    # ========================================================

    def seleccionar_con_mouse(
        self,
        indice
    ):

        self.indice = indice

        self.actualizar_seleccion()


    def jugar_indice(
        self,
        indice
    ):

        self.indice = indice

        self.actualizar_seleccion()

        self.jugar_seleccionado()


    def actualizar_seleccion(
        self
    ):

        if not self.tarjetas:
            return

        for i, tarjeta in enumerate(
            self.tarjetas
        ):

            seleccionado = (
                i == self.indice
            )

            if seleccionado:

                tarjeta.configure(
                    bg=
                        COLOR_TARJETA_SELECCIONADA,

                    highlightbackground=
                        COLOR_AZUL_CLARO,

                    highlightcolor=
                        COLOR_AZUL_CLARO,

                    highlightthickness=4
                )

            else:

                tarjeta.configure(
                    bg=COLOR_TARJETA,
                    highlightthickness=0
                )

        self.actualizar_detalle()

        self.asegurar_visible()


    # ========================================================
    # DETALLE
    # ========================================================

    def actualizar_detalle(
        self
    ):

        if not self.juegos_visibles:
            return

        juego = (
            self.juegos_visibles[
                self.indice
            ]
        )

        self.detalle_nombre.config(
            text=juego["nombre"]
        )

        self.detalle_sistema.config(
            text=(
                "SISTEMA  •  "
                + juego["sistema"]
            )
        )

        self.imagen_detalle_actual = (
            cargar_imagen(
                juego.get(
                    "portada"
                ),
                178,
                268
            )
        )

        if self.imagen_detalle_actual:

            self.detalle_portada.config(
                image=
                    self.imagen_detalle_actual,
                text=""
            )

        else:

            self.detalle_portada.config(
                image="",
                text=(
                    "🎮\n\n"
                    + juego["sistema"]
                )
            )

        ejecutable = (
            SISTEMAS[
                juego["sistema"]
            ]["exe"]
        )
        if juego["sistema"] == "GBA":
            ejecutable = localizar_mgba()
        elif juego["sistema"] in ("Wii", "GameCube"):
            ejecutable = localizar_dolphin()

        if ejecutable:

            self.detalle_estado.config(
                text="● LISTO PARA JUGAR",
                fg=COLOR_VERDE
            )

            self.boton_jugar_grande.config(
                bg=COLOR_AZUL
            )

        else:

            self.detalle_estado.config(
                text="● EMULADOR PENDIENTE",
                fg=COLOR_AMARILLO
            )

            self.boton_jugar_grande.config(
                bg="#475569"
            )


    # ========================================================
    # SCROLL AUTOMÁTICO
    # ========================================================

    def asegurar_visible(
        self
    ):

        if not self.tarjetas:
            return

        self.root.update_idletasks()

        tarjeta = (
            self.tarjetas[
                self.indice
            ]
        )

        y = tarjeta.winfo_y()

        alto_tarjeta = (
            tarjeta.winfo_height()
        )

        alto_total = max(
            1,
            self.zona_juegos.winfo_height()
        )

        alto_canvas = max(
            1,
            self.canvas.winfo_height()
        )

        posicion_actual = (
            self.canvas.canvasy(0)
        )

        if y < posicion_actual:

            self.canvas.yview_moveto(
                max(
                    0,
                    y / alto_total
                )
            )

        elif (
            y + alto_tarjeta
            >
            posicion_actual
            + alto_canvas
        ):

            destino = (
                y
                + alto_tarjeta
                - alto_canvas
            )

            self.canvas.yview_moveto(
                min(
                    1,
                    max(
                        0,
                        destino
                        / alto_total
                    )
                )
            )


    # ========================================================
    # TECLADO
    # ========================================================

    def configurar_teclado(
        self
    ):

        self.root.bind(
            "<Right>",
            lambda e:
                self.mover(1)
        )

        self.root.bind(
            "<Left>",
            lambda e:
                self.mover(-1)
        )

        self.root.bind(
            "<Down>",
            lambda e:
                self.mover(3)
        )

        self.root.bind(
            "<Up>",
            lambda e:
                self.mover(-3)
        )

        self.root.bind("<Tab>", lambda e: self.cambiar_sistema_relativo(1))
        self.root.bind("<Shift-Tab>", lambda e: self.cambiar_sistema_relativo(-1))

        self.root.bind(
            "<Return>",
            lambda e:
                self.jugar_seleccionado()
        )

        self.root.bind(
            "<F5>",
            lambda e:
                self.actualizar_biblioteca()
        )

        self.root.bind(
            "<F11>",
            lambda e:
                self.alternar_pantalla_completa()
        )

        self.root.bind(
            "<Escape>",
            lambda e:
                self.salir_pantalla_completa()
        )


    # ========================================================
    # MANDO
    # ========================================================

    def detectar_mando(self):
        """Detecta todos los mandos, no solamente el primer dispositivo."""
        encontrados = []
        for joystick_id in range(winmm.joyGetNumDevs()):
            info = JOYINFOEX()
            info.dwSize = ctypes.sizeof(JOYINFOEX)
            info.dwFlags = JOY_RETURNALL
            if winmm.joyGetPosEx(joystick_id, ctypes.byref(info)) == 0:
                encontrados.append(joystick_id)
                if joystick_id not in self.estados_mandos:
                    self.estados_mandos[joystick_id] = {
                        "botones": int(info.dwButtons),
                        "direccion": None,
                        "movimiento": 0.0,
                    }

        for joystick_id in list(self.estados_mandos):
            if joystick_id not in encontrados:
                del self.estados_mandos[joystick_id]

        self.mando_activo = encontrados[0] if encontrados else None
        if encontrados:
            self.estado_mando_label.config(
                text=f"🎮 {len(encontrados)} MANDO(S) CONECTADO(S)",
                fg=COLOR_VERDE,
            )
        else:
            self.estado_mando_label.config(
                text="🎮 MANDO NO DETECTADO", fg=COLOR_ROJO
            )

    def leer_mando(self):
        """Consulta cada mando de manera independiente, incluso si tienen el mismo nombre."""
        try:
            ahora = time.monotonic()
            if ahora - self.ultimo_escaneo_mandos >= 2.0:
                self.detectar_mando()
                self.ultimo_escaneo_mandos = ahora

            for joystick_id in list(self.estados_mandos):
                info = JOYINFOEX()
                info.dwSize = ctypes.sizeof(JOYINFOEX)
                info.dwFlags = JOY_RETURNALL
                if winmm.joyGetPosEx(joystick_id, ctypes.byref(info)) != 0:
                    del self.estados_mandos[joystick_id]
                    continue

                estado = self.estados_mandos[joystick_id]
                if self.juego_ejecutandose:
                    # La combinación START + Z se vigila en otro hilo.
                    estado["botones"] = int(info.dwButtons)
                    estado["direccion"] = None
                    continue

                self.procesar_direccion(info, estado)
                self.procesar_botones(int(info.dwButtons), estado)
        except Exception as error:
            print("Error leyendo mandos:", error)
        finally:
            self.root.after(40, self.leer_mando)

    def procesar_direccion(self, info, estado):
        direccion = None
        pov = int(info.dwPOV)
        if pov != 65535 and pov != 0xFFFFFFFF:
            if pov >= 31500 or pov <= 4500:
                direccion = "ARRIBA"
            elif 4500 < pov < 13500:
                direccion = "DERECHA"
            elif 13500 <= pov <= 22500:
                direccion = "ABAJO"
            elif 22500 < pov < 31500:
                direccion = "IZQUIERDA"

        if direccion is None:
            x, y = int(info.dwXpos), int(info.dwYpos)
            centro, zona_muerta = 32767, 12000
            if x < centro - zona_muerta:
                direccion = "IZQUIERDA"
            elif x > centro + zona_muerta:
                direccion = "DERECHA"
            elif y < centro - zona_muerta:
                direccion = "ARRIBA"
            elif y > centro + zona_muerta:
                direccion = "ABAJO"

        if direccion is None:
            estado["direccion"] = None
            return

        ahora = time.monotonic()
        if (direccion == estado["direccion"] and
                ahora - estado["movimiento"] < self.bloqueo_movimiento):
            return

        # Evita saltos dobles si ambos joysticks se usan al mismo tiempo.
        if ahora - self.ultimo_movimiento < 0.10:
            return

        movimientos = {
            "IZQUIERDA": -1,
            "DERECHA": 1,
            "ARRIBA": -3,
            "ABAJO": 3,
        }
        self.mover(movimientos[direccion])
        estado["direccion"] = direccion
        estado["movimiento"] = ahora
        self.ultimo_movimiento = ahora

    def procesar_botones(self, botones, estado):
        nuevos = botones & ~estado["botones"]
        estado["botones"] = botones
        if not nuevos:
            return

        # Project64 muestra Button 6/7, que son índices desde cero.
        if nuevos & (1 << 6):
            self.cambiar_sistema_relativo(-1)
            return
        if nuevos & (1 << 7):
            self.cambiar_sistema_relativo(1)
            return

        # A = Button 0; START = Button 11 según la configuración validada.
        if nuevos & ((1 << 0) | (1 << 11)):
            self.jugar_seleccionado()


    # ========================================================
    # MOVER
    # ========================================================

    def mover(
        self,
        cantidad
    ):

        if not self.juegos_visibles:
            return

        nuevo = (
            self.indice
            + cantidad
        )

        cantidad_juegos = len(
            self.juegos_visibles
        )

        if nuevo < 0:

            nuevo = (
                cantidad_juegos - 1
            )

        elif nuevo >= cantidad_juegos:

            nuevo = 0

        self.indice = nuevo

        self.actualizar_seleccion()


    # ========================================================
    # JUGAR
    # ========================================================

    def jugar_seleccionado(
        self
    ):

        if self.juego_ejecutandose:
            return

        if not self.juegos_visibles:
            return

        juego = (
            self.juegos_visibles[
                self.indice
            ]
        )

        datos = SISTEMAS[
            juego["sistema"]
        ]

        ejecutable = (
            datos["exe"]
        )
        if juego["sistema"] == "GBA":
            ejecutable = localizar_mgba()
            if not ejecutable:
                messagebox.showinfo(
                    "Instalar mGBA",
                    "Para jugar GBA instala mGBA desde https://mgba.io/downloads/\n\n"
                    "Coloca mGBA.exe en C:\\Juegos\\Emuladores\\GBA o en Archivos de programa.\n"
                    "La Biblioteca lo detectará automáticamente al volver a abrirla."
                )
                return

        if juego["sistema"] in ("Wii", "GameCube"):
            ejecutable = localizar_dolphin()
            if not ejecutable:
                messagebox.showinfo(
                    "Dolphin no encontrado",
                    "No encontré Dolphin.exe. Colócalo dentro de "
                    "C:\\Juegos\\Emuladores\\Dolphin o ajusta la ruta "
                    "en la función localizar_dolphin() de biblioteca.py."
                )
                return

        if not ejecutable:

            messagebox.showinfo(
                "Emulador pendiente",
                (
                    "Todavía no está "
                    "configurado el emulador "
                    "para:\n\n"
                    + juego["sistema"]
                )
            )

            return

        if not os.path.isfile(
            ejecutable
        ):

            messagebox.showerror(
                "Emulador no encontrado",
                ejecutable
            )

            return

        if juego["sistema"] == "Wii":
            tipo = tipo_mando_wii(juego)
            if tipo is None:
                respuesta = messagebox.askyesnocancel(
                    "Tipo de mando Wii",
                    "¿Este juego utiliza Mando Clásico?\n\n"
                    "Sí: Mando Clásico (Budokai)\n"
                    "No: Wii Remote + Nunchuk (Mario Galaxy)\n"
                    "Cancelar: no iniciar el juego"
                )
                if respuesta is None:
                    return
                tipo = "Classic" if respuesta else "Nunchuk"
                try:
                    guardar_tipo_mando_wii(juego, tipo)
                except OSError as error:
                    messagebox.showwarning("Perfiles Wii", str(error))
            try:
                configurar_mandos_wii(tipo)
            except Exception as error:
                messagebox.showerror("Mandos Wii", str(error))
                return

        self.juego_ejecutandose = True
        self.salida_solicitada.clear()
        self.combinacion_inicio.clear()

        self.root.withdraw()

        threading.Thread(
            target=
                self.ejecutar_y_esperar,
            args=(
                ejecutable,
                juego["ruta"]
            ),
            daemon=True
        ).start()


    def jugar_indice(
        self,
        indice
    ):

        self.indice = indice

        self.actualizar_seleccion()

        self.jugar_seleccionado()


    def ejecutar_y_esperar(
        self,
        ejecutable,
        rom
    ):

        datos_alias_nds = None
        try:

            # melonDS 1.1 puede fallar al abrir ciertas rutas absolutas
            # pasadas por línea de comandos. Para NDS, arrancamos desde
            # la carpeta de la ROM y pasamos solo su nombre de archivo.
            if os.path.basename(ejecutable).lower() == "melonds.exe":
                rom = os.path.abspath(rom)
                if not os.path.isfile(rom):
                    raise FileNotFoundError(
                        "No se encuentra la ROM de Nintendo DS:\n" + rom
                        + "\n\nPulsa F5 en la Biblioteca para actualizar la lista."
                    )
                rom_abrir, datos_alias_nds = preparar_rom_nds(rom)
                proceso = subprocess.Popen(
                    [ejecutable, os.path.basename(rom_abrir)],
                    cwd=os.path.dirname(rom_abrir)
                )
            elif os.path.basename(ejecutable).lower() == "dolphin.exe":
                # -b inicia directamente en modo de juego y -e carga la ROM.
                # No cambia perfiles, botones, gráficos ni ajustes de Dolphin.
                proceso = subprocess.Popen(
                    [ejecutable, "-b", "-e", os.path.abspath(rom)],
                    cwd=os.path.dirname(ejecutable)
                )
            else:
                proceso = subprocess.Popen(
                    [ejecutable, rom]
                )

            self.proceso_emulador = proceso
            threading.Thread(
                target=self.vigilar_salida_mandos,
                args=(proceso,),
                daemon=True
            ).start()

            time.sleep(4)

            if proceso.poll() is None and (
                "azahar"
                in
                os.path.basename(
                    ejecutable
                ).lower()
            ):

                self.activar_pantalla_completa_azahar()

            elif proceso.poll() is None and os.path.basename(ejecutable).lower() == "melonds.exe":
                self.activar_pantalla_completa_melonds(proceso.pid)

            elif proceso.poll() is None and (
                "project64"
                in os.path.basename(ejecutable).lower()
            ):
                self.activar_pantalla_completa_project64(proceso.pid)

            elif proceso.poll() is None and os.path.basename(ejecutable).lower() == "mgba.exe":
                self.activar_pantalla_completa_gba(proceso.pid)

            elif proceso.poll() is None and os.path.basename(ejecutable).lower() == "snes9x-x64.exe":
                self.activar_pantalla_completa_gba(proceso.pid, titulo_ventana="snes9x")

            elif proceso.poll() is None and os.path.basename(ejecutable).lower() == "dolphin.exe":
                # Dolphin.ini ya contiene [Display] Fullscreen = True.
                # No enviar Alt+Enter: podría DESACTIVAR la pantalla completa.
                pass

            proceso.wait()

        except Exception as error:

            self.root.after(
                0,
                lambda e=str(error):
                    messagebox.showerror(
                        "Error",
                        e
                    )
            )

        finally:
            try:
                finalizar_rom_nds(datos_alias_nds)
            except Exception as error_guardado:
                self.root.after(0, lambda e=str(error_guardado):
                    messagebox.showwarning("Guardado NDS", "Revisa el guardado del juego: " + e))
            self.proceso_emulador = None
            self.salida_solicitada.set()
            self.root.after(0, self.regresar_biblioteca)

    def vigilar_salida_mandos(self, proceso):
        """START + Z (botones 11 y 10), sostenidos 2 segundos.
        Funciona mientras Tkinter está oculto y acepta cualquiera de los 2 mandos.
        """
        mascara = (1 << 11) | (1 << 10)
        while proceso.poll() is None and not self.salida_solicitada.is_set():
            try:
                for joystick_id in range(winmm.joyGetNumDevs()):
                    info = JOYINFOEX()
                    info.dwSize = ctypes.sizeof(JOYINFOEX)
                    info.dwFlags = JOY_RETURNALL
                    if winmm.joyGetPosEx(joystick_id, ctypes.byref(info)) != 0:
                        self.combinacion_inicio.pop(joystick_id, None)
                        continue
                    if info.dwButtons & mascara == mascara:
                        inicio = self.combinacion_inicio.setdefault(joystick_id, time.monotonic())
                        if time.monotonic() - inicio >= 2.0:
                            self.salida_solicitada.set()
                            self.cerrar_emulador(proceso)
                            return
                    else:
                        self.combinacion_inicio.pop(joystick_id, None)
            except Exception as error:
                print("Error comprobando salida con joystick:", error)
            time.sleep(0.07)

    def cerrar_emulador(self, proceso):
        """Solicita cierre normal, luego fuerza salida solo si es necesario."""
        if proceso.poll() is not None:
            return
        try:
            user32 = ctypes.windll.user32
            pid_objetivo = proceso.pid
            ventanas = []
            callback_tipo = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            @callback_tipo
            def recoger(hwnd, extra):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == pid_objetivo and user32.IsWindowVisible(hwnd):
                    ventanas.append(hwnd)
                return True

            user32.EnumWindows(recoger, 0)
            for hwnd in ventanas:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
            try:
                proceso.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proceso.terminate()
                try:
                    proceso.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proceso.kill()
        except Exception as error:
            print("Error cerrando emulador:", error)
            if proceso.poll() is None:
                proceso.terminate()


    def activar_pantalla_completa_melonds(self, pid):
        """Fullscreen sin depender de atajos de teclado que melonDS puede ignorar."""
        try:
            user32 = ctypes.windll.user32
            callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            hwnd_objetivo = None

            @callback_type
            def enumerar(hwnd, _):
                nonlocal hwnd_objetivo
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid_ventana = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_ventana))
                if pid_ventana.value != pid:
                    return True
                largo = user32.GetWindowTextLengthW(hwnd)
                if largo:
                    texto = ctypes.create_unicode_buffer(largo + 1)
                    user32.GetWindowTextW(hwnd, texto, largo + 1)
                    if "melonds" in texto.value.lower():
                        hwnd_objetivo = hwnd
                        return False
                return True

            for _ in range(24):
                user32.EnumWindows(enumerar, 0)
                if hwnd_objetivo:
                    break
                time.sleep(0.25)
            if not hwnd_objetivo:
                print("melonDS: no se encontró su ventana")
                return
            # Modo sin bordes que ocupa toda la pantalla. No cambia la
            # resolución interna del emulador ni sus opciones gráficas.
            GWL_STYLE = -16
            WS_OVERLAPPEDWINDOW = 0x00CF0000
            SWP_FRAMECHANGED = 0x0020
            SWP_SHOWWINDOW = 0x0040
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
                user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
                user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
                estilo = user32.GetWindowLongPtrW(hwnd_objetivo, GWL_STYLE)
                user32.SetWindowLongPtrW(hwnd_objetivo, GWL_STYLE, estilo & ~WS_OVERLAPPEDWINDOW)
            else:
                estilo = user32.GetWindowLongW(hwnd_objetivo, GWL_STYLE)
                user32.SetWindowLongW(hwnd_objetivo, GWL_STYLE, estilo & ~WS_OVERLAPPEDWINDOW)
            ancho = user32.GetSystemMetrics(0)
            alto = user32.GetSystemMetrics(1)
            user32.ShowWindow(hwnd_objetivo, 9)
            user32.SetWindowPos(hwnd_objetivo, 0, 0, 0, ancho, alto,
                                SWP_FRAMECHANGED | SWP_SHOWWINDOW)
            user32.SetForegroundWindow(hwnd_objetivo)
        except Exception as error:
            print("melonDS: no se pudo activar pantalla completa:", error)


    def activar_pantalla_completa_dolphin(self, pid):
        """Activa Alt+Enter solo en la ventana de juego de Dolphin.

        Evita alterar mandos, preferencias y ventanas de otros emuladores.
        """
        try:
            user32 = ctypes.windll.user32
            callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongW.restype = ctypes.c_long
            hwnd_juego = None

            def enumerar(hwnd, _):
                nonlocal hwnd_juego
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid_ventana = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_ventana))
                if pid_ventana.value != pid:
                    return True
                n = user32.GetWindowTextLengthW(hwnd)
                if n <= 0:
                    return True
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                titulo = buf.value.lower()
                if "dolphin" in titulo and ("jit" in titulo or "hle" in titulo or "fps" in titulo):
                    hwnd_juego = hwnd
                    return False
                return True

            for _ in range(32):
                user32.EnumWindows(callback_type(enumerar), 0)
                if hwnd_juego:
                    break
                time.sleep(0.25)
            if not hwnd_juego:
                print("Dolphin: ventana de juego no encontrada para pantalla completa")
                return
            # Si no tiene barra de título, ya puede estar en pantalla completa.
            if not (user32.GetWindowLongW(hwnd_juego, -16) & 0x00C00000):
                return
            user32.ShowWindow(hwnd_juego, 9)
            user32.BringWindowToTop(hwnd_juego)
            user32.SetForegroundWindow(hwnd_juego)
            time.sleep(0.35)
            KEYUP = 0x0002
            user32.keybd_event(0x12, 0, 0, 0)  # ALT
            user32.keybd_event(0x0D, 0, 0, 0)  # ENTER
            time.sleep(0.12)
            user32.keybd_event(0x0D, 0, KEYUP, 0)
            user32.keybd_event(0x12, 0, KEYUP, 0)
        except Exception as error:
            print("Dolphin: error al activar pantalla completa:", error)

    def activar_pantalla_completa_gba(self, pid, titulo_ventana="mgba"):
        """Activa el fullscreen propio de mGBA (Alt+Enter), no maximizar.

        Solo actúa sobre la ventana visible perteneciente al proceso iniciado.
        No modifica configuración de gráficos, partidas ni otros emuladores.
        """
        try:
            user32 = ctypes.windll.user32
            callback_type = ctypes.WINFUNCTYPE(
                ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
            )
            hwnd_juego = None

            def enumerar(hwnd, _):
                nonlocal hwnd_juego
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid_ventana = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_ventana))
                if pid_ventana.value != pid:
                    return True
                longitud = user32.GetWindowTextLengthW(hwnd)
                if not longitud:
                    return True
                titulo = ctypes.create_unicode_buffer(longitud + 1)
                user32.GetWindowTextW(hwnd, titulo, longitud + 1)
                if titulo_ventana in titulo.value.lower():
                    hwnd_juego = hwnd
                    return False
                return True

            for _ in range(24):
                user32.EnumWindows(callback_type(enumerar), 0)
                if hwnd_juego:
                    break
                time.sleep(0.25)
            if not hwnd_juego:
                print("mGBA: no se encontró su ventana para activar fullscreen.")
                return

            # El fullscreen de mGBA elimina la barra de título. No alternar
            # de nuevo si ya está activo, pues Alt+Enter lo desactivaría.
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongW.restype = ctypes.c_long
            estilo = user32.GetWindowLongW(hwnd_juego, GWL_STYLE)
            if not (estilo & WS_CAPTION):
                return

            # Restaurar antes de enviar Alt+Enter: maximizar no es fullscreen.
            user32.ShowWindow(hwnd_juego, 9)  # SW_RESTORE
            user32.BringWindowToTop(hwnd_juego)
            user32.SetForegroundWindow(hwnd_juego)
            time.sleep(0.45)

            VK_MENU = 0x12
            VK_RETURN = 0x0D
            KEYUP = 0x0002
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.12)
            user32.keybd_event(VK_RETURN, 0, KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYUP, 0)
        except Exception as error:
            print("mGBA: error al activar fullscreen:", error)


    # ========================================================
    # PROJECT64: ALT + ENTER PARA PANTALLA COMPLETA
    # ========================================================

    def activar_pantalla_completa_project64(self, pid):
        """Activa pantalla completa en la ventana del juego de Project64.

        Se comprueba el PID para no enviar teclas a otra aplicación.
        Si el emulador ya está en pantalla completa, no se alterna.
        """
        try:
            user32 = ctypes.windll.user32
            user32.GetWindowThreadProcessId.argtypes = [
                wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
            ]
            user32.GetWindowThreadProcessId.restype = wintypes.DWORD
            user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
            user32.GetWindowTextLengthW.restype = ctypes.c_int
            user32.GetWindowTextW.argtypes = [
                wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
            ]
            user32.GetWindowTextW.restype = ctypes.c_int

            callback_type = ctypes.WINFUNCTYPE(
                ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
            )
            hwnd_juego = None

            def enumerar(hwnd, _):
                nonlocal hwnd_juego
                if not user32.IsWindowVisible(hwnd):
                    return True
                proceso_ventana = wintypes.DWORD()
                user32.GetWindowThreadProcessId(
                    hwnd, ctypes.byref(proceso_ventana)
                )
                if proceso_ventana.value != pid:
                    return True
                largo = user32.GetWindowTextLengthW(hwnd)
                if not largo:
                    return True
                buffer = ctypes.create_unicode_buffer(largo + 1)
                user32.GetWindowTextW(hwnd, buffer, largo + 1)
                titulo = buffer.value.lower()
                if "project64" in titulo and " - project64" in titulo:
                    hwnd_juego = hwnd
                    return False
                return True

            for _ in range(30):
                user32.EnumWindows(callback_type(enumerar), 0)
                if hwnd_juego:
                    break
                time.sleep(0.5)

            if not hwnd_juego:
                print("Project64: no se encontró la ventana del juego.")
                return

            # Evitar alternar a modo ventana si ya está en fullscreen.
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd_juego, ctypes.byref(rect))
            ancho = rect.right - rect.left
            alto = rect.bottom - rect.top
            pantalla_ancho = user32.GetSystemMetrics(0)
            pantalla_alto = user32.GetSystemMetrics(1)
            if (ancho >= pantalla_ancho and alto >= pantalla_alto
                    and rect.left <= 0 and rect.top <= 0):
                return

            user32.ShowWindow(hwnd_juego, 9)
            time.sleep(0.4)
            user32.SetForegroundWindow(hwnd_juego)
            time.sleep(0.8)

            # ALT (VK_MENU) + ENTER (VK_RETURN)
            VK_MENU = 0x12
            VK_RETURN = 0x0D
            KEYUP = 0x0002
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.12)
            user32.keybd_event(VK_RETURN, 0, KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYUP, 0)
        except Exception as error:
            print("Error pantalla completa Project64:", error)


    # ========================================================
    # AZAHAR F11
    # ========================================================

    def activar_pantalla_completa_azahar(
        self
    ):

        try:

            user32 = (
                ctypes.windll.user32
            )

            ventanas = []

            EnumWindowsProc = (
                ctypes.WINFUNCTYPE(
                    ctypes.c_bool,
                    ctypes.c_void_p,
                    ctypes.c_void_p
                )
            )

            def callback(
                hwnd,
                lparam
            ):

                if not (
                    user32.IsWindowVisible(
                        hwnd
                    )
                ):

                    return True

                longitud = (
                    user32.GetWindowTextLengthW(
                        hwnd
                    )
                )

                if longitud == 0:
                    return True

                buffer = (
                    ctypes.create_unicode_buffer(
                        longitud + 1
                    )
                )

                user32.GetWindowTextW(
                    hwnd,
                    buffer,
                    longitud + 1
                )

                if (
                    "Azahar"
                    in buffer.value
                ):

                    ventanas.append(
                        hwnd
                    )

                return True

            hwnd = None

            for intento in range(30):

                ventanas.clear()

                user32.EnumWindows(
                    EnumWindowsProc(
                        callback
                    ),
                    0
                )

                if ventanas:

                    hwnd = ventanas[0]

                    break

                time.sleep(
                    0.5
                )

            if not hwnd:
                return

            user32.ShowWindow(
                hwnd,
                9
            )

            time.sleep(
                0.5
            )

            user32.SetForegroundWindow(
                hwnd
            )

            time.sleep(
                0.8
            )

            VK_F11 = 0x7A

            KEYEVENTF_KEYUP = 0x0002

            user32.keybd_event(
                VK_F11,
                0,
                0,
                0
            )

            time.sleep(
                0.12
            )

            user32.keybd_event(
                VK_F11,
                0,
                KEYEVENTF_KEYUP,
                0
            )

        except Exception as error:

            print(
                "Error F11 Azahar:",
                error
            )


    # ========================================================
    # REGRESAR
    # ========================================================

    def regresar_biblioteca(
        self
    ):

        self.juego_ejecutandose = False

        self.estado_botones_anterior = 0

        self.direccion_anterior = None

        self.root.deiconify()

        self.root.attributes(
            "-fullscreen",
            True
        )

        self.root.lift()

        self.root.focus_force()

        self.actualizar_seleccion()


    # ========================================================
    # FILTROS
    # ========================================================

    def cambiar_sistema_relativo(self, desplazamiento):
        sistemas = ["TODOS", "3DS", "N64", "NDS", "GBA", "SNES", "NES", "GameCube", "Wii", "PSP", "PS1"]
        if self.juego_ejecutandose:
            return
        ahora = time.monotonic()
        if ahora - self.ultimo_cambio_sistema < 0.20:
            return
        self.ultimo_cambio_sistema = ahora
        posicion = sistemas.index(self.filtro_actual) if self.filtro_actual in sistemas else 0
        self.cambiar_filtro(sistemas[(posicion + desplazamiento) % len(sistemas)])

    def cambiar_filtro(
        self,
        sistema
    ):

        self.filtro_actual = (
            sistema
        )

        self.indice = 0

        self.canvas.yview_moveto(
            0
        )

        self.mostrar_juegos()


    # ========================================================
    # F5
    # ========================================================

    def actualizar_biblioteca(
        self
    ):

        self.estado_biblioteca.config(
            text="⟳ ESCANEANDO...",
            fg=COLOR_AMARILLO
        )

        self.juegos = (
            buscar_juegos()
        )

        self.indice = 0

        self.canvas.yview_moveto(
            0
        )

        self.mostrar_juegos()

        self.root.after(
            500,
            self.iniciar_actualizacion_metadatos
        )


    # ========================================================
    # FULLSCREEN
    # ========================================================

    def alternar_pantalla_completa(
        self
    ):

        actual = (
            self.root.attributes(
                "-fullscreen"
            )
        )

        self.root.attributes(
            "-fullscreen",
            not actual
        )


    def salir_pantalla_completa(
        self
    ):

        self.root.attributes(
            "-fullscreen",
            False
        )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = Biblioteca(
        root
    )

    root.mainloop()