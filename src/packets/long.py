from io import BytesIO

from quic.packets import QuicPacket
from quic.var_int import VarInt


class QuicLongPacket(QuicPacket):
    def __init__(
            self,
            long_packet_type=None,
            type_specific_bits=None,
            version=None,
            dst_conn_id=None,
            src_conn_id=None,
            fixed_bit=1,
            **kwargs,
    ):
        super().__init__(1, fixed_bit)
        self.long_packet_type = long_packet_type
        self._type_specific_bits = type_specific_bits
        self.version = version
        self.dst_conn_id = dst_conn_id
        self.src_conn_id = src_conn_id

    @classmethod
    def from_bytes(cls, data: BytesIO, **kwargs):
        first_byte = int.from_bytes(data.read(1))

        long_packet_type = (first_byte & 0b00110000) >> 4
        type_specific_bits = (first_byte & 0b00001111)
        kwargs["type_specific_bits"] = type_specific_bits

        version_bytes = data.read(4)
        kwargs["version"] = int.from_bytes(version_bytes)

        dst_conn_id_length_bytes = data.read(1)
        dst_conn_id_length = int.from_bytes(dst_conn_id_length_bytes)

        dst_conn_id_bytes = data.read(dst_conn_id_length)
        kwargs["dst_conn_id"] = int.from_bytes(dst_conn_id_bytes)

        src_conn_id_length_bytes = data.read(1)
        src_conn_id_length = int.from_bytes(src_conn_id_length_bytes)

        src_conn_id_bytes = data.read(src_conn_id_length)
        kwargs["src_conn_id"] = int.from_bytes(src_conn_id_bytes)

        if long_packet_type == 0:
            from quic.packets.initial import QuicInitialPacket
            return QuicInitialPacket.from_bytes(data, **kwargs)

        raise Exception(f"Unrecognized long packet type {long_packet_type}")

    def to_bytes(self):
        buffer = super().to_bytes()
        buffer[0] = buffer[0] | (0b00001111 & self._type_specific_bits)

        buffer += self.version.to_bytes(4)

        dst_conn_id_length = VarInt.length_of(self.dst_conn_id)
        buffer.append(int.from_bytes(dst_conn_id_length.to_bytes()))
        buffer += self.dst_conn_id.to_bytes(dst_conn_id_length.value)

        src_conn_id_length = VarInt.length_of(self.src_conn_id)
        buffer.append(int.from_bytes(src_conn_id_length.to_bytes()))
        buffer += self.src_conn_id.to_bytes(src_conn_id_length.value)

        return buffer
