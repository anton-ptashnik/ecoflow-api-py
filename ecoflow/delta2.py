"""
Delta 2 power station API
"""

import logging
import asyncio
import struct
from collections import namedtuple

from .common import OutputCircuit
from .common import StateField as SF
from .common import BleConnectionMixin

LOGGER = logging.getLogger(__name__)

class Delta2(BleConnectionMixin):
    """
    Delta 2 API
    """
    async def turn_on_circuit(self, circuit: OutputCircuit):
        """
        Turn on a specified power output circuit
        """
        await self._circuit_set(circuit, True)

    async def turn_off_circuit(self, circuit: OutputCircuit):
        """
        Turn off a specified power output circuit
        """
        await self._circuit_set(circuit, False)

    async def _circuit_set(self, circuit: OutputCircuit, state: bool):
        data = CircuitStateEncoder.encode(circuit, state)
        await self.device.write_gatt_char(0x0029, data)

    async def start_state_stream(self, callback):
        """
        Subscribe to state notifications and deliver parsed data to `callback`
        """
        parser = StateDataParser(callback)
        await self.device.start_notify(0x002b, parser.parse)

    async def stop_state_stream(self):
        """
        Unsubscribe from state notifications
        """
        await self.device.stop_notify(0x002b)


class CircuitStateEncoder:
    """
    Assembles a data packet for turning off/on an output circuit
    """
    Packet = namedtuple("Packet", ['header', 'state'])
    State = namedtuple("State", ['off', 'on'])

    packets = {
        OutputCircuit.AC: Packet(
            b"\xaa\x02\x07\x00\xde\x0d\x00\x00\x00\x00\x00\x00\x21\x05\x20\x42",
            State(b"\x00\xff\xff\xff\xff\xff\xff\x7b\xd1", b"\x01\xff\xff\xff\xff\xff\xff\x6b\x11")
        ),
        OutputCircuit.DC: Packet(
            b"\xaa\x02\x01\x00\xa0\x0d\x00\x00\x00\x00\x00\x00\x21\x05\x20\x51",
            State(b"\x00\xf3\x02", b"\x01\x32\xc2")
        ),
        OutputCircuit.USB: Packet(
            b"\xaa\x02\x01\x00\xa0\x0d\x00\x00\x00\x00\x00\x00\x21\x02\x20\x22",
            State(b"\x00\xd7\x46", b"\x01\x16\x86")
        ),
    }

    @staticmethod
    def encode(circuit: OutputCircuit, state: bool):
        packet = CircuitStateEncoder.packets[circuit]
        return packet.header + packet.state[state]


class StateDataParser:
    """
    Parses state notification bytes into a structured object
    """

    PAGE_HEADER = b"\xaa\x02"

    def __init__(self, callback) -> None:
        self.callback = callback
        self.page_parsers = {
            0x85: self._parse_page85,
            0x5e: self._parse_page5e,
            0x2e: self._parse_page2e,
        }

    def parse(self, _char, data):
        """
        Receive state notification data as raw bytes and parses into a dict with state fields
        """
        pages = self._split_pages(bytes(data))
        state_fields = {}
        for page in pages:
            page_code = self._page_code(page)
            try:
                parser = self.page_parsers.get(page_code, self._nop_parser)
                parsed_page = parser(page)
            except:
                LOGGER.exception("could not parse a page %s. Data: %s", page_code, page)
                parsed_page = {}
            state_fields.update(parsed_page)

        if asyncio.iscoroutinefunction(self.callback):
            asyncio.create_task(self.callback(state_fields))
        else:
            self.callback(state_fields)

    def _split_pages(self, data):
        pages = []
        unsplit = data
        while unsplit:
            unsplit, page_start, page_data = unsplit.rpartition(self.PAGE_HEADER)
            pages.append(page_start + page_data)
        return pages

    def _page_code(self, page):
        return page[2]

    def _nop_parser(self, page):
        LOGGER.warning("skipped a data page %s", self._page_code(page))
        return {}

    def _parse_page85(self, page):
        ac_input, = struct.unpack('H', page[33:35])
        return {
            SF.CHARGE_LEVEL: page[30],
            SF.AC_OUTPUT_IS_ON: bool(page[136]),
            SF.DC_OUTPUT_IS_ON: bool(page[49]),
            SF.USB_OUTPUT_IS_ON: bool(page[40]),
            SF.AC_INPUT: ac_input,
        }

    def _parse_page5e(self, page):
        charge_speed, = struct.unpack('H', page[89:91])
        return {
            SF.CHARGE_SPEED: charge_speed,
        }

    def _parse_page2e(self, page):
        th_min, th_max = page[59], page[28]
        if th_min > 100:
            # workaround for unexpected page structure
            # sometimes a data page has unexpected structure for several seconds after boot
            return {}
        remaining_time_minutes, = struct.unpack('H', page[33:35])
        Time = namedtuple("Time", "hrs mins")
        remaining_time_hrs_mins = Time(remaining_time_minutes // 60, remaining_time_minutes % 60)
        return {
            SF.CHARGE_TH_MIN: th_min,
            SF.CHARGE_TH_MAX: th_max,
            SF.REMAINING_TIME: remaining_time_hrs_mins
        }
