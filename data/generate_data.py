"""
Synthetic Annotation Platform Dataset Generator
Based on IDIR Lab annotation platform schema (3 research projects, ~50K annotations)
Run: python data/generate_data.py
Output: data/annotations.csv, data/annotators.csv, data/projects.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

# --- CONFIG ---
START_DATE = datetime(2025, 1, 15)
END_DATE   = datetime(2025, 6, 10)

PROJECTS = [
    {"project_id": "P001", "name": "ClaimScore Survey",   "task_type": "claim_verification",   "target_annotations": 20000},
    {"project_id": "P002", "name": "Wildfire Detection",  "task_type": "entity_classification","target_annotations": 18000},
    {"project_id": "P003", "name": "CheckWorthy Tweets",  "task_type": "relevance_labeling",   "target_annotations": 14000},
]

ANNOTATORS = [
    {"annotator_id": "A01", "name": "Aisha Patel",     "level": "senior",  "project_ids": ["P001", "P002"]},
    {"annotator_id": "A02", "name": "James Liu",       "level": "senior",  "project_ids": ["P001", "P003"]},
    {"annotator_id": "A03", "name": "Maria Santos",    "level": "mid",     "project_ids": ["P002", "P003"]},
    {"annotator_id": "A04", "name": "David Kim",       "level": "mid",     "project_ids": ["P001", "P002"]},
    {"annotator_id": "A05", "name": "Priya Nair",      "level": "junior",  "project_ids": ["P001"]},
    {"annotator_id": "A06", "name": "Carlos Rivera",   "level": "junior",  "project_ids": ["P002", "P003"]},
    {"annotator_id": "A07", "name": "Fatima Hassan",   "level": "mid",     "project_ids": ["P003"]},
    {"annotator_id": "A08", "name": "Tom Nguyen",      "level": "junior",  "project_ids": ["P001", "P003"]},
]

LEVEL_PARAMS = {
    "senior": {"accuracy_mean": 0.94, "accuracy_std": 0.03, "speed_mean": 38, "speed_std": 5,  "daily_count_mean": 210, "daily_count_std": 30},
    "mid":    {"accuracy_mean": 0.88, "accuracy_std": 0.04, "speed_mean": 52, "speed_std": 8,  "daily_count_mean": 170, "daily_count_std": 35},
    "junior": {"accuracy_mean": 0.81, "accuracy_std": 0.06, "speed_mean": 71, "speed_std": 12, "daily_count_mean": 130, "daily_count_std": 40},
}

TASK_COMPLEXITY = {
    "claim_verification":    {"speed_mult": 1.3, "accuracy_penalty": -0.02},
    "entity_classification": {"speed_mult": 0.9, "accuracy_penalty": 0.01},
    "relevance_labeling":    {"speed_mult": 0.75,"accuracy_penalty": 0.02},
}

def date_range(start, end):
    current = start
    while current <= end:
        # Skip weekends sometimes (annotators occasionally work weekends)
        if current.weekday() < 5 or random.random() < 0.15:
            yield current
        current += timedelta(days=1)

records = []
record_id = 1

for date in date_range(START_DATE, END_DATE):
    # Simulate ramp-up: fewer annotations in early weeks
    days_elapsed = (date - START_DATE).days
    ramp_factor = min(1.0, 0.4 + (days_elapsed / 60) * 0.6)

    for ann in ANNOTATORS:
        level = ann["level"]
        params = LEVEL_PARAMS[level]

        for proj in PROJECTS:
            if proj["project_id"] not in ann["project_ids"]:
                continue

            task = proj["task_type"]
            complexity = TASK_COMPLEXITY[task]

            # Some days annotator doesn't work this project
            if random.random() < 0.25:
                continue

            count = int(np.random.normal(
                params["daily_count_mean"] * ramp_factor,
                params["daily_count_std"]
            ))
            count = max(10, count)

            avg_review_time = max(15, np.random.normal(
                params["speed_mean"] * complexity["speed_mult"],
                params["speed_std"]
            ))

            accuracy = min(1.0, max(0.6, np.random.normal(
                params["accuracy_mean"] + complexity["accuracy_penalty"],
                params["accuracy_std"]
            )))

            # Simulate fatigue: accuracy drops slightly on high-volume days
            if count > 200:
                accuracy = max(0.6, accuracy - 0.02)

            records.append({
                "record_id":        record_id,
                "date":             date.strftime("%Y-%m-%d"),
                "week":             date.isocalendar()[1],
                "month":            date.strftime("%Y-%m"),
                "annotator_id":     ann["annotator_id"],
                "annotator_name":   ann["name"],
                "annotator_level":  level,
                "project_id":       proj["project_id"],
                "project_name":     proj["name"],
                "task_type":        task,
                "annotations_count":count,
                "avg_review_time_sec": round(avg_review_time, 1),
                "accuracy_rate":    round(accuracy, 4),
                "flagged_count":    int(count * (1 - accuracy)),
            })
            record_id += 1

df = pd.DataFrame(records)

# --- Derived columns ---
df["throughput_per_hour"] = (df["annotations_count"] / (df["avg_review_time_sec"] / 3600)).round(1)

print(f"Generated {len(df)} daily records")
print(f"Total annotations: {df['annotations_count'].sum():,}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"\nSample:\n{df.head(3).to_string()}")

df.to_csv("data/annotations.csv", index=False)

# --- Annotator summary table ---
ann_df = pd.DataFrame(ANNOTATORS)
ann_df.to_csv("data/annotators.csv", index=False)

# --- Project table ---
proj_df = pd.DataFrame(PROJECTS)
proj_df.to_csv("data/projects.csv", index=False)

print("\n✅ Saved: data/annotations.csv, data/annotators.csv, data/projects.csv")
