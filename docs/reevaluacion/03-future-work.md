# Trabajo futuro

> Mejoras realistas sobre el producto actual, ordenadas por prioridad, con su relación con los Objetivos de Desarrollo Sostenible (ODS). El Charter y el PMP ya alineaban el proyecto con los ODS 9 y 11.

## ODS de referencia

| ODS | Relación con la Casa de la Cultura |
|---|---|
| **4 · Educación de calidad** | Acercar la lectura y la cultura a todos los vecinos, recomendando a cada lector su siguiente libro. |
| **9 · Industria, innovación e infraestructura** | Digitalizar un servicio público con software libre y reutilizar el equipo que ya tiene el ayuntamiento. |
| **11 · Ciudades y comunidades sostenibles** | Un servicio cultural municipal accesible, reutilizable por otros ayuntamientos y bibliotecas. |

## Mejoras propuestas

| # | Mejora | Valor | ODS | Origen |
|---|---|---|---|---|
| 1 | **Instalador para el PC de la sala** con PostgreSQL en modo portable, Python incluido y la base de datos ya cargada, sin conexión a internet. | Es el paso que falta para usarlo en la sala sin personal técnico. | 9, 11 | Requisito del cliente (Charter RNF-01, RNF-02); alcance negativo AN-09 |
| 2 | **Actualización periódica de las recomendaciones**: regenerar las reglas automáticamente (por ejemplo, cada noche) a medida que se registran valoraciones nuevas. | Las recomendaciones aprenden de los gustos actuales sin intervención técnica. | 4 | Las valoraciones ya se guardan en la base de datos |
| 3 | **Recomendador híbrido** para los libros poco leídos (el 91 % del catálogo no tiene reglas): combinar Apriori con similitud por género y autor, y valorar FP-Growth, que encuentra los mismos conjuntos frecuentes con menos coste, para bajar el soporte mínimo. | Más libros del fondo llegan a los lectores, no solo los superventas. | 4 | Limitación medida del recomendador actual |
| 4 | **Portadas sin conexión**: descargar una vez las ~6.700 portadas disponibles (~67 MB) y servirlas desde el propio equipo. | Catálogo más atractivo para el público. | 4 | El cliente da mucha importancia a lo visual (S2, min 25) |
| 5 | **Gestión de usuarios y del catálogo**: alta de lectores y libros desde la aplicación en lugar de los Excel, con roles para el personal. | Mantenimiento sin herramientas externas. | 9 | El cliente lo plantea *"dentro de uno o dos años"* (S5, min 17) |
| 6 | **Calidad de datos en origen**: corregir títulos con caracteres mal escapados y encadenar el ETL dentro de la base de datos (ficheros originales → tablas de origen → limpieza → tablas finales). | Trazabilidad completa del dato y menos errores visibles. | 9 | Limitaciones detectadas en la reevaluación |
| 7 | **Adaptación legal y accesibilidad**: revisión RGPD y pautas de accesibilidad web (contraste, lectura fácil). | Requisito para un servicio público y para llegar a más vecinos. | 4, 11 | El cliente la pospone a siguientes iteraciones (S2, min 38) |
| 8 | **Reutilización por otros organismos**: documentar la instalación y la carga de datos de otra biblioteca. | Lo que pidió el cliente: poder ofrecer la solución a otros ayuntamientos. | 11 | S2, min 21; Charter |
