"""
Annotation Analytics — Analysis Runner
Runs all 5 SQL queries via pandas, exports results as CSVs for Tableau/Power BI,
and generates matplotlib charts for README screenshots.

Run: python analysis/run_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import sqlite3
import os

os.makedirs("dashboard_exports", exist_ok=True)
os.makedirs("assets", exist_ok=True)

# --- Load data ---
df = pd.read_csv("data/annotations.csv", parse_dates=["date"])
projects_df = pd.read_csv("data/projects.csv")

print(f"Loaded {len(df):,} records | {df['annotations_count'].sum():,} total annotations\n")

# ================================================================
# QUERY 1: Weekly Throughput by Project
# ================================================================
q1 = (df.groupby(["week", "project_name", "task_type"])
        .agg(
            weekly_annotations=("annotations_count", "sum"),
            avg_accuracy_pct=("accuracy_rate", lambda x: round(x.mean() * 100, 2)),
            avg_review_time_sec=("avg_review_time_sec", "mean"),
            active_annotators=("annotator_id", "nunique"),
            total_flagged=("flagged_count", "sum"),
        )
        .reset_index())
q1.to_csv("dashboard_exports/q1_weekly_throughput.csv", index=False)
print("✅ Q1 exported: weekly throughput by project")

# ================================================================
# QUERY 2: Annotator Performance Scorecard
# ================================================================
q2 = (df.groupby(["annotator_id", "annotator_name", "annotator_level"])
        .agg(
            total_annotations=("annotations_count", "sum"),
            avg_accuracy_pct=("accuracy_rate", lambda x: round(x.mean() * 100, 2)),
            avg_review_time_sec=("avg_review_time_sec", "mean"),
            total_flagged=("flagged_count", "sum"),
            projects_worked=("project_id", "nunique"),
        )
        .reset_index())
q2["flag_rate_pct"] = (q2["total_flagged"] / q2["total_annotations"] * 100).round(2)
q2["efficiency_score"] = (q2["avg_accuracy_pct"] / (q2["avg_review_time_sec"] / 30)).round(2)
q2 = q2.sort_values("efficiency_score", ascending=False)
q2.to_csv("dashboard_exports/q2_annotator_scorecard.csv", index=False)
print("✅ Q2 exported: annotator performance scorecard")

# ================================================================
# QUERY 3: Task Type Complexity
# ================================================================
q3 = (df.groupby(["task_type", "project_name"])
        .agg(
            annotator_count=("annotator_id", "nunique"),
            total_annotations=("annotations_count", "sum"),
            avg_review_time_sec=("avg_review_time_sec", "mean"),
            min_review_time=("avg_review_time_sec", "min"),
            max_review_time=("avg_review_time_sec", "max"),
            avg_accuracy_pct=("accuracy_rate", lambda x: round(x.mean() * 100, 2)),
        )
        .reset_index())
q3["flag_rate_pct"] = q3.apply(
    lambda r: round(df[(df.task_type == r.task_type) & (df.project_name == r.project_name)]["flagged_count"].sum() /
                    df[(df.task_type == r.task_type) & (df.project_name == r.project_name)]["annotations_count"].sum() * 100, 2), axis=1)
q3 = q3.sort_values("avg_review_time_sec", ascending=False)
q3.to_csv("dashboard_exports/q3_task_complexity.csv", index=False)
print("✅ Q3 exported: task type complexity")

# ================================================================
# QUERY 4: Monthly Trend
# ================================================================
q4 = (df.groupby(["month", "project_name", "annotator_level"])
        .agg(
            monthly_volume=("annotations_count", "sum"),
            avg_accuracy_pct=("accuracy_rate", lambda x: round(x.mean() * 100, 2)),
            avg_review_time_sec=("avg_review_time_sec", "mean"),
            monthly_flagged=("flagged_count", "sum"),
        )
        .reset_index())
q4["flag_rate_pct"] = (q4["monthly_flagged"] / q4["monthly_volume"] * 100).round(2)
q4.to_csv("dashboard_exports/q4_monthly_trend.csv", index=False)
print("✅ Q4 exported: monthly trend")

# ================================================================
# QUERY 5: Bottleneck / Alert Detection
# ================================================================
def alert_status(row):
    if row["accuracy_rate"] < 0.82 and row["annotations_count"] > 150:
        return "HIGH RISK"
    elif row["accuracy_rate"] < 0.82:
        return "QUALITY ALERT"
    elif row["annotations_count"] > 200 and row["accuracy_rate"] < 0.87:
        return "FATIGUE RISK"
    return "Normal"

q5 = df[(df["accuracy_rate"] < 0.85) | (df["annotations_count"] > 200)].copy()
q5["alert_status"] = q5.apply(alert_status, axis=1)
q5 = q5.sort_values(["accuracy_rate", "annotations_count"], ascending=[True, False]).head(50)
q5.to_csv("dashboard_exports/q5_bottleneck_alerts.csv", index=False)
print("✅ Q5 exported: bottleneck alerts")

# ================================================================
# CHARTS FOR README
# ================================================================
COLORS = {
    "ClaimScore Survey":  "#4C72B0",
    "Wildfire Detection": "#DD8452",
    "CheckWorthy Tweets": "#55A868",
    "senior": "#4C72B0",
    "mid":    "#DD8452",
    "junior": "#55A868",
}
plt.rcParams.update({"font.family": "sans-serif", "axes.spines.top": False, "axes.spines.right": False})

# --- Chart 1: Weekly Throughput Line ---
fig, ax = plt.subplots(figsize=(10, 4))
for proj, grp in q1.groupby("project_name"):
    ax.plot(grp["week"], grp["weekly_annotations"], marker="o", markersize=4,
            label=proj, color=COLORS.get(proj), linewidth=2)
ax.set_title("Weekly Annotation Throughput by Project", fontsize=13, fontweight="bold")
ax.set_xlabel("Week of Year (2025)")
ax.set_ylabel("Annotations")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.legend(fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("assets/chart1_weekly_throughput.png", dpi=150)
plt.close()
print("📊 Chart 1 saved")

# --- Chart 2: Annotator Efficiency Scorecard (bar) ---
fig, ax = plt.subplots(figsize=(9, 5))
colors = [COLORS.get(lvl, "#888") for lvl in q2["annotator_level"]]
bars = ax.barh(q2["annotator_name"], q2["efficiency_score"], color=colors, edgecolor="white")
ax.set_title("Annotator Efficiency Score (Accuracy / Speed)", fontsize=13, fontweight="bold")
ax.set_xlabel("Efficiency Score (higher = better)")
for bar, score in zip(bars, q2["efficiency_score"]):
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
            f"{score:.1f}", va="center", fontsize=8)
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=COLORS["senior"], label="Senior"),
                   Patch(facecolor=COLORS["mid"], label="Mid"),
                   Patch(facecolor=COLORS["junior"], label="Junior")]
ax.legend(handles=legend_elements, fontsize=9)
plt.tight_layout()
plt.savefig("assets/chart2_annotator_efficiency.png", dpi=150)
plt.close()
print("📊 Chart 2 saved")

# --- Chart 3: Accuracy vs Volume scatter (fatigue analysis) ---
fig, ax = plt.subplots(figsize=(8, 5))
monthly_summary = df.groupby(["month", "project_name"]).agg(
    volume=("annotations_count", "sum"),
    accuracy=("accuracy_rate", "mean")
).reset_index()
for proj, grp in monthly_summary.groupby("project_name"):
    ax.scatter(grp["volume"], grp["accuracy"] * 100, label=proj,
               color=COLORS.get(proj), s=80, alpha=0.85, edgecolors="white", linewidth=0.5)
z = np.polyfit(monthly_summary["volume"], monthly_summary["accuracy"] * 100, 1)
p = np.poly1d(z)
x_line = np.linspace(monthly_summary["volume"].min(), monthly_summary["volume"].max(), 100)
ax.plot(x_line, p(x_line), "k--", alpha=0.4, linewidth=1.2, label="Trend")
ax.set_title("Accuracy vs Monthly Volume — Fatigue Analysis", fontsize=13, fontweight="bold")
ax.set_xlabel("Monthly Annotation Volume")
ax.set_ylabel("Avg Accuracy (%)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.legend(fontsize=9)
ax.grid(linestyle="--", alpha=0.3)
plt.tight_layout()
plt.savefig("assets/chart3_accuracy_vs_volume.png", dpi=150)
plt.close()
print("📊 Chart 3 saved")

# --- Chart 4: Task Type Review Time ---
fig, ax = plt.subplots(figsize=(7, 4))
task_summary = df.groupby("task_type").agg(
    avg_time=("avg_review_time_sec", "mean"),
    avg_accuracy=("accuracy_rate", lambda x: x.mean() * 100)
).reset_index().sort_values("avg_time", ascending=True)
task_labels = {
    "claim_verification": "Claim Verification",
    "entity_classification": "Entity Classification",
    "relevance_labeling": "Relevance Labeling"
}
task_summary["label"] = task_summary["task_type"].map(task_labels)
bars = ax.barh(task_summary["label"], task_summary["avg_time"],
               color=["#4C72B0", "#DD8452", "#55A868"][:len(task_summary)], edgecolor="white")
ax.set_title("Avg Review Time by Task Type (Bottleneck Detection)", fontsize=12, fontweight="bold")
ax.set_xlabel("Avg Review Time (seconds)")
for bar, t in zip(bars, task_summary["avg_time"]):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{t:.1f}s", va="center", fontsize=9)
plt.tight_layout()
plt.savefig("assets/chart4_task_complexity.png", dpi=150)
plt.close()
print("📊 Chart 4 saved")

# ================================================================
# PRINT KEY INSIGHTS
# ================================================================
print("\n" + "="*60)
print("KEY INSIGHTS SUMMARY")
print("="*60)
print(f"Total annotations: {df['annotations_count'].sum():,}")
print(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}")
print(f"Active annotators: {df['annotator_id'].nunique()}")
print(f"Projects: {df['project_name'].nunique()}")
print(f"\nTop performer: {q2.iloc[0]['annotator_name']} (efficiency: {q2.iloc[0]['efficiency_score']})")
print(f"Most complex task: {q3.iloc[0]['task_type']} ({q3.iloc[0]['avg_review_time_sec']:.1f}s avg)")
print(f"Overall avg accuracy: {df['accuracy_rate'].mean()*100:.1f}%")
print(f"Total flagged records: {df['flagged_count'].sum():,}")
alerts = q5[q5["alert_status"] != "Normal"]
print(f"Alert days detected: {len(alerts)} ({len(alerts[alerts['alert_status']=='HIGH RISK'])} HIGH RISK)")
print("="*60)
print("\n✅ All exports ready in dashboard_exports/ and assets/")
print("   Load CSVs into Tableau Public or Power BI Desktop")
