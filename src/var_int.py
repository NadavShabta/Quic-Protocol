from io import BytesIO
from math import log2, ceil


class VarInt:
    def __init__(self, value: int):
        self.value = value

        if self.value < 0x3fffffffffffffff:
            self.length = 8

        if self.value < 0x3fffffff:
            self.length = 4

        if self.value < 0x3fff:
            self.length = 2

        if self.value < 0x3f:
            self.length = 1

    def to_bytes(self):
        msb2 = int(log2(self.length))
        value = (msb2 << (self.length * 8 - 2)) | self.value
        if self.length < 0:
            print("NEGATIVE LENGTH", self.length)
        return value.to_bytes(self.length)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value})"

    @staticmethod
    def length_to_format(length):
        length_to_format = {
            0: "c",
            1: "c",
            2: "H",
            4: "I",
            8: "Q",
        }
        return length_to_format[length]

    @property
    def format(self):
        return self.length_to_format(self.length)

    @classmethod
    def from_bytes(cls, buffer: BytesIO):
        first_byte = int.from_bytes(buffer.read(1))
        msb2 = first_byte >> 6
        length = 2 ** msb2
        value_head = (first_byte & 0b00111111) << ((length - 1) * 8)
        value = value_head | int.from_bytes(buffer.read(length - 1))

        return cls(value)

    @classmethod
    def length_of(cls, value: int):
        return VarInt(ceil(value.bit_length() / 8))
