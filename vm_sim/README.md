# Two-VM Network Connection Simulation
#
# Simulates alpha (10.0.0.1) and beta (10.0.0.2) on a virtual LAN (vnet0).
# Covers ARP discovery, ICMP ping, TCP three-way handshake, data exchange,
# and graceful teardown.

## Quick start (CLI)

```bash
# From the repo root
python -m vm_sim

# Custom messages / latency
python -m vm_sim --latency 10 --msg-a "ping payload" --msg-b "pong payload"
```

## Interactive UI (Streamlit)

```bash
streamlit run vm_sim/ui.py --server.port 8502
```

Open http://localhost:8502 — use the sidebar to set latency and messages, then **Run simulation**.

## What it demonstrates

| Step | What happens |
|------|----------------|
| 1 | Both VMs power on and register NICs on `vnet0` |
| 2 | `beta` listens on TCP port 8080 |
| 3 | `alpha` ARP-resolves `beta`, then ICMP-pings it |
| 4 | TCP handshake: SYN → SYN-ACK → ACK |
| 5 | Application messages exchanged both ways |
| 6 | FIN / FIN-ACK teardown |

## Layout

```
vm_sim/
  __init__.py
  __main__.py      # CLI entry: python -m vm_sim
  network.py       # Virtual LAN, packets, event log
  vm.py            # VirtualMachine + TCP-like stack
  simulator.py     # Scenario orchestration
  ui.py            # Streamlit visualizer
  README.md
```

No extra dependencies beyond the project `requirements.txt` (Streamlit is already listed).
The core simulation uses only the Python standard library.
