"""Orchestrates a two-VM connection simulation scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .network import VirtualNetwork, NetworkEvent, Packet
from .vm import VirtualMachine, ConnectionState


@dataclass
class SimulationStep:
    """One annotated step in the scenario timeline."""

    index: int
    title: str
    description: str
    actor: str = ""


@dataclass
class SimulationResult:
    """Full outcome of a completed simulation run."""

    success: bool
    steps: List[SimulationStep]
    events: List[NetworkEvent]
    packets: List[Packet]
    vm_a_log: List[str]
    vm_b_log: List[str]
    vm_a_status: dict
    vm_b_status: dict
    messages_delivered: List[str] = field(default_factory=list)
    summary: str = ""


class Simulation:
    """
    Two VMs on a shared virtual LAN:

        alpha (10.0.0.1)  ←→  vnet0  ←→  beta (10.0.0.2)

    Default scenario:
      1. Power on both VMs
      2. beta listens on port 8080
      3. alpha pings beta (ARP + ICMP)
      4. alpha connects to beta (TCP handshake)
      5. Exchange messages
      6. Close the connection
    """

    def __init__(
        self,
        latency_ms: float = 2.0,
        message_a_to_b: str = "Hello from Alpha VM!",
        message_b_to_a: str = "Hello from Beta VM!",
        listen_port: int = 8080,
    ):
        self.latency_ms = latency_ms
        self.message_a_to_b = message_a_to_b
        self.message_b_to_a = message_b_to_a
        self.listen_port = listen_port

        self.network = VirtualNetwork(name="vnet0", latency_ms=latency_ms)
        self.vm_a = VirtualMachine("alpha", "10.0.0.1", self.network, mac="02:00:00:00:00:01")
        self.vm_b = VirtualMachine("beta", "10.0.0.2", self.network, mac="02:00:00:00:00:02")
        self.steps: List[SimulationStep] = []

    def run(self) -> SimulationResult:
        """Execute the full connection scenario."""
        self.steps.clear()
        self.network.reset_logs()

        try:
            self._step(1, "Power on VMs", "Both virtual machines boot and attach to vnet0", "system")
            self.vm_a.power_on()
            self.vm_b.power_on()

            self._step(
                2,
                "Beta listens",
                f"beta opens TCP port {self.listen_port} and waits for connections",
                "beta",
            )
            self.vm_b.listen(self.listen_port)

            self._step(
                3,
                "ARP + ICMP ping",
                "alpha resolves beta's MAC via ARP, then sends an ICMP echo",
                "alpha",
            )
            ping_ok = self.vm_a.ping(self.vm_b.ip)
            if not ping_ok:
                return self._fail("Ping failed — VMs cannot reach each other on the LAN")

            self._step(
                4,
                "TCP three-way handshake",
                "alpha → SYN → beta → SYN-ACK → alpha → ACK (connection ESTABLISHED)",
                "alpha",
            )
            conn = self.vm_a.connect(self.vm_b.ip, self.listen_port)
            if conn.state != ConnectionState.ESTABLISHED:
                return self._fail(f"Handshake incomplete — state is {conn.state.value}")

            # Confirm beta side is also established
            beta_ok = any(
                c.state == ConnectionState.ESTABLISHED for c in self.vm_b.connections.values()
            )
            if not beta_ok:
                return self._fail("Beta did not reach ESTABLISHED state")

            self._step(
                5,
                "Exchange application data",
                "Both VMs send messages over the established TCP session",
                "both",
            )
            self.vm_a.send(self.vm_b.ip, self.listen_port, self.message_a_to_b)

            # Find beta's view of the connection to reply
            beta_conn = next(
                (
                    c
                    for c in self.vm_b.connections.values()
                    if c.state == ConnectionState.ESTABLISHED
                ),
                None,
            )
            if beta_conn:
                self.vm_b.send(beta_conn.remote_ip, beta_conn.remote_port, self.message_b_to_a)

            self._step(
                6,
                "Graceful teardown",
                "alpha sends FIN; beta replies FIN-ACK; connection closed",
                "alpha",
            )
            self.vm_a.close(self.vm_b.ip, self.listen_port)

            delivered = []
            for c in self.vm_b.connections.values():
                delivered.extend(c.inbox)
            for c in self.vm_a.connections.values():
                delivered.extend(c.inbox)

            return SimulationResult(
                success=True,
                steps=list(self.steps),
                events=list(self.network.events),
                packets=list(self.network.packets),
                vm_a_log=list(self.vm_a.log),
                vm_b_log=list(self.vm_b.log),
                vm_a_status=self.vm_a.status(),
                vm_b_status=self.vm_b.status(),
                messages_delivered=delivered,
                summary=(
                    f"Connected {self.vm_a.name} ({self.vm_a.ip}) ↔ "
                    f"{self.vm_b.name} ({self.vm_b.ip}:{self.listen_port}). "
                    f"{len(self.network.packets)} packets exchanged, "
                    f"{len(delivered)} messages delivered."
                ),
            )
        except Exception as exc:
            return self._fail(str(exc))
        finally:
            # Leave VMs on so status remains inspectable; caller may power off
            pass

    def shutdown(self) -> None:
        self.vm_a.power_off()
        self.vm_b.power_off()

    def _step(self, index: int, title: str, description: str, actor: str) -> None:
        self.steps.append(
            SimulationStep(index=index, title=title, description=description, actor=actor)
        )

    def _fail(self, reason: str) -> SimulationResult:
        return SimulationResult(
            success=False,
            steps=list(self.steps),
            events=list(self.network.events),
            packets=list(self.network.packets),
            vm_a_log=list(self.vm_a.log),
            vm_b_log=list(self.vm_b.log),
            vm_a_status=self.vm_a.status(),
            vm_b_status=self.vm_b.status(),
            summary=f"Simulation failed: {reason}",
        )
