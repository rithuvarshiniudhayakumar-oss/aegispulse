"""AegisPulse dashboard. Run: streamlit run apps/dashboard/app.py"""
import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API = os.getenv("AEGISPULSE_API", "http://localhost:8000")
st.set_page_config(page_title="AegisPulse", page_icon="🛡️", layout="wide")


def call(method, path, **kwargs):
    try:
        resp = requests.request(method, f"{API}{path}", timeout=60, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"API error on {path}: {exc}")
        return None


st.title("🛡️ AegisPulse")
st.caption(f"Incident intelligence on simulated microservice telemetry · API: {API}")

scenarios = call("GET", "/scenarios")
if not scenarios:
    st.stop()

with st.sidebar:
    st.header("Simulation")
    scenario = st.selectbox("Scenario", [s["name"] for s in scenarios])
    fixed = st.checkbox("Fixed seed (reproducible)")
    seed = st.number_input("Seed", value=1, step=1) if fixed else None
    if st.button("Run monitoring cycle", type="primary", use_container_width=True):
        payload = {"scenario": scenario, "seed": int(seed) if fixed else None,
                   "include_timeseries": True}
        st.session_state["result"] = call("POST", "/simulate", json=payload)

tab_overview, tab_metrics, tab_incidents, tab_bench = st.tabs(
    ["Overview", "Metrics", "Incidents", "Benchmark"])
result = st.session_state.get("result")

with tab_overview:
    if not result:
        st.info("Pick a scenario in the sidebar and click **Run monitoring cycle**.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Severity", result["severity"])
        c2.metric("Risk score", result["risk_score"])
        c3.metric("Root cause", result["root_cause"] or "None")
        c4.metric("Matches ground truth", "Yes" if result["root_cause_correct"] else "No")
        if result["incident_id"]:
            note = " (existing incident reused)" if result["deduplicated"] else " (new)"
            st.warning(f"Incident #{result['incident_id']}{note}")
        if result["recommendation"]:
            st.info(result["recommendation"])
        left, right = st.columns(2)
        with left:
            st.subheader("Service status")
            st.dataframe(pd.DataFrame(result["services"]), use_container_width=True,
                         hide_index=True)
        with right:
            st.subheader("Root cause ranking")
            if result["root_cause_ranking"]:
                rank = pd.DataFrame(result["root_cause_ranking"])
                st.plotly_chart(px.bar(rank, x="service", y="share"),
                                use_container_width=True)
            else:
                st.success("No anomalous services.")

with tab_metrics:
    if not result:
        st.info("Run a cycle first.")
    else:
        ts = pd.DataFrame(result["timeseries"])
        ts["timestamp"] = pd.to_datetime(ts["timestamp"])
        metric = st.selectbox("Metric", ["cpu", "memory", "latency", "error_rate",
                                         "requests", "anomaly_score"])
        st.plotly_chart(px.line(ts, x="timestamp", y=metric, color="service"),
                        use_container_width=True)

with tab_incidents:
    status = st.selectbox("Filter", ["All", "OPEN", "ACKNOWLEDGED", "RESOLVED"])
    items = call("GET", "/incidents", params={} if status == "All" else {"status": status})
    if items is not None and not items:
        st.info("No incidents.")
    for inc in items or []:
        title = f"#{inc['id']} · {inc['severity']} · {inc['root_cause']} · {inc['status']}"
        with st.expander(title):
            st.write(f"Risk {inc['risk_score']} · affected: {', '.join(inc['affected_services'])}")
            st.write(inc["recommendation"])
            a, b = st.columns(2)
            if inc["status"] == "OPEN" and a.button("Acknowledge", key=f"a{inc['id']}"):
                call("PATCH", f"/incidents/{inc['id']}/status", json={"status": "ACKNOWLEDGED"})
                st.rerun()
            if inc["status"] != "RESOLVED" and b.button("Resolve", key=f"r{inc['id']}"):
                call("PATCH", f"/incidents/{inc['id']}/status", json={"status": "RESOLVED"})
                st.rerun()

with tab_bench:
    st.caption("Synthetic train and test data from one simulator: an optimistic estimate.")
    n = st.slider("Seeds per scenario", 1, 20, 5)
    if st.button("Run benchmark"):
        report = call("GET", "/benchmark", params={"seeds": n})
        if report:
            det = report["detector_point_level"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precision", det["precision"])
            c2.metric("Recall", det["recall"])
            c3.metric("F1", det["f1"])
            c4.metric("False positive rate", det["false_positive_rate"])
            acc = pd.DataFrame(report["root_cause_top1_accuracy"].items(),
                               columns=["scenario", "top1_accuracy"])
            st.plotly_chart(px.bar(acc, x="scenario", y="top1_accuracy", range_y=[0, 1]),
                            use_container_width=True)
            st.write(f"False alarm rate on normal operations: "
                     f"{report['normal_ops_false_alarm_rate']}")
