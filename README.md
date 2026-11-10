PRÁCTICA FORMATIVA INTEGRADORA: INTEGRIDAD DEL DATO Y PRIMEROS PASOS CON HDFS

Esta práctica tiene dos partes. En la primera compruebo que el fichero de telemetría que nos han dado está íntegro, lo limpio de registros erróneos y vuelvo a calcular su huella. En la segunda levanto un Hadoop con Docker, subo el fichero limpio a HDFS y miro cómo lo ha guardado por dentro. Todo lo he hecho en Windows, con PowerShell, Python 3.13 y Docker Desktop.

El repositorio está organizado así: en scripts/ está saneamiento.py, que calcula los hashes y limpia el dataset; en datos/ están el CSV original y el limpio; en evidencias/ están las cuatro capturas; y en la raíz está el docker-compose.yml que usé para levantar Hadoop.


1. INTEGRIDAD DEL DATO (MÓDULO 5075)

Para saber si un fichero ha cambiado usé el algoritmo SHA-256. Funciona como una huella dactilar: a partir del contenido del fichero genera un código de 64 caracteres hexadecimales. Si el fichero no cambia, el código sale siempre igual, pero si cambia aunque sea una coma, el código sale completamente distinto (es lo que se llama efecto avalancha). Además es unidireccional, es decir, a partir del hash no se puede reconstruir el fichero.

Lo primero que hice fue calcular el hash del fichero original tal como lo descargué, con este comando de PowerShell:

    Get-FileHash -Algorithm SHA256 ./datos/telemetria_envios.csv

El resultado coincide exactamente con el hash de referencia que viene en el enunciado, así que puedo asegurar que el fichero no se había alterado antes de empezar a trabajar con él. Tuve cuidado de no abrirlo con Excel en ningún momento, porque al guardar cambia el formato y con él el hash.

Después exploré los datos con pandas en el script saneamiento.py. Con isnull() conté las celdas vacías, con duplicated() las filas repetidas, con describe() miré los mínimos y máximos de las columnas numéricas y con value_counts() vi qué estados aparecían. Encontré estos problemas:

Había 2 filas duplicadas, que eran copia exacta de otras (los envíos ENV-2026-1012 y ENV-2026-1078 aparecían dos veces).

Había 3 celdas vacías, una en temp_celsius (ENV-2026-1015), otra en peso_kg (ENV-2026-1067) y otra en destino (ENV-2026-1189).

Había un peso negativo de -45.5 kg (ENV-2026-1088), cosa imposible.

Había una temperatura de 98.4 °C (ENV-2026-1142), cuando el resto de lecturas del compartimento refrigerado están entre -0.4 y unos 11 °C.

Había un estado DESCONOCIDO_ERROR (ENV-2026-1210), que no es un estado real del envío sino un fallo del sistema. El estado INCIDENCIA_REPARTO sí lo mantuve, porque describe una situación real.

Decidí eliminar las filas con problemas en vez de intentar corregirlas, porque eran muy pocas (8 de 300) y rellenarlas, por ejemplo con la media, habría sido inventar datos. Las reglas que apliqué, en este orden, fueron: quitar duplicados, quitar filas con alguna celda vacía, quedarme solo con pesos mayores que 0, quedarme solo con temperaturas entre -5 y 15 °C (un rango razonable para carga refrigerada que deja dentro todas las lecturas normales y fuera la de 98.4 °C) y quitar el estado DESCONOCIDO_ERROR. Para ejecutar el script:

    python scripts/saneamiento.py

El resultado es el fichero datos/telemetria_limpia.csv, con 292 registros. Las cuentas cuadran: 300 menos 2 duplicados, menos 3 vacíos, menos 1 peso, menos 1 temperatura y menos 1 estado dan 292.

Estos son los dos hashes, calculados con PowerShell y también desde el propio script con hashlib (salen iguales por los dos caminos):

    Fichero original (telemetria_envios.csv, 300 registros)
    4471c18a0284b3aa5b32a0713e691e3c7fcadae402f105e901c7c57f49474911

    Fichero limpio (telemetria_limpia.csv, 292 registros)
    23fe3d0b4801e8d90fe7bd79004f79c74058fa79c6de0a62d0964ce616f42513

Como era de esperar, los hashes no se parecen en nada, porque al eliminar 8 filas cambia el contenido del fichero. Otra cosa que comprobé es que, cada vez que ejecuto el script, el hash del fichero limpio sale idéntico, lo que demuestra que la limpieza es reproducible.


2. DESPLIEGUE Y HDFS (MÓDULO 5074)

Para no tener que instalar Hadoop y Java en Windows usé un contenedor Docker con la imagen apache/hadoop:3.4.0, en modo pseudodistribuido (todos los servicios dentro del mismo contenedor). El docker-compose.yml mapea dos puertos: el 9870, que es la interfaz web del NameNode, y el 8088, que es la interfaz web del ResourceManager de YARN. También monta mi carpeta datos/ dentro del contenedor como /workspace, que es como el contenedor puede ver el CSV limpio.

Aquí tuve el primer problema. Con el docker-compose.yml tal como venía en el enunciado, el contenedor arrancaba y se apagaba al instante. Con docker ps no aparecía, y con docker ps -a vi que había terminado con el código 127, que significa "comando no encontrado". La causa era la línea command: ["standalone"], porque en esta imagen no existe ningún comando con ese nombre. Lo solucioné modificando el docker-compose.yml. Por un lado añadí una sección environment con la configuración mínima de Hadoop: la dirección de HDFS (fs.defaultFS), un factor de replicación de 1 porque solo hay un nodo, y la configuración de YARN. Por otro lado cambié el command para que formatee HDFS la primera vez, arranque los cuatro daemons (NameNode, DataNode, ResourceManager y NodeManager) y deje el contenedor encendido con tail -f /dev/null. Con ese cambio, docker ps ya mostraba hadoop-lab en estado Up y con los dos puertos mapeados.

    docker compose up -d
    docker ps
    docker exec -it hadoop-lab bash

El segundo problema fue al verificar los servicios: dentro del contenedor jps daba "command not found". Lo busqué con find / -name jps y no apareció en ningún sitio, porque esta imagen trae solo el entorno de ejecución de Java (JRE) y no las herramientas de desarrollo (JDK), que es donde viene jps. Como alternativa comprobé los procesos con ps, aprovechando que Hadoop arranca cada daemon con un identificador proc_ seguido de su nombre:

    ps -ef | grep -o 'proc_[a-z]*' | sort -u

Salieron los cuatro: proc_namenode, proc_datanode, proc_resourcemanager y proc_nodemanager.

Con el clúster funcionando, ejecuté estos comandos de HDFS:

    hdfs dfs -mkdir -p /empresa/logistica/input
    hdfs dfs -put /workspace/telemetria_limpia.csv /empresa/logistica/input/
    hdfs dfs -ls /empresa/logistica/input/
    hdfs dfs -head /empresa/logistica/input/telemetria_limpia.csv
    hdfs dfs -tail /empresa/logistica/input/telemetria_limpia.csv
    hdfs dfs -cat /empresa/logistica/input/telemetria_limpia.csv
    hdfs dfs -cat /empresa/logistica/input/telemetria_limpia.csv | wc -l
    hdfs fsck /empresa/logistica/input/telemetria_limpia.csv -files -blocks -locations

El -ls mostró el fichero con un tamaño de 36339 bytes, propietario hadoop y replicación 1. El -head y el -tail muestran el primer y el último kilobyte del fichero, y por eso cortan alguna línea por la mitad. El -cat contado con wc -l dio 293 líneas, que son los 292 registros más la cabecera, así que no se perdió nada al subirlo.

El fsck dio estado HEALTHY. Como el fichero ocupa unos 36 KB y el tamaño de bloque de HDFS es de 128 MB, se guardó en un único bloque, con identificador blk_1073741825 y perteneciente al block pool BP-227585335-172.18.0.2-1794326510541. Ese bloque está guardado en el DataNode 172.18.0.2:9866 (la IP del contenedor dentro de la red de Docker y el puerto del DataNode), con una sola réplica y sin bloques perdidos ni corruptos.

Por último entré en http://localhost:9870 desde el navegador, fui a Utilities y luego a Browse the file system, y navegué hasta /empresa/logistica/input. Allí aparece telemetria_limpia.csv con 35.49 KB, replicación 1 y bloque de 128 MB. La hora que muestra la web va una hora por delante de la del terminal porque el navegador usa la hora de España y el contenedor usa UTC.


3. ANÁLISIS CRÍTICO

¿Por qué un fichero en HDFS no se corrompe ni se pierde aunque falle o se apague un DataNode en un clúster de producción?

La razón principal es la replicación. HDFS no guarda un fichero entero en un solo sitio: lo divide en bloques (de 128 MB por defecto) y guarda cada bloque varias veces en DataNodes distintos. En producción el factor de replicación habitual es 3. Además, la política de colocación de réplicas tiene en cuenta los racks: normalmente pone una copia en un nodo y las otras dos en otro rack diferente, para que ni siquiera la caída de un rack entero deje un bloque sin copias. Si se apaga un DataNode, los bloques que tenía siguen disponibles en las otras réplicas y los clientes leen de ellas sin enterarse del fallo.

El NameNode es quien vigila que esto se cumpla. Cada DataNode le envía un heartbeat cada pocos segundos y, periódicamente, un informe con la lista de bloques que tiene (block report). Si un DataNode deja de dar señales durante un tiempo (unos diez minutos con la configuración por defecto), el NameNode lo marca como muerto, detecta qué bloques se han quedado por debajo del factor de replicación y ordena copiarlos desde las réplicas que quedan hacia otros nodos sanos. Así el clúster se repara solo y vuelve a tener las tres copias de cada bloque. En el fsck de mi práctica se ven precisamente los contadores que controlan esto, como Under-replicated blocks o Missing blocks.

En cuanto a la corrupción, HDFS calcula sumas de verificación (checksums) de los datos cuando se escriben y las guarda junto a cada bloque. Cada vez que un cliente lee un bloque, vuelve a calcularlas y las compara, y los DataNodes también revisan sus bloques periódicamente en segundo plano. Si una réplica no coincide, se descarta como corrupta, se lee otra réplica sana y el NameNode programa una copia nueva para sustituir la dañada. Es la misma idea que he usado con el SHA-256 en la primera parte, pero aplicada de forma automática y continua a cada bloque. Hay que tener en cuenta que en mi entorno de laboratorio nada de esto me protegería: con un solo DataNode y replicación 1, como se ve en el fsck (Live_repl=1), si ese nodo fallara el fichero se perdería. Esta protección solo existe en un clúster real con varios nodos y un factor de replicación mayor que 1.


4. EVIDENCIAS GRÁFICAS

Las capturas están en la carpeta evidencias/:

evidencias/01_hashes_sha256.png muestra el cálculo del SHA-256 del fichero original y del limpio en PowerShell.

evidencias/02_jps_servicios.png muestra el intento con jps, la búsqueda con find y la comprobación de los cuatro daemons con ps.

evidencias/03_hdfs_comandos_fsck.png muestra los comandos hdfs dfs -put y hdfs dfs -ls y la salida de hdfs fsck con el bloque y su ubicación.

evidencias/04_webui_hdfs_browse.png muestra la interfaz web del NameNode con el fichero en /empresa/logistica/input.
