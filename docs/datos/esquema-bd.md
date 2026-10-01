# Esquema de la base de datos — Casa de la Cultura

> Última actualización: 29/09/2026
> Implementación actual basada en Django ORM y PostgreSQL.

---

## Decisiones de diseño

La base de datos se ha adaptado para utilizar PostgreSQL como sistema de persistencia principal.

Las entidades principales del dominio son:

- `Author`: autores disponibles en el catálogo.
- `Genre`: géneros literarios asociados a los libros.
- `Book`: información bibliográfica de cada libro.
- `Copy`: ejemplares físicos disponibles de cada libro.
- `LibraryUser`: usuarios de la Casa de la Cultura.
- `Rating`: valoraciones realizadas por los usuarios sobre ejemplares.
- `AprioriRun`: registro de cada ejecución del algoritmo Apriori.
- `AssociationRule`: reglas de asociación generadas por Apriori.
- `AssociationRuleTarget`: libros que forman el consecuente de cada regla.

Las relaciones entre libros y autores, así como entre libros y géneros, se representan mediante relaciones muchos a muchos gestionadas por Django.

Las recomendaciones ya no se almacenan como una relación directa entre usuario y libro. El sistema utiliza reglas de asociación del tipo:

`Libro A => [Libro B, Libro C, ...]`

Estas reglas se generan mediante el algoritmo Apriori a partir del histórico de valoraciones.

---

## Entidades principales

### Author

Representa un autor del catálogo.

Campos principales:

- `id`: clave primaria generada por Django.
- `name`: nombre del autor.

Un autor puede estar relacionado con varios libros y un libro puede tener varios autores.

---

### Genre

Representa un género literario.

Campos principales:

- `id`: clave primaria.
- `name`: nombre del género.

El campo `name` es único.

La relación con `Book` es muchos a muchos.

---

### Book

Representa un libro del catálogo.

Campos principales:

- `id`: clave primaria interna.
- `book_id`: identificador original del dataset.
- `title`: título.
- `original_title`: título original.
- `isbn`: ISBN, cuando está disponible.
- `publication_year`: año de publicación.
- `language_code`: idioma.
- `image_url`: URL de la imagen.
- `authors`: relación N:M con `Author`.
- `genres`: relación N:M con `Genre`.

`book_id` es único.

---

### Copy

Representa un ejemplar físico de un libro.

Campos principales:

- `id`: clave primaria.
- `copy_id`: identificador original del ejemplar.
- `book`: libro al que pertenece el ejemplar.
- `available`: indica si el ejemplar se encuentra disponible.

Cada ejemplar pertenece a un único libro.

`copy_id` es único.

---

### LibraryUser

Representa un usuario de la biblioteca.

Campos principales:

- `id`: clave primaria.
- `user_id`: identificador original del usuario.
- `birth_date`: fecha de nacimiento, si está disponible.
- `comment`: información adicional o preferencias.

`user_id` es único.

---

### Rating

Representa una valoración realizada por un usuario sobre un ejemplar.

Campos principales:

- `id`: clave primaria.
- `user`: usuario que realiza la valoración.
- `copy`: ejemplar valorado.
- `rating`: puntuación entre 1 y 5.
- `created_at`: fecha de creación del registro.

Restricciones:

- `rating` debe estar comprendido entre 1 y 5.
- Un mismo usuario no puede valorar dos veces el mismo ejemplar.

---

## Modelo de recomendaciones Apriori

### AprioriRun

Registra cada ejecución del algoritmo Apriori.

Campos principales:

- `id`: clave primaria.
- `started_at`: fecha y hora de inicio.
- `finished_at`: fecha y hora de finalización.
- `min_support`: soporte mínimo utilizado.
- `min_confidence`: confianza mínima utilizada.
- `min_lift`: lift mínimo utilizado.
- `min_rating`: valoración mínima utilizada para construir las transacciones.
- `max_len`: longitud máxima de los conjuntos procesados.
- `is_active`: indica si esta ejecución es la actualmente utilizada por la aplicación.
- `transactions_count`: número de transacciones utilizadas.
- `rules_count`: número de reglas generadas.

Restricciones:

- `min_support` entre 0 y 1.
- `min_confidence` entre 0 y 1.
- `min_lift` mayor o igual que 0.
- `min_rating` entre 1 y 5.
- `max_len` mayor o igual que 2.
- `transactions_count` y `rules_count` no pueden ser negativos.
- Solo puede existir una ejecución con `is_active = true`.

---

### AssociationRule

Representa una regla de asociación generada por Apriori.

Cada regla tiene un único libro como antecedente.

Campos principales:

- `id`: clave primaria.
- `run`: ejecución Apriori que generó la regla.
- `source_book`: libro antecedente.
- `support`: soporte de la regla.
- `confidence`: confianza de la regla.
- `lift`: lift de la regla.
- `created_at`: fecha de creación.

Restricciones:

- `support` entre 0 y 1.
- `confidence` entre 0 y 1.
- `lift` mayor o igual que 0.

---

### AssociationRuleTarget

Representa cada libro incluido en el consecuente de una regla.

Campos principales:

- `id`: clave primaria.
- `rule`: regla de asociación.
- `book`: libro perteneciente al consecuente.

Una misma regla no puede contener dos veces el mismo libro.

Este diseño permite almacenar reglas con más de un libro en el consecuente, por ejemplo:

`Libro A => [Libro B, Libro C]`

sin convertirla incorrectamente en dos reglas independientes.

---

## Diagrama ER

```mermaid
erDiagram

    AUTHOR {
        bigint id PK
        varchar name
    }

    GENRE {
        bigint id PK
        varchar name UK
    }

    BOOK {
        bigint id PK
        int book_id UK
        varchar title
        varchar original_title
        varchar isbn
        int publication_year
        varchar language_code
        varchar image_url
    }

    COPY {
        bigint id PK
        int copy_id UK
        boolean available
        bigint book_id FK
    }

    LIBRARY_USER {
        bigint id PK
        int user_id UK
        date birth_date
        text comment
    }

    RATING {
        bigint id PK
        int rating
        datetime created_at
        bigint user_id FK
        bigint copy_id FK
    }

    APRIORI_RUN {
        bigint id PK
        datetime started_at
        datetime finished_at
        float min_support
        float min_confidence
        float min_lift
        int min_rating
        int max_len
        boolean is_active
        int transactions_count
        int rules_count
    }

    ASSOCIATION_RULE {
        bigint id PK
        float support
        float confidence
        float lift
        datetime created_at
        bigint run_id FK
        bigint source_book_id FK
    }

    ASSOCIATION_RULE_TARGET {
        bigint id PK
        bigint rule_id FK
        bigint book_id FK
    }

    BOOK }o--o{ AUTHOR : "authors"
    BOOK }o--o{ GENRE : "genres"
    BOOK ||--o{ COPY : "copies"
    LIBRARY_USER ||--o{ RATING : "ratings"
    COPY ||--o{ RATING : "ratings"

    APRIORI_RUN ||--o{ ASSOCIATION_RULE : "rules"
    BOOK ||--o{ ASSOCIATION_RULE : "source"
    ASSOCIATION_RULE ||--o{ ASSOCIATION_RULE_TARGET : "targets"
    BOOK ||--o{ ASSOCIATION_RULE_TARGET : "target"
```

---

## Restricciones de integridad

La implementación utiliza restricciones tanto en Django como directamente en PostgreSQL.

### Valoraciones

La puntuación de `Rating` debe estar comprendida entre 1 y 5.

```text
1 <= rating <= 5
```

Además, existe una restricción de unicidad sobre:

```text
(user, copy)
```

para evitar que un mismo usuario valore dos veces el mismo ejemplar.

### Ejecuciones Apriori

Los parámetros utilizados por Apriori están limitados a valores válidos:

```text
0 <= min_support <= 1
0 <= min_confidence <= 1
min_lift >= 0
1 <= min_rating <= 5
max_len >= 2
```

Solo puede existir una ejecución Apriori marcada como activa.

### Reglas de asociación

Las métricas de las reglas cumplen:

```text
0 <= support <= 1
0 <= confidence <= 1
lift >= 0
```

Cada pareja:

```text
(rule, book)
```

de `AssociationRuleTarget` debe ser única.

---

## Índices

PostgreSQL crea automáticamente índices sobre las claves primarias y los campos con restricciones de unicidad, y Django crea uno sobre cada clave foránea.

Además, se han definido índices específicos para consultas frecuentes.

### Rating

`user` y `copy` ya están indexados por ser claves foráneas, y el par `(user, copy)` por su restricción de unicidad. El modelo declaraba además dos índices sobre `user` y `copy` que duplicaban los anteriores; se eliminaron en la migración `0005` porque ocupaban espacio en una tabla de ~6 millones de filas y ralentizaban las inserciones sin aportar nada.

### AssociationRule

Se han creado índices sobre:

- `confidence`
- `lift`
- `(source_book, confidence)`

El índice compuesto sobre `source_book` y `confidence` permite obtener eficientemente las reglas asociadas a un libro y ordenarlas o filtrarlas por confianza.

### Vistas materializadas del dashboard

Las consultas del dashboard resumen los ~6 millones de valoraciones (votos y nota media por libro, por género y por puntuación). Recorren la tabla entera, así que un índice normal no las acelera: se probó un índice cubriente `(copy_id) INCLUDE (rating)` y la consulta de libros más valorados pasó de 914 a 875 ms, una mejora irrelevante.

La solución es precalcularlas en vistas materializadas (migración `0006`) e indexar las vistas:

| Vista | Contenido | Índices |
|---|---|---|
| `estadisticas_libro` | votos y nota media por libro | único `(book_id)`, `(votos DESC)`, `(nota_media DESC, votos DESC)` |
| `estadisticas_genero` | libros, valoraciones, valoraciones positivas y nota media por género | único `(genre_id)` |
| `distribucion_valoraciones` | nº de valoraciones de 1 a 5 estrellas | único `(rating)` |

Se refrescan con `python manage.py refrescar_estadisticas` (~1,2 s), que se ejecuta automáticamente al final de la carga y al registrar una valoración. El índice único de cada vista permite refrescarla con `REFRESH MATERIALIZED VIEW CONCURRENTLY`, sin bloquear las lecturas.

La cobertura del recomendador (libros con reglas y lectores cubiertos) se calcula una vez al generar las reglas y se guarda en `AprioriRun`, en vez de calcularla en cada visita (3,7 s).

Tiempo de cada consulta del dashboard (`EXPLAIN ANALYZE`):

| Consulta | Sobre las tablas | Con vistas / precálculo |
|---|---|---|
| Libros más valorados | 914 ms | 0,02 ms |
| Libros mejor valorados | 918 ms | 1,5 ms |
| Gustos por género | 576 ms | 0,4 ms |
| Distribución de valoraciones | 235 ms | 0,3 ms |
| Cobertura de Apriori | 3.695 ms | 2 ms |
| Reglas más fuertes | 28 ms | 5,6 ms (la mejor regla de cada libro) |

Comparación reproducible en `psql` o pgAdmin:

```sql
-- Directamente sobre las ~6 millones de valoraciones
EXPLAIN ANALYZE
SELECT b.title, count(*) AS votos, avg(r.rating) AS nota
FROM app_rating r
JOIN app_copy c ON c.id = r.copy_id
JOIN app_book b ON b.id = c.book_id
GROUP BY b.id, b.title
ORDER BY votos DESC
LIMIT 10;

-- Sobre la vista materializada indexada
EXPLAIN ANALYZE
SELECT b.title, e.votos, e.nota_media
FROM estadisticas_libro e
JOIN app_book b ON b.id = e.book_id
ORDER BY e.votos DESC
LIMIT 10;
```

---

## Integridad referencial

Las relaciones principales utilizan claves foráneas gestionadas mediante Django.

Las eliminaciones utilizan `CASCADE` en las relaciones principales:

- eliminar un `Book` elimina sus `Copy`.
- eliminar un `Copy` elimina sus `Rating`.
- eliminar un `LibraryUser` elimina sus `Rating`.
- eliminar un `AprioriRun` elimina sus `AssociationRule`.
- eliminar una `AssociationRule` elimina sus `AssociationRuleTarget`.
- eliminar un `Book` elimina sus relaciones como antecedente o consecuente de reglas.

Las relaciones N:M entre libros, autores y géneros son gestionadas mediante las tablas intermedias creadas automáticamente por Django.

---

## Persistencia

La base de datos utilizada actualmente es PostgreSQL.

La configuración de conexión se realiza mediante variables de entorno definidas en el archivo `.env`.

La creación y evolución del esquema se gestiona mediante las migraciones de Django:

```cmd
python manage.py migrate
```

La carga inicial de los datos del proyecto se realiza mediante:

```cmd
python load_data_postgres.py
```