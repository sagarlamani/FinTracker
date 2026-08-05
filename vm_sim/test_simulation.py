"""Tests for the two-VM connection simulation."""

from __future__ import annotations

import unittest

from vm_sim import Simulation, VirtualMachine, VirtualNetwork
from vm_sim.network import PacketType
from vm_sim.vm import ConnectionState


class TestTwoVmConnection(unittest.TestCase):
    def test_full_scenario_succeeds(self):
        result = Simulation(latency_ms=0).run()
        self.assertTrue(result.success, result.summary)
        self.assertEqual(len(result.steps), 6)
        self.assertIn("Hello from Alpha VM!", result.messages_delivered)
        self.assertIn("Hello from Beta VM!", result.messages_delivered)

    def test_handshake_packet_order(self):
        result = Simulation(latency_ms=0).run()
        types = [p.packet_type for p in result.packets]

        self.assertIn(PacketType.ARP_REQUEST, types)
        self.assertIn(PacketType.ARP_REPLY, types)
        self.assertIn(PacketType.ICMP_ECHO, types)
        self.assertIn(PacketType.ICMP_REPLY, types)

        syn_i = types.index(PacketType.SYN)
        synack_i = types.index(PacketType.SYN_ACK)
        # First ACK after SYN-ACK completes the handshake
        ack_i = next(
            i for i, t in enumerate(types) if t == PacketType.ACK and i > synack_i
        )
        self.assertLess(syn_i, synack_i)
        self.assertLess(synack_i, ack_i)

    def test_custom_messages(self):
        result = Simulation(
            latency_ms=0,
            message_a_to_b="alpha-payload",
            message_b_to_a="beta-payload",
            listen_port=9000,
        ).run()
        self.assertTrue(result.success)
        self.assertIn("alpha-payload", result.messages_delivered)
        self.assertIn("beta-payload", result.messages_delivered)

    def test_listen_required(self):
        net = VirtualNetwork(latency_ms=0)
        a = VirtualMachine("a", "10.0.0.1", net, mac="02:00:00:00:00:01")
        b = VirtualMachine("b", "10.0.0.2", net, mac="02:00:00:00:00:02")
        a.power_on()
        b.power_on()
        # No listen on b — SYN should not establish
        conn = a.connect("10.0.0.2", 8080)
        self.assertEqual(conn.state, ConnectionState.SYN_SENT)
        a.power_off()
        b.power_off()


if __name__ == "__main__":
    unittest.main()
