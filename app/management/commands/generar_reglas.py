"""
Genera las reglas de recomendación con el algoritmo Apriori y las guarda
en PostgreSQL.

Uso:
    python manage.py generar_reglas
    python manage.py generar_reglas --min-rating 4 --soporte 0.01 \
        --confianza 0.3 --lift 1 --max-len 3

Flujo (salida del algoritmo -> entrada de la base de datos):

1. Transacciones: para cada usuario, el conjunto de libros que valoró con
   al menos --min-rating estrellas (un libro "que le gustó").
2. Apriori (mlxtend) obtiene los conjuntos de libros frecuentes, es decir,
   los que aparecen juntos en al menos --soporte de las transacciones.
3. De ellos se generan reglas "libro A => {libros}" con un único libro en
   el antecedente, filtradas por confianza y lift.
4. Se guardan en AprioriRun (configuración y estadísticas), AssociationRule
   (antecedente y métricas) y AssociationRuleTarget (libros del
   consecuente). La nueva ejecución queda como la activa.

Los valores por defecto salen del estudio de parámetros: con valoración >= 4,
soporte 1 %, confianza 30 % y max_len 3 se obtienen ~16.000 reglas en
~1,5 minutos y ~1 GB de RAM, y el 80 % de los 1.000 libros más leídos tiene
alguna regla. low_memory=True es imprescindible: sin él, la misma ejecución
necesita decenas de GB.
"""

import time

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from mlxtend.frequent_patterns import apriori, association_rules

from app.models import AprioriRun, AssociationRule, AssociationRuleTarget


class Command(BaseCommand):
    help = "Genera reglas de asociación libro => libros con Apriori y las guarda en la BBDD."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-rating", type=int, default=4,
            help="Valoración mínima para considerar que un libro gustó (1-5).",
        )
        parser.add_argument(
            "--soporte", type=float, default=0.01,
            help="Soporte mínimo: fracción de usuarios que comparten el conjunto.",
        )
        parser.add_argument(
            "--confianza", type=float, default=0.3,
            help="Confianza mínima de la regla.",
        )
        parser.add_argument(
            "--lift", type=float, default=1.0,
            help="Lift mínimo de la regla.",
        )
        parser.add_argument(
            "--max-len", type=int, default=3,
            help="Tamaño máximo de los conjuntos (3 permite reglas A => {B, C}).",
        )

    def handle(self, *args, **opciones):
        min_rating = opciones["min_rating"]
        soporte = opciones["soporte"]
        confianza = opciones["confianza"]
        min_lift = opciones["lift"]
        max_len = opciones["max_len"]

        if not 1 <= min_rating <= 5:
            raise CommandError("--min-rating debe estar entre 1 y 5.")
        if not 0 < soporte <= 1 or not 0 <= confianza <= 1:
            raise CommandError("--soporte y --confianza deben estar entre 0 y 1.")
        if min_lift < 0 or max_len < 2:
            raise CommandError("--lift debe ser >= 0 y --max-len >= 2.")

        inicio = time.monotonic()

        run = AprioriRun.objects.create(
            min_support=soporte,
            min_confidence=confianza,
            min_lift=min_lift,
            min_rating=min_rating,
            max_len=max_len,
        )
        self.stdout.write(
            f"Ejecución Apriori #{run.id}: valoración >= {min_rating}, "
            f"soporte {soporte}, confianza {confianza}, lift >= {min_lift}, "
            f"max_len {max_len}"
        )

        try:
            transacciones, n_transacciones = self.cargar_transacciones(min_rating, soporte)
            reglas = self.ejecutar_apriori(transacciones, n_transacciones, soporte, confianza, min_lift, max_len)

            if reglas.empty:
                raise CommandError(
                    "No se ha generado ninguna regla con esta configuración. "
                    "Se mantiene la ejecución activa anterior. "
                    "Prueba con un soporte o una confianza más bajos."
                )

            cobertura = self.calcular_cobertura(transacciones, reglas)
            self.guardar_reglas(run, reglas, n_transacciones, cobertura)
        except BaseException:
            # Una ejecución fallida o interrumpida (Ctrl+C) no debe quedar a
            # medias en la BBDD.
            run.delete()
            raise

        self.stdout.write(self.style.SUCCESS(
            f"Ejecución #{run.id} activa: {run.rules_count} reglas guardadas "
            f"en {time.monotonic() - inicio:.1f} s."
        ))
        self.mostrar_ejemplos(run)

    def cargar_transacciones(self, min_rating, soporte):
        """
        Construye la matriz usuario x libro (True si al usuario le gustó).

        @pre  las tablas de valoraciones, ejemplares y libros están cargadas
        @return (DataFrame booleano con columnas = id de Book, nº de transacciones)

        Solo se incluyen como columnas los libros que por sí solos superan
        el soporte mínimo: es el primer paso de Apriori (un conjunto no puede
        ser frecuente si alguno de sus libros no lo es) y reduce la memoria.
        """
        t = time.monotonic()
        # Paso 1. Entrada desde PostgreSQL: los libros que cada lector valoró
        # con 4 o 5 estrellas (--min-rating). Cada lector es una "cesta".
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT r.user_id, c.book_id
                FROM app_rating r
                JOIN app_copy c ON c.id = r.copy_id
                WHERE r.rating >= %s
                """,
                [min_rating],
            )
            pares = np.array(cursor.fetchall(), dtype=np.int64)

        if len(pares) == 0:
            raise CommandError("No hay valoraciones que cumplan la valoración mínima.")

        usuarios, fila = np.unique(pares[:, 0], return_inverse=True)
        libros, columna = np.unique(pares[:, 1], return_inverse=True)
        n_transacciones = len(usuarios)

        frecuencia = np.bincount(columna, minlength=len(libros)) / n_transacciones
        frecuentes = np.where(frecuencia >= soporte)[0]

        nueva_columna = np.full(len(libros), -1)
        nueva_columna[frecuentes] = np.arange(len(frecuentes))
        mascara = nueva_columna[columna] >= 0

        if len(frecuentes) == 0:
            raise CommandError(
                f"Ningún libro alcanza el soporte {soporte}. "
                "Prueba con un soporte más bajo."
            )

        matriz = np.zeros((n_transacciones, len(frecuentes)), dtype=bool)
        matriz[fila[mascara], nueva_columna[columna[mascara]]] = True

        self.stdout.write(
            f"Transacciones: {n_transacciones} usuarios, "
            f"{len(libros)} libros valorados, {len(frecuentes)} libros frecuentes "
            f"({time.monotonic() - t:.1f} s)"
        )
        return pd.DataFrame(matriz, columns=libros[frecuentes]), n_transacciones

    def ejecutar_apriori(self, transacciones, n_transacciones, soporte, confianza, min_lift, max_len):
        """
        Ejecuta Apriori y genera las reglas con un único libro antecedente.

        @return DataFrame de reglas (antecedents, consequents, support,
                confidence, lift), ordenado por lift descendente
        """
        t = time.monotonic()
        # Paso 2. Apriori busca los grupos de libros que gustan juntos a muchos
        # lectores: soporte mínimo (1 % por defecto), grupos de hasta max_len
        # libros y low_memory para no pasar de ~1 GB de RAM (sin él, 28 GB).
        conjuntos = apriori(
            transacciones,
            min_support=soporte,
            use_colnames=True,
            max_len=max_len,
            low_memory=True,
        )
        self.stdout.write(
            f"Apriori: {len(conjuntos)} conjuntos frecuentes "
            f"({time.monotonic() - t:.1f} s)"
        )

        if conjuntos.empty:
            return pd.DataFrame(columns=["antecedents", "consequents", "support", "confidence", "lift"])

        t = time.monotonic()
        # Paso 3. De esos grupos salen las reglas "si te gusta A, te gustan B
        # (y C)" que superan la confianza mínima (30 % por defecto).
        reglas = association_rules(
            conjuntos,
            num_itemsets=n_transacciones,
            metric="confidence",
            min_threshold=confianza,
        )
        # Paso 4. Solo reglas con un libro de partida y lift >= 1: más
        # frecuentes de lo que saldría por casualidad.
        reglas = reglas[
            (reglas["antecedents"].apply(len) == 1)
            & (reglas["lift"] >= min_lift)
        ].sort_values("lift", ascending=False)

        self.stdout.write(
            f"Reglas libro => libros: {len(reglas)} "
            f"({time.monotonic() - t:.1f} s)"
        )
        return reglas

    def calcular_cobertura(self, transacciones, reglas):
        """
        Mide a cuántos libros y lectores llegan las reglas.

        @return (libros con alguna regla como antecedente,
                 lectores a los que les gustó al menos uno de esos libros)

        Los antecedentes son siempre libros frecuentes, así que son columnas
        de la matriz de transacciones.
        """
        antecedentes = list({next(iter(a)) for a in reglas["antecedents"]})
        lectores = int(transacciones[antecedentes].any(axis=1).sum())

        self.stdout.write(
            f"Cobertura: {len(antecedentes)} libros con reglas, "
            f"{lectores} de {len(transacciones)} lectores "
            f"({lectores / len(transacciones):.1%}) pueden recibir recomendaciones por reglas"
        )
        return len(antecedentes), lectores

    # Paso 5. Salida del algoritmo -> entrada en PostgreSQL. Todo en una
    # transacción: si algo falla, no se guarda nada y sigue la ejecución anterior.
    @transaction.atomic
    def guardar_reglas(self, run, reglas, n_transacciones, cobertura):
        """
        Persiste las reglas, la cobertura y activa la ejecución.

        @post existe una única AprioriRun activa: esta
        """
        t = time.monotonic()

        # Cada regla: libro de partida, soporte, confianza y lift.
        objetos = [
            AssociationRule(
                run=run,
                source_book_id=int(next(iter(fila.antecedents))),
                support=float(fila.support),
                confidence=float(fila.confidence),
                lift=float(fila.lift),
            )
            for fila in reglas.itertuples()
        ]
        # En PostgreSQL bulk_create devuelve los objetos con su id.
        objetos = AssociationRule.objects.bulk_create(objetos, batch_size=5000)

        # Los libros recomendados de cada regla.
        destinos = [
            AssociationRuleTarget(rule=regla, book_id=int(libro))
            for regla, consecuente in zip(objetos, reglas["consequents"])
            for libro in consecuente
        ]
        AssociationRuleTarget.objects.bulk_create(destinos, batch_size=5000)

        # Esta ejecución pasa a ser la activa; la anterior queda como historial.
        AprioriRun.objects.filter(is_active=True).update(is_active=False)
        run.finished_at = timezone.now()
        run.transactions_count = n_transacciones
        run.rules_count = len(objetos)
        run.books_with_rules_count, run.covered_users_count = cobertura
        run.is_active = True
        run.save()

        self.stdout.write(
            f"Guardado en PostgreSQL: {len(objetos)} reglas y "
            f"{len(destinos)} libros recomendados ({time.monotonic() - t:.1f} s)"
        )

    def mostrar_ejemplos(self, run, cuantas=5):
        """Muestra las reglas con mayor lift, ya leídas de la BBDD."""
        reglas = (
            AssociationRule.objects.filter(run=run)
            .select_related("source_book")
            .prefetch_related("targets__book")
            .order_by("-lift")[:cuantas]
        )
        if not reglas:
            return

        self.stdout.write("")
        self.stdout.write("Reglas con mayor lift (leídas de la BBDD):")
        for regla in reglas:
            consecuente = ", ".join(t.book.title for t in regla.targets.all())
            self.stdout.write(
                f"  {regla.source_book.title}  =>  [{consecuente}]\n"
                f"      soporte {regla.support:.3f} · confianza {regla.confidence:.2f} · lift {regla.lift:.2f}"
            )
