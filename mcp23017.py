"""
MicroPython MCP23017 16-bit I/O Expander

https://ww1.microchip.com/downloads/en/devicedoc/20001952c.pdf

Based on https://github.com/mcauser/micropython-mcp23017

MIT License

Copyright (c) 2019 Mike Causer
Copyright (c) 2025-2026 Seth Hardy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from machine import I2C
from micropython import const


__version__ = "1.0.0"

# default values
_DEFAULT_ADDR    = const(0x20)

# device constants
_PINS_PER_PORT   = const(8)
_MAX_PIN         = const(15)
_BANK_SHIFT      = const(4)
_MASK_BYTE       = const(0xFF)

# registers (addresses in port=0, bank=1 mode)
_REG_IODIR       = const(0x00)  # R/W I/O Direction Register
_REG_IPOL        = const(0x01)  # R/W Input Polarity Port Register
_REG_GPINTEN     = const(0x02)  # R/W Interrupt-on-Change Pins
_REG_DEFVAL      = const(0x03)  # R/W Default Value Register
_REG_INTCON      = const(0x04)  # R/W Interrupt-on-Change Control Register
_REG_IOCON       = const(0x05)  # R/W Configuration Register
_REG_GPPU        = const(0x06)  # R/W Pull-Up Resistor Register
_REG_INTF        = const(0x07)  # R   Interrupt Flag Register (read clears)
_REG_INTCAP      = const(0x08)  # R   Interrupt Captured Value For Port Register
_REG_GPIO        = const(0x09)  # R/W General Purpose I/O Port Register
_REG_OLAT        = const(0x0A)  # R/W Output Latch Register

# config register (IOCON) bits
_IOCON_INTPOL    = const(0x02)
_IOCON_ODR       = const(0x04)
# _IOCON_HAEN    = const(0x08)  # not used - for spi flavour of this chip
_IOCON_DISSLW    = const(0x10)
_IOCON_SEQOP     = const(0x20)
_IOCON_MIRROR    = const(0x40)
_IOCON_BANK      = const(0x80)

# pin mode constants (matching machine.Pin)
_PIN_IN      = const(1)
_PIN_OUT     = const(0)
_PIN_PULL_UP = const(1)

# IRQ trigger constants
_IRQ_RISING         = const(1)
_IRQ_FALLING        = const(2)
_IRQ_RISING_FALLING = const(3)


class Port:
    """Represents one of the two 8-bit ports (A or B)."""

    _port: int
    _mcp: "MCP23017"

    def __init__(self, port: int, mcp: "MCP23017") -> None:
        self._port = port & 1  # 0=PortA, 1=PortB
        self._mcp = mcp

    @property
    def index(self) -> int:
        """Port index: 0 for port A, 1 for port B."""
        return self._port

    def _which_reg(self, reg: int) -> int:
        if self._mcp.config_cache & _IOCON_BANK:
            # bank = 1
            return reg | (self._port << _BANK_SHIFT)
        else:
            # bank = 0
            return (reg << 1) + self._port

    def flip_property_bit(self, reg: str, condition: int, bit: int) -> None:
        """Set or clear a bit in a register property."""
        if condition:
            setattr(self, reg, getattr(self, reg) | bit)
        else:
            setattr(self, reg, getattr(self, reg) & ~bit)

    def _read(self, reg: int) -> int:
        return self._mcp.i2c.readfrom_mem(self._mcp.address, self._which_reg(reg), 1)[0]

    def _write(self, reg: int, val: int) -> None:
        val &= _MASK_BYTE
        self._mcp.i2c.writeto_mem(
            self._mcp.address, self._which_reg(reg), bytearray([val])
        )
        # if writing to the config register, make a copy in mcp so that it knows
        # which bank you're using for subsequent writes
        if reg == _REG_IOCON:
            self._mcp.config_cache = val

    # ----- register 0x00: I/O direction (IODIR)

    @property
    def mode(self) -> int:
        return self._read(_REG_IODIR)

    @mode.setter
    def mode(self, val: int) -> None:
        self._write(_REG_IODIR, val)

    # ----- register 0x01: input polarity (IPOL)

    @property
    def input_polarity(self) -> int:
        return self._read(_REG_IPOL)

    @input_polarity.setter
    def input_polarity(self, val: int) -> None:
        self._write(_REG_IPOL, val)

    # ----- register 0x02: interrupt-on-change enable (GPINTEN)

    @property
    def interrupt_enable(self) -> int:
        return self._read(_REG_GPINTEN)

    @interrupt_enable.setter
    def interrupt_enable(self, val: int) -> None:
        self._write(_REG_GPINTEN, val)

    # ----- register 0x03: default compare value (DEFVAL)

    @property
    def default_value(self) -> int:
        return self._read(_REG_DEFVAL)

    @default_value.setter
    def default_value(self, val: int) -> None:
        self._write(_REG_DEFVAL, val)

    # ----- register 0x04: interrupt control (INTCON)

    @property
    def interrupt_compare_default(self) -> int:
        return self._read(_REG_INTCON)

    @interrupt_compare_default.setter
    def interrupt_compare_default(self, val: int) -> None:
        self._write(_REG_INTCON, val)

    # ----- register 0x05: I/O configuration (IOCON)

    @property
    def io_config(self) -> int:
        return self._read(_REG_IOCON)

    @io_config.setter
    def io_config(self, val: int) -> None:
        self._write(_REG_IOCON, val)

    # ----- register 0x06: pull-up resistor (GPPU)

    @property
    def pullup(self) -> int:
        return self._read(_REG_GPPU)

    @pullup.setter
    def pullup(self, val: int) -> None:
        self._write(_REG_GPPU, val)

    # ----- register 0x07: interrupt flag (INTF) - read only

    @property
    def interrupt_flag(self) -> int:
        return self._read(_REG_INTF)

    # ----- register 0x08: interrupt captured (INTCAP) - read only

    @property
    def interrupt_captured(self) -> int:
        return self._read(_REG_INTCAP)

    # ----- register 0x09: GPIO port (GPIO)

    @property
    def gpio(self) -> int:
        return self._read(_REG_GPIO)

    @gpio.setter
    def gpio(self, val: int) -> None:
        # writing to this register modifies the OLAT register for pins configured as output
        self._write(_REG_GPIO, val)

    # ----- register 0x0A: output latch (OLAT)

    @property
    def output_latch(self) -> int:
        return self._read(_REG_OLAT)

    @output_latch.setter
    def output_latch(self, val: int) -> None:
        self._write(_REG_OLAT, val)


class VirtualPin:
    """A pin-like interface for MCP23017 GPIO pins.

    Mimics machine.Pin API for drop-in compatibility.
    """

    # constants for API compatibility
    IN = _PIN_IN
    OUT = _PIN_OUT
    PULL_UP = _PIN_PULL_UP
    PULL_DOWN = object()  # sentinel - raises error if used
    IRQ_RISING = _IRQ_RISING
    IRQ_FALLING = _IRQ_FALLING
    IRQ_RISING_FALLING = _IRQ_RISING_FALLING

    _pin: int
    _bit: int
    _port: Port

    def __init__(
        self,
        pin: int,
        port: Port,
        mode: int | None = None,
        pull: int | None = None,
        value: int | None = None,
    ) -> None:
        self._pin = pin % _PINS_PER_PORT
        self._bit = 1 << self._pin
        self._port = port
        if mode is not None:
            self.init(mode, pull, value)

    def __repr__(self) -> str:
        port = "B" if self._port.index else "A"
        return f"VirtualPin(pin={self._pin}, port={port})"

    def __call__(self, val: int | None = None) -> int | None:
        """Read or write pin value. Equivalent to value()."""
        return self.value(val)

    def _flip_bit(self, value: int, condition: int) -> int:
        return value | self._bit if condition else value & ~self._bit

    def _get_bit(self, value: int) -> int:
        return (value & self._bit) >> self._pin

    def init(
        self,
        mode: int | None = None,
        pull: int | None = None,
        value: int | None = None,
    ) -> None:
        """Reinitialize the pin with new mode, pull, and value."""
        if pull is VirtualPin.PULL_DOWN:
            raise NotImplementedError("MCP23017 does not support pull-down resistors")
        if mode is not None:
            self._port.mode = self._flip_bit(self._port.mode, mode & 1)
        if pull is not None:
            self._port.pullup = self._flip_bit(self._port.pullup, pull & 1)
        if value is not None:
            self._port.gpio = self._flip_bit(self._port.gpio, value & 1)

    def value(self, val: int | None = None) -> int | None:
        """Read or write pin value."""
        if val is not None:
            self._port.gpio = self._flip_bit(self._port.gpio, val & 1)
            return None
        else:
            return self._get_bit(self._port.gpio)

    def on(self) -> None:
        """Set pin high."""
        self.value(1)

    def off(self) -> None:
        """Set pin low."""
        self.value(0)

    def toggle(self) -> None:
        """Toggle pin state."""
        self.value(1 - self._get_bit(self._port.gpio))

    def input(self, pull: int | None = None) -> None:
        """Configure pin as input with optional pull-up."""
        if pull is VirtualPin.PULL_DOWN:
            raise NotImplementedError("MCP23017 does not support pull-down resistors")
        self._port.mode = self._flip_bit(self._port.mode, _PIN_IN)
        if pull is not None:
            self._port.pullup = self._flip_bit(self._port.pullup, pull & 1)

    def output(self, val: int | None = None) -> None:
        """Configure pin as output with optional initial value."""
        self._port.mode = self._flip_bit(self._port.mode, _PIN_OUT)
        if val is not None:
            self._port.gpio = self._flip_bit(self._port.gpio, val & 1)

    def mode(self) -> int:
        """Return current pin direction: VirtualPin.IN or VirtualPin.OUT."""
        return self._get_bit(self._port.mode)

    def irq(self, handler: object = None, trigger: int | None = None) -> None:
        """Interrupt configuration placeholder.

        Note: MCP23017 interrupts are handled at the chip level via
        MCP23017.pin() with interrupt_enable parameter. This method
        is provided for API compatibility but does not set up handlers.
        Use MCP23017's interrupt_flag and interrupt_captured properties
        with external IRQ on INTA/INTB pins instead.
        """
        raise NotImplementedError(
            "Use MCP23017.pin(interrupt_enable=True) and external IRQ on INTA/INTB"
        )


class MCP23017:
    """MCP23017 16-bit I/O expander driver."""

    i2c: I2C
    address: int
    config_cache: int  # cached IOCON value for bank mode detection

    porta: Port
    portb: Port

    def __init__(self, i2c: I2C, address: int = _DEFAULT_ADDR) -> None:
        self.i2c = i2c
        self.address = address
        self.config_cache = 0x00
        self._virtual_pins: dict[int, VirtualPin] = {}

        self.porta = Port(0, self)
        self.portb = Port(1, self)

        # io expander configuration - same on both ports, only need to write once
        self.io_config = 0x00

        # Reset to all inputs with no pull-ups and no inverted polarity.
        self.mode = 0xFFFF                       # direction (0=out, 1=in)
        self.input_polarity = 0x0000             # (0=normal, 1=invert)
        self.interrupt_enable = 0x0000           # (0=disabled, 1=enabled)
        self.default_value = 0x0000              # default for int-on-change
        self.interrupt_compare_default = 0x0000  # (0=prev val, 1=defval)
        self.pullup = 0x0000                     # (0=disabled, 1=enabled)
        self.gpio = 0x0000                       # (0=low, 1=high)

    def config(
        self,
        interrupt_polarity: int | None = None,
        interrupt_open_drain: int | None = None,
        sda_slew: int | None = None,
        sequential_operation: int | None = None,
        interrupt_mirror: int | None = None,
        bank: int | None = None,
    ) -> None:
        """Configure the IOCON register."""
        io_config = self.porta.io_config

        if interrupt_polarity is not None:
            # configure INT as push-pull
            # 0: Active low
            # 1: Active high
            io_config = self.flip_bit(io_config, interrupt_polarity, _IOCON_INTPOL)
            if interrupt_polarity:
                # if setting to 1, unset ODR bit - interrupt_open_drain
                interrupt_open_drain = False
        if interrupt_open_drain is not None:
            # configure INT as open drain, overriding interrupt_polarity
            # 0: INTPOL sets the polarity
            # 1: Open drain, INTPOL ignored
            io_config = self.flip_bit(io_config, interrupt_open_drain, _IOCON_ODR)
        if sda_slew is not None:
            # 0: Slew rate function on SDA pin enabled
            # 1: Slew rate function on SDA pin disabled
            io_config = self.flip_bit(io_config, sda_slew, _IOCON_DISSLW)
        if sequential_operation is not None:
            # 0: Enabled, address pointer increments
            # 1: Disabled, address pointer fixed
            io_config = self.flip_bit(io_config, sequential_operation, _IOCON_SEQOP)
        if interrupt_mirror is not None:
            # 0: Independent INTA,INTB pins
            # 1: Internally linked INTA,INTB pins
            io_config = self.flip_bit(io_config, interrupt_mirror, _IOCON_MIRROR)
        if bank is not None:
            # 0: Registers alternate between A and B ports
            # 1: All port A registers first then all port B
            io_config = self.flip_bit(io_config, bank, _IOCON_BANK)

        # both ports share the same register, so you only need to write on one
        self.porta.io_config = io_config
        self.config_cache = io_config

    @staticmethod
    def flip_bit(value: int, condition: int, bit: int) -> int:
        """Set or clear a bit in a value based on condition."""
        if condition:
            value |= bit
        else:
            value &= ~bit
        return value

    def pin(
        self,
        pin: int,
        mode: int | None = None,
        value: int | None = None,
        pullup: int | None = None,
        polarity: int | None = None,
        interrupt_enable: int | None = None,
        interrupt_compare_default: int | None = None,
        default_value: int | None = None,
    ) -> bool | None:
        """Configure or read a single pin."""
        if not 0 <= pin <= _MAX_PIN:
            raise ValueError("pin out of range (0-15)")
        port = self.portb if pin // _PINS_PER_PORT else self.porta
        bit = 1 << (pin % _PINS_PER_PORT)
        if mode is not None:
            # 0: Pin is configured as an output
            # 1: Pin is configured as an input
            port.flip_property_bit("mode", mode & 1, bit)
        if value is not None:
            # 0: Pin is set to logic low
            # 1: Pin is set to logic high
            port.flip_property_bit("gpio", value & 1, bit)
        if pullup is not None:
            # 0: Weak pull-up 100k ohm resistor disabled
            # 1: Weak pull-up 100k ohm resistor enabled
            port.flip_property_bit("pullup", pullup & 1, bit)
        if polarity is not None:
            # 0: GPIO register bit reflects the same logic state of the input pin
            # 1: GPIO register bit reflects the opposite logic state of the input pin
            port.flip_property_bit("input_polarity", polarity & 1, bit)
        if interrupt_enable is not None:
            # 0: Disables GPIO input pin for interrupt-on-change event
            # 1: Enables GPIO input pin for interrupt-on-change event
            port.flip_property_bit("interrupt_enable", interrupt_enable & 1, bit)
        if interrupt_compare_default is not None:
            # 0: Pin value is compared against the previous pin value
            # 1: Pin value is compared against the associated bit in the DEFVAL register
            port.flip_property_bit(
                "interrupt_compare_default", interrupt_compare_default & 1, bit
            )
        if default_value is not None:
            # DEFVAL comparison value (0=low, 1=high)
            port.flip_property_bit("default_value", default_value & 1, bit)
        if value is None:
            return port.gpio & bit == bit
        return None

    def interrupt_triggered_gpio(self, port: int) -> int:
        """Get which GPIO triggered the interrupt (only 1 bit will be set)."""
        p = self.portb if port else self.porta
        return p.interrupt_flag

    def interrupt_captured_gpio(self, port: int) -> int:
        """Get captured GPIO values at time of interrupt (reading clears the interrupt)."""
        p = self.portb if port else self.porta
        return p.interrupt_captured

    # ----- register 0x00: I/O direction (IODIR) - 16-bit

    @property
    def mode(self) -> int:
        return self.porta.mode | (self.portb.mode << _PINS_PER_PORT)

    @mode.setter
    def mode(self, val: int) -> None:
        self.porta.mode = val
        self.portb.mode = val >> _PINS_PER_PORT

    # ----- register 0x01: input polarity (IPOL) - 16-bit

    @property
    def input_polarity(self) -> int:
        return self.porta.input_polarity | (self.portb.input_polarity << _PINS_PER_PORT)

    @input_polarity.setter
    def input_polarity(self, val: int) -> None:
        self.porta.input_polarity = val
        self.portb.input_polarity = val >> _PINS_PER_PORT

    # ----- register 0x02: interrupt-on-change enable (GPINTEN) - 16-bit

    @property
    def interrupt_enable(self) -> int:
        return self.porta.interrupt_enable | (
            self.portb.interrupt_enable << _PINS_PER_PORT
        )

    @interrupt_enable.setter
    def interrupt_enable(self, val: int) -> None:
        self.porta.interrupt_enable = val
        self.portb.interrupt_enable = val >> _PINS_PER_PORT

    # ----- register 0x03: default compare value (DEFVAL) - 16-bit

    @property
    def default_value(self) -> int:
        return self.porta.default_value | (self.portb.default_value << _PINS_PER_PORT)

    @default_value.setter
    def default_value(self, val: int) -> None:
        self.porta.default_value = val
        self.portb.default_value = val >> _PINS_PER_PORT

    # ----- register 0x04: interrupt control (INTCON) - 16-bit

    @property
    def interrupt_compare_default(self) -> int:
        return self.porta.interrupt_compare_default | (
            self.portb.interrupt_compare_default << _PINS_PER_PORT
        )

    @interrupt_compare_default.setter
    def interrupt_compare_default(self, val: int) -> None:
        self.porta.interrupt_compare_default = val
        self.portb.interrupt_compare_default = val >> _PINS_PER_PORT

    # ----- register 0x05: I/O configuration (IOCON)
    # This register is duplicated in each port. Changing one changes both.

    @property
    def io_config(self) -> int:
        return self.porta.io_config

    @io_config.setter
    def io_config(self, val: int) -> None:
        self.porta.io_config = val

    # ----- register 0x06: pull-up resistor (GPPU) - 16-bit

    @property
    def pullup(self) -> int:
        return self.porta.pullup | (self.portb.pullup << _PINS_PER_PORT)

    @pullup.setter
    def pullup(self, val: int) -> None:
        self.porta.pullup = val
        self.portb.pullup = val >> _PINS_PER_PORT

    # ----- register 0x07: interrupt flag (INTF) - 16-bit, read only

    @property
    def interrupt_flag(self) -> int:
        return self.porta.interrupt_flag | (self.portb.interrupt_flag << _PINS_PER_PORT)

    # ----- register 0x08: interrupt captured (INTCAP) - 16-bit, read only

    @property
    def interrupt_captured(self) -> int:
        return self.porta.interrupt_captured | (
            self.portb.interrupt_captured << _PINS_PER_PORT
        )

    # ----- register 0x09: GPIO port (GPIO) - 16-bit

    @property
    def gpio(self) -> int:
        return self.porta.gpio | (self.portb.gpio << _PINS_PER_PORT)

    @gpio.setter
    def gpio(self, val: int) -> None:
        self.porta.gpio = val
        self.portb.gpio = val >> _PINS_PER_PORT

    # ----- register 0x0A: output latch (OLAT) - 16-bit

    @property
    def output_latch(self) -> int:
        return self.porta.output_latch | (self.portb.output_latch << _PINS_PER_PORT)

    @output_latch.setter
    def output_latch(self, val: int) -> None:
        self.porta.output_latch = val
        self.portb.output_latch = val >> _PINS_PER_PORT

    # ----- end registers

    def __getitem__(self, pin: int) -> VirtualPin:
        """Get a VirtualPin for the given pin number (lazy creation)."""
        if not 0 <= pin <= _MAX_PIN:
            raise ValueError("pin out of range (0-15)")
        if pin not in self._virtual_pins:
            self._virtual_pins[pin] = VirtualPin(
                pin, self.portb if pin // _PINS_PER_PORT else self.porta
            )
        return self._virtual_pins[pin]

    def test(self) -> None:
        """Print diagnostic info for MCP23017."""
        print("MCP23017")
        print(f"  address: 0x{self.address:02X}")
        iocon = self.porta.io_config
        flags = []
        if iocon & _IOCON_BANK:
            flags.append("BANK")
        if iocon & _IOCON_MIRROR:
            flags.append("MIRROR")
        if iocon & _IOCON_SEQOP:
            flags.append("SEQOP")
        if iocon & _IOCON_ODR:
            flags.append("ODR")
        if iocon & _IOCON_INTPOL:
            flags.append("INTPOL")
        flag_str = ', '.join(flags) if flags else 'default'
        print(f"  iocon: 0x{iocon:02X} [{flag_str}]")
        for name, port in (("A", self.porta), ("B", self.portb)):
            d, p, g = bin(port.mode), bin(port.pullup), bin(port.gpio)
            print(f"  port {name}: dir={d} pullup={p} gpio={g}")
        int_a = self.porta.interrupt_enable
        int_b = self.portb.interrupt_enable
        if int_a or int_b:
            print(f"  interrupts: A={bin(int_a)} B={bin(int_b)}")
