import datetime
import logging
import random
import sys

from quic.client import Client
from quic.packets.numbered_packet import NumberedPacket


class UnreliableClient(Client):
    def __init__(
            self,
            server_ip,
            server_port,
            fail_chance,
            package_reordering_threshold=15,
            seed=random.randrange(sys.maxsize),
    ):
        super().__init__(server_ip, server_port, package_reordering_threshold=package_reordering_threshold)

        self.fail_chance = fail_chance
        self.random = random.Random(seed)

        self.packet_count = 0

    def send_packet(self, packet: NumberedPacket):
        if self.random.random() <= self.fail_chance:
            logging.debug(f"Packet failed with chance {self.fail_chance}")
            self.unacked_packets[packet.packet_number] = packet
            self.transmission_times[packet.packet_number] = datetime.datetime.now()
        else:
            super().send_packet(packet)
            self.packet_count += 1
