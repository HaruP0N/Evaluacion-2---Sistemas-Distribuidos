"""
Script para generar el archivo de entrada in.txt
usado para probar el índice invertido.

Uso:
    python3 crear_input.py

Genera el archivo in.txt en el mismo directorio.
Puedes modificar 'documentos' y 'consultas' para crear tus propios casos de prueba.
"""

# -------------------------------------------------------
# Define aquí tus documentos y consultas
# -------------------------------------------------------

documentos = [
    ("primero.html",  ["hola", "mundo", "perro"]),
    ("segundo.html",  ["hola", "perro", "gato", "auto"]),
    ("tercero.html",  ["perro", "auto", "casa"]),
]

consultas = ["gato", "perro", "mundo", "edificio", "hotel"]

# -------------------------------------------------------
# Generar el archivo in.txt
# -------------------------------------------------------

with open("in.txt", "w") as f:

    # Número de documentos
    f.write(f"{len(documentos)}\n")

    # Por cada documento: nombre, cantidad de términos, términos
    for nombre, terminos in documentos:
        f.write(f"{nombre}\n")
        f.write(f"{len(terminos)}\n")
        f.write(f"{' '.join(terminos)}\n")

    # Número de consultas y las consultas
    f.write(f"{len(consultas)}\n")
    f.write(f"{' '.join(consultas)}\n")

print("Archivo in.txt generado exitosamente.")
print(f"  - Documentos : {len(documentos)}")
print(f"  - Consultas  : {consultas}")
print()
print("Contenido de in.txt:")
print("-" * 30)
with open("in.txt", "r") as f:
    print(f.read())