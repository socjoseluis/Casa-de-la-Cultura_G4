# Modelo de datos

> Diagramas generados con `python docs/reevaluacion/diagramas/generar_diagramas.py` a partir del esquema real de PostgreSQL. Notación UML, como en la cápsula de diagramas E-R de la asignatura: clase con atributos, clave primaria subrayada y asociaciones con multiplicidad.

## 1. Diagramas

| Diagrama | Contenido |
|---|---|
| [Completo](diagramas/1-completo.png) | Las 11 tablas de la aplicación con todas sus columnas, tipos y claves |
| [General](diagramas/2-general.png) | Modelo conceptual sin atributos, agrupado en tres zonas |
| [Catálogo](diagramas/3-catalogo.png) | Libros, autores, géneros y ejemplares |
| [Lectores](diagramas/4-lectores.png) | Lectores y valoraciones |
| [Recomendador](diagramas/5-recomendador.png) | Ejecuciones de Apriori y reglas libro ⇒ libros |

Las tablas internas de Django (usuarios del panel de administración, sesiones, permisos y migraciones) no forman parte del dominio y no se representan.

### Asociaciones del modelo conceptual

| Asociación | Multiplicidad | Significado |
|---|---|---|
| Book — Author | `*` — `1..*` | Un libro tiene al menos un autor; un autor puede tener varios libros |
| Book — Genre | `*` — `1..3` | Cada libro se clasifica en 1 a 3 géneros |
| Book — Copy | `1` — `1..*` | Todo libro tiene al menos un ejemplar; cada ejemplar es de un único libro |
| LibraryUser — Copy (Rating) | `*` — `*` | Un lector valora muchos ejemplares y un ejemplar es valorado por muchos lectores. `Rating` es una **clase asociativa**: la valoración pertenece a la pareja lector-ejemplar y tiene atributos propios (puntuación y fecha) |
| AprioriRun — AssociationRule | `1` — `*` | Cada ejecución de Apriori genera muchas reglas |
| AssociationRule — Book (antecedente) | `*` — `1` | «Si te gusta…»: cada regla parte de un único libro |
| AssociationRule — Book (consecuente) | `*` — `1..2` | «…también te gustan»: cada regla recomienda uno o dos libros (`max_len` = 3) |

## 2. Paso al modelo relacional

Siguiendo las reglas de la asignatura: cada clase es una tabla; una asociación `1 — *` pone una referencia en el lado `*`; una asociación `* — *` genera una tabla propia con las dos referencias, y una clase asociativa es esa tabla con sus atributos.

- BOOK(<u>id</u>, book_id, title, original_title, isbn, publication_year, language_code, image_url)
- AUTHOR(<u>id</u>, name)
- GENRE(<u>id</u>, name)
- BOOK_AUTHORS(<u>id</u>, book, author)
  Donde {book} referencia a BOOK y {author} referencia a AUTHOR
- BOOK_GENRES(<u>id</u>, book, genre)
  Donde {book} referencia a BOOK y {genre} referencia a GENRE
- COPY(<u>id</u>, copy_id, book, available)
  Donde {book} referencia a BOOK
- LIBRARYUSER(<u>id</u>, user_id, birth_date, comment)
- RATING(<u>id</u>, user, copy, rating, created_at)
  Donde {user} referencia a LIBRARYUSER y {copy} referencia a COPY
- APRIORIRUN(<u>id</u>, started_at, finished_at, min_rating, min_support, min_confidence, min_lift, max_len, is_active, transactions_count, rules_count, books_with_rules_count, covered_users_count)
- ASSOCIATIONRULE(<u>id</u>, run, source_book, support, confidence, lift, created_at)
  Donde {run} referencia a APRIORIRUN y {source_book} referencia a BOOK
- ASSOCIATIONRULETARGET(<u>id</u>, rule, book)
  Donde {rule} referencia a ASSOCIATIONRULE y {book} referencia a BOOK

En PostgreSQL las tablas llevan el prefijo de la aplicación Django (`app_book`, `app_rating`…) y las referencias, el sufijo `_id` (`book_id`, `run_id`…).

## 3. Decisiones de diseño

- **Clave primaria sustituta (`id`) y clave del sistema anterior como única.** Cada tabla tiene un `id` autonumérico generado por Django y conserva el identificador original del cliente (`book_id`, `copy_id`, `user_id`) con restricción de unicidad, para poder rastrear cada registro hasta los ficheros recibidos.
- **Unicidad de las parejas.** `BOOK_AUTHORS (book, author)`, `BOOK_GENRES (book, genre)`, `RATING (user, copy)` y `ASSOCIATIONRULETARGET (rule, book)` son únicas: un lector no puede valorar dos veces el mismo ejemplar ni una regla repetir un libro en su consecuente.
- **Restricciones `CHECK`.** La valoración está entre 1 y 5; soporte y confianza, entre 0 y 1; lift ≥ 0; `max_len` ≥ 2.
- **Una única ejecución activa.** Restricción de unicidad parcial sobre `is_active` (`UNIQUE … WHERE is_active`): la aplicación siempre sabe qué reglas usar y las ejecuciones anteriores quedan como historial.
- **Consecuente en tabla propia.** `ASSOCIATIONRULETARGET` permite guardar reglas `A ⇒ {B, C}` con sus propias métricas, en lugar de convertirlas en dos reglas `A ⇒ B` y `A ⇒ C`, que tendrían otro soporte, confianza y lift.
- **Borrado en cascada gestionado por Django**: al borrar un libro desde la aplicación se borran sus ejemplares, valoraciones y reglas, y al borrar una ejecución, sus reglas. En PostgreSQL las claves foráneas quedan como `NO ACTION`, así que la base de datos impide borrar directamente un registro que otro referencia.
- **Valores nulos solo donde faltan datos en origen**: ISBN, título original, año, idioma, fecha de nacimiento y comentario.
- **Sin el campo `sexo`** de `user_info`, por indicación del cliente y minimización de datos.
- **Vistas materializadas** (`estadisticas_libro`, `estadisticas_genero`, `distribucion_valoraciones`): no son entidades del modelo, sino resúmenes precalculados para el dashboard (ver `docs/datos/esquema-bd.md`).
