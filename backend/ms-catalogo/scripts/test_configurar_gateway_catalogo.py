"""Pruebas sin Docker ni Django para la inserción segura de rutas Nginx."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).with_name("configurar_gateway_catalogo.py")
spec = importlib.util.spec_from_file_location("cata08", HERE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

BASE = """server {
    listen 8000;
    location ^~ /api/internal/ { return 404; }
    location /api/ {
        proxy_pass http://ms-identidad:8000;
        proxy_set_header Host $host;
    }
    location / { return 404; }
}
"""


class GatewayTests(unittest.TestCase):
    def test_inserta_las_cuatro_rutas_sin_cambiar_identidad(self):
        generado = app.integrar(BASE)
        self.assertIn("proxy_pass http://ms-identidad:8000;", generado)
        self.assertIn("location ^~ /api/internal/ { return 404; }", generado)
        for nombre in app.ROUTES:
            self.assertIn(f"location ^~ /api/{nombre}/", generado)
            self.assertIn(f"location = /api/{nombre}", generado)
        self.assertEqual(generado.count("proxy_pass http://ms-catalogo:8000;"), 4)

    def test_no_agrega_rutas_internas_a_catalogo(self):
        generado = app.integrar(BASE)
        self.assertNotIn("proxy_pass http://ms-catalogo:8000/api/internal", generado)
        self.assertIn('proxy_set_header X-Internal-Service-Key "";', generado)

    def test_conserva_uri_sin_reescribir_sufijos(self):
        generado = app.integrar(BASE)
        self.assertNotIn("proxy_pass http://ms-catalogo:8000/;", generado)
        self.assertIn("proxy_pass http://ms-catalogo:8000;", generado)

    def test_idempotente(self):
        first = app.integrar(BASE)
        self.assertEqual(app.integrar(first), first)

    def test_rechaza_colision_con_otro_integrante(self):
        con_catalogo = BASE.replace("location /api/ {", "location /api/libros/ { return 200; }\n location /api/ {")
        with self.assertRaises(app.ConfiguracionIncompatible):
            app.integrar(con_catalogo)

    def test_rechaza_ausencia_de_bloqueo_interno(self):
        with self.assertRaisesRegex(app.ConfiguracionIncompatible, "/api/internal/"):
            app.integrar(BASE.replace("location ^~ /api/internal/ { return 404; }", ""))

    def test_rechaza_guardia_exclusivamente_exacta(self):
        with self.assertRaises(app.ConfiguracionIncompatible):
            app.integrar(BASE.replace("location ^~ /api/internal/", "location = /api/internal/"))

    def test_rechaza_guardia_sin_prioridad_ante_regex(self):
        vulnerable = BASE.replace(
            "location ^~ /api/internal/", "location /api/internal/"
        ).replace("location /api/ {", "location ~ ^/api/ { return 200; }\n location /api/ {")
        with self.assertRaises(app.ConfiguracionIncompatible):
            app.integrar(vulnerable)

    def test_rechaza_bloqueo_interno_inseguro(self):
        with self.assertRaises(app.ConfiguracionIncompatible):
            app.integrar(BASE.replace("return 404", "proxy_pass http://ms-identidad:8000", 1))

    def test_rechaza_multiples_servers_publicos(self):
        with self.assertRaises(app.ConfiguracionIncompatible):
            app.integrar(BASE + "\n" + BASE)

    def test_rechaza_server_sin_rutas(self):
        with self.assertRaises(app.ConfiguracionIncompatible):
            app.integrar("server { listen 8000; }")

    def test_ignora_otro_server_sin_api(self):
        generado = app.integrar("server { listen 9000; }\n" + BASE)
        self.assertEqual(generado.count(app.START), 1)
        self.assertIn("server { listen 9000; }", generado)

    def test_diff_no_escribe_archivo(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "default.conf"
            config.write_text(BASE, encoding="utf-8")
            with patch("sys.stdout"):
                self.assertEqual(app.main(["--config", str(config), "--diff"]), 0)
            self.assertEqual(config.read_text(encoding="utf-8"), BASE)

    def test_write_actualiza_y_es_idempotente(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "default.conf"
            config.write_text(BASE, encoding="utf-8")
            with patch("sys.stdout"):
                self.assertEqual(app.main(["--config", str(config), "--write"]), 0)
            saved = config.read_text(encoding="utf-8")
            self.assertIn(app.START, saved)
            with patch("sys.stdout"):
                self.assertEqual(app.main(["--config", str(config), "--write"]), 0)
            self.assertEqual(config.read_text(encoding="utf-8"), saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)
