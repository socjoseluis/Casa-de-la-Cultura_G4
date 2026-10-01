"""
Estadísticas del catálogo y del recomendador para el dashboard.

Las cifras agregadas sobre las valoraciones se leen de vistas materializadas
(migración 0006), que hay que refrescar cuando cambian los datos.
"""

import time

from django.db import connection


VISTAS = (
    "estadisticas_libro",
    "estadisticas_genero",
    "distribucion_valoraciones",
)


def refrescar_estadisticas():
    """
    Recalcula las vistas materializadas a partir de las tablas actuales.

    @post las vistas reflejan todas las valoraciones guardadas
    @return dict {vista: segundos que ha tardado}

    CONCURRENTLY permite seguir consultando las vistas mientras se refrescan.
    """
    tiempos = {}
    with connection.cursor() as cursor:
        for vista in VISTAS:
            inicio = time.monotonic()
            cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {vista}")
            tiempos[vista] = time.monotonic() - inicio
    return tiempos


def _filas(sql, parametros=None):
    """Ejecuta una consulta y devuelve las filas como lista de dicts."""
    with connection.cursor() as cursor:
        cursor.execute(sql, parametros or [])
        columnas = [c[0] for c in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def resumen_catalogo():
    """Cifras clave: libros, ejemplares, lectores, valoraciones y nota media."""
    return _filas(
        """
        SELECT
            (SELECT count(*) FROM app_book) AS libros,
            (SELECT count(*) FROM app_copy) AS ejemplares,
            (SELECT count(*) FROM app_libraryuser) AS lectores,
            (SELECT sum(total) FROM distribucion_valoraciones) AS valoraciones,
            (SELECT round(sum(rating * total)::numeric / sum(total), 2)
             FROM distribucion_valoraciones) AS nota_media
        """
    )[0]


def distribucion_valoraciones():
    """Número de valoraciones de 1 a 5 estrellas."""
    return _filas("SELECT rating, total FROM distribucion_valoraciones ORDER BY rating")


def gustos_por_genero(limite=15):
    """Géneros ordenados por valoraciones positivas (4-5 estrellas)."""
    return _filas(
        """
        SELECT genero, libros, valoraciones, valoraciones_positivas, nota_media
        FROM estadisticas_genero
        WHERE valoraciones > 0
        ORDER BY valoraciones_positivas DESC
        LIMIT %s
        """,
        [limite],
    )


def libros_mas_leidos(limite=10):
    """Libros con más valoraciones."""
    return _filas(
        """
        SELECT b.title, e.votos, e.nota_media
        FROM estadisticas_libro e
        JOIN app_book b ON b.id = e.book_id
        ORDER BY e.votos DESC
        LIMIT %s
        """,
        [limite],
    )


def libros_mejor_valorados(limite=10, min_votos=1000):
    """Libros con mejor nota media entre los que tienen al menos min_votos."""
    return _filas(
        """
        SELECT b.title, e.votos, e.nota_media
        FROM estadisticas_libro e
        JOIN app_book b ON b.id = e.book_id
        WHERE e.votos >= %s
        ORDER BY e.nota_media DESC, e.votos DESC
        LIMIT %s
        """,
        [min_votos, limite],
    )


def ejecucion_apriori_activa():
    """Configuración y resultados de la ejecución de Apriori que usa la app."""
    filas = _filas(
        """
        SELECT
            id, started_at, finished_at, min_rating, min_support,
            min_confidence, min_lift, max_len, transactions_count,
            rules_count, books_with_rules_count, covered_users_count,
            (SELECT count(*) FROM app_book) AS total_libros,
            (SELECT count(*) FROM app_libraryuser) AS total_lectores
        FROM app_apriorirun
        WHERE is_active
        """
    )
    return filas[0] if filas else None


def reglas_mas_fuertes(limite=10):
    """
    Reglas de la ejecución activa con mayor lift, con sus libros recomendados.

    Se toma la mejor regla de cada libro antecedente (DISTINCT ON) para que
    una sola saga no ocupe todo el ranking.
    """
    return _filas(
        """
        WITH mejor_por_libro AS (
            -- La regla con mayor lift de cada libro antecedente...
            SELECT DISTINCT ON (ar.source_book_id)
                ar.id, ar.source_book_id, ar.support, ar.confidence, ar.lift
            FROM app_associationrule ar
            JOIN app_apriorirun run ON run.id = ar.run_id AND run.is_active
            ORDER BY ar.source_book_id, ar.lift DESC
        ),
        top AS (
            -- ...y de ellas, las n con mayor lift.
            SELECT * FROM mejor_por_libro
            ORDER BY lift DESC
            LIMIT %s
        )
        -- ...y después sus libros, en vez de agrupar todas las reglas.
        SELECT
            sb.title AS antecedente,
            string_agg(tb.title, ' · ' ORDER BY tb.title) AS consecuente,
            top.support, top.confidence, top.lift
        FROM top
        JOIN app_book sb ON sb.id = top.source_book_id
        JOIN app_associationruletarget t ON t.rule_id = top.id
        JOIN app_book tb ON tb.id = t.book_id
        GROUP BY top.id, sb.title, top.support, top.confidence, top.lift
        ORDER BY top.lift DESC
        """,
        [limite],
    )
