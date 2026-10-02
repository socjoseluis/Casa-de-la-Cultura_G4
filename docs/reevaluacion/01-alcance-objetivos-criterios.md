# Alcance, objetivos y criterios de aceptación

> Reevaluación de Proyectos de Software, curso 2025-2026. Proyecto "Casa de la Cultura" (Grupo 4).
> Fuentes: enunciado de la reevaluación, Project Charter (30/04/2026), PMP (07/05/2026) y sesiones de minería de requisitos con el cliente (S2 del 24/04, S5 del 04/05 y S6 del 08/05). Las citas indican sesión y minuto de la grabación.

---

## 1. Punto de partida: cambio de requisitos

En el proyecto original la elección tecnológica era libre: el cliente la consideraba *"transparente"* (Charter §14), y PostgreSQL y Apriori se ofrecían como herramientas opcionales. Con esa libertad, el equipo eligió SQLite el 07/05/2026 por las condiciones de uso (un único PC, sin conexión a internet y sin personal técnico que mantenga un servidor) y un recomendador por similitud coseno.

El enunciado de la reevaluación introduce requisitos nuevos y obligatorios. Se tratan como una petición de cambio sobre el producto ya construido:

| Punto | Producto a 18/05/2026 | Requisito de la reevaluación |
|---|---|---|
| Base de datos | SQLite | PostgreSQL, con los datos proporcionados y las recomendaciones |
| Recomendador | Similitud coseno ítem-ítem, sin guardar reglas | Reglas de asociación con Apriori, del tipo `libroA ⇒ {libros}`, guardadas en la BBDD |
| Dashboard | Rankings leídos de CSV precalculados | Visualización de lo almacenado en la BBDD |

**Impacto del cambio:** se conserva lo que sigue siendo válido (datos depurados, ETL, aplicación Django) y se rehacen la capa de datos, el recomendador y el dashboard. El empaquetado para el PC de la sala, que dependía de SQLite, queda fuera de esta iteración (ver AN-09).

---

## 2. Alcance

### 2.1 Dentro del alcance (alcance positivo)

| ID | Qué se hace | Origen |
|---|---|---|
| AP-01 | Persistir en PostgreSQL todos los datos proporcionados por el cliente (libros, autores, géneros, ejemplares, usuarios y valoraciones), depurados y con integridad referencial, sin descartar ningún libro, ejemplar ni valoración. | Enunciado; S2 min 8: *"que todo esto se guarde en una base de datos"*; S5 min 7: *"si creéis que es necesario hacer esta tarea de limpieza de datos, me parece perfecto… para eso os contratamos"* |
| AP-02 | Generar reglas de asociación con el algoritmo Apriori a partir de las valoraciones, con el formato `libroA ⇒ {libroSet}`, y guardarlas en PostgreSQL junto con sus métricas (soporte, confianza, lift) y los parámetros de cada ejecución. | Enunciado; S5 min 11: *"que un usuario pueda poner el libro que ha leído y de ahí se recomiendan otros libros"* |
| AP-03 | Mostrar recomendaciones en la aplicación de dos formas: a partir de un libro y a partir del identificador de un usuario (los libros que le gustaron), indicando el libro del que sale cada una. | S5 min 11 y min 19: *"si, aparte, pones tu identificador, pues ya lo tienes en base de tu histórico"* |
| AP-04 | Dashboard que visualice lo almacenado en la BBDD: cifras del catálogo, libros más leídos y mejor valorados, gustos por género, distribución de valoraciones y recomendaciones calculadas. | Enunciado; S2 min 21: *"donde yo pueda ver qué libros están leyendo, cuáles salen más"* |
| AP-05 | Acceso al catálogo, a las recomendaciones y al dashboard sin autenticación, identificando al usuario solo por su ID. | S2 min 40: *"los usuarios tienen un ID"*; S5 min 18: *"yo no le veo problema… que todos los usuarios puedan acceder"* |
| AP-06 | Funcionamiento local sin conexión a internet en tiempo de ejecución: librerías y datos incluidos en el proyecto. | S2 min 39-41: *"esta máquina por defecto no la tenemos conectada a internet… nuestra idea es que sea todo offline"* |

### 2.2 Fuera del alcance (alcance negativo)

| ID | Qué no se hace | Motivo |
|---|---|---|
| AN-01 | Gestión de préstamos, reservas o disponibilidad de ejemplares. | S2 min 43-44: lo intentaron con el bibliobús y lo dejaron por ser *"muy difícil de mantener"*; los libros no salen de la sala. |
| AN-02 | Login con contraseña, roles o panel de administración de usuarios. | S5 min 17: *"lo de los usuarios es lo que menos le doy importancia ahora mismo"*; posible ampliación *"dentro de uno o dos años"*. |
| AN-03 | Alta de libros o ejemplares nuevos desde la aplicación. | S2 min 59: *"los datos son estos, no van a cambiar"*; el cliente sigue usando sus Excel. |
| AN-04 | Recogida de nuevos datos personales o uso de la demografía (sexo, edad) para recomendar. El campo `sexo` no se guarda. | Indicación del cliente (Charter); minimización de datos (RGPD). Solo 501 de 53.424 usuarios tienen esos datos. |
| AN-05 | Conexión a internet en tiempo de ejecución o integración con servicios externos. | S2 min 39-41. El enriquecimiento con fuentes externas (géneros, ISBN, sinopsis) se hizo antes, en desarrollo, y su resultado va incluido en los datos. |
| AN-06 | Versión móvil o acceso remoto desde otros equipos. | S2 min 15: el uso es en el PC de la sala; Charter §4.2. |
| AN-07 | Adaptación legal completa (contratación pública, protección de datos). | S2 min 38: *"de momento para esta demo no nos hace falta"*. |
| AN-08 | Compra o digitalización de libros para cubrir idiomas que faltan. | S5 min 2-3: *"no podemos comenzar a comprar más libros, porque no estaba previsto"*. |
| AN-09 | Instalador para el PC de la sala (Windows 11) con PostgreSQL incluido. | No lo exige el enunciado de la reevaluación y el profesor confirmó que no es necesario en esta entrega (consulta del 01/10/2026). El anterior dependía de SQLite. Se plantea como siguiente iteración (PostgreSQL en modo portable). |

---

## 3. Objetivos SMART

Se sigue la definición de la asignatura: **S**pecific, **M**easurable, **A**greed upon, **R**ealistic, **T**ime bound. La restricción de hardware de todos los objetivos es el PC de la sala: **8 GB de RAM y 4 hilos** (S2 min 15). Cada objetivo incluye el resultado medido.

### OB-01 — Datos en PostgreSQL

| | |
|---|---|
| **Specific** | Cargar en PostgreSQL todos los datos proporcionados, depurados y con claves foráneas entre libros, ejemplares, usuarios y valoraciones. |
| **Measurable** | Todos los libros, ejemplares y valoraciones de los ficheros originales están en la BBDD; las tablas cumplen todas las restricciones (claves foráneas, valoración entre 1 y 5); la carga informa de cada registro descartado y su motivo. |
| **Agreed upon** | Encargo del enunciado y PMP OB-01; el cliente aprueba la depuración (S5 min 7). |
| **Realistic** | El volumen (~6 M de valoraciones) es manejable en PostgreSQL; el ETL ya existía y estaba probado. |
| **Time bound** | 02/10/2026. |
| **Resultado** | ✅ 01/10/2026. 10.000 libros, 55.327 ejemplares, 53.425 usuarios, 30 géneros y 5.976.479 valoraciones; 0 descartadas. Dos filas mal formadas de `books.csv` se repararon a mano para no perder ningún libro. Carga completa en ~3 min. |

### OB-02 — Reglas de asociación con Apriori

| | |
|---|---|
| **Specific** | Generar reglas `libroA ⇒ {libroSet}` con Apriori a partir de los libros bien valorados por cada usuario, y guardarlas en PostgreSQL junto con sus métricas y los parámetros de la ejecución. |
| **Measurable** | La generación completa termina en ≤ 10 min y sin superar 6 GB de RAM. Todas las reglas guardadas tienen lift > 1 y antecedente no vacío. Al menos el 80 % de los 1.000 libros más valorados tiene alguna regla. |
| **Agreed upon** | Enunciado (Apriori obligatorio); cliente: *"sí o sí tiene que tener un sistema inteligente detrás"* (S2 min 22) y recomendación a partir de un libro leído (S5 min 11). |
| **Realistic** | Apriori es un algoritmo conocido y con implementaciones abiertas; el volumen se controla con el umbral de valoración, el soporte mínimo y la longitud máxima de las reglas. |
| **Time bound** | 02/10/2026. |
| **Resultado** | ✅ 01/10/2026, con una salvedad. 15.915 reglas (8.117 con dos libros en el consecuente) en 78 s y ~1 GB de RAM; ninguna con lift < 1 ni antecedente vacío. La cobertura del top 1.000 es del **79,7 %**, a tres décimas del objetivo: bajar el soporte la superaría, pero a costa de reglas apoyadas por menos lectores y más tiempo de cálculo (con soporte 0,5 %: 100 % de cobertura, 46.646 reglas y 5,4 min). Se mantiene la configuración por equilibrio entre cobertura y fiabilidad. |

### OB-03 — Recomendaciones en la aplicación

| | |
|---|---|
| **Specific** | Mostrar recomendaciones leyendo las reglas de la BBDD a partir de un libro o del ID de un usuario, con un mecanismo de respaldo (por género o popularidad) cuando no haya reglas aplicables. |
| **Measurable** | Respuesta en < 1 s. El 100 % de los usuarios con valoraciones recibe al menos una recomendación. Cada recomendación por reglas indica el libro del que sale. |
| **Agreed upon** | S5 min 11 y 19; S5 min 1: *"prefiero recomendar un libro con una puntuación de 3 antes que no recomendar nada"*. |
| **Realistic** | Consultas indexadas sobre reglas ya calculadas; no hay cálculo pesado en tiempo real. |
| **Time bound** | 02/10/2026. |
| **Resultado** | ✅ 01/10/2026. Páginas en < 0,5 s. El 99,8 % de los lectores tiene algún libro favorito con reglas y puede recibir recomendaciones por ellas; los demás las reciben por género o popularidad. Cada recomendación muestra «Si te gustó X · N % de coincidencia». |

### OB-04 — Dashboard sobre la BBDD

| | |
|---|---|
| **Specific** | Dashboard con visualizaciones de gustos y uso del catálogo, alimentado solo con consultas a PostgreSQL. |
| **Measurable** | Al menos 5 visualizaciones. Cada consulta tarda < 1 s, comprobado con `EXPLAIN ANALYZE`. |
| **Agreed upon** | Enunciado; S2 min 21 y min 25: *"la visualización es muy importante"*. |
| **Realistic** | Tecnología conocida (Django), librería de gráficos incluida en el proyecto, índices y vistas materializadas en PostgreSQL. |
| **Time bound** | 02/10/2026. |
| **Resultado** | ✅ 01/10/2026. 6 bloques (cifras clave, gustos por género, distribución de valoraciones, más leídos, mejor valorados y recomendaciones). Consultas entre 0,02 y 6 ms gracias a las vistas materializadas (antes, 0,2-3,7 s). |

---

## 4. Criterios de aceptación

### 4.1 Criterios de aprobación (verificables)

| ID | Criterio | Cómo se verifica | Objetivo | Resultado |
|---|---|---|---|---|
| CA-01 | Todos los libros, ejemplares y valoraciones de los ficheros originales están en PostgreSQL. | Recuentos de la carga frente a los ficheros. | OB-01 | ✅ 10.000 / 55.327 / 5.976.479 |
| CA-02 | Las tablas no tienen violaciones de integridad. | Restricciones activas en la BBDD (claves foráneas, `CHECK`, unicidad). | OB-01 | ✅ |
| CA-03 | El generador de reglas se ejecuta en directo con parámetros configurables y escribe las reglas en la BBDD. | `python manage.py generar_reglas`; consulta de las tablas de reglas. | OB-02 | ✅ |
| CA-04 | Toda regla guardada tiene lift > 1 y antecedente no vacío. | Consulta de control sobre la tabla de reglas. | OB-02 | ✅ 0 incumplimientos |
| CA-05 | Dado un libro o un ID de usuario, la aplicación devuelve recomendaciones leídas de la BBDD en < 1 s. | Prueba con varios libros y usuarios; tiempo medido. | OB-03 | ✅ < 0,5 s |
| CA-06 | El dashboard muestra al menos 5 visualizaciones, todas desde PostgreSQL y en < 1 s cada una. | Revisión de las consultas y `EXPLAIN ANALYZE`. | OB-04 | ✅ 6 bloques, ≤ 6 ms |
| CA-07 | La base de datos se puede regenerar desde los ficheros del cliente con resultados idénticos. | `python load_data_postgres.py` + `python manage.py generar_reglas`. | OB-01, OB-02 | ✅ |

### 4.2 Criterios de satisfacción (perspectiva del cliente)

| ID | Criterio | Cómo se comprueba | Estado |
|---|---|---|---|
| CS-01 | Los libros más leídos y los géneros preferidos se consultan con un solo clic desde el catálogo, sin configurar nada. | Desde el catálogo, botón «Ver más estadísticas». | ✅ |
| CS-02 | Las recomendaciones se entienden: cada una indica el libro que la origina. | Revisión de la pantalla de recomendaciones. | ✅ «Si te gustó X · N % de coincidencia» |
| CS-03 | El dashboard usa un lenguaje no técnico; los detalles del algoritmo quedan en un apartado aparte. | Revisión del dashboard. | ✅ «Detalles técnicos» plegable |

---

## 5. Trazabilidad

| Necesidad del cliente | Alcance | Objetivo | Criterios |
|---|---|---|---|
| Guardar los datos en una BBDD | AP-01 | OB-01 | CA-01, CA-02, CA-07 |
| Recomendador inteligente ("quien leyó X también disfrutó Y") | AP-02, AP-03 | OB-02, OB-03 | CA-03, CA-04, CA-05, CS-02 |
| Cuadro de mandos visual | AP-04 | OB-04 | CA-06, CS-01, CS-03 |
| Funcionar en el PC de la sala, sin internet | AP-05, AP-06 | — (instalador en AN-09) | — |
