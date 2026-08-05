"""
Streamlit UI — Two-VM Network Connection Simulation

Visualizes ARP resolution, ICMP ping, TCP handshake, data exchange,
and connection teardown between two simulated virtual machines.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Allow running via `streamlit run vm_sim/ui.py` from repo root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vm_sim.simulator import Simulation
from vm_sim.network import PacketType


st.set_page_config(
    page_title="VM Connection Simulation",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Visual direction: deep slate + amber signal lights (not purple/cream) ──
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@600;700;800&display=swap');

html, body, [class*="css"] {
  font-family: 'IBM Plex Mono', monospace;
}

.stApp {
  background:
    radial-gradient(ellipse 90% 60% at 10% 0%, #1a3a32 0%, transparent 55%),
    radial-gradient(ellipse 70% 50% at 90% 100%, #2a2416 0%, transparent 50%),
    linear-gradient(165deg, #0c1210 0%, #121a18 45%, #0e1412 100%);
  color: #d8e6df;
}

h1, h2, h3, .syne {
  font-family: 'Syne', sans-serif !important;
  letter-spacing: -0.02em;
}

#MainMenu, footer, header { visibility: hidden; }

.hero-brand {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: clamp(2.2rem, 5vw, 3.4rem);
  line-height: 1.05;
  color: #f0f7f3;
  margin: 0 0 0.4rem 0;
}

.hero-sub {
  color: #8aa89a;
  font-size: 0.95rem;
  max-width: 36rem;
  margin-bottom: 1.5rem;
}

.vm-panel {
  background: linear-gradient(145deg, rgba(26, 48, 42, 0.85), rgba(14, 22, 20, 0.9));
  border: 1px solid rgba(120, 180, 150, 0.22);
  border-radius: 4px;
  padding: 1.25rem 1.4rem;
  position: relative;
  overflow: hidden;
}

.vm-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.03) 2px,
      rgba(0,0,0,0.03) 4px
    );
  pointer-events: none;
}

.vm-name {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 1.45rem;
  color: #e8f5ee;
  margin: 0;
}

.vm-meta {
  color: #7a9e8c;
  font-size: 0.78rem;
  margin-top: 0.35rem;
}

.status-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.dot-on { background: #3dcc8c; box-shadow: 0 0 8px #3dcc8c88; }
.dot-off { background: #5a625e; }
.dot-link { background: #e8a838; box-shadow: 0 0 10px #e8a83899; }

.conn-rail {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.5rem 0.5rem;
  font-size: 0.75rem;
  color: #8aa89a;
}

.rail-line {
  flex: 1;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3dcc8c88, #e8a83888, #3dcc8c88, transparent);
  position: relative;
}

.rail-label {
  font-family: 'Syne', sans-serif;
  font-weight: 600;
  color: #e8a838;
  white-space: nowrap;
}

.pkt {
  font-size: 0.78rem;
  padding: 0.45rem 0.7rem;
  margin: 0.25rem 0;
  border-left: 3px solid #3dcc8c;
  background: rgba(20, 36, 30, 0.7);
  color: #c5d9ce;
}

.pkt.arp { border-left-color: #6ec6ff; }
.pkt.icmp { border-left-color: #b48cff; }
.pkt.syn, .pkt.syn_ack, .pkt.ack { border-left-color: #e8a838; }
.pkt.data { border-left-color: #3dcc8c; }
.pkt.fin, .pkt.fin_ack { border-left-color: #e85d5d; }

.step-card {
  padding: 0.7rem 0.9rem;
  margin: 0.35rem 0;
  background: rgba(18, 32, 28, 0.75);
  border-radius: 3px;
  border: 1px solid rgba(100, 150, 125, 0.15);
}

.step-num {
  color: #e8a838;
  font-weight: 600;
  margin-right: 0.4rem;
}

.success-banner {
  background: linear-gradient(90deg, rgba(61, 204, 140, 0.18), transparent);
  border-left: 3px solid #3dcc8c;
  padding: 0.9rem 1.1rem;
  margin: 1rem 0;
  color: #d4f0e2;
  font-family: 'Syne', sans-serif;
  font-weight: 600;
}

.fail-banner {
  background: linear-gradient(90deg, rgba(232, 93, 93, 0.18), transparent);
  border-left: 3px solid #e85d5d;
  padding: 0.9rem 1.1rem;
  margin: 1rem 0;
  color: #f0d4d4;
  font-family: 'Syne', sans-serif;
  font-weight: 600;
}

.log-line {
  font-size: 0.74rem;
  color: #9bb5a8;
  padding: 0.15rem 0;
  border-bottom: 1px solid rgba(80, 110, 95, 0.15);
}

div[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0e1614 0%, #121c18 100%);
  border-right: 1px solid rgba(100, 150, 125, 0.2);
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def packet_css_class(packet_type: PacketType) -> str:
    return packet_type.value.lower()


def render_topology(connected: bool, a_on: bool, b_on: bool) -> None:
    a_dot = "dot-link" if connected else ("dot-on" if a_on else "dot-off")
    b_dot = "dot-link" if connected else ("dot-on" if b_on else "dot-off")
    rail = "SESSION UP" if connected else "vnet0 · 10.0.0.0/24"

    col_a, col_mid, col_b = st.columns([1, 0.85, 1])

    with col_a:
        st.markdown(
            f"""
            <div class="vm-panel">
              <p class="vm-name"><span class="status-dot {a_dot}"></span>alpha</p>
              <div class="vm-meta">IP 10.0.0.1 &nbsp;·&nbsp; MAC 02:00:00:00:00:01</div>
              <div class="vm-meta">role: client initiator</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_mid:
        st.markdown(
            f"""
            <div class="conn-rail">
              <div class="rail-line"></div>
              <span class="rail-label">{rail}</span>
              <div class="rail-line"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            f"""
            <div class="vm-panel">
              <p class="vm-name"><span class="status-dot {b_dot}"></span>beta</p>
              <div class="vm-meta">IP 10.0.0.2 &nbsp;·&nbsp; MAC 02:00:00:00:00:02</div>
              <div class="vm-meta">role: listening server</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def animated_flow_html(packets) -> str:
    """Lightweight CSS animation of packet types crossing the wire."""
    labels = []
    for p in packets[:18]:
        labels.append(p.packet_type.value)

    chips = "".join(
        f'<span class="chip c{i % 5}" style="animation-delay:{i * 0.18}s">{lab}</span>'
        for i, lab in enumerate(labels)
    )

    return f"""
    <style>
      .flow-wrap {{
        height: 56px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(120,180,150,0.2);
        background: rgba(10,18,16,0.8);
        border-radius: 3px;
        margin: 0.5rem 0 1rem 0;
      }}
      .flow-wire {{
        position: absolute;
        top: 50%;
        left: 8%;
        right: 8%;
        height: 1px;
        background: rgba(100,160,130,0.35);
      }}
      .chip {{
        position: absolute;
        top: 16px;
        left: -10%;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        padding: 3px 8px;
        color: #0c1210;
        background: #3dcc8c;
        border-radius: 2px;
        animation: fly 3.2s ease-in-out infinite;
        white-space: nowrap;
      }}
      .c1 {{ background: #6ec6ff; }}
      .c2 {{ background: #e8a838; }}
      .c3 {{ background: #b48cff; }}
      .c4 {{ background: #e85d5d; color: #fff; }}
      @keyframes fly {{
        0%   {{ left: -12%; opacity: 0; }}
        10%  {{ opacity: 1; }}
        90%  {{ opacity: 1; }}
        100% {{ left: 100%; opacity: 0; }}
      }}
    </style>
    <div class="flow-wrap">
      <div class="flow-wire"></div>
      {chips}
    </div>
    """


def main() -> None:
    st.markdown('<p class="hero-brand">vnet link</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">Watch two virtual machines discover each other, '
        "complete a TCP handshake, and exchange messages on a simulated LAN.</p>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Controls")
        latency = st.slider("Latency (ms)", 0.0, 50.0, 2.0, 0.5)
        port = st.number_input("Listen port", min_value=1, max_value=65535, value=8080)
        msg_a = st.text_input("Alpha → Beta message", "Hello from Alpha VM!")
        msg_b = st.text_input("Beta → Alpha message", "Hello from Beta VM!")
        run_btn = st.button("Run simulation", type="primary", use_container_width=True)
        st.markdown("---")
        st.caption(
            "CLI: `python -m vm_sim`  ·  "
            "Stack: ARP → ICMP → TCP handshake → DATA → FIN"
        )

    if "result" not in st.session_state:
        st.session_state.result = None

    if run_btn:
        with st.spinner("Bringing VMs online…"):
            sim = Simulation(
                latency_ms=latency,
                message_a_to_b=msg_a,
                message_b_to_a=msg_b,
                listen_port=int(port),
            )
            result = sim.run()
            sim.shutdown()
            st.session_state.result = result

    result = st.session_state.result

    if result is None:
        render_topology(connected=False, a_on=False, b_on=False)
        st.info("Configure options in the sidebar, then run the simulation.")
        return

    a_established = result.vm_a_status.get("established_count", 0) > 0 or any(
        c.get("state") in ("ESTABLISHED", "CLOSED_DONE", "FIN_WAIT")
        for c in result.vm_a_status.get("connections", [])
    )
    render_topology(
        connected=result.success,
        a_on=result.vm_a_status.get("powered_on", True) or True,
        b_on=result.vm_b_status.get("powered_on", True) or True,
    )

    if result.success:
        st.markdown(
            f'<div class="success-banner">✓ {result.summary}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="fail-banner">✗ {result.summary}</div>',
            unsafe_allow_html=True,
        )

    if result.packets:
        components.html(animated_flow_html(result.packets), height=70)

    tab_steps, tab_packets, tab_logs, tab_status = st.tabs(
        ["Scenario", "Packets", "VM Logs", "State"]
    )

    with tab_steps:
        for step in result.steps:
            st.markdown(
                f"""
                <div class="step-card">
                  <span class="step-num">{step.index:02d}</span>
                  <strong style="color:#e8f5ee;font-family:Syne,sans-serif">
                    {step.title}
                  </strong>
                  <div style="color:#8aa89a;font-size:0.8rem;margin-top:0.25rem">
                    {step.description}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_packets:
        for i, pkt in enumerate(result.packets, 1):
            cls = packet_css_class(pkt.packet_type)
            st.markdown(
                f'<div class="pkt {cls}"><code>{i:02d}</code> &nbsp; {pkt.summary()}</div>',
                unsafe_allow_html=True,
            )

    with tab_logs:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**alpha**")
            for line in result.vm_a_log:
                st.markdown(f'<div class="log-line">{line}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown("**beta**")
            for line in result.vm_b_log:
                st.markdown(f'<div class="log-line">{line}</div>', unsafe_allow_html=True)

    with tab_status:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**alpha status**")
            st.json(result.vm_a_status)
        with c2:
            st.markdown("**beta status**")
            st.json(result.vm_b_status)

        if result.messages_delivered:
            st.markdown("**Messages delivered**")
            for msg in result.messages_delivered:
                st.code(msg)

    # Suppress unused warning for a_established in quieter linters
    _ = a_established


if __name__ == "__main__":
    main()
