"""Pruebas independientes que no necesitan iniciar MySQL."""
from unittest.mock import patch
from django.db.utils import OperationalError
from django.test import SimpleTestCase
from django.urls import reverse


class HealthTests(SimpleTestCase):
    def test_live_devuelve_ok(self):
        response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"servicio": "catalogo", "estado": "ok"})

    def test_ready_devuelve_200_con_mysql(self):
        with patch("catalogo.health.connections") as conexiones:
            response = self.client.get(reverse("health-ready"))
            conexiones["default"].cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SELECT 1")
        self.assertEqual(response.status_code, 200)

    def test_ready_devuelve_503_si_mysql_no_responde(self):
        with patch("catalogo.health.connections") as conexiones:
            conexiones["default"].cursor.side_effect = OperationalError("No disponible")
            response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"servicio": "catalogo", "estado": "no_disponible"})
