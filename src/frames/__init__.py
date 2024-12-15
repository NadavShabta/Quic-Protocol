from io import BytesIO, SEEK_CUR


class QuicFrame:
    def __init__(self, type_: int):
        self.type = type_

    def to_bytes(self):
        buffer = bytearray()

        buffer.append(self.type)

        return buffer

    @classmethod
    def from_bytes(cls, buffer: BytesIO):
        type_ = int.from_bytes(buffer.read(1))

        if type_ == 2:
            from quic.frames.ack import AckFrame
            return AckFrame.from_bytes(buffer)

        if type_ >> 3 == 1:
            from quic.frames.stream import StreamFrame
            buffer.seek(-1, SEEK_CUR)
            return StreamFrame.from_bytes(buffer)
