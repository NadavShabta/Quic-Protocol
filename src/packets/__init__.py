from io import BytesIO


class QuicPacket:
    def __init__(self, header_form=None, fixed_bit=1):
        self.header_form = header_form
        self.fixed_bit = fixed_bit

    @classmethod
    def from_bytes(cls, data: BytesIO):
        first_byte = int.from_bytes(data.read(1))

        header_form = (first_byte & 0b10000000) >> 7
        fixed_bit = (first_byte & 0b01000000) >> 6

        data.seek(0)

        if header_form == 0:
            from quic.packets.short import QuicShortPacket
            return QuicShortPacket.from_bytes(data, header_form=header_form, fixed_bit=fixed_bit)
        else:
            from quic.packets.long import QuicLongPacket
            return QuicLongPacket.from_bytes(data, header_form=header_form, fixed_bit=fixed_bit)

    def to_bytes(self):
        return bytearray(((self.header_form << 7) | (self.fixed_bit << 6)).to_bytes())
