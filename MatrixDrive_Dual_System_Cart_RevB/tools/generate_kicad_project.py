#!/usr/bin/env python3
"""Generate the MatrixDrive Rev B logical KiCad schematic and netlisted PCB.

The repository deliberately carries a generated, auditable engineering capture.
The schematic uses the KiCad legacy text format because the build container does
not ship Eeschema; KiCad 8/9 opens it and offers a lossless conversion to
``.kicad_sch``.  The PCB is native KiCad 8 format.

Large programmable devices use logical pin names until the exact package pin
assignment is approved.  Their PCB footprints are consequently marked
UNVERIFIED and must not be released to fabrication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
PROJECT = "MatrixDrive-RevB"


@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    net: str | None
    kind: str = "B"


@dataclass
class Component:
    ref: str
    value: str
    description: str
    package: str
    group: str
    pins: list[Pin] = field(default_factory=list)
    dnp: bool = False
    pcb_at: tuple[float, float, float] | None = None

    def add(self, number: str | int, name: str, net: str | None,
            kind: str = "B") -> "Component":
        self.pins.append(Pin(str(number), name, net, kind))
        return self


def add_bus(c: Component, first_pin: int, pin_prefix: str, net_prefix: str,
            count: int, kind: str = "B") -> None:
    for i in range(count):
        c.add(first_pin + i, f"{pin_prefix}{i}", f"{net_prefix}{i}", kind)


def passive(ref: str, value: str, a: str, b: str, group: str,
            package: str = "0603", dnp: bool = False) -> Component:
    return Component(ref, value, value, package, group,
                     [Pin("1", "1", a, "P"), Pin("2", "2", b, "P")], dnp)


def qfn_logical(ref: str, value: str, group: str) -> Component:
    return Component(ref, value,
                     "Logical programmable-device symbol; verify package pins",
                     "UNVERIFIED_LOGICAL_PACKAGE", group)


def build_components() -> list[Component]:
    cs: list[Component] = []

    # Console cartridge edge, in physical A/B contact order.
    j1 = Component("J1", "MEGA_DRIVE_EDGE_2x32", "Mega Drive cartridge edge",
                   "MD_2x32_EDGE", "Console interface", pcb_at=(0, 0, 0))
    edge = {
        "A1":"GND", "A2":"CART_5V_IN", "A3":"VA8", "A4":"VA11",
        "A5":"VA7", "A6":"VA12", "A7":"VA6", "A8":"VA13",
        "A9":"VA5", "A10":"VA14", "A11":"VA4", "A12":"VA15",
        "A13":"VA3", "A14":"VA16", "A15":"VA2", "A16":"VA17",
        "A17":"VA1", "A18":"GND", "A19":"VD7", "A20":"VD0",
        "A21":"VD8", "A22":"VD6", "A23":"VD1", "A24":"VD9",
        "A25":"VD5", "A26":"VD2", "A27":"VD10", "A28":"VD4",
        "A29":"VD3", "A30":"VD11", "A31":"CART_5V_IN", "A32":"GND",
        "B1":None, "B2":"MRES_N", "B3":None, "B4":"VA9",
        "B5":"VA10", "B6":"VA18", "B7":"VA19", "B8":"VA20",
        "B9":"VA21", "B10":"VA22", "B11":"VA23_PAUSE",
        "B12":None, "B13":None, "B14":None, "B15":None,
        "B16":"CAS0_N", "B17":"CE0_N", "B18":"AS_N",
        "B19":"VCLK", "B20":None, "B21":"CAS2_N", "B22":"VD15",
        "B23":"VD14", "B24":"VD13", "B25":"VD12", "B26":None,
        "B27":"VRES_N", "B28":"LWR_N", "B29":"UWR_N",
        "B30":"M3_N", "B31":"TIME_N", "B32":"CART_N",
    }
    for contact, net in edge.items():
        j1.add(contact, contact, net, "B")
    cs.append(j1)

    # USB-C receptacle. D+/D- duplicate pins are tied at the receptacle.
    j2 = Component("J2", "USB4105-GF-A", "USB-C USB2 UFP receptacle",
                   "USB_C_16P", "USB and controller", pcb_at=(50, 2.5, 0))
    usb_pins = [
        ("A1","GND","GND"),("A4","VBUS","USB_VBUS"),("A5","CC1","CC1"),
        ("A6","D+","USB_DP"),("A7","D-","USB_DM"),("A9","VBUS","USB_VBUS"),
        ("A12","GND","GND"),("B1","GND","GND"),("B4","VBUS","USB_VBUS"),
        ("B5","CC2","CC2"),("B6","D+","USB_DP"),("B7","D-","USB_DM"),
        ("B9","VBUS","USB_VBUS"),("B12","GND","GND"),("S1","SHIELD","GND"),
    ]
    for n, name, net in usb_pins: j2.add(n, name, net)
    cs.append(j2)

    # RP2350B logical capture. GPIO numbering is authoritative from firmware;
    # physical QFN pad numbers remain a release gate.
    u1 = qfn_logical("U1", "RP2350B", "USB and controller")
    for i in range(21): u1.add(f"GPIO{i}", f"GPIO{i}", f"ROM_A{i}")
    for i in range(16): u1.add(f"GPIO{21+i}", f"GPIO{21+i}", f"MEM_D{i}")
    for i, net in enumerate(("ROM_CE_N","ROM_OE_N","ROM_WE_N",
                             "STAGE_MISO","STAGE_CS_N","STAGE_SCK","STAGE_MOSI",
                             "USB_SENSE_PROGRAM","LED_GREEN","LED_AMBER","LED_RED"), 37):
        u1.add(f"GPIO{i}", f"GPIO{i}", net)
    for name, net in (("USB_DP","USB_DP_MCU"),("USB_DM","USB_DM_MCU"),
                      ("XIN","XIN"),("XOUT","XOUT"),("QSPI_CS","BOOT_QSPI_CS"),
                      ("QSPI_SCLK","BOOT_QSPI_SCK"),("QSPI_SD0","BOOT_QSPI_IO0"),
                      ("QSPI_SD1","BOOT_QSPI_IO1"),("QSPI_SD2","BOOT_QSPI_IO2"),
                      ("QSPI_SD3","BOOT_QSPI_IO3"),("SWDIO","SWDIO"),
                      ("SWCLK","SWCLK"),("RUN","RUN_N"),("UART_TX","UART_TX"),
                      ("UART_RX","UART_RX"),("VREG_IN","3V3"),
                      ("VREG_SW","VREG_SW"),("VREG_FB","1V1"),
                      ("VREG_AVDD","VREG_AVDD"),("ADC_AVDD","ADC_AVDD"),
                      ("IOVDD_1","3V3"),("IOVDD_2","3V3"),("DVDD","1V1"),
                      ("GND_1","GND"),("GND_2","GND"),("EP","GND")):
        u1.add(name, name, net)
    u1.pcb_at=(49,15,0)
    cs.append(u1)

    # Active parallel NOR.
    u2 = qfn_logical("U2", "S29GL032N90TFI040", "ROM and save memory")
    for i in range(21): u2.add(f"A{i}", f"A{i}", f"ROM_A{i}")
    for i in range(16): u2.add(f"DQ{i}", f"DQ{i}", f"MEM_D{i}")
    for name, net in (("CE_N","ROM_CE_N"),("OE_N","ROM_OE_N"),
                      ("WE_N","ROM_WE_N"),("RESET_N","ROM_RESET_N"),
                      ("WP_N","ROM_WP_N"),("BYTE_N","ROM_BYTE_N"),
                      ("VCC","3V3"),("GND","GND")):
        u2.add(name,name,net)
    u2.package="TSOP-I-48_UNVERIFIED_PINMAP"; u2.pcb_at=(55,45,0)
    cs.append(u2)

    def translator(ref: str, a_nets: list[str], b_nets: list[str],
                   dir_net: str, oe_net: str, at: tuple[float,float,float]) -> Component:
        c=Component(ref,"SN74LVC8T245PWR","8-bit dual-supply translator",
                    "TSSOP-24_LOGICAL","Bus translation",pcb_at=at)
        for i,(a,b) in enumerate(zip(a_nets,b_nets),1):
            c.add(f"A{i}",f"A{i}",a); c.add(f"B{i}",f"B{i}",b)
        c.add("DIR","DIR",dir_net,"I").add("OE_N","OE_N",oe_net,"I")
        c.add("VCCA","VCCA","CART_5V","W").add("VCCB","VCCB","3V3","W")
        c.add("GND","GND","GND","W")
        return c

    cs.append(translator("U3",[f"VA{i}" for i in range(1,9)],
                         [f"CART_A{i}" for i in range(8)],"U3_DIR","BUS_DISABLE",(15,42,0)))
    cs.append(translator("U4",[f"VA{i}" for i in range(9,17)],
                         [f"CART_A{i}" for i in range(8,16)],"U4_DIR","BUS_DISABLE",(24,42,0)))
    cs.append(translator("U5",["VA17","VA18","VA19","VA20","VA21","CE0_N","CAS0_N","CAS2_N"],
                         ["CART_A16","CART_A17","CART_A18","CART_A19","CART_A20","CE0_3V3","CAS0_3V3","CAS2_3V3"],
                         "U5_DIR","BUS_DISABLE",(33,42,0)))
    cs.append(translator("U6",[f"VD{i}" for i in range(8)],
                         [f"MEM_D{i}" for i in range(8)],"LOW_DATA_DIR","BUS_DISABLE",(76,42,0)))
    cs.append(translator("U7",[f"VD{i}" for i in range(8,16)],
                         [f"MEM_D{i}" for i in range(8,16)],"U7_DIR","DATA_HIGH_DISABLE",(86,42,0)))
    cs.append(translator("U14",["LWR_N","MRES_N","UWR_N","AS_N","TIME_N","GND","GND","GND"],
                         ["LWR_3V3","MRES_3V3","UWR_3V3","AS_3V3","TIME_3V3",None,None,None],
                         "U14_DIR","BUS_DISABLE",(13,30,0)))

    u8=Component("U8","SN74LVC1G17DBVR","USB-present bus-disable buffer",
                 "SOT-23-5","Power and isolation",pcb_at=(22,9,0))
    for p in (("A","A","USB_PRESENT"),("Y","Y","BUS_DISABLE"),
              ("VCC","VCC","CART_5V"),("GND","GND","GND")): u8.add(*p)
    cs.append(u8)

    def spi_flash(ref: str, value: str, nets: tuple[str,str,str,str,str,str], at) -> Component:
        c=Component(ref,value,"Serial NOR flash","SOIC-8", "USB and controller",pcb_at=at)
        for num,name,net in ((1,"CS_N",nets[0]),(2,"DO",nets[1]),(3,"WP_N",nets[4]),
                             (4,"GND","GND"),(5,"DI",nets[2]),(6,"CLK",nets[3]),
                             (7,"HOLD_N",nets[5]),(8,"VCC","3V3")): c.add(num,name,net)
        return c
    cs.append(spi_flash("U9","W25Q16JVSSIQ",("BOOT_QSPI_CS","BOOT_QSPI_IO1","BOOT_QSPI_IO0","BOOT_QSPI_SCK","BOOT_QSPI_IO2","BOOT_QSPI_IO3"),(38,13,0)))
    cs.append(spi_flash("U10","W25Q128JVSIQ",("STAGE_CS_N","STAGE_MISO","STAGE_MOSI","STAGE_SCK","3V3","3V3"),(62,13,0)))

    u11=Component("U11","TLV75533PDBVR","3.3 V LDO","SOT-23-5","Power and isolation",pcb_at=(13,10,0))
    for num,name,net in ((1,"IN","SYS_5V"),(2,"GND","GND"),(3,"EN","SYS_5V"),(4,"NC",None),(5,"OUT","3V3")): u11.add(num,name,net)
    cs.append(u11)

    u12=Component("U12","TPD2EUSB30DRTR","USB D+/D- ESD protector","DRT-9_LOGICAL","USB and controller",pcb_at=(55,7,0))
    for n,name,net in (("IO1A","IO1A","USB_DP"),("IO1B","IO1B","USB_DP_MCU"),
                       ("IO2A","IO2A","USB_DM"),("IO2B","IO2B","USB_DM_MCU"),
                       ("GND","GND","GND")): u12.add(n,name,net)
    cs.append(u12)

    # CPLD logical symbol follows the synthesizable module ports.
    u13=qfn_logical("U13","ATF1508ASV-15AU100","Mapper and control")
    for i in range(21): u13.add(f"CART_A{i}",f"CART_A{i}",f"CART_A{i}")
    for i in range(8): u13.add(f"DATA_IN{i}",f"DATA_IN{i}",f"MEM_D{i}")
    for name,net in (("CE0_N","CE0_3V3"),("CAS0_N","CAS0_3V3"),("CAS2_N","CAS2_3V3"),
                     ("LWR_N","LWR_3V3"),("RESET_N","MRES_3V3"),("SMS_MODE","SMS_MODE_3V3"),
                     ("CODEMASTERS","SMS_MAPPER_CM_3V3"),("USB_MODE","USB_MODE_3V3")):
        u13.add(name,name,net)
    for i in range(21): u13.add(f"ROM_A{i}",f"ROM_A{i}",f"ROM_A{i}")
    for name,net in (("ROM_CE_N","ROM_CE_N"),("ROM_OE_N","ROM_OE_N"),
                     ("FRAM_A13","FRAM_A13"),("FRAM_A14","FRAM_A14"),
                     ("FRAM_CE_N","FRAM_CE_N"),("FRAM_HI_CE_N","FRAM_HI_CE_N"),
                     ("MD_FRAM_CE_N","MD_FRAM_CE_N"),("FRAM_OE_N","FRAM_OE_N"),
                     ("FRAM_WE_N","FRAM_WE_N"),("MD_HIGH_DISABLE","MD_HIGH_DISABLE_3V3"),
                     ("TCK","CPLD_TCK"),("TMS","CPLD_TMS"),("TDI","CPLD_TDI"),
                     ("TDO","CPLD_TDO"),("VCC_1","3V3"),("VCC_2","3V3"),
                     ("GND_1","GND"),("GND_2","GND")):
        u13.add(name,name,net)
    u13.package="TQFP-100_UNASSIGNED"; u13.pcb_at=(28,26,0)
    cs.append(u13)

    u15=Component("U15","SN74LVC2G32DCUR","Dual OR upper-data disable",
                  "VSSOP-8","Bus translation",pcb_at=(73,30,0))
    for n,name,net in ((1,"1A","BUS_DISABLE"),(2,"1B","SMS_MODE_5V"),(3,"1Y","DATA_HIGH_BASE_DISABLE"),
                       (4,"GND","GND"),(5,"2Y","DATA_HIGH_DISABLE"),(6,"2A","DATA_HIGH_BASE_DISABLE"),
                       (7,"2B","MD_HIGH_DISABLE_5V"),(8,"VCC","CART_5V")): u15.add(n,name,net)
    cs.append(u15)
    u16=Component("U16","SN74LVC1G04DBVR","Low-data direction inverter",
                  "SOT-23-5","Bus translation",pcb_at=(78,30,0))
    for n,name,net in ((1,"A","LWR_N"),(2,"GND","GND"),(4,"Y","LOW_DATA_DIR"),(5,"VCC","CART_5V")): u16.add(n,name,net)
    cs.append(u16)

    def fram(ref: str, ce: str, at, md: bool=False) -> Component:
        c=Component(ref,"FM18W08-SG","32Kx8 nonvolatile FRAM","SOIC-28_LOGICAL",
                    "ROM and save memory",pcb_at=at)
        for i in range(13): c.add(f"A{i}",f"A{i}",f"CART_A{i}")
        c.add("A13","A13","GND" if md else "FRAM_A13")
        c.add("A14","A14","GND" if md else "FRAM_A14")
        for i in range(8): c.add(f"DQ{i}",f"DQ{i}",f"MEM_D{i}")
        for name,net in (("CE_N",ce),("OE_N","FRAM_OE_N"),("WE_N","FRAM_WE_N"),
                         ("VDD","3V3"),("VSS","GND")): c.add(name,name,net)
        return c
    cs.append(fram("U17","FRAM_CE_N",(88,24,0)))
    cs.append(fram("U18","FRAM_HI_CE_N",(88,36,0)))
    cs.append(fram("U20","MD_FRAM_CE_N",(88,50,0),True))

    u19=Component("U19","SN74LVC1T45DBVR","MD high-data-disable translator",
                  "SOT-23-6","Bus translation",pcb_at=(75,24,0))
    for n,name,net in ((1,"VCCA","3V3"),(2,"A","MD_HIGH_DISABLE_3V3"),(3,"GND","GND"),
                       (4,"B","MD_HIGH_DISABLE_5V"),(5,"DIR","3V3"),(6,"VCCB","CART_5V")): u19.add(n,name,net)
    cs.append(u19)

    # Programming headers.
    j3=Component("J3","SWD_UART_2x5","SWD debug and UART header","HDR_2x5_1.27",
                 "USB and controller",dnp=True,pcb_at=(66,5,0))
    for n,name,net in ((1,"3V3","3V3"),(2,"SWDIO","SWDIO"),(3,"GND","GND"),(4,"SWCLK","SWCLK"),
                       (5,"GND","GND"),(6,"RUN_N","RUN_N"),(7,"NC",None),(8,"UART_TX","UART_TX"),
                       (9,"GND","GND"),(10,"UART_RX","UART_RX")): j3.add(n,name,net)
    cs.append(j3)
    j4=Component("J4","CPLD_JTAG_2x5","CPLD JTAG programming header","HDR_2x5_1.27",
                 "Mapper and control",pcb_at=(8,5,0))
    for n,name,net in ((1,"3V3","3V3"),(2,"TMS","CPLD_TMS"),(3,"GND","GND"),(4,"TCK","CPLD_TCK"),
                       (5,"GND","GND"),(6,"TDO","CPLD_TDO"),(7,"NC",None),(8,"TDI","CPLD_TDI"),
                       (9,"GND","GND"),(10,"NC",None)): j4.add(n,name,net)
    cs.append(j4)

    # Power, clock, source isolation, LEDs, switches and open-drain controls.
    cs += [
        passive("F1","MF-MSMF020-2","CART_5V_IN","CART_5V","Power and isolation","1812"),
        passive("D1","PMEG2010AEB","CART_5V","SYS_5V","Power and isolation","SOD-523"),
        passive("D2","PMEG2010AEB","USB_VBUS","SYS_5V","Power and isolation","SOD-523"),
        passive("D3","GREEN_LED","LED_GREEN_A","GND","Indicators","0603_LED"),
        passive("D4","AMBER_LED","LED_AMBER_A","GND","Indicators","0603_LED"),
        passive("D5","RED_LED","LED_RED_A","GND","Indicators","0603_LED"),
        passive("Y1","12MHz_CRYSTAL","XIN_XTAL","XOUT","USB and controller","3225_4P"),
        passive("L1","3.3uH","VREG_SW","1V1","USB and controller","2016"),
    ]

    for idx,(drain,gate) in enumerate((("M3_N","SMS_MODE_3V3"),("VA21","SMS_MODE_3V3"),
                                       ("VA22","SMS_MODE_3V3"),("VA23_PAUSE","PAUSE_GATE")),1):
        q=Component(f"Q{idx}","2N7002","Open-drain cartridge control","SOT-23","Mode controls")
        q.add(1,"G",gate).add(2,"S","GND").add(3,"D",drain)
        cs.append(q)

    sw1=Component("SW1","PROGRAM","Momentary program button","SW_2P","USB and controller")
    sw1.add(1,"1","USB_SENSE_PROGRAM").add(2,"2","GND"); cs.append(sw1)
    sw2=Component("SW2","MD_SMS_DPDT","Break-before-make mode selector","SW_DPDT_6P","Mode controls",pcb_at=(86,7,0))
    for n,name,net in ((1,"A_MD","GND"),(2,"A_COM","SMS_MODE_3V3"),(3,"A_SMS","3V3"),
                       (4,"B_MD","GND"),(5,"B_COM","SMS_MODE_5V"),(6,"B_SMS","CART_5V")): sw2.add(n,name,net)
    cs.append(sw2)
    sw3=Component("SW3","SMS_PAUSE","Momentary Master System Pause","SW_2P","Mode controls",pcb_at=(86,14,0))
    sw3.add(1,"1","SMS_MODE_3V3").add(2,"2","PAUSE_GATE"); cs.append(sw3)
    sw4=Component("SW4","PROFILE_SPDT","Break-before-make mapper/save selector","SW_SPDT_3P","Mode controls",pcb_at=(86,20,0))
    sw4.add(1,"LOW","GND").add(2,"COM","SMS_MAPPER_CM_3V3").add(3,"HIGH","3V3"); cs.append(sw4)

    # Resistors, including explicit DNP translator OE options.
    rmap = {
        1:("CC1","GND","5.1k"),2:("CC2","GND","5.1k"),
        3:("USB_DP","USB_DP_MCU","27R"),4:("USB_DM","USB_DM_MCU","27R"),
        5:("USB_VBUS","USB_PRESENT","10k"),6:("USB_PRESENT","GND","100k"),
        7:("USB_VBUS","USB_SENSE_PROGRAM","100k"),8:("USB_SENSE_PROGRAM","GND","100k"),
        9:("LED_GREEN","LED_GREEN_A","1k"),10:("LED_AMBER","LED_AMBER_A","1k"),
        11:("LED_RED","LED_RED_A","1k"),12:("ROM_WE_N","3V3","10k"),
        13:("CART_N","GND","0R"),14:("BUS_DISABLE","GND","100k"),
        15:("BUS_DISABLE","GND","10k"),16:("BUS_DISABLE","GND","10k"),
        17:("BUS_DISABLE","GND","10k"),18:("BUS_DISABLE","GND","10k"),
        19:("U3_DIR","CART_5V","10k"),20:("U4_DIR","CART_5V","10k"),
        21:("U5_DIR","CART_5V","10k"),22:("U14_DIR","CART_5V","10k"),
        23:("U7_DIR","GND","10k"),24:("3V3","VREG_AVDD","33R"),
        25:("ROM_RESET_N","3V3","10k"),26:("ROM_WP_N","3V3","10k"),
        27:("ROM_BYTE_N","3V3","10k"),28:("XIN_XTAL","XIN","1k"),
        29:("USB_VBUS","USB_MODE_3V3","100k"),30:("USB_MODE_3V3","GND","100k"),
        31:("ROM_CE_N","3V3","10k"),32:("ROM_OE_N","3V3","10k"),
        33:("FRAM_A14","GND","10k"),34:("FRAM_CE_N","3V3","10k"),
        35:("FRAM_OE_N","3V3","10k"),36:("FRAM_WE_N","3V3","10k"),
        37:("SMS_MODE_3V3","GND","100k"),38:("SMS_MODE_3V3","GND","100k"),
        39:("SMS_MODE_3V3","GND","100k"),40:("PAUSE_GATE","GND","100k"),
        41:("MRES_3V3","GND","100k"),42:("FRAM_A13","GND","10k"),
        43:("FRAM_HI_CE_N","3V3","10k"),44:("SMS_MAPPER_CM_3V3","GND","100k"),
        45:("MD_FRAM_CE_N","3V3","10k"),
    }
    for i,(a,b,val) in rmap.items():
        cs.append(passive(f"R{i}",val,a,b,"Passives","0603",15 <= i <= 18))

    # Capacitor allocation is explicit and conservative; values C28-C33 remain
    # reference-design gates called out in the BOM.
    decouple_nets = ["3V3"]*18
    for i,net in enumerate(decouple_nets,1): cs.append(passive(f"C{i}","100nF",net,"GND","Passives"))
    for i,net in zip(range(19,23),("3V3","CART_5V","3V3","3V3")):
        cs.append(passive(f"C{i}","1uF",net,"GND","Power and isolation"))
    cs.append(passive("C23","10uF","SYS_5V","GND","Power and isolation","0805"))
    cs.append(passive("C24","10uF","3V3","GND","Power and isolation","0805"))
    cs.append(passive("C25","15pF","XIN_XTAL","GND","USB and controller","0402"))
    cs.append(passive("C26","15pF","XOUT","GND","USB and controller","0402"))
    cs.append(passive("C27","4.7uF","1V1","GND","USB and controller"))
    support=("1V1","3V3","VREG_AVDD","ADC_AVDD","3V3","3V3")
    for i,net in zip(range(28,34),support): cs.append(passive(f"C{i}","TBD_REF",net,"GND","USB and controller","0402"))
    cs.append(passive("C34","100nF","3V3","GND","ROM and save memory"))
    cs.append(passive("C35","100nF","3V3","GND","Bus translation"))
    cs.append(passive("C36","100nF","3V3","GND","ROM and save memory"))

    tp_nets=("CART_5V","USB_VBUS","SYS_5V","3V3","GND","BUS_DISABLE",
             "SMS_MODE_3V3","SMS_MODE_5V","USB_MODE_3V3","ROM_CE_N","ROM_OE_N",
             "ROM_WE_N","FRAM_CE_N","FRAM_HI_CE_N","FRAM_OE_N","FRAM_WE_N",
             "MD_FRAM_CE_N","MD_HIGH_DISABLE_3V3","LWR_3V3","UWR_3V3","AS_3V3","TIME_3V3")
    for i,net in enumerate(tp_nets,1):
        c=Component(f"TP{i}",net,"Diagnostic test point","TP_SMD_1MM","Test points")
        c.add(1,"TP",net); cs.append(c)

    return cs


def validate_model(cs: list[Component]) -> None:
    refs=[c.ref for c in cs]
    assert len(refs)==len(set(refs)), "duplicate references"
    required={"U1","U2","U13","U17","U18","U20","J1","J2","SW2","SW4","F1"}
    assert required <= set(refs)
    nets={p.net for c in cs for p in c.pins if p.net}
    for net in ("GND","3V3","CART_5V","USB_VBUS","SYS_5V","ROM_A20","MEM_D15",
                "FRAM_HI_CE_N","MD_FRAM_CE_N","USB_MODE_3V3"):
        assert net in nets, net
    counts={n:0 for n in nets}
    for c in cs:
        numbers=[p.number for p in c.pins]
        assert len(numbers)==len(set(numbers)), f"duplicate pin numbers on {c.ref}"
        for p in c.pins:
            if p.net: counts[p.net]+=1
    dangling=sorted(n for n,c in counts.items() if c < 2 and not n.startswith("VCLK") and not n.startswith("VRES"))
    assert not dangling, f"single-pin nets: {dangling}"


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+","_",text)


def symbol_geometry(c: Component) -> tuple[int,int,list[tuple[Pin,int,int,str]]]:
    pins=c.pins
    half=(len(pins)+1)//2
    rows=max(half,len(pins)-half,3)
    height=max(600,(rows+1)*100)
    assigned=[]
    for i,p in enumerate(pins):
        if i < half:
            y=height//2-100-(i*100); assigned.append((p,-800,y,"R"))
        else:
            j=i-half; y=height//2-100-(j*100); assigned.append((p,800,y,"L"))
    return 1200,height,assigned


def write_symbol_library(cs: list[Component]) -> None:
    out=["EESchema-LIBRARY Version 2.4\n","#encoding utf-8\n"]
    for c in cs:
        name=safe_name(f"{c.ref}_{c.value}")
        width,height,pins=symbol_geometry(c)
        prefix=re.match(r"[A-Za-z]+",c.ref).group(0)
        out += [f"#\n# {name}\n#\n",f"DEF {name} {prefix} 0 40 Y Y 1 F N\n",
                f'F0 "{prefix}" 0 {-(height//2+180)} 50 H V C CNN\n',
                f'F1 "{c.value}" 0 {height//2+180} 50 H V C CNN\n',
                "DRAW\n",f"S -600 {-height//2} 600 {height//2} 0 1 10 f\n"]
        for p,x,y,orient in pins:
            px=-800 if x<0 else 800
            ptype={"I":"I","O":"O","W":"W","P":"P","B":"B"}.get(p.kind,"B")
            out.append(f"X {safe_name(p.name)} {safe_name(p.number)} {px} {y} 200 {orient} 40 40 1 1 {ptype}\n")
        out += ["ENDDRAW\n","ENDDEF\n"]
    out.append("#\n#End Library\n")
    (HW / "MatrixDrive_RevB.lib").write_text("".join(out))


def place_schematic(cs: list[Component]) -> dict[str,tuple[int,int]]:
    # A0 portrait-like packing. Big logical devices are placed first, followed
    # by functional groups; net labels make the capture electrically connected.
    columns=[3500,9000,14500,20000,25500,31000,36500,42000]
    y=[2200]*len(columns)
    positions={}
    order=sorted(cs,key=lambda c:(-symbol_geometry(c)[1],c.group,c.ref))
    for c in order:
        _,h,_=symbol_geometry(c)
        idx=min(range(len(columns)),key=lambda i:y[i])
        positions[c.ref]=(columns[idx],y[idx]+h//2)
        y[idx]+=h+600
    if max(y)>32200:
        raise RuntimeError(f"schematic packing exceeds A0: {max(y)}")
    return positions


def write_schematic(cs: list[Component]) -> None:
    pos=place_schematic(cs)
    out=[
        "EESchema Schematic File Version 4\n",
        "LIBS:MatrixDrive_RevB\n",
        "EELAYER 29 0\nEELAYER END\n",
        "$Descr A0 46811 33110\nencoding utf-8\nSheet 1 1\n",
        'Title "MatrixDrive Revision B - Complete Logical Engineering Capture"\n',
        'Date "2026-08-28"\nRev "B-LOGICAL"\nComp "Matrixite"\n',
        'Comment1 "NOT FOR FABRICATION - verify RP2350B, NOR and CPLD package pins"\n',
        'Comment2 "KiCad 8/9 can open and convert this legacy schematic"\n',
        'Comment3 "Generated from tools/generate_kicad_project.py"\n',
        'Comment4 "USB-loadable MD/32X/SMS cartridge with lock-on saves"\n',
        "$EndDescr\n",
        "Text Notes 1200 900 0    120  ~ 24\nMATRIXDRIVE REV B - LOGICAL ENGINEERING SCHEMATIC\n",
        "Text Notes 1200 1200 0    70   ~ 14\nAll repeated net labels are electrically connected. Programmable-device physical pin numbers remain release gates.\n",
    ]
    stamp=0x66000000
    for c in cs:
        x,y=pos[c.ref]; name=safe_name(f"{c.ref}_{c.value}"); stamp+=1
        out += ["$Comp\n",f"L MatrixDrive_RevB:{name} {c.ref}\n",f"U 1 1 {stamp:08X}\n",f"P {x} {y}\n",
                f'F 0 "{c.ref}" H {x} {y+80} 50  0000 C CNN\n',
                f'F 1 "{c.value}" H {x} {y-80} 40  0000 C CNN\n',
                'F 2 "" H 0 0 50 0001 C CNN\nF 3 "" H 0 0 50 0001 C CNN\n',
                f"\t1    {x} {y}\n\t1    0    0    -1\n$EndComp\n"]
        _,_,pins=symbol_geometry(c)
        for p,rx,ry,_ in pins:
            px=x+rx; py=y-ry
            if p.net is None:
                out.append(f"NoConn ~ {px} {py}\n")
                continue
            end=px-300 if rx<0 else px+300
            out += [f"Wire Wire Line\n\t{px} {py} {end} {py}\n",
                    f"Text Label {end} {py} {0 if rx<0 else 2}    35   ~ 0\n{p.net}\n"]
    out += [
        "Text Notes 1200 32300 0    60   ~ 12\nRELEASE GATES: assign/fix U1 and U13 physical pins; confirm U2 package straps; route and run ERC/DRC/SI/power review.\n",
        "$EndSCHEMATC\n",
    ]
    (HW / f"{PROJECT}.sch").write_text("".join(out))


def net_table(cs: list[Component]) -> dict[str,int]:
    nets=sorted({p.net for c in cs for p in c.pins if p.net})
    # Ground gets the first nonzero ID, which is conventional and convenient.
    nets.remove("GND"); nets.insert(0,"GND")
    return {name:i+1 for i,name in enumerate(nets)}


def pcb_escape(text: str) -> str:
    return text.replace('\\','\\\\').replace('"','\\"')


def pad_line(number: str, x: float, y: float, sx: float, sy: float,
             net: str | None, nets: dict[str,int], thru: bool=False) -> str:
    netpart="" if not net else f' (net {nets[net]} "{pcb_escape(net)}")'
    if thru:
        return f'    (pad "{number}" thru_hole oval (at {x:.3f} {y:.3f}) (size {sx:.3f} {sy:.3f}) (drill 0.65) (layers "*.Cu" "*.Mask"){netpart})\n'
    return f'    (pad "{number}" smd roundrect (at {x:.3f} {y:.3f}) (size {sx:.3f} {sy:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2){netpart})\n'


def footprint_for(c: Component, at: tuple[float,float,float], nets: dict[str,int]) -> str:
    x,y,rot=at
    value=pcb_escape(c.value + (" DNP" if c.dnp else ""))
    out=[f'  (footprint "MatrixDrive:{safe_name(c.package)}" (layer "F.Cu") (at {x:.3f} {y:.3f} {rot:.1f})\n',
         f'    (fp_text reference "{c.ref}" (at 0 -2.4 {rot:.1f}) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))\n',
         f'    (fp_text value "{value}" (at 0 2.4 {rot:.1f}) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))\n',
         '    (fp_rect (start -2 -1.5) (end 2 1.5) (stroke (width 0.18) (type default)) (fill none) (layer "F.SilkS"))\n']
    if c.ref=="J1":
        out[0]=f'  (footprint "MatrixDrive:MD_2x32_EDGE" (layer "F.Cu") (at 0 0)\n'
        out[1]='    (fp_text reference "J1" (at 5 58 90) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
        out[2]='    (fp_text value "MEGA_DRIVE_EDGE" (at 95 55 90) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
        out[3]=''
        lookup={p.number:p.net for p in c.pins}
        for i in range(32):
            px=10.63+i*2.54
            for side,layer in (("B","F.Cu"),("A","B.Cu")):
                n=f"{side}{i+1}"; net=lookup[n]
                netpart="" if not net else f' (net {nets[net]} "{pcb_escape(net)}")'
                layers='"F.Cu" "F.Mask"' if side=="B" else '"B.Cu" "B.Mask"'
                out.append(f'    (pad "{n}" connect rect (at {px:.3f} 61.5) (size 1.8 7.0) (layers {layers}){netpart})\n')
        out.append("  )\n"); return "".join(out)

    pins=c.pins
    if len(pins)==1:
        out.append(pad_line(pins[0].number,0,0,1.2,1.2,pins[0].net,nets))
    elif len(pins)==2:
        out.append(pad_line(pins[0].number,-1,0,1.0,1.1,pins[0].net,nets))
        out.append(pad_line(pins[1].number,1,0,1.0,1.1,pins[1].net,nets))
    elif c.ref in ("J3","J4"):
        for i,p in enumerate(pins):
            px=(i%2)*1.27-0.635; py=(i//2)*1.27-2.54
            out.append(pad_line(p.number,px,py,1.0,1.0,p.net,nets,True))
    elif c.ref=="J2":
        for i,p in enumerate(pins):
            row=0 if i<8 else 1; col=i if i<8 else i-8
            px=(col-3.5)*0.5; py=-1.5 if row==0 else 1.5
            out.append(pad_line(p.number,px,py,0.28,1.0,p.net,nets))
    else:
        # Logical perimeter footprint. Alphanumeric pads intentionally prevent
        # accidental use as a fabricated package before pin mapping is approved.
        half=(len(pins)+1)//2
        pitch=max(0.35,min(0.75,10.0/max(half,1)))
        body_h=max(3.0,(half-1)*pitch+1.2)
        out[3]=f'    (fp_rect (start -2 {-body_h/2:.3f}) (end 2 {body_h/2:.3f}) (stroke (width 0.18) (type default)) (fill none) (layer "F.SilkS"))\n'
        for i,p in enumerate(pins):
            if i<half: px=-2.35; py=(i-(half-1)/2)*pitch
            else:
                j=i-half; right=len(pins)-half; px=2.35; py=(j-(right-1)/2)*pitch
            out.append(pad_line(p.number,px,py,0.65,0.32,p.net,nets))
    out.append("  )\n")
    return "".join(out)


def assign_pcb_positions(cs: list[Component]) -> dict[str,tuple[float,float,float]]:
    pos={c.ref:c.pcb_at for c in cs if c.pcb_at}
    # Compact service-component placement in the upper and centre corridors.
    free=[(3+(i%22)*4.3, 6+(i//22)*4.1, 0.0) for i in range(286)]

    def extent(c: Component) -> tuple[float,float]:
        if c.ref == "J1": return (50.0,4.0)
        if len(c.pins) <= 2: return (2.1,1.7)
        if c.ref in ("J3","J4"): return (1.5,3.4)
        if c.ref == "J2": return (2.4,2.2)
        half=(len(c.pins)+1)//2
        pitch=max(0.35,min(0.75,10.0/max(half,1)))
        return (2.6,max(2.0,((half-1)*pitch+1.2)/2+0.4))

    fixed=[]
    by_ref={c.ref:c for c in cs}
    for ref,(x,y,_) in pos.items():
        if ref == "J1":
            fixed.append((50.0,61.0,50.0,4.0))
        else:
            ex,ey=extent(by_ref[ref]); fixed.append((x,y,ex,ey))

    def clear(pt):
        x,y,_=pt
        ex,ey=2.1,1.7
        return (2<x<98 and 4<y<56 and
                all(abs(x-rx) >= ex+rex or abs(y-ry) >= ey+rey
                    for rx,ry,rex,rey in fixed))
    free=[p for p in free if clear(p)]
    for c in cs:
        if c.ref in pos: continue
        if not free: raise RuntimeError("PCB auto-placement exhausted")
        p=free.pop(0); pos[c.ref]=p
    return pos


def write_pcb(cs: list[Component]) -> None:
    nets=net_table(cs); pos=assign_pcb_positions(cs)
    out=[
        '(kicad_pcb (version 20240108) (generator "matrixdrive_project_generator")\n',
        '  (general (thickness 1.6))\n',
        '  (paper "A4")\n',
        '  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (44 "Edge.Cuts" user))\n',
        '  (setup (pad_to_mask_clearance 0))\n',
    ]
    for name,num in nets.items(): out.append(f'  (net {num} "{pcb_escape(name)}")\n')
    out += [
        '  (gr_rect (start 0 0) (end 100 65) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))\n',
        '  (gr_text "MATRIXDRIVE REV B - NETLISTED ENGINEERING PCB" (at 50 2) (layer "F.SilkS") (effects (font (size 1.1 1.1) (thickness 0.18))))\n',
        '  (gr_text "DO NOT FABRICATE - UNROUTED / PROGRAMMABLE PIN MAPS UNVERIFIED" (at 50 4) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.14))))\n',
    ]
    for c in cs: out.append(footprint_for(c,pos[c.ref],nets))
    # Copper pours deliberately provide GND reference only; signal routing is a
    # release gate and is not guessed by the generator.
    gnd=nets["GND"]
    for layer in ("F.Cu","B.Cu"):
        out.append(f'  (zone (net {gnd}) (net_name "GND") (layer "{layer}") (hatch edge 0.5)\n')
        out.append('    (connect_pads (clearance 0.25)) (min_thickness 0.25) (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))\n')
        out.append('    (polygon (pts (xy 1 1) (xy 99 1) (xy 99 59) (xy 1 59)))\n  )\n')
    out.append(')\n')
    (HW / f"{PROJECT}.kicad_pcb").write_text("".join(out))


def write_project_files() -> None:
    (HW / "sym-lib-table").write_text(
        '(sym_lib_table\n  (lib (name "MatrixDrive_RevB")(type "Legacy")'
        '(uri "${KIPRJMOD}/MatrixDrive_RevB.lib")(options "")(descr "MatrixDrive generated logical symbols"))\n)\n')
    project={
        "board": {"design_settings": {"defaults": {"board_outline_line_width": 0.1,
                    "copper_line_width": 0.25, "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5, "copper_text_thickness": 0.3}}},
        "boards": [], "cvpcb": {}, "erc": {}, "libraries": {}, "meta": {
            "filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"bus_width": 12, "clearance": 0.2,
            "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3,
            "microvia_drill": 0.1, "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)",
            "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.25,
            "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6}],
            "meta": {"version": 3}},
        "pcbnew": {}, "schematic": {}, "sheets": [], "text_variables": {}
    }
    (HW / f"{PROJECT}.kicad_pro").write_text(json.dumps(project,indent=2)+"\n")


def write_manifest(cs: list[Component]) -> None:
    nets=net_table(cs)
    data={
        "project": PROJECT,
        "status": "logical-complete; PCB net-assigned and unrouted",
        "component_count": len(cs),
        "pin_count": sum(len(c.pins) for c in cs),
        "net_count": len(nets),
        "release_gates": [
            "Assign and verify RP2350B QFN-80 physical pad numbers",
            "Fit and assign ATF1508ASV TQFP-100 pins, then close timing",
            "Verify S29GL032N TSOP-I-48 package pinout and strap polarity",
            "Replace logical translator/FRAM footprints with verified library footprints",
            "Route all signal and power nets, refill zones, and pass KiCad ERC/DRC",
            "Review USB impedance, translator timing, current draw, and cartridge mechanics",
        ],
        "generated_files": [f"{PROJECT}.sch",f"{PROJECT}.kicad_pcb",
                            f"{PROJECT}.kicad_pro","MatrixDrive_RevB.lib","sym-lib-table"],
    }
    (HW / "kicad-project-manifest.json").write_text(json.dumps(data,indent=2)+"\n")


def main() -> None:
    cs=build_components()
    validate_model(cs)
    write_symbol_library(cs)
    write_schematic(cs)
    write_pcb(cs)
    write_project_files()
    write_manifest(cs)
    print(f"Generated {PROJECT}: {len(cs)} components, "
          f"{sum(len(c.pins) for c in cs)} pins, {len(net_table(cs))} nets")


if __name__ == "__main__":
    main()
