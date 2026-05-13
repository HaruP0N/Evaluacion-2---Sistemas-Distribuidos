"""
INF-515 - Sistemas Distribuidos
Evaluación Unidad 2: Índice Invertido Paralelo
Autores: Leandro Torres y Nicolas Rojas

Descripción:
    Construye un índice invertido en paralelo usando multiprocessing,
    siguiendo el patrón de índices locales + barrera + fusión global.

        FASE 1 (paralela): cada proceso construye su índice local.
        FASE 2 (barrera) : todos esperan sincronización.
        FASE 3 (proceso 0): fusiona índices y resuelve consultas.

    Restricciones cumplidas:
        - No se utiliza Pool
        - Uso de Process, Barrier y Manager
        - Compatible con cualquier número de procesos
        - Código documentado extensamente

Uso:
    python evaluacion2.py <N_PROCESOS> < in.txt
"""

import multiprocessing
import sys


# ---------------------------------------------------------------------------
# Función que ejecuta cada proceso en paralelo
# ---------------------------------------------------------------------------
def construir_indice_local(pid, documentos_asignados, indices_locales, barrera, consultas):
    """
    Cada proceso:
        1. Construye su índice local.
        2. Espera en barrera.
        3. Solo proceso 0 fusiona y responde consultas.
    """

    # -------------------------------------------------------------------
    # FASE 1: Construcción de índice local
    # -------------------------------------------------------------------
    # Estructura:
    # { termino: set(archivo1, archivo2, ...) }
    #
    # Se usa set() para evitar duplicados eficientemente en O(1).
    indice_local = {}

    for nombre_archivo, terminos in documentos_asignados:
        for termino in terminos:
            if termino not in indice_local:
                indice_local[termino] = set()
            indice_local[termino].add(nombre_archivo)

    # Convertir sets a listas ordenadas antes de almacenar en Manager.
    # IMPORTANTE: el Manager solo detecta cambios por asignación completa
    # al slot [pid]. Modificar el dict directamente no funciona.
    indices_locales[pid] = {
        termino: sorted(list(archivos))
        for termino, archivos in indice_local.items()
    }

    print(
        f"[Proceso {pid}] Fase 1 completada: "
        f"{len(indice_local)} términos únicos en "
        f"{len(documentos_asignados)} documento(s).",
        flush=True
    )

    # -------------------------------------------------------------------
    # FASE 2: Barrera de sincronización
    # -------------------------------------------------------------------
    # Ningún proceso avanza hasta que todos lleguen aquí.
    # timeout=30 evita cuelgue indefinido si algún proceso falla antes
    # de llegar a la barrera.
    try:
        barrera.wait(timeout=30)
    except multiprocessing.BrokenBarrierError:
        print(
            f"[Proceso {pid}] Error: barrera interrumpida o timeout excedido.",
            flush=True
        )
        return

    # -------------------------------------------------------------------
    # FASE 3: Fusión global (solo proceso 0)
    # -------------------------------------------------------------------
    # Los demás procesos terminan aquí sin hacer nada más.
    if pid == 0:
        print("\n[Proceso 0] Iniciando fusión de índices locales...", flush=True)

        # Usar sets globalmente para mayor eficiencia en la fusión.
        # set.update() agrega todos los elementos de una lista en O(k),
        # evitando la verificación manual de duplicados.
        indice_global = {}

        for indice in indices_locales:
            for termino, archivos in indice.items():
                if termino not in indice_global:
                    indice_global[termino] = set()
                indice_global[termino].update(archivos)

        # Convertir sets globales a listas ordenadas para salida consistente
        for termino in indice_global:
            indice_global[termino] = sorted(list(indice_global[termino]))

        print(
            f"[Proceso 0] Índice global construido: "
            f"{len(indice_global)} términos únicos.",
            flush=True
        )

        # ---------------------------------------------------------------
        # Resolver consultas
        # ---------------------------------------------------------------
        print("\n--- Resultados de las consultas ---", flush=True)

        for termino in consultas:
            if termino in indice_global and indice_global[termino]:
                archivos = " ".join(indice_global[termino])
                print(f'Resultados para "{termino}": {archivos}', flush=True)
            else:
                print(
                    f'Resultados para "{termino}": No hay resultados.',
                    flush=True
                )


# ---------------------------------------------------------------------------
# Lectura de entrada estándar
# ---------------------------------------------------------------------------
def leer_entrada():
    """
    Formato esperado:
        N_DOCUMENTOS
        nombre_doc_1
        cantidad_terminos_1
        terminos_doc_1
        ...
        N_CONSULTAS
        consulta1 consulta2 ...
    """

    lineas = [
        linea.strip()
        for linea in sys.stdin.read().split('\n')
        if linea.strip()
    ]

    idx = 0

    n_docs = int(lineas[idx])
    idx += 1

    documentos = []

    for _ in range(n_docs):
        nombre = lineas[idx]
        idx += 1

        cantidad_terminos = int(lineas[idx])
        idx += 1

        terminos = lineas[idx].split()
        idx += 1

        # Validación defensiva: avisar si el conteo declarado no coincide
        if len(terminos) != cantidad_terminos:
            print(
                f"Advertencia: el documento {nombre} declara "
                f"{cantidad_terminos} términos pero contiene {len(terminos)}.",
                flush=True
            )

        documentos.append((nombre, terminos))

    n_consultas = int(lineas[idx])
    idx += 1

    consultas = lineas[idx].split()

    # Validación defensiva: avisar si el conteo de consultas no coincide
    if len(consultas) != n_consultas:
        print(
            f"Advertencia: se declararon {n_consultas} consultas, "
            f"pero se recibieron {len(consultas)}.",
            flush=True
        )

    return documentos, consultas


# ---------------------------------------------------------------------------
# Distribución de documentos
# ---------------------------------------------------------------------------
def distribuir_documentos(documentos, n_procesos):
    """
    Distribuye documentos equitativamente en bloques contiguos.

    Ejemplo:
        5 docs, 3 procesos -> [2, 2, 1]
        3 docs, 5 procesos -> [1, 1, 1, 0, 0]

    Los procesos con lista vacía participan igualmente en la barrera
    y entregan un índice local vacío en la fusión.
    """

    total = len(documentos)
    subconjuntos = []
    inicio = 0

    for pid in range(n_procesos):
        tamano = total // n_procesos + (1 if pid < total % n_procesos else 0)
        subconjuntos.append(documentos[inicio:inicio + tamano])
        inicio += tamano

    return subconjuntos


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
if __name__ == '__main__':

    # Validar que se entregó el argumento del número de procesos
    if len(sys.argv) < 2:
        print("Uso: python3 indice_invertido.py <N_PROCESOS> < in.txt")
        sys.exit(1)

    # Validar que el argumento sea un entero válido
    try:
        N_PROCESOS = int(sys.argv[1])
    except ValueError:
        print("Error: N_PROCESOS debe ser un número entero.")
        sys.exit(1)

    # Validar que haya al menos 1 proceso
    if N_PROCESOS < 1:
        print("Error: debe utilizar al menos 1 proceso.")
        sys.exit(1)

    documentos, consultas = leer_entrada()

    print(f"\n[Main] Documentos leídos   : {len(documentos)}")
    print(f"[Main] Consultas a procesar: {consultas}")
    print(f"[Main] Procesos a utilizar : {N_PROCESOS}")

    # Advertencia informativa si hay más procesos que documentos
    if N_PROCESOS > len(documentos):
        print(
            f"[Main] Advertencia: hay más procesos ({N_PROCESOS}) "
            f"que documentos ({len(documentos)}). "
            f"Los procesos sobrantes no tendrán documentos asignados."
        )

    print()

    # Distribuir documentos entre procesos
    subconjuntos = distribuir_documentos(documentos, N_PROCESOS)

    for i, sub in enumerate(subconjuntos):
        nombres = [doc[0] for doc in sub]
        print(
            f"[Main] Proceso {i} recibirá: "
            f"{nombres if nombres else '(sin documentos)'}",
            flush=True
        )

    print()

    # -------------------------------------------------------------------
    # Estructuras compartidas
    # -------------------------------------------------------------------
    # Lista compartida: un dict (índice local) por proceso.
    # Cada proceso escribe exclusivamente en su slot [pid],
    # por lo que no se necesita Lock en Fase 1.
    manager = multiprocessing.Manager()
    indices_locales = manager.list([{} for _ in range(N_PROCESOS)])

    # Barrera: todos los procesos deben llegar antes de que alguno avance
    barrera = multiprocessing.Barrier(N_PROCESOS)

    # -------------------------------------------------------------------
    # Creación y lanzamiento de procesos
    # -------------------------------------------------------------------
    procesos = []

    for pid in range(N_PROCESOS):
        proceso = multiprocessing.Process(
            target=construir_indice_local,
            args=(
                pid,
                subconjuntos[pid],
                indices_locales,
                barrera,
                consultas
            )
        )
        procesos.append(proceso)

    # Lanzar todos los procesos
    for proceso in procesos:
        proceso.start()

    # Esperar a que todos terminen antes de salir del main
    for proceso in procesos:
        proceso.join()