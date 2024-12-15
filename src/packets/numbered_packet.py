from abc import ABC, abstractmethod
from math import log2, ceil


class NumberedPacket(ABC):
    def __init__(self, packet_number, frames=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.packet_number = packet_number

        if frames is None:
            frames = []

        self.frames = frames

    def encode_packet_number(self):
        num_unacked = self.packet_number + 1

        min_bits = log2(num_unacked) + 1
        num_bytes = ceil(min_bits / 8)

        return self.packet_number.to_bytes(num_bytes)

    @staticmethod
    def decode_packet_number():
        pass

    @abstractmethod
    def to_bytes(self):
        raise NotImplementedError()
