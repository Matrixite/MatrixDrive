#!/usr/bin/env python3
"""Executable reference-model tests for the Rev B Sega mapper equations."""


class Mapper:
    def __init__(self):
        self.control = 0
        self.banks = [0, 1, 2]

    def write(self, address: int, value: int) -> None:
        if 0xFFFC <= address <= 0xFFFF:
            index = address - 0xFFFC
            if index == 0:
                self.control = value & 0xFF
            else:
                self.banks[index - 1] = value & 0xFF

    def rom_word(self, address: int):
        if not 0 <= address <= 0xBFFF:
            return None
        if 0x8000 <= address <= 0xBFFF and self.control & 0x08:
            return None
        if address < 0x0400:
            bank = 0
        else:
            bank = self.banks[address >> 14]
        return ((bank & 0x7F) << 14) | (address & 0x3FFF)

    def fram_address(self, address: int):
        if not (self.control & 0x08 and 0x8000 <= address <= 0xBFFF):
            return None
        return ((self.control >> 2) & 1) << 14 | (address & 0x3FFF)


def main() -> None:
    m = Mapper()
    assert m.rom_word(0x0000) == 0x0000
    assert m.rom_word(0x03FF) == 0x03FF
    assert m.rom_word(0x4000) == (1 << 14)
    assert m.rom_word(0x8000) == (2 << 14)

    m.write(0xFFFD, 0x25)
    m.write(0xFFFE, 0x46)
    m.write(0xFFFF, 0xFF)
    assert m.rom_word(0x0000) == 0x0000  # fixed window ignores bank0
    assert m.rom_word(0x0400) == (0x25 << 14) | 0x0400
    assert m.rom_word(0x4001) == (0x46 << 14) | 1
    assert m.rom_word(0x8002) == (0x7F << 14) | 2

    m.write(0xFFFC, 0x08)
    assert m.rom_word(0x8000) is None
    assert m.fram_address(0x8000) == 0
    assert m.fram_address(0xBFFF) == 0x3FFF
    m.write(0xFFFC, 0x0C)
    assert m.fram_address(0x8000) == 0x4000
    assert m.fram_address(0xBFFF) == 0x7FFF
    assert m.fram_address(0x7FFF) is None

    print("SMS mapper reference-model tests passed")


if __name__ == "__main__":
    main()
