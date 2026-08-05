"""Simulated virtual machine with NIC and TCP-like stack."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING
import random
import time

from .network import Packet, PacketType, Protocol, VirtualNetwork

if TYPE_CHECKING:
    pass


class ConnectionState(str, Enum):
    CLOSED = "CLOSED"
    LISTEN = "LISTEN"
    SYN_SENT = "SYN_SENT"
    SYN_RECEIVED = "SYN_RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT = "FIN_WAIT"
    CLOSE_WAIT = "CLOSE_WAIT"
    CLOSED_DONE = "CLOSED_DONE"


@dataclass
class Connection:
    """TCP-like connection endpoint state."""

    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    state: ConnectionState = ConnectionState.CLOSED
    seq: int = 0
    ack: int = 0
    inbox: List[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.local_ip}:{self.local_port}-{self.remote_ip}:{self.remote_port}"


class VirtualMachine:
    """
    Lightweight VM with:
    - hostname, IP, MAC
    - ARP cache
    - TCP-like connect / listen / send / close
    """

    def __init__(
        self,
        name: str,
        ip: str,
        network: VirtualNetwork,
        mac: Optional[str] = None,
    ):
        self.name = name
        self.ip = ip
        self.mac = mac or self._generate_mac()
        self.network = network
        self.arp_cache: Dict[str, str] = {ip: self.mac}
        self.connections: Dict[str, Connection] = {}
        self._listeners: Dict[int, Connection] = {}
        self._pending_syn: Dict[str, Connection] = {}
        self.boot_time = time.time()
        self.uptime_ticks = 0
        self.log: List[str] = []
        self.powered_on = False

    @staticmethod
    def _generate_mac() -> str:
        octets = [0x02] + [random.randint(0x00, 0xFF) for _ in range(5)]
        return ":".join(f"{o:02x}" for o in octets)

    def power_on(self) -> None:
        if self.powered_on:
            return
        self.network.register(self.ip, self.mac, self._on_packet)
        self.powered_on = True
        self._vm_log(f"Powered on — IP {self.ip}, MAC {self.mac}")

    def power_off(self) -> None:
        if not self.powered_on:
            return
        self.network.unregister(self.mac)
        self.powered_on = False
        self.connections.clear()
        self._listeners.clear()
        self._vm_log("Powered off")

    def listen(self, port: int) -> None:
        self._require_on()
        conn = Connection(
            local_ip=self.ip,
            local_port=port,
            remote_ip="0.0.0.0",
            remote_port=0,
            state=ConnectionState.LISTEN,
        )
        self._listeners[port] = conn
        self._vm_log(f"Listening on port {port}")

    def connect(self, remote_ip: str, remote_port: int, local_port: int = 0) -> Connection:
        """Initiate a TCP three-way handshake to a remote VM."""
        self._require_on()
        local_port = local_port or random.randint(40000, 60000)

        # ARP resolution
        remote_mac = self._resolve_arp(remote_ip)
        if not remote_mac:
            raise ConnectionError(f"ARP failed: host {remote_ip} unreachable")

        seq = random.randint(1000, 9999)
        conn = Connection(
            local_ip=self.ip,
            local_port=local_port,
            remote_ip=remote_ip,
            remote_port=remote_port,
            state=ConnectionState.SYN_SENT,
            seq=seq,
        )
        self.connections[conn.key] = conn
        self._pending_syn[f"{remote_ip}:{remote_port}"] = conn

        packet = Packet(
            src_ip=self.ip,
            dst_ip=remote_ip,
            src_mac=self.mac,
            dst_mac=remote_mac,
            protocol=Protocol.TCP,
            packet_type=PacketType.SYN,
            src_port=local_port,
            dst_port=remote_port,
            seq=seq,
            payload=f"SYN seq={seq}",
        )
        self._vm_log(f"Connecting to {remote_ip}:{remote_port} (SYN seq={seq})")
        self.network.send(packet)
        return conn

    def send(self, remote_ip: str, remote_port: int, message: str) -> bool:
        conn = self._find_established(remote_ip, remote_port)
        if not conn:
            raise ConnectionError("No established connection")

        remote_mac = self.arp_cache.get(remote_ip) or self.network.resolve_mac(remote_ip)
        if not remote_mac:
            raise ConnectionError(f"No MAC for {remote_ip}")

        conn.seq += 1
        packet = Packet(
            src_ip=self.ip,
            dst_ip=remote_ip,
            src_mac=self.mac,
            dst_mac=remote_mac,
            protocol=Protocol.TCP,
            packet_type=PacketType.DATA,
            src_port=conn.local_port,
            dst_port=remote_port,
            seq=conn.seq,
            ack=conn.ack,
            payload=message,
        )
        self._vm_log(f"TX data → {remote_ip}:{remote_port}: {message!r}")
        return self.network.send(packet)

    def close(self, remote_ip: str, remote_port: int) -> None:
        conn = self._find_established(remote_ip, remote_port)
        if not conn:
            return

        remote_mac = self.arp_cache.get(remote_ip) or self.network.resolve_mac(remote_ip)
        conn.state = ConnectionState.FIN_WAIT
        packet = Packet(
            src_ip=self.ip,
            dst_ip=remote_ip,
            src_mac=self.mac,
            dst_mac=remote_mac or "",
            protocol=Protocol.TCP,
            packet_type=PacketType.FIN,
            src_port=conn.local_port,
            dst_port=remote_port,
            seq=conn.seq + 1,
            ack=conn.ack,
            payload="FIN",
        )
        self._vm_log(f"Closing connection to {remote_ip}:{remote_port}")
        self.network.send(packet)

    def ping(self, remote_ip: str) -> bool:
        self._require_on()
        remote_mac = self._resolve_arp(remote_ip)
        if not remote_mac:
            self._vm_log(f"Ping to {remote_ip} failed — host unreachable")
            return False

        packet = Packet(
            src_ip=self.ip,
            dst_ip=remote_ip,
            src_mac=self.mac,
            dst_mac=remote_mac,
            protocol=Protocol.ICMP,
            packet_type=PacketType.ICMP_ECHO,
            payload=f"ping from {self.name}",
        )
        self._vm_log(f"ICMP echo → {remote_ip}")
        return self.network.send(packet)

    def _resolve_arp(self, ip: str) -> Optional[str]:
        if ip in self.arp_cache:
            return self.arp_cache[ip]

        self._vm_log(f"ARP who-has {ip}? tell {self.ip}")
        request = Packet(
            src_ip=self.ip,
            dst_ip=ip,
            src_mac=self.mac,
            dst_mac="ff:ff:ff:ff:ff:ff",
            protocol=Protocol.ARP,
            packet_type=PacketType.ARP_REQUEST,
            payload=f"who-has {ip}? tell {self.ip}",
        )
        self.network.send(request)
        return self.arp_cache.get(ip)

    def _on_packet(self, packet: Packet) -> None:
        if packet.packet_type == PacketType.ARP_REQUEST:
            if packet.dst_ip == self.ip:
                self.arp_cache[packet.src_ip] = packet.src_mac
                reply = Packet(
                    src_ip=self.ip,
                    dst_ip=packet.src_ip,
                    src_mac=self.mac,
                    dst_mac=packet.src_mac,
                    protocol=Protocol.ARP,
                    packet_type=PacketType.ARP_REPLY,
                    payload=f"{self.ip} is-at {self.mac}",
                )
                self._vm_log(f"ARP reply → {packet.src_ip}: {self.ip} is-at {self.mac}")
                self.network.send(reply)
            return

        if packet.packet_type == PacketType.ARP_REPLY:
            if packet.dst_ip == self.ip:
                self.arp_cache[packet.src_ip] = packet.src_mac
                self._vm_log(f"ARP learned {packet.src_ip} → {packet.src_mac}")
            return

        if packet.packet_type == PacketType.ICMP_ECHO:
            if packet.dst_ip == self.ip:
                reply = Packet(
                    src_ip=self.ip,
                    dst_ip=packet.src_ip,
                    src_mac=self.mac,
                    dst_mac=packet.src_mac,
                    protocol=Protocol.ICMP,
                    packet_type=PacketType.ICMP_REPLY,
                    payload=f"pong from {self.name}",
                )
                self._vm_log(f"ICMP reply → {packet.src_ip}")
                self.network.send(reply)
            return

        if packet.packet_type == PacketType.ICMP_REPLY:
            if packet.dst_ip == self.ip:
                self._vm_log(f"ICMP reply ← {packet.src_ip}: {packet.payload}")
            return

        # TCP handling
        if packet.protocol != Protocol.TCP:
            return

        if packet.packet_type == PacketType.SYN:
            listener = self._listeners.get(packet.dst_port)
            if not listener:
                self._vm_log(f"Dropped SYN — nothing listening on {packet.dst_port}")
                return

            seq = random.randint(1000, 9999)
            conn = Connection(
                local_ip=self.ip,
                local_port=packet.dst_port,
                remote_ip=packet.src_ip,
                remote_port=packet.src_port,
                state=ConnectionState.SYN_RECEIVED,
                seq=seq,
                ack=packet.seq + 1,
            )
            self.connections[conn.key] = conn
            self.arp_cache[packet.src_ip] = packet.src_mac

            reply = Packet(
                src_ip=self.ip,
                dst_ip=packet.src_ip,
                src_mac=self.mac,
                dst_mac=packet.src_mac,
                protocol=Protocol.TCP,
                packet_type=PacketType.SYN_ACK,
                src_port=packet.dst_port,
                dst_port=packet.src_port,
                seq=seq,
                ack=packet.seq + 1,
                payload=f"SYN-ACK seq={seq} ack={packet.seq + 1}",
            )
            self._vm_log(
                f"Accepting connection from {packet.src_ip}:{packet.src_port} "
                f"(SYN-ACK seq={seq})"
            )
            self.network.send(reply)
            return

        if packet.packet_type == PacketType.SYN_ACK:
            key = f"{packet.src_ip}:{packet.src_port}"
            conn = self._pending_syn.pop(key, None)
            if not conn:
                # Try matching by connection keys
                for c in self.connections.values():
                    if (
                        c.remote_ip == packet.src_ip
                        and c.remote_port == packet.src_port
                        and c.state == ConnectionState.SYN_SENT
                    ):
                        conn = c
                        break
            if not conn:
                return

            conn.ack = packet.seq + 1
            conn.state = ConnectionState.ESTABLISHED
            ack_pkt = Packet(
                src_ip=self.ip,
                dst_ip=packet.src_ip,
                src_mac=self.mac,
                dst_mac=packet.src_mac,
                protocol=Protocol.TCP,
                packet_type=PacketType.ACK,
                src_port=conn.local_port,
                dst_port=packet.src_port,
                seq=conn.seq + 1,
                ack=conn.ack,
                payload=f"ACK ack={conn.ack}",
            )
            self._vm_log(
                f"Connection established with {packet.src_ip}:{packet.src_port}"
            )
            self.network.send(ack_pkt)
            return

        if packet.packet_type == PacketType.ACK:
            for conn in self.connections.values():
                if (
                    conn.remote_ip == packet.src_ip
                    and conn.remote_port == packet.src_port
                    and conn.state == ConnectionState.SYN_RECEIVED
                ):
                    conn.state = ConnectionState.ESTABLISHED
                    conn.ack = packet.seq
                    self._vm_log(
                        f"Connection established with {packet.src_ip}:{packet.src_port}"
                    )
                    return
            return

        if packet.packet_type == PacketType.DATA:
            for conn in self.connections.values():
                if (
                    conn.remote_ip == packet.src_ip
                    and conn.local_port == packet.dst_port
                    and conn.state == ConnectionState.ESTABLISHED
                ):
                    conn.inbox.append(packet.payload)
                    conn.ack = packet.seq
                    self._vm_log(
                        f"RX data ← {packet.src_ip}:{packet.src_port}: {packet.payload!r}"
                    )
                    # Send ACK
                    ack_pkt = Packet(
                        src_ip=self.ip,
                        dst_ip=packet.src_ip,
                        src_mac=self.mac,
                        dst_mac=packet.src_mac,
                        protocol=Protocol.TCP,
                        packet_type=PacketType.ACK,
                        src_port=conn.local_port,
                        dst_port=packet.src_port,
                        seq=conn.seq,
                        ack=packet.seq,
                        payload=f"ACK data seq={packet.seq}",
                    )
                    self.network.send(ack_pkt)
                    return
            return

        if packet.packet_type == PacketType.FIN:
            for conn in self.connections.values():
                if (
                    conn.remote_ip == packet.src_ip
                    and conn.local_port == packet.dst_port
                ):
                    conn.state = ConnectionState.CLOSE_WAIT
                    reply = Packet(
                        src_ip=self.ip,
                        dst_ip=packet.src_ip,
                        src_mac=self.mac,
                        dst_mac=packet.src_mac,
                        protocol=Protocol.TCP,
                        packet_type=PacketType.FIN_ACK,
                        src_port=conn.local_port,
                        dst_port=packet.src_port,
                        seq=conn.seq + 1,
                        ack=packet.seq + 1,
                        payload="FIN-ACK",
                    )
                    self._vm_log(f"Connection closing with {packet.src_ip}")
                    self.network.send(reply)
                    conn.state = ConnectionState.CLOSED_DONE
                    return
            return

        if packet.packet_type == PacketType.FIN_ACK:
            for conn in self.connections.values():
                if (
                    conn.remote_ip == packet.src_ip
                    and conn.state == ConnectionState.FIN_WAIT
                ):
                    conn.state = ConnectionState.CLOSED_DONE
                    self._vm_log(f"Connection closed with {packet.src_ip}")
                    return

    def _find_established(self, remote_ip: str, remote_port: int) -> Optional[Connection]:
        for conn in self.connections.values():
            if (
                conn.remote_ip == remote_ip
                and conn.remote_port == remote_port
                and conn.state == ConnectionState.ESTABLISHED
            ):
                return conn
        return None

    def _require_on(self) -> None:
        if not self.powered_on:
            raise RuntimeError(f"{self.name} is powered off")

    def _vm_log(self, message: str) -> None:
        entry = f"[{self.name}] {message}"
        self.log.append(entry)

    def status(self) -> dict:
        established = [
            c for c in self.connections.values() if c.state == ConnectionState.ESTABLISHED
        ]
        return {
            "name": self.name,
            "ip": self.ip,
            "mac": self.mac,
            "powered_on": self.powered_on,
            "listening_ports": list(self._listeners.keys()),
            "connections": [
                {
                    "remote": f"{c.remote_ip}:{c.remote_port}",
                    "local_port": c.local_port,
                    "state": c.state.value,
                    "inbox": list(c.inbox),
                }
                for c in self.connections.values()
            ],
            "arp_cache": dict(self.arp_cache),
            "established_count": len(established),
        }
