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
        """
        Initializes a QUIC server instance.

        Args:
            bind_host (str): IP address to bind the server to.
            bind_port (int): Port number to bind the server to.
            timeout (float): Timeout value for the server socket in seconds.
            ack_threshold (int): Number of packets to acknowledge in a single ACK frame.
        """
        self.bind_host = bind_host
        self.bind_port = bind_port

        self.timeout = timeout
        self.ack_threshold = ack_threshold

        self.id = random.randint(0, 10000)

        self._current_ack_range_length = 0  # Tracks how many packets are consecutively acked
        self._largest_acked = -1  # Tracks the largest acknowledged packet number

    def __enter__(self):
        """
        Context manager entry: creates and binds the UDP socket.
        """
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(self.timeout)
        self._sock.bind((self.bind_host, self.bind_port))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: closes the socket on cleanup.
        """
        self._sock.close()

    def send_packet(self, packet: NumberedPacket, addr):
        """
        Sends a packet to the specified client address.

        Args:
            packet (NumberedPacket): The packet to send.
            addr (tuple): The (IP, port) tuple of the destination client.
        """
        buffer = bytes(packet.to_bytes())
        self._sock.sendto(buffer, addr)

    def receive_packet(self) -> tuple[QuicPacket, tuple[str, int]]:
        """
        Receives a packet from the client, interprets it, and responds with an ACK if necessary.

        Returns:
            tuple: The received packet and the sender's address.
        """
        buffer, addr = self._sock.recvfrom(1500)
        packet = QuicPacket.from_bytes(BytesIO(buffer))

        if isinstance(packet, NumberedPacket):
            # Build initial response packet
            response = QuicInitialPacket(
                packet_number=packet.packet_number + 100000,
                version=1,
                dst_conn_id=0,
                src_conn_id=self.id,
            )

            # Determine the expected next packet number
            expected_packet_number = self._largest_acked + self._current_ack_range_length + 1

            # If the packet is expected and we haven't hit the threshold, just track it
            if packet.packet_number == expected_packet_number and self._current_ack_range_length != self.ack_threshold:
                self._current_ack_range_length += 1

            # If we either received an out-of-order packet or hit the threshold, send ACK
            elif packet.packet_number > expected_packet_number or self._current_ack_range_length == self.ack_threshold:
                if self._current_ack_range_length != 0:
                    ack = AckFrame(
                        largest_acknowledged=self._largest_acked + self._current_ack_range_length,
                        first_ack_range=self._current_ack_range_length - 1,
                    )

                    logging.debug(f"ACKing {ack.smallest_acknowledged} - {ack.largest_acknowledged}")

                    response.frames.append(ack)
                    self.send_packet(response, addr)

                # Update largest acknowledged and reset range
                self._largest_acked = packet.packet_number - 1
                self._current_ack_range_length = 1

        return packet, addr
