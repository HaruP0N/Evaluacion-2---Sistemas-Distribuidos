# INF-515 - Sistemas Distribuidos
## Evaluación Unidad 2: Índice Invertido Paralelo
**Autores:** Leandro Torres y Nicolas Rojas  
**Universidad Católica del Maule — Semestre 1, 2026**

---

## ¿Qué hace este programa?

Construye un **índice invertido** en paralelo usando la librería `multiprocessing` de Python. Un índice invertido es la estructura de datos que usan los motores de búsqueda: dado un término, entrega la lista de documentos donde ese término aparece.

La construcción sigue el patrón de **índices locales + barrera + fusión global** (Algoritmo 7 del libro):

| Fase | Quién | Qué hace |
|------|-------|----------|
| Fase 1 | Todos los procesos (en paralelo) | Cada proceso construye su índice local con los documentos que le fueron asignados |
| Fase 2 | Todos los procesos | Esperan en la barrera hasta que todos terminen la Fase 1 |
| Fase 3 | Solo el proceso 0 | Fusiona todos los índices locales en uno global y resuelve las consultas |

---

## Restricciones cumplidas

- No se utiliza `Pool`
- Se usan `Process`, `Barrier` y `Manager`
- Todos los procesos participan en la creación del índice
- Compatible con cualquier número de procesos
- Código documentado extensamente

---

## Estructura del proyecto

```
unidad2/
├── evaluacion2.py   # Programa principal
├── in.txt           # Archivo de entrada (ejemplo)
└── README.md        # Este archivo
```

---

## Formato del archivo de entrada (`in.txt`)

```
N_DOCUMENTOS
nombre_documento_1
cantidad_terminos_1
termino1 termino2 termino3
nombre_documento_2
cantidad_terminos_2
termino1 termino2 ...
...
N_CONSULTAS
consulta1 consulta2 consulta3 ...
```

### Ejemplo concreto:

```
3
primero.html
3
hola mundo perro
segundo.html
4
hola perro gato auto
tercero.html
3
perro auto casa
5
gato perro mundo edificio hotel
```

---

## Cómo ejecutar

### Requisito previo: tener Python instalado

Verificar con:
```bash
python --version
```

Si no está instalado, descargarlo desde https://www.python.org/downloads/  
**Importante:** al instalar, marcar la casilla *"Add Python to PATH"*.

### Comando de ejecución

```bash
python evaluacion2.py <N_PROCESOS> < in.txt
```

Donde `<N_PROCESOS>` es el número de procesos paralelos a utilizar.

### Ejemplos:

```bash
# Ejecutar con 3 procesos
python evaluacion2.py 3 < in.txt

# Ejecutar con 5 procesos
python evaluacion2.py 5 < in.txt
```

> En Linux/Mac usar `python3` en lugar de `python`.

---

## Salida esperada (con el ejemplo de 3 procesos)

```
[Main] Documentos leídos   : 3
[Main] Consultas a procesar: ['gato', 'perro', 'mundo', 'edificio', 'hotel']
[Main] Procesos a utilizar : 3

[Main] Proceso 0 recibirá: ['primero.html']
[Main] Proceso 1 recibirá: ['segundo.html']
[Main] Proceso 2 recibirá: ['tercero.html']

[Proceso 0] Fase 1 completada: 3 términos únicos en 1 documento(s).
[Proceso 2] Fase 1 completada: 3 términos únicos en 1 documento(s).
[Proceso 1] Fase 1 completada: 4 términos únicos en 1 documento(s).

[Proceso 0] Iniciando fusión de índices locales...
[Proceso 0] Índice global construido: 6 términos únicos.

--- Resultados de las consultas ---
Resultados para "gato": segundo.html
Resultados para "perro": primero.html segundo.html tercero.html
Resultados para "mundo": primero.html
Resultados para "edificio": No hay resultados.
Resultados para "hotel": No hay resultados.
```

> **Nota:** el orden en que los procesos imprimen su "Fase 1 completada" puede variar entre ejecuciones. Esto es normal y esperado: es justamente la naturaleza del paralelismo real.

---

## Explicación del código

### 1. Los imports

```python
import multiprocessing
import sys
```

`multiprocessing` es la librería que permite crear procesos reales en Python. A diferencia de los threads (hilos), los procesos tienen memoria separada y corren verdaderamente en paralelo en distintos núcleos del procesador.

`sys` se usa para leer los argumentos de la línea de comandos (`sys.argv`) y para leer la entrada estándar (`sys.stdin`).

---

### 2. La función `leer_entrada()`

```python
lineas = [linea.strip() for linea in sys.stdin.read().split('\n') if linea.strip()]
```

Lee todo el contenido del archivo `in.txt` de una vez, lo divide por saltos de línea, elimina espacios sobrantes y descarta líneas vacías. Luego recorre las líneas siguiendo el formato exacto de la pauta: número de documentos, luego por cada documento su nombre, cantidad de términos y los términos, y al final las consultas.

Incluye validaciones defensivas que avisan si el número de términos declarado no coincide con los términos reales, o si el número de consultas declarado no coincide con las consultas recibidas.

---

### 3. La función `distribuir_documentos()`

```python
tamano = total // n_procesos + (1 if pid < total % n_procesos else 0)
```

Divide la lista de documentos en bloques contiguos lo más equitativos posible. La división entera `//` da el tamaño base, y el `% n_procesos` calcula el sobrante. Ese sobrante se reparte dando un documento extra a los primeros procesos.

**Ejemplo concreto:** 5 documentos, 3 procesos → proceso 0 recibe 2, proceso 1 recibe 2, proceso 2 recibe 1.

Si hay más procesos que documentos, los procesos sobrantes reciben una lista vacía y participan igual en la barrera, simplemente sin hacer trabajo en Fase 1.

---

### 4. Las estructuras compartidas

```python
manager = multiprocessing.Manager()
indices_locales = manager.list([{} for _ in range(N_PROCESOS)])
```

El **Manager** es un proceso servidor especial que administra objetos compartidos entre procesos. Como cada proceso tiene su propia memoria, no pueden compartir variables directamente — el Manager actúa como intermediario.

`indices_locales` es una lista compartida con un diccionario vacío por cada proceso. El proceso 0 escribe en `indices_locales[0]`, el proceso 1 en `indices_locales[1]`, y así. Nunca se pisan entre ellos.

```python
barrera = multiprocessing.Barrier(N_PROCESOS)
```

La **Barrier** es un punto de encuentro. Ningún proceso puede pasar de ahí hasta que todos los `N_PROCESOS` hayan llegado. Es exactamente el patrón del Algoritmo 7 del libro.

---

### 5. La Fase 1 — construcción del índice local

```python
indice_local = {}
for nombre_archivo, terminos in documentos_asignados:
    for termino in terminos:
        if termino not in indice_local:
            indice_local[termino] = set()
        indice_local[termino].add(nombre_archivo)
```

Cada proceso recorre sus documentos asignados y construye su propio diccionario local. La clave es el término y el valor es un `set` con los archivos donde aparece ese término.

Se usa `set()` en lugar de lista porque agregar un elemento a un set es O(1) y automáticamente evita duplicados, sin necesidad de verificar manualmente si el archivo ya estaba.

**No se necesita sincronización aquí** porque cada proceso escribe solo en su variable local `indice_local`, que está en su propia memoria. Nadie más la toca.

```python
indices_locales[pid] = {
    termino: sorted(list(archivos))
    for termino, archivos in indice_local.items()
}
```

Una vez terminado, se convierte el set a lista ordenada y se guarda en el slot `[pid]` de la lista compartida. Se hace una asignación completa porque el Manager solo detecta cambios cuando se asigna el slot completo — si se intentara modificar el diccionario internamente (`indices_locales[pid][termino] = ...`), el Manager no lo detectaría y el cambio se perdería.

---

### 6. La Fase 2 — barrera

```python
try:
    barrera.wait(timeout=30)
except multiprocessing.BrokenBarrierError:
    print(f"[Proceso {pid}] Error: barrera interrumpida...")
    return
```

Todos los procesos llegan aquí y esperan. El último en llegar libera a todos al mismo tiempo. El `timeout=30` significa que si en 30 segundos no llegaron todos, se lanza un `BrokenBarrierError` y el proceso termina de forma controlada en lugar de quedar colgado indefinidamente.

---

### 7. La Fase 3 — fusión y consultas (solo proceso 0)

```python
if pid == 0:
    indice_global = {}
    for indice in indices_locales:
        for termino, archivos in indice.items():
            if termino not in indice_global:
                indice_global[termino] = set()
            indice_global[termino].update(archivos)
```

Solo el proceso 0 ejecuta esto. Recorre todos los índices locales y los fusiona en uno global usando `set.update()`, que agrega todos los elementos de una lista al set en una sola operación.

```python
for termino in indice_global:
    indice_global[termino] = sorted(list(indice_global[termino]))
```

Convierte los sets del índice global a listas ordenadas para que los resultados siempre salgan en el mismo orden.

```python
for termino in consultas:
    if termino in indice_global and indice_global[termino]:
        print(f'Resultados para "{termino}": {" ".join(indice_global[termino])}')
    else:
        print(f'Resultados para "{termino}": No hay resultados.')
```

Busca cada término consultado en el índice global. Si existe y tiene archivos, los imprime. Si no, imprime "No hay resultados." — cubriendo así tanto el caso de término inexistente como el de lista vacía.

---

### 8. El main — creación y lanzamiento de procesos

```python
proceso = multiprocessing.Process(target=construir_indice_local, args=(...))
```

Se crea un objeto `Process` por cada proceso. `target` es la función que va a ejecutar y `args` son los argumentos que recibe.

```python
for proceso in procesos:
    proceso.start()

for proceso in procesos:
    proceso.join()
```

Primero se lanzan todos con `start()`, luego el proceso principal espera a que cada uno termine con `join()`. Se hace en dos loops separados para que todos partan al mismo tiempo — si se hiciera `start()` y `join()` en el mismo loop, cada proceso esperaría a que el anterior terminara antes de lanzar el siguiente, perdiendo el paralelismo.

---

## Preguntas frecuentes de defensa

**¿Por qué no se necesita Lock en la Fase 1?**  
Porque cada proceso escribe exclusivamente en su propia variable local `indice_local` (en su memoria privada) y luego en su slot `[pid]` de la lista compartida. Nunca dos procesos escriben en el mismo slot.

**¿Por qué se asigna `indices_locales[pid]` completo y no se modifica internamente?**  
El Manager detecta cambios en la lista compartida solo cuando se asigna el slot completo. Si se intentara `indices_locales[pid][termino] = algo`, el Manager no lo detectaría y el cambio se perdería.

**¿Qué pasa si hay más procesos que documentos?**  
Los procesos sobrantes reciben lista vacía, su Fase 1 no itera, guardan un índice vacío y llegan igual a la barrera. El programa funciona correctamente.

**¿Por qué el orden de los mensajes "Fase 1 completada" varía?**  
Porque los procesos corren en paralelo real y el sistema operativo decide cuándo le da tiempo de CPU a cada uno. El orden de llegada no está garantizado, y eso es correcto.

**¿Qué hace `barrera.wait(timeout=30)`?**  
Hace que el proceso espere en ese punto hasta que todos los demás lleguen. Si en 30 segundos no llegaron todos (por ejemplo, porque uno falló con una excepción), lanza `BrokenBarrierError` y el proceso termina de forma controlada en lugar de quedar colgado.

**¿Por qué se usan dos loops separados para `start()` y `join()`?**  
Si se hiciera `start()` y `join()` en el mismo loop, cada proceso esperaría a que el anterior terminara antes de lanzar el siguiente, perdiendo el paralelismo. Con dos loops separados, todos los procesos parten al mismo tiempo.
