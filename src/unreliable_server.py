import logging
import random
import sys

from quic.frames.ack import AckFrame
from quic.packets.numbered_packet import NumberedPacket
from quic.server import Server


class UnreliableServer(Server):
    def __init__(
            self,
            bind_host="127.0.0.1",
            bind_port=5555,
            fail_chance=0,
            ack_threshold=10,
            seed=random.randrange(sys.maxsize),
    ):
        super().__init__(bind_host, bind_port, ack_threshold=ack_threshold)

        self.fail_chance = fail_chance
        self.random = random.Random(seed)

        self.packet_count = 0

    def send_packet(self, packet: NumberedPacket, addr):
        has_ack = False

        for frame in packet.frames:
            if isinstance(frame, AckFrame):
                has_ack = True

        if has_ack:
            if self.random.random() <= self.fail_chance:
                logging.debug(f"ACK failed with chance {self.fail_chance}")
                pass
            else:
                super().send_packet(packet, addr)
                self.packet_count += 1


if __name__ == "__main__":
    with UnreliableServer() as server:
        while True:
            server.receive_packet()
