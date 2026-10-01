"""
Vistas materializadas para el dashboard.

Las consultas del dashboard resumen los ~6 millones de valoraciones (votos y
nota media por libro, por género y por estrellas) y tardan ~0,2-0,9 s cada una
aunque haya índices, porque tienen que recorrer la tabla entera; un índice
cubriente sobre app_rating no las mejora. Se precalculan en vistas
materializadas indexadas: el dashboard lee unas pocas filas en milisegundos y
las vistas se refrescan (python manage.py refrescar_estadisticas) al cargar los
datos y al registrar una valoración.

Cada vista tiene un índice único para poder refrescarla con
REFRESH MATERIALIZED VIEW CONCURRENTLY, que no bloquea las lecturas.
"""

from django.db import migrations


CREAR = """
-- Votos y nota media por libro.
CREATE MATERIALIZED VIEW estadisticas_libro AS
SELECT
    c.book_id,
    count(*)::integer AS votos,
    round(avg(r.rating)::numeric, 2) AS nota_media
FROM app_rating r
JOIN app_copy c ON c.id = r.copy_id
GROUP BY c.book_id;

CREATE UNIQUE INDEX estadisticas_libro_book_id_uniq ON estadisticas_libro (book_id);
-- Libros más leídos (ORDER BY votos DESC LIMIT n).
CREATE INDEX estadisticas_libro_votos_idx ON estadisticas_libro (votos DESC);
-- Libros mejor valorados (ORDER BY nota_media DESC con un mínimo de votos).
CREATE INDEX estadisticas_libro_nota_idx ON estadisticas_libro (nota_media DESC, votos DESC);


-- Libros, valoraciones y nota media por género (gustos de los lectores).
CREATE MATERIALIZED VIEW estadisticas_genero AS
SELECT
    g.id AS genre_id,
    g.name AS genero,
    coalesce(l.libros, 0)::integer AS libros,
    coalesce(v.valoraciones, 0)::integer AS valoraciones,
    coalesce(v.positivas, 0)::integer AS valoraciones_positivas,
    v.nota_media
FROM app_genre g
LEFT JOIN (
    SELECT genre_id, count(*) AS libros
    FROM app_book_genres
    GROUP BY genre_id
) l ON l.genre_id = g.id
LEFT JOIN (
    SELECT
        bg.genre_id,
        count(*) AS valoraciones,
        count(*) FILTER (WHERE r.rating >= 4) AS positivas,
        round(avg(r.rating)::numeric, 2) AS nota_media
    FROM app_rating r
    JOIN app_copy c ON c.id = r.copy_id
    JOIN app_book_genres bg ON bg.book_id = c.book_id
    GROUP BY bg.genre_id
) v ON v.genre_id = g.id;

CREATE UNIQUE INDEX estadisticas_genero_genre_id_uniq ON estadisticas_genero (genre_id);


-- Número de valoraciones de cada puntuación (1 a 5 estrellas).
CREATE MATERIALIZED VIEW distribucion_valoraciones AS
SELECT rating, count(*)::integer AS total
FROM app_rating
GROUP BY rating;

CREATE UNIQUE INDEX distribucion_valoraciones_rating_uniq ON distribucion_valoraciones (rating);
"""

BORRAR = """
DROP MATERIALIZED VIEW IF EXISTS distribucion_valoraciones;
DROP MATERIALIZED VIEW IF EXISTS estadisticas_genero;
DROP MATERIALIZED VIEW IF EXISTS estadisticas_libro;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_quitar_indices_duplicados_y_cobertura_apriori'),
    ]

    operations = [
        migrations.RunSQL(CREAR, reverse_sql=BORRAR),
    ]
