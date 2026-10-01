"""
Genera los diagramas entidad-relación de la base de datos con Graphviz.

Uso (desde la raíz del proyecto, requiere el programa `dot` de Graphviz):
    python docs/reevaluacion/diagramas/generar_diagramas.py

Notación UML, como en la cápsula de diagramas E-R de la asignatura: clases
con sus atributos, clave primaria subrayada y asociaciones con multiplicidad.

Diagramas:
  1-completo        todas las tablas de PostgreSQL con todas sus columnas
  2-general         modelo conceptual sin atributos, por zonas
  3-catalogo        libros, autores, géneros y ejemplares
  4-lectores        lectores y valoraciones (clase asociativa)
  5-recomendador    ejecuciones de Apriori y reglas libro => libros
"""

import subprocess
from pathlib import Path

CARPETA = Path(__file__).resolve().parent

# Colores de cada zona (fondo de la cabecera de la clase).
ZONAS = {
    "catalogo": ("#e7eef8", "Catálogo"),
    "lectores": ("#e8f3e9", "Lectores y valoraciones"),
    "recomendador": ("#f7e7e9", "Recomendador (Apriori)"),
}
TINTA = "#2c2825"
TENUE = "#6e6459"
LINEA = "#6e6459"

# Tablas físicas de PostgreSQL. Atributo: (nombre, tipo, marca)
# marca: "pk" subrayado, "fk" clave foránea, "uq" único, "" normal; "?" = admite NULL.
TABLAS = {
    "Book": ("catalogo", [
        ("id", "bigint", "pk"), ("book_id", "integer", "uq"), ("title", "varchar", ""),
        ("original_title", "varchar ?", ""), ("isbn", "varchar ?", ""),
        ("publication_year", "integer ?", ""), ("language_code", "varchar ?", ""),
        ("image_url", "varchar ?", ""),
    ]),
    "Author": ("catalogo", [("id", "bigint", "pk"), ("name", "varchar", "")]),
    "Genre": ("catalogo", [("id", "bigint", "pk"), ("name", "varchar", "uq")]),
    "Book_authors": ("catalogo", [("id", "bigint", "pk"), ("book_id", "bigint", "fk"), ("author_id", "bigint", "fk")]),
    "Book_genres": ("catalogo", [("id", "bigint", "pk"), ("book_id", "bigint", "fk"), ("genre_id", "bigint", "fk")]),
    "Copy": ("catalogo", [
        ("id", "bigint", "pk"), ("copy_id", "integer", "uq"), ("book_id", "bigint", "fk"), ("available", "boolean", ""),
    ]),
    "LibraryUser": ("lectores", [
        ("id", "bigint", "pk"), ("user_id", "integer", "uq"), ("birth_date", "date ?", ""), ("comment", "text ?", ""),
    ]),
    "Rating": ("lectores", [
        ("id", "bigint", "pk"), ("user_id", "bigint", "fk"), ("copy_id", "bigint", "fk"),
        ("rating", "integer (1-5)", ""), ("created_at", "timestamptz", ""),
    ]),
    "AprioriRun": ("recomendador", [
        ("id", "bigint", "pk"), ("started_at", "timestamptz", ""), ("finished_at", "timestamptz ?", ""),
        ("min_rating", "integer", ""), ("min_support", "float", ""), ("min_confidence", "float", ""),
        ("min_lift", "float", ""), ("max_len", "integer", ""), ("is_active", "boolean", ""),
        ("transactions_count", "integer ?", ""), ("rules_count", "integer ?", ""),
        ("books_with_rules_count", "integer ?", ""), ("covered_users_count", "integer ?", ""),
    ]),
    "AssociationRule": ("recomendador", [
        ("id", "bigint", "pk"), ("run_id", "bigint", "fk"), ("source_book_id", "bigint", "fk"),
        ("support", "float", ""), ("confidence", "float", ""), ("lift", "float", ""), ("created_at", "timestamptz", ""),
    ]),
    "AssociationRuleTarget": ("recomendador", [
        ("id", "bigint", "pk"), ("rule_id", "bigint", "fk"), ("book_id", "bigint", "fk"),
    ]),
}

# Relaciones físicas: (origen con la FK, destino, mult. origen, mult. destino, etiqueta)
RELACIONES_FISICAS = [
    ("Book_authors", "Book", "*", "1", ""),
    ("Book_authors", "Author", "*", "1", ""),
    ("Book_genres", "Book", "*", "1", ""),
    ("Book_genres", "Genre", "*", "1", ""),
    ("Copy", "Book", "1..*", "1", ""),
    ("Rating", "LibraryUser", "*", "1", ""),
    ("Rating", "Copy", "*", "1", ""),
    ("AssociationRule", "AprioriRun", "*", "1", ""),
    ("AssociationRule", "Book", "*", "1", ""),
    ("AssociationRuleTarget", "AssociationRule", "1..2", "1", ""),
    ("AssociationRuleTarget", "Book", "*", "1", ""),
]

# Modelo conceptual: atributos sin claves foráneas (las representan las asociaciones).
CONCEPTUAL = {
    "Book": ["id", "book_id", "title", "original_title", "isbn", "publication_year", "language_code", "image_url"],
    "Author": ["id", "name"],
    "Genre": ["id", "name"],
    "Copy": ["id", "copy_id", "available"],
    "LibraryUser": ["id", "user_id", "birth_date", "comment"],
    "Rating": ["id", "rating", "created_at"],
    "AprioriRun": ["id", "started_at", "finished_at", "min_rating", "min_support", "min_confidence",
                   "min_lift", "max_len", "is_active", "transactions_count", "rules_count",
                   "books_with_rules_count", "covered_users_count"],
    "AssociationRule": ["id", "support", "confidence", "lift", "created_at"],
}

# Asociaciones conceptuales: (A, B, mult. en A, mult. en B, nombre)
ASOCIACIONES = {
    "catalogo": [
        ("Book", "Author", "*", "1..*", "escrito por"),
        ("Book", "Genre", "*", "1..3", "clasificado en"),
        ("Book", "Copy", "1", "1..*", "tiene"),
    ],
    "recomendador": [
        ("AprioriRun", "AssociationRule", "1", "*", "genera"),
        ("AssociationRule", "Book", "*", "1", "antecedente\n(si te gusta)"),
        ("AssociationRule", "Book", "*", "1..2", "consecuente\n(te gustan)"),
    ],
}


def tipo_de(tabla, atributo):
    return next(t for n, t, _ in TABLAS[tabla][1] if n == atributo)


def marca_de(tabla, atributo):
    return next(m for n, _, m in TABLAS[tabla][1] if n == atributo)


def clase(nombre, atributos=None, fisica=False):
    """Nodo con forma de clase UML (tabla HTML de Graphviz)."""
    zona = TABLAS[nombre][0]
    color = ZONAS[zona][0]
    filas = [f'<TR><TD BGCOLOR="{color}"><B>{nombre}</B></TD></TR>']
    if atributos is not None:
        lineas = []
        for atributo in atributos:
            tipo = tipo_de(nombre, atributo)
            marca = marca_de(nombre, atributo)
            texto = atributo
            if marca == "pk":
                texto = f"<U>{texto}</U>"
            sufijo = {"fk": " (FK)", "uq": " (único)"}.get(marca, "")
            lineas.append(f'{texto}<FONT COLOR="{TENUE}">: {tipo}{sufijo}</FONT>')
        filas.append(f'<TR><TD ALIGN="LEFT" BALIGN="LEFT">{"<BR/>".join(lineas)}</TD></TR>')
    tabla = (
        f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6" COLOR="{LINEA}">'
        + "".join(filas) + "</TABLE>>"
    )
    return f'  "{nombre}" [label={tabla}];'


def cabecera(nombre, horizontal=True, separacion="0.9"):
    return [
        f'digraph "{nombre}" {{',
        f'  graph [rankdir={"LR" if horizontal else "TB"}, bgcolor="white", nodesep=0.6, ranksep={separacion}, pad=0.3,',
        f'         fontname="Helvetica", fontsize=16, fontcolor="{TINTA}"];',
        f'  node [shape=plain, fontname="Helvetica", fontsize=12, fontcolor="{TINTA}"];',
        f'  edge [arrowhead=none, color="{LINEA}", penwidth=1.3, fontname="Helvetica", fontsize=11,',
        f'        fontcolor="{TINTA}", labelfontsize=12, labelfontcolor="{TINTA}", labeldistance=1.6];',
    ]


def asociacion(a, b, ma, mb, nombre=""):
    etiqueta = f', label="{nombre}"' if nombre else ""
    return f'  "{a}" -> "{b}" [taillabel="{ma}", headlabel="{mb}"{etiqueta}];'


def leyenda(con_clave=True):
    filas = "".join(
        f'<TR><TD BGCOLOR="{color}" WIDTH="18"></TD><TD ALIGN="LEFT">{texto}</TD></TR>'
        for color, texto in ZONAS.values()
    )
    return (
        '  leyenda [label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4">'
        + filas
        + (f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT COLOR="{TENUE}"><U>subrayado</U> = clave primaria</FONT></TD></TR>' if con_clave else '')
        + '</TABLE>>];'
    )


def diagrama_completo():
    lineas = cabecera("completo", horizontal=True, separacion="1.1")
    lineas.append('  label="Base de datos completa (PostgreSQL)"; labelloc=t;')
    for nombre, (_, atributos) in TABLAS.items():
        lineas.append(clase(nombre, [a for a, _, _ in atributos], fisica=True))
    for origen, destino, mo, md, etiqueta in RELACIONES_FISICAS:
        lineas.append(asociacion(origen, destino, mo, md, etiqueta))
    lineas.append(leyenda())
    return lineas + ["}"]


def diagrama_general():
    lineas = cabecera("general", horizontal=True, separacion="1.2")
    lineas.append('  label="Modelo conceptual"; labelloc=t;')
    for nombre in CONCEPTUAL:
        lineas.append(clase(nombre))
    for a, b, ma, mb, n in ASOCIACIONES["catalogo"] + ASOCIACIONES["recomendador"]:
        lineas.append(asociacion(a, b, ma, mb, n.split("\n")[0]))
    lineas += [
        '  ratingpunto [shape=point, width=0.05, color="#6e6459"];',
        '  "LibraryUser" -> ratingpunto [taillabel="*"];',
        '  ratingpunto -> "Copy" [headlabel="*", label="valora"];',
        '  ratingpunto -> "Rating" [style=dashed];',
        leyenda(con_clave=False),
    ]
    return lineas + ["}"]


def diagrama_catalogo():
    lineas = cabecera("catalogo", horizontal=True)
    lineas.append('  label="Catálogo"; labelloc=t;')
    for nombre in ("Book", "Author", "Genre", "Copy"):
        lineas.append(clase(nombre, CONCEPTUAL[nombre]))
    for a, b, ma, mb, n in ASOCIACIONES["catalogo"]:
        lineas.append(asociacion(a, b, ma, mb, n))
    return lineas + ["}"]


def diagrama_lectores():
    lineas = cabecera("lectores", horizontal=True, separacion="1.4")
    lineas.append('  label="Lectores y valoraciones"; labelloc=t;')
    for nombre in ("LibraryUser", "Copy", "Rating"):
        lineas.append(clase(nombre, CONCEPTUAL[nombre]))
    lineas += [
        '  ratingpunto [shape=point, width=0.05, color="#6e6459"];',
        '  { rank=same; ratingpunto; "Rating"; }',
        '  "LibraryUser" -> ratingpunto [taillabel="*"];',
        '  ratingpunto -> "Copy" [headlabel="*", label="valora"];',
        '  ratingpunto -> "Rating" [style=dashed, constraint=false];',
    ]
    return lineas + ["}"]


def diagrama_recomendador():
    lineas = cabecera("recomendador", horizontal=True, separacion="1.4")
    lineas.append('  label="Recomendador (Apriori)"; labelloc=t;')
    lineas.append(clase("AprioriRun", CONCEPTUAL["AprioriRun"]))
    lineas.append(clase("AssociationRule", CONCEPTUAL["AssociationRule"]))
    lineas.append(clase("Book", ["id", "book_id", "title"]))
    for a, b, ma, mb, n in ASOCIACIONES["recomendador"]:
        lineas.append(asociacion(a, b, ma, mb, n))
    return lineas + ["}"]


DIAGRAMAS = {
    "1-completo": diagrama_completo,
    "2-general": diagrama_general,
    "3-catalogo": diagrama_catalogo,
    "4-lectores": diagrama_lectores,
    "5-recomendador": diagrama_recomendador,
}


if __name__ == "__main__":
    for nombre, funcion in DIAGRAMAS.items():
        fuente = CARPETA / f"{nombre}.dot"
        fuente.write_text("\n".join(funcion()) + "\n", encoding="utf-8")
        for formato in ("svg", "png"):
            opciones = ["-Gdpi=200"] if formato == "png" else []
            subprocess.run(
                ["dot", f"-T{formato}", *opciones, str(fuente), "-o", str(CARPETA / f"{nombre}.{formato}")],
                check=True,
            )
        print(f"{nombre}: .dot, .svg y .png")
