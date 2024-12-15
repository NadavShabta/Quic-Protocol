from io import BytesIO

from quic.frames import QuicFrame
from quic.var_int import VarInt


class StreamFrame(QuicFrame):
    def __init__(
            self,
            stream_id: int,
            include_length: bool,
            offset: int = None,
            finish: bool = False,
            data: bytes = b"",
    ):
        type_ = 8
        if offset is not None:
            type_ |= 0x04

        if include_length:
            type_ |= 0x02

        if finish:
            type_ |= 0x01

        super().__init__(type_)

        self.stream_id = stream_id
        self.offset = offset
        self.include_length = include_length
        self.finish = finish
        self.data = data

    def to_bytes(self):
        buffer = super().to_bytes()

        buffer += VarInt(self.stream_id).to_bytes()

        if self.offset is not None:
            buffer += VarInt(self.offset).to_bytes()

        if self.include_length:
            buffer += VarInt(len(self.data)).to_bytes()

        buffer += self.data

        return buffer

    @classmethod
    def from_bytes(cls, buffer: BytesIO):
        type_ = int.from_bytes(buffer.read(1))

        finish = bool(type_ & 1)
        length_present = bool((type_ >> 1) & 1)
        offset_present = bool((type_ >> 2) & 1)

        stream_id = VarInt.from_bytes(buffer).value

        offset = None
        if offset_present:
            offset = VarInt.from_bytes(buffer).value

        data = None
        if length_present:
            length = VarInt.from_bytes(buffer).value
            data = buffer.read(length)

        return cls(
            stream_id,
            include_length=length_present,
            offset=offset,
            finish=finish,
            data=data,
        )
