# Ecoflow Python API

[![Test](https://github.com/anton-ptashnik/ecoflow-api-py/actions/workflows/test.yml/badge.svg)](https://github.com/anton-ptashnik/ecoflow-api-py/actions/workflows/test.yml)

Python library for communicating with Ecoflow power stations over BLE, based on bleak.

## Supported features

Delta 2 device is the only supported for now. Extending support is planned

| Feature \ Device                                     | Delta 2 | River 2 |
| ---------------------------------------------------- | ------- | ------- |
| Output circuit control - AC                          | +       | pending |
| Output circuit control - DC                          | +       | pending |
| Output circuit control - USB                         | +       | pending |
| Reading output circuits state                        | +       | pending |
| Reading charge level                                 | +       | pending |
| Reading configured charging speed                    | +       | pending |
| Reading configured min/max charging speed thresholds | +       | pending |
| Reading realtime charging speed - AC input           | +       | pending |
| Reading realtime charging speed - Solar input        | -       | pending |

## Usage

```
import asyncio
import bleak
from ecoflow import Delta2, OutputCircuit


async def main():
    mac = "00:00:00:00:00:01"
    ble_client = bleak.BleakClient(mac, timeout=15)
    async with Delta2(ble_client) as dev:
        await dev.turn_on_circuit(OutputCircuit.USB)
        await dev.turn_off_circuit(OutputCircuit.AC)

        await dev.start_state_stream(print_state)
        await asyncio.sleep(40)
        await dev.stop_state_stream()


def print_state(data):
    print("state update...")
    for k, v in data.items():
        print(f"{k} = {v}")
    print("-"*20)


asyncio.run(main())
```

Note to understand the example completely one may need to refer to:

- bleak https://github.com/hbldh/bleak
- Python asyncio https://realpython.com/async-io-python/
