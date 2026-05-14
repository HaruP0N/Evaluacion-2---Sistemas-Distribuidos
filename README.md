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

### Parte 1: Los imports

```python
import multiprocessing
import sys
```

Son las únicas dos librerías que usa el programa, y ambas vienen incluidas en Python, no hay que instalar nada.

`multiprocessing` es la librería principal del programa. Permite crear procesos reales del sistema operativo, cada uno con su propia memoria. Es distinto a los threads (hilos), que comparten memoria. Acá se usan tres cosas de esta librería:
- `Process` → para crear y lanzar cada proceso
- `Barrier` → para sincronizar los procesos en un punto de encuentro
- `Manager` → para compartir datos entre procesos que tienen memoria separada

`sys` se usa para dos cosas concretas:
- `sys.argv` → leer el argumento que se pasa al ejecutar (`python evaluacion2.py 3 < in.txt` → el `3`)
- `sys.stdin` → leer el contenido del archivo `in.txt` que se redirige con `<`

---

### Parte 2: La función `leer_entrada()`

```python
def leer_entrada():
    lineas = [
        linea.strip()
        for linea in sys.stdin.read().split('\n')
        if linea.strip()
    ]
```

Esta función se encarga de leer y parsear todo el archivo `in.txt`. La primera línea lee todo el contenido de golpe con `sys.stdin.read()`, lo divide en líneas con `split('\n')`, elimina espacios sobrantes con `.strip()` y descarta líneas vacías con el `if linea.strip()`. El resultado es una lista limpia de líneas listas para procesar.

```python
    n_docs = int(lineas[idx])
    idx += 1
```

Lee la primera línea del archivo, que es el número de documentos. El `idx` es un contador que va avanzando línea por línea a medida que se lee el archivo.

```python
    for _ in range(n_docs):
        nombre = lineas[idx]; idx += 1
        cantidad_terminos = int(lineas[idx]); idx += 1
        terminos = lineas[idx].split(); idx += 1

        if len(terminos) != cantidad_terminos:
            print(f"Advertencia: el documento {nombre} declara "
                  f"{cantidad_terminos} términos pero contiene {len(terminos)}.")

        documentos.append((nombre, terminos))
```

Por cada documento lee tres cosas en orden: el nombre del archivo, la cantidad de términos declarada, y los términos en sí. El `split()` convierte la línea `"hola mundo perro"` en la lista `["hola", "mundo", "perro"]`. La validación defensiva avisa si el número declarado no coincide con los términos reales. Finalmente guarda una tupla `(nombre, terminos)` en la lista de documentos.

```python
    n_consultas = int(lineas[idx]); idx += 1
    consultas = lineas[idx].split()
```

Lee el número de consultas y luego la línea con todas las consultas separadas por espacio, convirtiéndolas en lista con `split()`.

---

### Parte 3: La función `distribuir_documentos()`

```python
def distribuir_documentos(documentos, n_procesos):
    total = len(documentos)
    subconjuntos = []
    inicio = 0

    for pid in range(n_procesos):
        tamano = total // n_procesos + (1 if pid < total % n_procesos else 0)
        subconjuntos.append(documentos[inicio:inicio + tamano])
        inicio += tamano

    return subconjuntos
```

Esta función divide la lista de documentos en `n_procesos` grupos lo más equitativos posible.

La línea clave es el cálculo del tamaño:
- `total // n_procesos` da el tamaño base para todos los procesos
- `total % n_procesos` calcula cuántos documentos sobran
- Los procesos con `pid` menor al sobrante reciben un documento extra

**Ejemplo concreto con 5 documentos y 3 procesos:**
- Tamaño base: `5 // 3 = 1`
- Sobrante: `5 % 3 = 2`
- Proceso 0 (`pid=0 < 2`): recibe `1 + 1 = 2` documentos
- Proceso 1 (`pid=1 < 2`): recibe `1 + 1 = 2` documentos
- Proceso 2 (`pid=2 < 2` es falso): recibe `1 + 0 = 1` documento

Si hay más procesos que documentos (ej: 3 docs, 5 procesos), los últimos procesos simplemente reciben listas vacías y el programa funciona igual.

---

### Parte 4: Las estructuras compartidas en el main

```python
manager = multiprocessing.Manager()
indices_locales = manager.list([{} for _ in range(N_PROCESOS)])
```

Como cada proceso tiene su propia memoria separada, no pueden compartir variables normales de Python. El **Manager** es un proceso servidor especial que actúa de intermediario, permitiendo que todos accedan a los mismos datos.

`indices_locales` es una lista compartida que se inicializa con un diccionario vacío por cada proceso — `[{}, {}, {}]` si hay 3 procesos. Cada proceso escribe exclusivamente en su propio slot `[pid]`, por lo que nunca se pisan entre ellos y no se necesita ningún Lock.

```python
barrera = multiprocessing.Barrier(N_PROCESOS)
```

La **Barrier** es un punto de encuentro obligatorio. Se inicializa con `N_PROCESOS` para indicar cuántos procesos deben llegar antes de que alguno pueda continuar. Es exactamente el patrón del Algoritmo 7 del libro.

---

### Parte 5: Creación y lanzamiento de procesos en el main

```python
procesos = []

for pid in range(N_PROCESOS):
    proceso = multiprocessing.Process(
        target=construir_indice_local,
        args=(pid, subconjuntos[pid], indices_locales, barrera, consultas)
    )
    procesos.append(proceso)
```

Se crea un objeto `Process` por cada proceso. `target` es la función que va a ejecutar cuando parta, y `args` son los argumentos que recibirá esa función. En este momento los procesos están creados pero todavía no han partido.

```python
for proceso in procesos:
    proceso.start()

for proceso in procesos:
    proceso.join()
```

Se usan dos loops separados a propósito. El primero lanza todos los procesos de una vez con `start()`. El segundo espera a que cada uno termine con `join()`. Si se hiciera en un solo loop (`start()` y `join()` juntos), cada proceso esperaría a que el anterior terminara antes de lanzar el siguiente, perdiendo completamente el paralelismo.

---

### Parte 6: Fase 1 — construcción del índice local

```python
indice_local = {}

for nombre_archivo, terminos in documentos_asignados:
    for termino in terminos:
        if termino not in indice_local:
            indice_local[termino] = set()
        indice_local[termino].add(nombre_archivo)
```

Esta es la parte que corre en paralelo real. Cada proceso recorre sus documentos asignados y construye su propio diccionario local en su memoria privada. La estructura es `{ término: set(archivos) }`.

Se usa `set()` en lugar de lista por dos razones: agregar un elemento es O(1) en vez de O(n), y evita duplicados automáticamente sin verificación manual.

```python
indices_locales[pid] = {
    termino: sorted(list(archivos))
    for termino, archivos in indice_local.items()
}
```

Una vez terminado el índice local, se convierte cada set a lista ordenada y se guarda de una sola vez en el slot `[pid]` de la lista compartida. Se hace la asignación completa porque el Manager solo detecta cambios cuando se asigna el slot entero — si se intentara hacer `indices_locales[pid][termino] = algo` directamente, el Manager no lo detectaría y el cambio se perdería silenciosamente.

---

### Parte 7: Fase 2 — barrera

```python
try:
    barrera.wait(timeout=30)
except multiprocessing.BrokenBarrierError:
    print(f"[Proceso {pid}] Error: barrera interrumpida o timeout excedido.")
    return
```

Todos los procesos llegan a este punto y se quedan esperando. El último proceso en llegar libera a todos al mismo tiempo para que continúen. El `timeout=30` es una protección: si en 30 segundos no llegaron todos los procesos (por ejemplo porque uno falló con una excepción antes de llegar), se lanza un `BrokenBarrierError` y cada proceso termina de forma controlada en lugar de quedar colgado indefinidamente.

---

### Parte 8: Fase 3 — fusión y consultas (solo proceso 0)

```python
if pid == 0:
    indice_global = {}

    for indice in indices_locales:
        for termino, archivos in indice.items():
            if termino not in indice_global:
                indice_global[termino] = set()
            indice_global[termino].update(archivos)
```

Solo el proceso 0 entra a este bloque. Los demás procesos simplemente terminan. El proceso 0 recorre todos los índices locales guardados en `indices_locales` y los fusiona en un único diccionario global. Usa `set.update()` que agrega todos los elementos de una lista al set en una sola operación, siendo más eficiente que agregar uno por uno.

```python
    for termino in indice_global:
        indice_global[termino] = sorted(list(indice_global[termino]))
```

Una vez fusionado todo, convierte los sets del índice global a listas ordenadas. El `sorted()` garantiza que los resultados siempre salgan en el mismo orden alfabético entre ejecuciones.

```python
    for termino in consultas:
        if termino in indice_global and indice_global[termino]:
            archivos = " ".join(indice_global[termino])
            print(f'Resultados para "{termino}": {archivos}')
        else:
            print(f'Resultados para "{termino}": No hay resultados.')
```

Recorre cada consulta y la busca en el índice global. Si el término existe y tiene archivos asociados, los imprime separados por espacio. Si no existe o la lista está vacía, imprime "No hay resultados." — cubriendo ambos casos que pide la pauta.

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

**¿El número de procesos viene del archivo `in.txt`?**  
No. El número de procesos se pasa como argumento en la línea de comandos (`python evaluacion2.py 3 < in.txt` → el `3`). Lo que viene de la primera línea del `in.txt` es el número de documentos. Son dos cosas completamente independientes.
