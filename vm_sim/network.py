"""Virtual network fabric for simulated VMs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional
import time
import uuid


class Protocol(str, Enum):
    ARP = "ARP"
    TCP = "TCP"
    ICMP = "ICMP"


class PacketType(str, Enum):
    ARP_REQUEST = "ARP_REQUEST"
    ARP_REPLY = "ARP_REPLY"
    SYN = "SYN"
    SYN_ACK = "SYN_ACK"
    ACK = "ACK"
    DATA = "DATA"
    FIN = "FIN"
    FIN_ACK = "FIN_ACK"
    ICMP_ECHO = "ICMP_ECHO"
    ICMP_REPLY = "ICMP_REPLY"


@dataclass
class Packet:
    """A single virtual network packet."""

    src_ip: str
    dst_ip: str
    protocol: Protocol
    packet_type: PacketType
    payload: str = ""
    src_mac: str = ""
    dst_mac: str = ""
    src_port: int = 0
    dst_port: int = 0
    seq: int = 0
    ack: int = 0
    ttl: int = 64
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)

    def summary(self) -> str:
        direction = f"{self.src_ip}:{self.src_port} → {self.dst_ip}:{self.dst_port}"
        if self.protocol == Protocol.ARP:
            direction = f"{self.src_ip} → {self.dst_ip}"
        detail = self.payload if self.payload else self.packet_type.value
        return f"[{self.protocol.value}] {self.packet_type.value} | {direction} | {detail}"


@dataclass
class NetworkEvent:
    """Logged event on the virtual network."""

    kind: str
    message: str
    packet: Optional[Packet] = None
    timestamp: float = field(default_factory=time.time)
    wall_time: str = field(
        default_factory=lambda: datetime.now().strftime("%H:%M:%S.%f")[:-3]
    )


class VirtualNetwork:
    """
    Simulated Ethernet LAN / L2 switch.

    VMs register by MAC + IP. Packets are delivered synchronously with
    optional latency, and every hop is recorded for visualization.
    """

    def __init__(self, name: str = "vnet0", latency_ms: float = 5.0):
        self.name = name
        self.latency_ms = latency_ms
        self._hosts: Dict[str, Callable[[Packet], None]] = {}
        self._arp_table: Dict[str, str] = {}  # ip -> mac
        self._mac_to_ip: Dict[str, str] = {}
        self.events: List[NetworkEvent] = []
        self.packets: List[Packet] = []

    def register(self, ip: str, mac: str, handler: Callable[[Packet], None]) -> None:
        self._hosts[mac] = handler
        self._arp_table[ip] = mac
        self._mac_to_ip[mac] = ip
        self._log("REGISTER", f"Host {ip} ({mac}) joined {self.name}")

    def unregister(self, mac: str) -> None:
        ip = self._mac_to_ip.pop(mac, None)
        self._hosts.pop(mac, None)
        if ip:
            self._arp_table.pop(ip, None)
            self._log("UNREGISTER", f"Host {ip} ({mac}) left {self.name}")

    def resolve_mac(self, ip: str) -> Optional[str]:
        return self._arp_table.get(ip)

    def send(self, packet: Packet) -> bool:
        """Deliver a packet to the destination host."""
        self.packets.append(packet)
        self._log("TX", packet.summary(), packet)

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)

        # Broadcast ARP requests
        if packet.packet_type == PacketType.ARP_REQUEST:
            delivered = False
            for mac, handler in list(self._hosts.items()):
                if mac != packet.src_mac:
                    handler(packet)
                    delivered = True
            if delivered:
                self._log("RX", f"ARP request flooded on {self.name}", packet)
            return delivered

        dst_mac = packet.dst_mac or self._arp_table.get(packet.dst_ip)
        if not dst_mac:
            self._log("DROP", f"No route to {packet.dst_ip}", packet)
            return False

        handler = self._hosts.get(dst_mac)
        if not handler:
            self._log("DROP", f"Host {dst_mac} offline", packet)
            return False

        packet.dst_mac = dst_mac
        handler(packet)
        self._log("RX", f"Delivered to {packet.dst_ip} ({dst_mac})", packet)
        return True

    def _log(self, kind: str, message: str, packet: Optional[Packet] = None) -> None:
        self.events.append(NetworkEvent(kind=kind, message=message, packet=packet))

    def reset_logs(self) -> None:
        self.events.clear()
        self.packets.clear()
