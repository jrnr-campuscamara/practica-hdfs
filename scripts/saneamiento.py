import pandas as pd
import hashlib


# ---------- FUNCIÓN PARA CALCULAR EL HASH SHA-256 ----------
def obtener_sha256(ruta_fichero):
    sha = hashlib.sha256()
    with open(ruta_fichero, "rb") as f:
        for bloque in iter(lambda: f.read(4096), b""):
            sha.update(bloque)
    return sha.hexdigest()


RUTA_ORIGINAL = "datos/telemetria_envios.csv"
RUTA_LIMPIA = "datos/telemetria_limpia.csv"

# ---------- 1. HASH DEL ORIGINAL (antes de tocar nada) ----------
print("Hash SHA-256 original:", obtener_sha256(RUTA_ORIGINAL))  

# ---------- 2. CARGA ----------
df = pd.read_csv(RUTA_ORIGINAL)

# ---------- 3. EXPLORACIÓN ----------
print("\nTamaño (filas, columnas):", df.shape)
print(df.head())

print("\n--- Celdas vacías por columna ---")
print(df.isnull().sum())

print("\n--- Filas duplicadas ---")
print(df.duplicated().sum())

print("\n--- Resumen de columnas numéricas ---")
print(df.describe())

print("\n--- Estados que aparecen ---")
print(df["estado_envio"].value_counts())

# ---------- 4. LIMPIEZA ----------
# Quitar filas repetidas
df = df.drop_duplicates()

# Quitar filas con alguna celda vacía (destino, peso_kg o temp_celsius)
df = df.dropna()

# Un peso negativo o cero es imposible
df = df[df["peso_kg"] > 0]

# Rango válido para un compartimento refrigerado: de -5 a 15 °C
df = df[(df["temp_celsius"] >= -5) & (df["temp_celsius"] <= 15)]

# DESCONOCIDO_ERROR no es un estado real del envío
df = df[df["estado_envio"] != "DESCONOCIDO_ERROR"]

print("\nTamaño después de limpiar:", df.shape)

# ---------- 5. GUARDADO ----------
df.to_csv(RUTA_LIMPIA, index=False)
print("Fichero limpio guardado en", RUTA_LIMPIA)

# ---------- 6. HASH DEL LIMPIO (solo existe después de guardarlo) ----------
print("Hash SHA-256 limpio:  ", obtener_sha256(RUTA_LIMPIA))   