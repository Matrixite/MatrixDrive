#!/usr/bin/env python3
"""Dependency-free behavioral checks for the SMS FM front-end and PDM DAC."""


class SmsFmModel:
    def __init__(self) -> None:
        self.detect = 0b111
        self.core_writes: list[tuple[int, int]] = []

    def write(self, address: int, data: int, *, iorq: bool,
              sms_mode: bool = True, usb_mode: bool = False) -> None:
        if not sms_mode or usb_mode or not iorq:
            return
        address &= 0xFF
        data &= 0xFF
        if address == 0xF2:
            self.detect = data & 0x07
        elif address in (0xF0, 0xF1):
            self.core_writes.append((address & 1, data))

    def read(self, address: int, *, iorq: bool,
             sms_mode: bool = True, usb_mode: bool = False) -> int | None:
        if sms_mode and not usb_mode and iorq and (address & 0xFF) == 0xF2:
            return 0xF8 | self.detect
        return None


def pdm_ones(sample: int, cycles: int = 65536) -> int:
    unsigned_sample = (sample & 0xFFFF) ^ 0x8000
    accumulator = 0
    ones = 0
    for _ in range(cycles):
        total = accumulator + unsigned_sample
        ones += (total >> 16) & 1
        accumulator = total & 0xFFFF
    return ones


def main() -> None:
    fm = SmsFmModel()
    assert fm.read(0xF2, iorq=True) == 0xFF
    assert fm.read(0xF2, iorq=False) is None

    fm.write(0xF2, 0x00, iorq=False)
    assert fm.detect == 0b111
    fm.write(0xF0, 0x20, iorq=True)
    fm.write(0xF1, 0x17, iorq=True)
    assert fm.core_writes == [(0, 0x20), (1, 0x17)]

    fm.write(0xF2, 0x02, iorq=True)
    assert fm.read(0xF2, iorq=True) == 0xFA
    assert fm.read(0xF2, iorq=True, usb_mode=True) is None

    assert pdm_ones(0) == 32768
    assert pdm_ones(0x4000) == 49152
    assert pdm_ones(-0x4000) == 16384
    print("SMS FM behavioral model tests passed")


if __name__ == "__main__":
    main()
