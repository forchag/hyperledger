# Hardware and Sensor Requirements

This project links farm sensors to a Hyperledger Fabric network through a Raspberry Pi gateway and optional LoRa backhaul. The following components are required to reproduce the system.

## Sensor Suite
- **DHT22 temperature and humidity sensor**
- **Soil moisture probe**
- **pH sensor**
- **Light sensor** (photodiode or LDR)
- **Water level sensor**

## Communication Modules
- **LoRa transceiver** (SX127x family or similar) for sensor nodes and the gateway
- **LoRa gateway** or a second transceiver acting as a receiver

## Processing and Gateway Hardware
- **Raspberry Pi 4** or comparable single-board computer for the edge gateway
- Additional Raspberry Pi boards for running the Hyperledger Fabric network if deploying multiple peers
- **MicroSD cards**, power supplies and network connectivity for each node

## Supporting Components
- Jumper wires and breadboard for prototyping
- Optional **MCP3008** ADC for sensors with analog outputs
- Antennas and enclosures appropriate for outdoor deployment

Ensure each sensor is powered according to its specifications and connected to the correct GPIO pins. Use female-to-male jumper wires for direct connection to the Pi header and verify readings with `python sensor_node.py <device-id>` before field deployment.
