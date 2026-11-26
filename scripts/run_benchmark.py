"""Run the benchmark, save docs/benchmark.json, and refresh the README table."""
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from incident.engine import IncidentEngine  # noqa: E402
from storage.database import Database  # noqa: E402


def main(n_seeds=10):
    with tempfile.TemporaryDirectory() as tmp:
        report = IncidentEngine(Database(f"{tmp}/bench.db")).benchmark(n_seeds)
    (ROOT / "docs" / "benchmark.json").write_text(json.dumps(report, indent=2))

    det = report["detector_point_level"]
    lines = [
        f"Measured over {report['seeds']} seeds per scenario ({det['samples']} samples).",
        "",
        "| Metric | Value |", "|---|---|",
        f"| Precision | {det['precision']} |",
        f"| Recall | {det['recall']} |",
        f"| F1 | {det['f1']} |",
        f"| False positive rate | {det['false_positive_rate']} |",
        f"| False alarms on normal operations | {report['normal_ops_false_alarm_rate']} |",
        "",
        "| Scenario | Root-cause top-1 accuracy |", "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in report["root_cause_top1_accuracy"].items()]
    block = "\n".join(lines)

    readme = ROOT / "README.md"
    text = readme.read_text()
    text = re.sub(r"(<!-- BENCHMARK:START -->).*?(<!-- BENCHMARK:END -->)",
                  lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", text, flags=re.S)
    readme.write_text(text)
    print(block)


if __name__ == "__main__":
    main()
