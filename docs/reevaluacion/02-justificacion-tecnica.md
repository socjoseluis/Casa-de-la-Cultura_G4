# Justificación técnica

> Por qué se tomó cada decisión de herramientas, código y diseño. Las cifras son mediciones reales sobre los datos del cliente (10.000 libros, 55.327 ejemplares, 53.425 usuarios y 5.976.479 valoraciones).

---

## 1. Arquitectura

La aplicación sigue la arquitectura de tres capas de la asignatura, en la que cada capa se comunica solo con la inferior:

| Capa | Componentes |
|---|---|
| Presentación | Plantillas de Django: catálogo, perfil y dashboard (`app/templates/`) |
| Lógica | Vistas (`app/views.py`), recomendador (`generar_reglas`) y estadísticas (`app/estadisticas.py`) |
| Datos | PostgreSQL: modelos y migraciones de Django, vistas materializadas |

Los procesos pesados se ejecutan fuera de la petición web como comandos (`load_data_postgres.py`, `manage.py generar_reglas`, `manage.py refrescar_estadisticas`): la aplicación solo lee resultados ya calculados y responde en menos de medio segundo.

---

## 2. Herramientas

| Herramienta | Por qué |
|---|---|
| **PostgreSQL 16** | Requisito de la reevaluación. Además aporta lo que el proyecto necesita: restricciones (`CHECK`, unicidad parcial), vistas materializadas, `EXPLAIN ANALYZE` para medir consultas y carga masiva eficiente. En la entrega original se usó SQLite por la libertad tecnológica y la instalación en un único PC; el paso a PostgreSQL se trata como un cambio de requisitos. |
| **Python + Django 6** | Ya era la base del proyecto. El ORM y las migraciones hacen el esquema reproducible: `python manage.py migrate` crea toda la base de datos, índices y vistas incluidos. |
| **mlxtend 0.25** | Implementación de Apriori mantenida y de referencia en Python. Evita reinventar el algoritmo (riesgo R-05 del PMP) y permite centrarse en su configuración. |
| **pandas / NumPy** | Construcción de la matriz de transacciones usuario × libro. |
| **Chart.js 4.5** | Gráficos del dashboard. Se incluye dentro del proyecto en lugar de cargarlo de internet para que funcione sin conexión. |
| **Graphviz** | Diagramas E-R generados a partir de una definición, siempre coherentes con el esquema. |

---

## 3. Datos

- **Versión extendida de la limpieza.** Se conservan los libros sin ISBN (con sus ejemplares y valoraciones), como se presentó al cliente: *"sin descartar ningún libro del catálogo original"*. La versión estricta perdía 218.535 valoraciones (3,7 %).
- **Dos filas mal formadas** de `books.csv` (líneas 6623 y 9273, comillas mal escapadas) se repararon a mano con las mismas normalizaciones que el ETL. Eran los únicos libros perdidos y explicaban los últimos 12 ejemplares y 281 valoraciones descartados. Resultado: **0 valoraciones descartadas**.
- **Sus géneros** se asignaron con las reglas del prompt original y en coherencia con los libros de su saga, en lugar de repetir todo el proceso con la API para dos libros.
- **Sin el campo `sexo`**, por indicación del cliente y minimización de datos.
- **Carga reproducible.** `load_data_postgres.py` vacía y recarga todo desde los ficheros, informa de cada descarte con su motivo y refresca las estadísticas. Permite hacer pruebas y entregar después la base de datos limpia.
- **Votos y nota media calculados desde la base de datos.** Antes se leían de un CSV generado meses atrás que no reflejaba las valoraciones nuevas ni los libros recuperados (720 libros aparecían con 0 votos).

---

## 4. Recomendador Apriori

### 4.1 Planteamiento

- **Transacción** = conjunto de libros que gustaron a un usuario, como la cesta de la compra de la cápsula de reglas de asociación. 53.406 transacciones.
- **Regla** = `libro A ⇒ {libros}` con **un único libro en el antecedente**, que es el formato del enunciado y lo que pidió el cliente: *"un usuario pueda poner el libro que ha leído y de ahí se recomiendan otros libros"* (S5, min 11).

### 4.2 Configuración y motivos

| Parámetro | Valor | Motivo |
|---|---|---|
| Valoración mínima | 4 | 4-5 estrellas = "le gustó". Con ≥ 3 se incluyen valoraciones neutras, las cestas pasan de 77 a 103 libros de media y el cálculo se multiplica (43.572 reglas, 3,8 min). |
| Soporte mínimo | 1 % | Unos 530 lectores comparten la combinación. Es el punto de equilibrio entre cobertura y fiabilidad (tabla siguiente). |
| Confianza mínima | 30 % | De los lectores a los que les gustó A, al menos un 30 % disfrutó también los recomendados. |
| Lift mínimo | 1 | Solo relaciones más frecuentes de lo esperable por casualidad. |
| `max_len` | 3 | Permite reglas `A ⇒ {B, C}`: 8.117 de las 15.915 reglas recomiendan dos libros. |

Estudio de parámetros (valoración ≥ 4, `max_len` 3):

| Soporte | Reglas | Libros con reglas | Top 1.000 cubierto | Tiempo | RAM |
|---|---|---|---|---|---|
| 5 % | 986 | 81 | 8 % | 0,5 s | 315 MB |
| 3 % | 2.506 | 192 | 19 % | 3,3 s | 320 MB |
| 2 % | 5.001 | 358 | 36 % | 11 s | 368 MB |
| **1 %** | **15.915** | **860** | **80 %** | **71 s** | **558 MB** |
| 0,5 % | 46.646 | 1.904 | 100 % | 5,4 min | 987 MB |

Con soportes altos solo se recomiendan superventas. Con 0,5 % se cubre todo, pero con reglas apoyadas por muy pocos lectores (el lift máximo sube a 156, típico de coincidencias raras) y un tiempo de cálculo cinco veces mayor.

### 4.3 Memoria: `low_memory=True`

El PC de la sala tiene 8 GB de RAM. Con la opción por defecto, `mlxtend` necesitó **28 GB** para soporte 2 % y no terminó con 1 %, porque prepara de golpe todas las combinaciones candidatas. Con `low_memory=True` genera exactamente las mismas reglas usando **~0,5 GB** y en menos tiempo. El comando completo, con Django, usa ~1 GB y tarda ~80 s.

### 4.4 Persistencia (salida del algoritmo → entrada de la base de datos)

- `AprioriRun` guarda la configuración, las fechas, el número de transacciones y reglas y la cobertura de cada ejecución.
- `AssociationRule` guarda el antecedente y las métricas (soporte, confianza, lift); `AssociationRuleTarget`, los libros del consecuente. Así una regla `A ⇒ {B, C}` conserva sus propias métricas en lugar de convertirse en dos reglas distintas.
- Solo una ejecución está activa (restricción de unicidad parcial); las anteriores quedan como historial.
- Si una ejecución falla, se interrumpe o no genera ninguna regla, se descarta y se mantiene la activa anterior.

### 4.5 Integración en la aplicación

- **Por libro:** al buscar un libro, *"Quienes disfrutaron X también disfrutaron…"*.
- **Por usuario:** se aplican las reglas a los libros que le gustaron y se descartan los que ya ha leído.
- **Explicable:** cada recomendación indica de dónde sale (*"Si te gustó X · 77 % de coincidencia"*).
- **Respaldo:** los libros poco leídos no alcanzan el soporte mínimo y no tienen reglas (es cómo funciona Apriori); para ellos se recomienda por género o popularidad.

---

## 5. Dashboard, índices y rendimiento

- **Lenguaje para el cliente.** El dashboard es para el personal de la Casa de la Cultura: cifras, gustos por género, libros más leídos y recomendaciones, sin términos técnicos. La configuración del algoritmo queda en un apartado plegable de "Detalles técnicos".
- **Índices duplicados eliminados.** `Rating` declaraba índices sobre `user` y `copy` que Django ya crea por ser claves foráneas; ocupaban espacio en una tabla de ~6 millones de filas y ralentizaban las inserciones.
- **Índices normales no bastan.** Las consultas del dashboard resumen todas las valoraciones. Un índice cubriente `(copy_id) INCLUDE (rating)` solo bajó de 914 a 875 ms: PostgreSQL tiene que leer igualmente todas las filas.
- **Vistas materializadas indexadas.** Se precalculan las estadísticas por libro, por género y por puntuación, y se indexan. Se refrescan con `REFRESH MATERIALIZED VIEW CONCURRENTLY` (~1,2 s) al cargar datos y al valorar un libro, sin bloquear las lecturas.

| Consulta | Antes | Después |
|---|---|---|
| Libros más valorados | 914 ms | 0,02 ms |
| Libros mejor valorados | 918 ms | 1,5 ms |
| Gustos por género | 576 ms | 0,4 ms |
| Distribución de valoraciones | 235 ms | 0,3 ms |
| Cobertura del recomendador | 3.695 ms | 2 ms (guardada al generar las reglas) |

---

## 6. Calidad

- **Comandos reproducibles e idempotentes**: se pueden repetir sin duplicar datos y siempre dan el mismo resultado.
- **Comprobaciones automáticas**: recuentos de la carga, reglas que cumplen la configuración, una sola ejecución activa.
- **Contratos de operación** (`@pre`, `@post`, `@param`, `@return`) en las funciones principales del recomendador y de las estadísticas, como se vio en la asignatura.
- **Documentación** del pipeline de datos, del esquema, del modelo de datos y de estas decisiones en el repositorio.

---

## 7. Limitaciones conocidas

- Solo el 8,6 % de los libros (860) tiene reglas propias; el resto recibe recomendaciones de respaldo. La cobertura de los 1.000 libros más leídos es del 79,7 %, a tres décimas del objetivo del 80 %.
- Algunos títulos de origen tienen apóstrofos duplicados (*Sorcerer''s Stone*), que no se corrigieron en el ETL.
- Las valoraciones históricas no tienen fecha en origen: todas registran la fecha de la carga.
- El instalador para el PC de la sala queda para la siguiente iteración (alcance negativo AN-09).
