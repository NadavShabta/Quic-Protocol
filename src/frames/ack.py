from io import BytesIO

from quic.frames import QuicFrame
from quic.var_int import VarInt


class AckFrame(QuicFrame):
    def __init__(self, largest_acknowledged=None, ack_delay=0, ack_range_count=0, first_ack_range=0):
        super().__init__(2)
        self.largest_acknowledged = largest_acknowledged
        self.ack_delay = ack_delay
        self.ack_range_count = ack_range_count
        self.first_ack_range = first_ack_range

    def to_bytes(self):
        buffer = bytearray()

        buffer.append(self.type)

        buffer += VarInt(self.largest_acknowledged).to_bytes()
        buffer += VarInt(self.ack_delay).to_bytes()
        buffer += VarInt(self.ack_range_count).to_bytes()
        buffer += VarInt(self.first_ack_range).to_bytes()

        return buffer

    @property
    def smallest_acknowledged(self):
        return self.largest_acknowledged - self.first_ack_range

    @classmethod
    def from_bytes(cls, buffer: BytesIO):
        largest_acknowledged = VarInt.from_bytes(buffer)
        ack_delay = VarInt.from_bytes(buffer)
        ack_range_count = VarInt.from_bytes(buffer)
        first_ack_range = VarInt.from_bytes(buffer)

        return cls(
            largest_acknowledged=largest_acknowledged.value,
            ack_delay=ack_delay.value,
            ack_range_count=ack_range_count.value,
            first_ack_range=first_ack_range.value,
        )
