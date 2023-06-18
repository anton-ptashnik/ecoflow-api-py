import asyncio
from unittest.mock import AsyncMock
import struct
import pytest
import bleak
from ecoflow import Delta2
from ecoflow.common import StateField, OutputCircuit

STATE_CHAR_HANDLE = 0x2b

@pytest.fixture
def ble_client():
    client = AsyncMock()
    client.mock_add_spec(bleak.BleakClient, spec_set=True)
    return client


@pytest.mark.asyncio
async def test_circuit_control_ac(ble_client: AsyncMock):
    header = bytes([0xaa, 0x02, 0x07, 0x00, 0xde, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21, 0x05, 0x20, 0x42])
    on_cmd_suffix = bytes([0x1, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x6b, 0x11])
    off_cmd_suffix = bytes([0x0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7b, 0xd1])

    exp_pkt_on = header + on_cmd_suffix
    exp_pkt_off = header + off_cmd_suffix

    dev = Delta2(ble_client)

    await dev.turn_on_circuit(OutputCircuit.AC)
    ble_client.write_gatt_char.assert_called_with(0x29, exp_pkt_on)

    await dev.turn_off_circuit(OutputCircuit.AC)
    ble_client.write_gatt_char.assert_called_with(0x29, exp_pkt_off)


@pytest.mark.asyncio
async def test_circuit_control_dc(ble_client: AsyncMock):
    header = bytes([0xaa, 0x02, 0x01, 0x00, 0xa0, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21, 0x05, 0x20, 0x51])
    on_cmd_suffix = bytes([0x1, 0x32, 0xc2])
    off_cmd_suffix = bytes([0x0, 0xf3, 0x2])

    exp_pkt_on = header + on_cmd_suffix
    exp_pkt_off = header + off_cmd_suffix

    dev = Delta2(ble_client)

    await dev.turn_on_circuit(OutputCircuit.DC)
    ble_client.write_gatt_char.assert_called_with(0x29, exp_pkt_on)

    await dev.turn_off_circuit(OutputCircuit.DC)
    ble_client.write_gatt_char.assert_called_with(0x29, exp_pkt_off)


@pytest.mark.asyncio
async def test_circuit_control_usb(ble_client: AsyncMock):
    header = bytes([0xaa, 0x02, 0x01, 0x00, 0xa0, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21, 0x2, 0x20, 0x22])
    on_cmd_suffix = bytes([0x1, 0x16, 0x86])
    off_cmd_suffix = bytes([0x0, 0xd7, 0x46])

    exp_pkt_on = header + on_cmd_suffix
    exp_pkt_off = header + off_cmd_suffix

    dev = Delta2(ble_client)

    await dev.turn_on_circuit(OutputCircuit.USB)
    ble_client.write_gatt_char.assert_called_with(0x29, exp_pkt_on)

    await dev.turn_off_circuit(OutputCircuit.USB)
    ble_client.write_gatt_char.assert_called_with(0x29, exp_pkt_off)


@pytest.mark.asyncio
async def test_state_notifications(ble_client: AsyncMock):
    state_data = {}
    def save_state_data_cb(data):
        nonlocal state_data
        state_data = data
    
    dev = Delta2(ble_client)
    src = FakeNotificationsSource()
    ble_client.start_notify.side_effect = src.register

    await dev.start_state_stream(save_state_data_cb)
    ble_client.start_notify.assert_called_with(STATE_CHAR_HANDLE, src.send)

    page_0x85 = [0xaa, 0x2, 0x85] + [0]*150
    charge_level = 55
    all_circuits_is_on = True
    ac_input_power = 540
    page_0x85[30] = charge_level
    page_0x85[40] = int(all_circuits_is_on)
    page_0x85[49] = int(all_circuits_is_on)
    page_0x85[136] = int(all_circuits_is_on)
    page_0x85[33:35] = struct.pack("H", ac_input_power)

    src.send(STATE_CHAR_HANDLE, page_0x85)
    assert state_data[StateField.CHARGE_LEVEL] == charge_level
    assert state_data[StateField.USB_OUTPUT_IS_ON] == all_circuits_is_on
    assert state_data[StateField.DC_OUTPUT_IS_ON] == all_circuits_is_on
    assert state_data[StateField.AC_OUTPUT_IS_ON] == all_circuits_is_on
    assert state_data[StateField.AC_INPUT] == ac_input_power

    page_0x2e = [0xaa, 0x2, 0x2e] + [0]*150
    charge_th_min, charge_th_max = 20, 85
    page_0x2e[59] = charge_th_min
    page_0x2e[28] = charge_th_max

    src.send(STATE_CHAR_HANDLE, page_0x2e)
    assert state_data[StateField.CHARGE_TH_MIN] == charge_th_min
    assert state_data[StateField.CHARGE_TH_MAX] == charge_th_max

    page_0x5e = [0xaa, 0x2, 0x5e] + [0]*150
    charge_speed = 650
    page_0x5e[89:91] = struct.pack("H", charge_speed)

    src.send(STATE_CHAR_HANDLE, page_0x5e)
    assert state_data[StateField.CHARGE_SPEED] == charge_speed

    await dev.stop_state_stream()
    ble_client.stop_notify.assert_called_with(STATE_CHAR_HANDLE)


@pytest.mark.asyncio
async def test_state_notifications_async_cb(ble_client: AsyncMock):
    q = asyncio.Queue()
    async def save_state_data_cb(data):
        await q.put(data)
    
    dev = Delta2(ble_client)
    src = FakeNotificationsSource()
    ble_client.start_notify.side_effect = src.register

    await dev.start_state_stream(save_state_data_cb)
    ble_client.start_notify.assert_called_with(STATE_CHAR_HANDLE, src.send)

    page_0x85 = [0xaa, 0x2, 0x85] + [0]*150
    charge_level = 55
    page_0x85[30] = charge_level

    src.send(STATE_CHAR_HANDLE, page_0x85)
    state_data = await asyncio.wait_for(q.get(), timeout=2)
    assert state_data[StateField.CHARGE_LEVEL] == charge_level

class FakeNotificationsSource:
    """
    Convenience object allowing tests to simulate BLE messages receival
    """
    def __init__(self) -> None:
        def nop():
            pass
        self.send = nop

    def register(self, _char, cb):
        self.send = cb
