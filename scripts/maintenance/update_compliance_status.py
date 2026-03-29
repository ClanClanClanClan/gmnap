#!/usr/bin/env python3
"""
Automated V7 Compliance Status Updater
Updates CLAUDE.md with current real compliance status from audit
"""

import subprocess
import json
import re
from datetime import datetime
from pathlib import Path


def run_audit():
    """Run the comprehensive V7 reality audit and parse results."""
    try:
        result = subprocess.run(
            ["python3", "scripts/audits/comprehensive_v7_reality_audit.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Parse the output for compliance score
        output = result.stdout

        # Extract compliance percentage
        compliance_match = re.search(r"V7 COMPLIANCE:\s*(\d+\.?\d*)%", output)
        compliance = float(compliance_match.group(1)) if compliance_match else 0

        # Extract component scores
        components = {}
        score_pattern = r"(\w+(?:_\w+)*): (\d+)/(\d+)"
        for match in re.finditer(score_pattern, output):
            component = match.group(1)
            score = int(match.group(2))
            total = int(match.group(3))
            components[component] = {"score": score, "total": total}

        # Extract performance metrics
        perf_match = re.search(r"Time per million:\s*([\d.]+)\s*minutes", output)
        time_per_million = float(perf_match.group(1)) if perf_match else 0

        throughput_match = re.search(r"Throughput:\s*([\d.]+)\s*entries/sec", output)
        throughput = float(throughput_match.group(1)) if throughput_match else 0

        return {
            "compliance": compliance,
            "components": components,
            "time_per_million": time_per_million,
            "throughput": throughput,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Error running audit: {e}")
        return None


def update_claude_md(audit_results):
    """Update CLAUDE.md with current compliance status."""
    if not audit_results:
        print("No audit results to update")
        return

    # Read current CLAUDE.md
    claude_path = Path("CLAUDE.md")
    if not claude_path.exists():
        print("CLAUDE.md not found")
        return

    content = claude_path.read_text()

    # Update the date
    date_str = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(
        r"\*Last Updated: .*\*", f"*Last Updated: {date_str} (AUTO-GENERATED FROM AUDIT)*", content
    )

    # Update compliance percentage
    compliance = audit_results["compliance"]
    if compliance >= 100:
        status = "100% V7 Compliance ACHIEVED"
        state = "Production-ready"
    elif compliance >= 95:
        status = f"{compliance:.0f}% V7 Compliance"
        state = f"Near production-ready ({100-compliance:.0f} points from 100%)"
    else:
        status = f"{compliance:.0f}% V7 Compliance"
        state = f"Development - {100-compliance:.0f} points from 100%"

    content = re.sub(
        r"## 🎯 \*\*CURRENT ACHIEVEMENT:.*\*\*", f"## 🎯 **CURRENT ACHIEVEMENT: {status}**", content
    )

    content = re.sub(r"\*\*System State\*\*: .*", f"**System State**: {state}", content)

    # Update performance metrics
    tpm = audit_results["time_per_million"]
    content = re.sub(
        r"\*\*Performance\*\*: .*",
        f'**Performance**: {tpm:.1f} min/1M entries ({"EXCEEDS" if tpm < 35 else "MEETS"} 35-min target)',
        content,
    )

    # Update component scores table
    components = audit_results["components"]

    # Build new table rows
    table_rows = []
    component_names = {
        "pipeline_runs": "Pipeline Runs",
        "authority_enrichment": "Authority Enrichment",
        "graph_coherence": "Graph Coherence",
        "short_forms": "Short Forms",
        "caching": "Caching",
        "stage_10_analytics": "Stage 10 Analytics",
        "stage_12_deployment": "Stage 12 Deployment",
        "performance": "Performance",
        "idempotency": "Idempotency",
        "quality_gates": "Quality Gates",
        "regional_processing": "Regional Processing",
        "collision_detection": "Collision Detection",
    }

    total_score = 0
    total_possible = 0

    for comp_id, comp_name in component_names.items():
        if comp_id in components:
            score = components[comp_id]["score"]
            total = components[comp_id]["total"]
            total_score += score
            total_possible += total

            if score == total:
                status = "✅ Working"
                notes = "Fully operational"
            elif score > 0:
                status = "⚠️ Partial"
                notes = f"{score}/{total} points"
            else:
                status = "❌ BROKEN"
                notes = "Not working"

            table_rows.append(f"| {comp_name} | {score}/{total} | {status} | {notes} |")

    # Replace the table
    table_header = "| Component | Score | Status | Notes |\n|-----------|-------|--------|-------|"
    new_table = table_header + "\n" + "\n".join(table_rows)

    # Find and replace the compliance breakdown table
    pattern = r"\| Component \| Score \| Status \| Notes \|.*?\n\*\*TOTAL:.*?\*\*"
    replacement = new_table + f"\n\n**TOTAL: {total_score}/{total_possible} points**"
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Write back
    claude_path.write_text(content)
    print(f"✅ Updated CLAUDE.md - Compliance: {compliance:.1f}%")


def create_status_badge(compliance):
    """Create a status badge for README."""
    if compliance >= 100:
        color = "brightgreen"
        status = "100%"
    elif compliance >= 95:
        color = "green"
        status = f"{compliance:.0f}%"
    elif compliance >= 90:
        color = "yellow"
        status = f"{compliance:.0f}%"
    elif compliance >= 80:
        color = "orange"
        status = f"{compliance:.0f}%"
    else:
        color = "red"
        status = f"{compliance:.0f}%"

    badge_url = f"https://img.shields.io/badge/V7_Compliance-{status}-{color}"
    return f"![V7 Compliance]({badge_url})"


def main():
    """Main function to update compliance status."""
    print("🔍 Running V7 compliance audit...")
    audit_results = run_audit()

    if audit_results:
        print(f"📊 Current compliance: {audit_results['compliance']:.1f}%")
        print(f"⚡ Performance: {audit_results['time_per_million']:.1f} min/1M entries")

        print("\n📝 Updating CLAUDE.md...")
        update_claude_md(audit_results)

        # Save results to JSON for tracking
        results_path = Path("data/compliance_history.json")
        results_path.parent.mkdir(exist_ok=True)

        # Load existing history
        history = []
        if results_path.exists():
            try:
                history = json.loads(results_path.read_text())
            except:
                pass

        # Add new result
        history.append(audit_results)

        # Keep only last 100 entries
        history = history[-100:]

        # Save back
        results_path.write_text(json.dumps(history, indent=2))
        print(f"📈 Saved compliance history to {results_path}")

        # Create badge
        badge = create_status_badge(audit_results["compliance"])
        print(f"\n🏷️  Status badge: {badge}")

    else:
        print("❌ Failed to get audit results")


if __name__ == "__main__":
    main()
