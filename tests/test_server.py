from unittest import TestCase
from unittest.mock import MagicMock, patch

from quic.packets import QuicPacket
from quic.packets.initial import QuicInitialPacket
from quic.server import Server


class TestServer(TestCase):
    @patch("socket.socket")
    def test_send_packet(self, mock_socket):
        mock_sock_instance = MagicMock()
        mock_socket.return_value = mock_sock_instance
        packet = QuicInitialPacket(
            packet_number=1,
            version=1,
            src_conn_id=1,
            dst_conn_id=2,
        )
        with Server("", 0, 0.1, 5) as s:
            addr = ("", 0)
            s.send_packet(packet, addr)
            mock_sock_instance.sendto.assert_called_once()
            sent_data, sent_addr = mock_sock_instance.sendto.call_args[0]
            self.assertEqual(sent_addr, addr)
            self.assertEqual(sent_data, bytes(packet.to_bytes()))

    @patch('socket.socket')
    def test_receive_packet(self, mock_socket):
        mock_sock_instance = MagicMock()
        mock_socket.return_value = mock_sock_instance
        mock_packet = QuicInitialPacket(
            packet_number=1,
            version=1,
            src_conn_id=1,
            dst_conn_id=2,
        )
        packet_data = mock_packet.to_bytes()
        addr = ("", 0)
        mock_sock_instance.recvfrom.return_value = (packet_data, addr)
        with Server("", 0, 0.1, 5) as s:
            packet, received_addr = s.receive_packet()
            self.assertIsInstance(packet, QuicPacket)
            self.assertEqual(received_addr, addr)
            if isinstance(packet, QuicInitialPacket):
                self.assertEqual(packet.packet_number, 1)
