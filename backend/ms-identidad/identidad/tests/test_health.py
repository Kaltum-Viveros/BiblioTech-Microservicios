from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import SimpleTestCase
from django.urls import reverse


class HealthTests(SimpleTestCase):

    def test_live_no_requiere_base_de_datos(self):
        respuesta = self.client.get(
            reverse("health-live")
        )

        self.assertEqual(
            respuesta.status_code,
            200
        )

        self.assertEqual(
            respuesta.json(),
            {
                "servicio": "identidad",
                "estado": "ok",
            }
        )

    def test_ready_devuelve_503_si_mysql_no_responde(self):
        with patch(
            "identidad.health.connections"
        ) as conexiones:

            conexiones.__getitem__.return_value.cursor.side_effect = (
                OperationalError("MySQL no disponible")
            )

            respuesta = self.client.get(
                reverse("health-ready")
            )

        self.assertEqual(
            respuesta.status_code,
            503
        )

        self.assertEqual(
            respuesta.json(),
            {
                "servicio": "identidad",
                "estado": "no_disponible",
            }
        )

    def test_ready_devuelve_200_si_mysql_responde(self):
        with patch(
            "identidad.health.connections"
        ) as conexiones:

            respuesta = self.client.get(
                reverse("health-ready")
            )

            conexiones[
                "default"
            ].cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
                "SELECT 1"
            )

        self.assertEqual(
            respuesta.status_code,
            200
        )

        self.assertEqual(
            respuesta.json(),
            {
                "servicio": "identidad",
                "estado": "ok",
            }
        )