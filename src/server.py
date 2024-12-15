import logging
import random
import socket
from io import BytesIO

from quic.frames.ack import AckFrame
from quic.packets import QuicPacket
from quic.packets.initial import QuicInitialPacket
from quic.packets.numbered_packet import NumberedPacket


class Server:
    def __init__(self, bind_host="127.0.0.1", bind_port=5555, timeout=0.01, ack_threshold=10):
        self.bind_host = bind_host
        self.bind_port = bind_port

        self.timeout = timeout
        self.ack_threshold = ack_threshold

        self.id = random.randint(0, 10000)

        self._current_ack_range_length = 0
        self._largest_acked = -1

    def __enter__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(self.timeout)
        self._sock.bind((self.bind_host, self.bind_port))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sock.close()

    def send_packet(self, packet: NumberedPacket, addr):
        buffer = bytes(packet.to_bytes())
        # logging.debug(f"Sending buffer: {buffer[:100]} (length: {len(buffer)})")
        self._sock.sendto(buffer, addr)

    def receive_packet(self) -> tuple[QuicPacket, tuple[str, int]]:
        buffer, addr = self._sock.recvfrom(1500)
        # logging.debug(f"Received header from {addr}")

        packet = QuicPacket.from_bytes(BytesIO(buffer))

        if isinstance(packet, NumberedPacket):
            response = QuicInitialPacket(
                packet_number=packet.packet_number + 100000,
                version=1,
                dst_conn_id=0,
                src_conn_id=self.id,
            )

            expected_packet_number = self._largest_acked + self._current_ack_range_length + 1

            if packet.packet_number == expected_packet_number and self._current_ack_range_length != self.ack_threshold:
                self._current_ack_range_length += 1

            elif packet.packet_number > expected_packet_number or self._current_ack_range_length == self.ack_threshold:
                if self._current_ack_range_length != 0:
                    ack = AckFrame(
                        largest_acknowledged=self._largest_acked + self._current_ack_range_length,
                        first_ack_range=self._current_ack_range_length - 1,
                    )

                    logging.debug(f"ACKing {ack.smallest_acknowledged} - {ack.largest_acknowledged}")

                    response.frames.append(ack)

                    self.send_packet(response, addr)

                self._largest_acked = packet.packet_number - 1
                self._current_ack_range_length = 1

        return packet, addr
