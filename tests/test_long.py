import unittest
from io import BytesIO
from quic.packets.long import QuicLongPacket


class TestQuicLongPacket(unittest.TestCase):
    def test_constructor(self):
        packet = QuicLongPacket(
            long_packet_type=0,
            type_specific_bits=0b0001,
            version=1,
            dst_conn_id=24601,
            src_conn_id=10642,
        )
        self.assertEqual(0, packet.long_packet_type)
        self.assertEqual(0b0001, packet._type_specific_bits)
        self.assertEqual(1, packet.version)
        self.assertEqual(24601, packet.dst_conn_id)
        self.assertEqual(10642, packet.src_conn_id)
        self.assertEqual(1, packet.fixed_bit)

    def test_from_bytes(self):
        source = BytesIO(b'\xc1\x00\x00\x00\x01\x01\x01\x01\x02\x00\x01\x00')
        packet = QuicLongPacket.from_bytes(source)
        self.assertEqual(0, packet.long_packet_type)
        self.assertEqual(1, packet._type_specific_bits)
        self.assertEqual(1, packet.version)
        self.assertEqual(1, packet.dst_conn_id)
        self.assertEqual(2, packet.src_conn_id)

    def test_to_bytes(self):
        packet = QuicLongPacket(
            long_packet_type=0,
            type_specific_bits=0b0001,
            version=1,
            dst_conn_id=1,
            src_conn_id=2,
        )
        output = packet.to_bytes()
        expected = b'\xc1\x00\x00\x00\x01\x01\x01\x01\x02'
        self.assertEqual(expected, output)

