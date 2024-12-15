from io import BytesIO

from quic.frames import QuicFrame
from quic.packets.long import QuicLongPacket
from quic.packets.numbered_packet import NumberedPacket
from quic.var_int import VarInt


class QuicInitialPacket(QuicLongPacket, NumberedPacket):
    def __init__(self, packet_number: int = None, token: bytes = b"", frames=None, **kwargs):
        kwargs.pop("header_form", None)
        kwargs["long_packet_type"] = 0

        NumberedPacket.__init__(self, packet_number, frames)
        QuicLongPacket.__init__(self, **kwargs)

        self.token = token

    @classmethod
    def from_bytes(cls, data: BytesIO, **kwargs):
        token_length = VarInt.from_bytes(data)

        token = data.read(token_length.value)

        length = VarInt.from_bytes(data)

        packet_number_length = 0b0011 & kwargs["type_specific_bits"]

        packet_number_bytes = data.read(packet_number_length)
        packet_number = int.from_bytes(packet_number_bytes)

        frames = []

        payload_size = length.value - packet_number_length

        start = data.tell()

        while data.tell() != start + payload_size:
            frame = QuicFrame.from_bytes(data)

            if frame is not None:
                frames.append(frame)

        return cls(
            packet_number=packet_number,
            token=token,
            frames=frames,
            **kwargs,
        )

    def to_bytes(self):
        encoded_packet_number = self.encode_packet_number()
        self._type_specific_bits = len(encoded_packet_number)

        buffer = super().to_bytes()
        buffer += VarInt.length_of(len(self.token)).to_bytes()
        buffer += self.token

        packed_frames = b""
        for frame in self.frames:
            packed_frames += frame.to_bytes()

        buffer += VarInt(len(packed_frames) + len(encoded_packet_number)).to_bytes()

        buffer += encoded_packet_number

        buffer += packed_frames

        return buffer
