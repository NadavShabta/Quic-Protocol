import datetime
import logging
import math
import random
import socket
from io import BytesIO
from pathlib import Path

from quic.frames.ack import AckFrame
from quic.frames.stream import StreamFrame
from quic.packets import QuicPacket
from quic.packets.numbered_packet import NumberedPacket


class Client:
    def __init__(
            self,
            server_ip,
            server_port,
            timeout=0.0001,
            package_reordering_threshold=15,
            waiting_time_threshold=40,
            k_initial_rtt=100000,
    ):
        self.server_ip = server_ip
        self.server_port = server_port

        self.timeout = timeout

        self.ack_detect = True
        self.time_detect = True

        self.package_reordering_threshold = package_reordering_threshold
        self.waiting_time_threshold = waiting_time_threshold

        self.largest_acked = -1
        self.last_ack_time = datetime.datetime.now()
        self.unacked_packets = {}
        self.transmission_times: dict[int, datetime.datetime] = {}

        self.k_initial_rtt = k_initial_rtt
        self.smoothed_rtt = self.k_initial_rtt
        self.rttvar = self.k_initial_rtt / 2
        self.min_rtt = float("inf")
        self.latest_rtt = self.k_initial_rtt

        self._largest_packet_number = -1
        self._largest_stream_id = -1

        self.id = random.randint(0, 10000)

    def __enter__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.connect((self.server_ip, self.server_port))
        self._sock.settimeout(self.timeout)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sock.close()

    def send_packet(self, packet: NumberedPacket):
        buffer = bytes(packet.to_bytes())
        self._sock.send(buffer)

        self.unacked_packets[packet.packet_number] = packet
        self.transmission_times[packet.packet_number] = datetime.datetime.now()

    def chunkify_file(self, path: Path, chunk_size=1000, stream_id: int = None):
        if stream_id is None:
            stream_id = self.get_stream_id()

        size = path.stat().st_size
        chunk_count = math.ceil(size / chunk_size)

        with path.open("rb") as f:
            for i in range(chunk_count):
                current_position = f.tell()
                buffer = f.read(chunk_size)

                yield StreamFrame(
                    stream_id,
                    include_length=True,
                    offset=current_position,
                    finish=size - current_position <= chunk_size,
                    data=buffer,
                )

    def is_lost(self, packet_number: int) -> bool:
        k_time_threshold = 9 / 8
        k_granularity = datetime.timedelta(milliseconds=1)

        lost = True

        if self.ack_detect:
            lost &= packet_number <= self.largest_acked - self.package_reordering_threshold

        if lost and self.time_detect:
            max_rtt = max(self.smoothed_rtt, self.latest_rtt)
            threshold_time = max(datetime.timedelta(microseconds=k_time_threshold * max_rtt), k_granularity)
            lost &= self.transmission_times[packet_number] < self.last_ack_time - threshold_time

        return lost

    def resend_lost_packets(self) -> dict[int, NumberedPacket]:
        lost_packets = {}
        for packet_number, packet in self.unacked_packets.items():
            if self.is_lost(packet_number):
                new_packet_number = self.get_packet_number()

                logging.debug(f"Resending {packet_number} as {new_packet_number}")
                lost_packets[packet.packet_number] = packet
                packet.packet_number = new_packet_number

        for old_packet_number, packet in lost_packets.items():
            self.unacked_packets.pop(old_packet_number)
            self.unacked_packets[packet.packet_number] = packet
            self.transmission_times.pop(old_packet_number)
            self.send_packet(packet)

        return lost_packets

    def receive_packet(self) -> tuple[QuicPacket, tuple[str, int], dict[int, NumberedPacket]]:
        buffer, addr = self._sock.recvfrom(1500)
        packet = QuicPacket.from_bytes(BytesIO(buffer))

        resent_lost_packets = None
        if isinstance(packet, NumberedPacket):
            for frame in packet.frames:
                if frame.type == 2:
                    frame: AckFrame

                    self.largest_acked = frame.largest_acknowledged
                    self.last_ack_time = datetime.datetime.now()

                    for packet_number in range(frame.smallest_acknowledged, frame.largest_acknowledged + 1):
                        self.unacked_packets.pop(packet_number, None)
                        transmission_time = self.transmission_times.pop(packet_number, None)

                        if transmission_time is not None:
                            latest_rtt = (datetime.datetime.now() - transmission_time).microseconds

                            if self.smoothed_rtt == self.k_initial_rtt:
                                self.smoothed_rtt = latest_rtt
                                self.rttvar = latest_rtt / 2
                            else:
                                self.min_rtt = min(self.min_rtt, latest_rtt)
                                ack_delay = 0
                                adjusted_rtt = latest_rtt
                                if latest_rtt >= self.min_rtt + ack_delay:
                                    adjusted_rtt = latest_rtt - ack_delay
                                self.smoothed_rtt = (7 / 8) * self.smoothed_rtt + (1 / 8) * adjusted_rtt
                                rttvar_sample = abs(self.smoothed_rtt - adjusted_rtt)
                                self.rttvar = (3 / 4) * self.rttvar + (1 / 4) * rttvar_sample

                            self.latest_rtt = latest_rtt

            resent_lost_packets = self.resend_lost_packets()

        return packet, addr, resent_lost_packets

    def get_packet_number(self):
        self._largest_packet_number += 1
        return self._largest_packet_number

    def get_stream_id(self):
        self._largest_stream_id += 1
        return self._largest_stream_id
