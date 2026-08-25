#!/usr/bin/env python3
"""Executable reference-model tests for the Sega and Codemasters equations."""


class Mapper:
    def __init__(self, profile: str = "sega"):
        if profile not in ("sega", "codemasters"):
            raise ValueError(profile)
        self.profile = profile
        self.sega_control = 0
        self.sega_banks = [0, 1, 2]
        self.codies_banks = [0, 1, 0]
        self.codies_ram_enabled = False
        self.codies_ram_bank = 0

    def write(self, address: int, value: int) -> None:
        value &= 0xFF
        if self.profile == "sega":
            if 0xFFFC <= address <= 0xFFFF:
                index = address - 0xFFFC
                if index == 0:
                    self.sega_control = value
                else:
                    self.sega_banks[index - 1] = value
            return

        if address == 0x0000:
            self.codies_banks[0] = value
        elif address == 0x4000:
            if value & 0x80:
                self.codies_ram_enabled = True
                self.codies_ram_bank = value & 0x07
            else:
                self.codies_ram_enabled = False
                self.codies_banks[1] = value
        elif address == 0x8000:
            self.codies_banks[2] = value

    def rom_word(self, address: int):
        if not 0 <= address <= 0xBFFF:
            return None
        if self.profile == "sega":
            if 0x8000 <= address <= 0xBFFF and self.sega_control & 0x08:
                return None
            if address < 0x0400:
                bank = 0
            else:
                bank = self.sega_banks[address >> 14]
        else:
            if 0xA000 <= address <= 0xBFFF and self.codies_ram_enabled:
                return None
            bank = self.codies_banks[address >> 14]
        return ((bank & 0x7F) << 14) | (address & 0x3FFF)

    def fram_address(self, address: int):
        if self.profile == "sega":
            if not (self.sega_control & 0x08 and 0x8000 <= address <= 0xBFFF):
                return None
            return ((self.sega_control >> 2) & 1) << 14 | (address & 0x3FFF)

        if not (self.codies_ram_enabled and 0xA000 <= address <= 0xBFFF):
            return None
        return (self.codies_ram_bank << 13) | (address & 0x1FFF)


def test_sega() -> None:
    mapper = Mapper("sega")
    assert mapper.rom_word(0x0000) == 0x0000
    assert mapper.rom_word(0x03FF) == 0x03FF
    assert mapper.rom_word(0x4000) == (1 << 14)
    assert mapper.rom_word(0x8000) == (2 << 14)

    mapper.write(0xFFFD, 0x25)
    mapper.write(0xFFFE, 0x46)
    mapper.write(0xFFFF, 0xFF)
    assert mapper.rom_word(0x0000) == 0x0000
    assert mapper.rom_word(0x0400) == (0x25 << 14) | 0x0400
    assert mapper.rom_word(0x4001) == (0x46 << 14) | 1
    assert mapper.rom_word(0x8002) == (0x7F << 14) | 2

    mapper.write(0xFFFC, 0x08)
    assert mapper.rom_word(0x8000) is None
    assert mapper.fram_address(0x8000) == 0
    assert mapper.fram_address(0xBFFF) == 0x3FFF
    mapper.write(0xFFFC, 0x0C)
    assert mapper.fram_address(0x8000) == 0x4000
    assert mapper.fram_address(0xBFFF) == 0x7FFF
    assert mapper.fram_address(0x7FFF) is None


def test_codemasters() -> None:
    mapper = Mapper("codemasters")
    assert mapper.rom_word(0x0000) == 0
    assert mapper.rom_word(0x4000) == (1 << 14)
    assert mapper.rom_word(0x8000) == 0

    mapper.write(0x0001, 0x44)
    mapper.write(0x0000, 0x25)
    mapper.write(0x4000, 0x46)
    mapper.write(0x8000, 0x7F)
    assert mapper.rom_word(0x0000) == (0x25 << 14)
    assert mapper.rom_word(0x03FF) == (0x25 << 14) | 0x03FF
    assert mapper.rom_word(0x4001) == (0x46 << 14) | 1
    assert mapper.rom_word(0x8002) == (0x7F << 14) | 2

    mapper.write(0x4000, 0x87)
    assert mapper.rom_word(0x4000) == (0x46 << 14)
    assert mapper.rom_word(0x8000) == (0x7F << 14)
    assert mapper.rom_word(0xA000) is None
    assert mapper.fram_address(0xA000) == 0xE000
    assert mapper.fram_address(0xBFFF) == 0xFFFF
    assert mapper.fram_address(0x9FFF) is None

    mapper.write(0x4000, 0x04)
    assert mapper.fram_address(0xA000) is None
    assert mapper.rom_word(0x4000) == (4 << 14)
    assert mapper.rom_word(0xA000) == (0x7F << 14) | 0x2000


def main() -> None:
    test_sega()
    test_codemasters()
    print("Sega and Codemasters mapper reference-model tests passed")


if __name__ == "__main__":
    main()
