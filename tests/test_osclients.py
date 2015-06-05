import unittest
from freezer.osclients import ClientManager
from freezer.utils import OpenstackOptions


class TestOsClients(unittest.TestCase):

    fake_options = OpenstackOptions("user", "tenant", "url", "password")

    def test_init(self):
        ClientManager(self.fake_options, None, None, None, None, None)

    def test_create_cinder(self):
        client = ClientManager(self.fake_options, None, None, None, None, None)
        client.create_cinder()

    def test_create_swift(self):
        client = ClientManager(self.fake_options, None, None, None, None, None)
        client.create_swift()

    def test_create_nova(self):
        client = ClientManager(self.fake_options, None, None, None, None, None)
        client.create_nova()
