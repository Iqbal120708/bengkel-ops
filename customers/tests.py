from django.core.exceptions import ValidationError
from django.test import TestCase

from customers.models import Customer


class CustomerPhoneValidationTest(TestCase):

    def test_invalid_phone_rejected(self):
        """Nomor terlalu pendek harus gagal validasi."""
        customer = Customer(name="Test", phone="123")
        with self.assertRaises(ValidationError):
            customer.full_clean()

    def test_non_numeric_phone_rejected(self):
        """Nomor berisi huruf harus gagal validasi."""
        customer = Customer(name="Test", phone="abc")
        with self.assertRaises(ValidationError):
            customer.full_clean()

    def test_valid_phone_normalized_to_e164(self):
        """Nomor lokal dengan strip harus dinormalisasi ke format E164."""
        customer = Customer(name="Test", phone="0815-4691-9836")
        customer.full_clean()
        self.assertEqual(str(customer.phone), "+6281546919836")

    def test_phone_with_country_code_stays_valid(self):
        """Nomor yang sudah pakai kode negara manual tetap valid."""
        customer = Customer(name="Test", phone="+6281546919836")
        customer.full_clean()
        self.assertEqual(str(customer.phone), "+6281546919836")