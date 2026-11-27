"""Modelos propios del microservicio de Catálogo Bibliográfico.

Se conservan nombres de tablas e identificadores del monolito para facilitar
la importación controlada de los datos históricos en CATA03.
No hay relaciones ORM con Identidad ni Circulación.
"""

from django.db import models


class Autor(models.Model):
    autor_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    nacionalidad = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "biblioteca_autor"

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    categoria_id = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "biblioteca_categoria"

    def __str__(self):
        return self.nombre_categoria


class Libro(models.Model):
    libro_id = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=100)
    isbn = models.CharField(max_length=13, unique=True)
    fecha_publicacion = models.DateField(null=True, blank=True)

    autores = models.ManyToManyField(Autor, through="LibroAutor")
    categorias = models.ManyToManyField(Categoria, through="CategoriaLibro")

    class Meta:
        db_table = "biblioteca_libro"

    def __str__(self):
        return self.titulo


class LibroAutor(models.Model):
    autor = models.ForeignKey(Autor, on_delete=models.CASCADE, db_column="autor_id")
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, db_column="libro_id")

    class Meta:
        db_table = "biblioteca_libros_autores"
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "autor"],
                name="unique_libro_autor",
            ),
        ]


class CategoriaLibro(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, db_column="categoria_id"
    )
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, db_column="libro_id")

    class Meta:
        db_table = "biblioteca_categoria_libros"
        constraints = [
            models.UniqueConstraint(
                fields=["libro", "categoria"],
                name="unique_libro_categoria",
            ),
        ]
