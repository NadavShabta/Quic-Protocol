import struct
from io import BytesIO

from quic.packets import QuicPacket


class QuicShortPacket(QuicPacket):
    def __init__(
            self,
            fixed_bit=1,
            spin_bit=None,
            key_phase=None,
            packet_number_length=None,
            dst_conn_id=None,
            packet_number=None,
    ):
        super().__init__(0, fixed_bit)
        self.spin_bit = spin_bit
        self.reserved_bits = 0
        self.key_phase = key_phase
        self._packet_number_length = packet_number_length - 1 if packet_number else None
        self.dst_conn_id = dst_conn_id
        self.packet_number = packet_number

    @classmethod
    def from_bytes(cls, data: BytesIO, **kwargs):
        data = int.from_bytes(data)

        packet = cls()

        struct.pack_into(">B", packet, 0, data)

        packet_number_bytes = s.recv(packet.packet_number_length)
        packet.packet_number = int.from_bytes(packet_number_bytes)

        return packet

    @property
    def packet_number_length(self):
        return self._packet_number_length + 1

    def to_bytes(self):
        return bytes(self) + self.packet_number.to_bytes(self.packet_number_length)
