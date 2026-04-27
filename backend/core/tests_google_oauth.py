from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.services.google_oauth import get_google_clock_skew_seconds, verify_google_id_token


class GoogleOAuthVerificationTests(SimpleTestCase):
    @override_settings(GOOGLE_OAUTH_CLOCK_SKEW_SECONDS=7)
    def test_clock_skew_setting_is_used(self):
        self.assertEqual(get_google_clock_skew_seconds(), 7)

    @override_settings(GOOGLE_OAUTH_CLIENT_IDS="client-1", GOOGLE_OAUTH_CLOCK_SKEW_SECONDS=10)
    def test_verify_google_id_token_passes_clock_skew_to_google_auth(self):
        with patch("google.auth.transport.requests.Request") as request_cls:
            with patch("google.oauth2.id_token.verify_oauth2_token") as verify:
                request_adapter = request_cls.return_value
                verify.return_value = {"email": "client@example.com"}

                payload = verify_google_id_token("token")

        self.assertEqual(payload["email"], "client@example.com")
        verify.assert_called_once_with(
            "token",
            request_adapter,
            "client-1",
            clock_skew_in_seconds=10,
        )
