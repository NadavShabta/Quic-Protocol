import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, mock_open, patch

from quic.client import Client
from quic.frames.stream import StreamFrame
from quic.packets.initial import QuicInitialPacket


class TestClient(TestCase):
    def test_get_packet_number(self):
        c = Client("", 0)
        initial = c._largest_packet_number
        assert initial == -1
        assert c.get_packet_number() == initial + 1

    def test_get_stream_id(self):
        c = Client("", 0)
        initial = c._largest_stream_id
        assert initial == -1
        assert c.get_stream_id() == initial + 1
        assert c.get_stream_id() != initial + 1

    def test_send_packet(self):
        packet = QuicInitialPacket(
            packet_number=1,
            version=1,
            src_conn_id=1,
            dst_conn_id=2,
        )
        with patch("socket.socket"), Client("", 0) as c:
            c.send_packet(packet)
            assert c.unacked_packets[packet.packet_number] == packet
            assert datetime.now() - c.transmission_times[packet.packet_number] < timedelta(seconds=1)

    def test_is_lost(self):
        # use epoch as a default date. https://xkcd.com/2676
        epoch = datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        with patch("socket.socket"), Client("", 0) as c:
            c.ack_detect, c.time_detect, c.largest_acked = True, False, 16
            assert c.is_lost(packet_number=1)
            assert not c.is_lost(packet_number=2)
            c.ack_detect, c.time_detect, c.smoothed_rtt, c.latest_rtt = False, True, 1000, 1000
            c.last_ack_time = epoch + timedelta(seconds=2)
            c.transmission_times = {
                1: epoch + timedelta(seconds=2) - timedelta(seconds=1),
                2: epoch + timedelta(seconds=2)
            }
            assert c.is_lost(packet_number=1)
            assert not c.is_lost(packet_number=2)

    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data=b"A" * 5000)
    def test_chunkify_file_no_remainder(self, mock_file, mock_stat):
        mock_stat.return_value = MagicMock()
        mock_stat.return_value.st_size = 5000
        path = Path("/fake/path")
        file_handle = mock_file.return_value.__enter__.return_value
        file_handle.tell.side_effect = [0, 1000, 2000, 3000, 4000]
        client = Client("", 0)
        client.get_stream_id = MagicMock(return_value=1)
        expected_chunks = [
            StreamFrame(1, include_length=True, offset=0, finish=False, data=b"A" * 1000),
            StreamFrame(1, include_length=True, offset=1000, finish=False, data=b"A" * 1000),
            StreamFrame(1, include_length=True, offset=2000, finish=False, data=b"A" * 1000),
            StreamFrame(1, include_length=True, offset=3000, finish=False, data=b"A" * 1000),
            StreamFrame(1, include_length=True, offset=4000, finish=True, data=b"A" * 1000),
        ]
        chunks = list(client.chunkify_file(path, chunk_size=1000))
        self.assertEqual(len(expected_chunks), len(chunks))
        for chunk, expected in zip(chunks, expected_chunks):
            self.assertEqual(expected.stream_id, chunk.stream_id)
            self.assertEqual(expected.offset, chunk.offset)
            self.assertEqual(expected.finish, chunk.finish)
            self.assertEqual(expected.data, chunk.data)

    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data=b"A" * 2500)
    def test_chunkify_file_with_remainder(self, mock_file, mock_stat):
        mock_stat.return_value = MagicMock()
        mock_stat.return_value.st_size = 2500
        path = Path("/fake/path")
        file_handle = mock_file.return_value.__enter__.return_value
        file_handle.tell.side_effect = [0, 1000, 2000]
        client = Client("", 0)
        client.get_stream_id = MagicMock(return_value=1)
        expected_chunks = [
            StreamFrame(1, include_length=True, offset=0, finish=False, data=b"A" * 1000),
            StreamFrame(1, include_length=True, offset=1000, finish=False, data=b"A" * 1000),
            StreamFrame(1, include_length=True, offset=2000, finish=True, data=b"A" * 500)
        ]
        chunks = list(client.chunkify_file(path, chunk_size=1000))
        self.assertEqual(len(expected_chunks), len(chunks))
        for chunk, expected in zip(chunks, expected_chunks):
            self.assertEqual(expected.stream_id, chunk.stream_id)
            self.assertEqual(expected.offset, chunk.offset)
            self.assertEqual(expected.finish, chunk.finish)
            self.assertEqual(expected.data, chunk.data)

    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data=b"")
    def test_chunkify_file_empty(self, mock_file, mock_stat):
        mock_stat.return_value = MagicMock()
        mock_stat.return_value.st_size = 0
        path = Path("/fake/path")
        file_handle = mock_file.return_value.__enter__.return_value
        file_handle.tell.side_effect = [0]
        client = Client("", 0)
        client.get_stream_id = MagicMock(return_value=1)
        chunks = list(client.chunkify_file(path, chunk_size=1000))
        self.assertEqual(0, len(chunks))

    def test_resend_lost_packets(self):
        epoch = datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        c = Client('', 0)
        c.get_packet_number = MagicMock(return_value=1)
        with patch("socket.socket"), Client("", 0) as c:
            c.unacked_packets = {
                1: MagicMock(packet_number=1),
                2: MagicMock(packet_number=2),
                3: MagicMock(packet_number=3),
            }
            c.transmission_times = {
                1: epoch,
                2: epoch,
                3: epoch
            }
            c.largest_acked = 3
            c.package_reordering_threshold = 1
            c.ack_detect = True
            c.time_detect = False
            c.get_packet_number = MagicMock(side_effect=[4, 5, 6])
            lost_packets = c.resend_lost_packets()
            self.assertEqual(2, len(lost_packets))
            self.assertIn(1, lost_packets)
            self.assertIn(2, lost_packets)
            self.assertEqual(c.unacked_packets[4], lost_packets[1])
            self.assertEqual(c.unacked_packets[5], lost_packets[2])
            self.assertEqual(4, lost_packets[1].packet_number)
            self.assertEqual(5, lost_packets[2].packet_number)
