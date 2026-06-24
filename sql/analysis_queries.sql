-- =============================================================
-- Annotation Analytics Dashboard — Business Analysis Queries
-- Database: SQLite (compatible with PostgreSQL / MySQL)
-- Data: IDIR Lab annotation platform (synthetic, 168K+ records)
-- Author: Prakhyat Chaube
-- =============================================================

-- ---------------------------------------------------------------
-- SETUP: Load CSV into SQLite
-- Run in terminal:
--   sqlite3 data/annotations.db
--   .mode csv
--   .import data/annotations.csv annotations
--   .import data/annotators.csv annotators
--   .import data/projects.csv projects
-- ---------------------------------------------------------------


-- =============================================================
-- QUERY 1: Weekly Annotation Throughput by Project
-- Business Question: Are we on track to hit annotation targets?
-- Used in: Throughput Trend dashboard view
-- =============================================================
SELECT
    week,
    project_name,
    task_type,
    SUM(annotations_count)                          AS weekly_annotations,
    ROUND(AVG(accuracy_rate) * 100, 2)              AS avg_accuracy_pct,
    ROUND(AVG(avg_review_time_sec), 1)              AS avg_review_time_sec,
    COUNT(DISTINCT annotator_id)                    AS active_annotators,
    SUM(flagged_count)                              AS total_flagged
FROM annotations
GROUP BY week, project_name, task_type
ORDER BY week, project_name;


-- =============================================================
-- QUERY 2: Annotator Performance Scorecard
-- Business Question: Who are the top performers? Where are the bottlenecks?
-- Used in: Annotator Leaderboard view
-- =============================================================
SELECT
    annotator_id,
    annotator_name,
    annotator_level,
    SUM(annotations_count)                              AS total_annotations,
    ROUND(AVG(accuracy_rate) * 100, 2)                  AS avg_accuracy_pct,
    ROUND(AVG(avg_review_time_sec), 1)                  AS avg_review_time_sec,
    SUM(flagged_count)                                  AS total_flagged,
    ROUND(
        CAST(SUM(flagged_count) AS FLOAT) /
        CAST(SUM(annotations_count) AS FLOAT) * 100, 2
    )                                                   AS flag_rate_pct,
    COUNT(DISTINCT project_id)                          AS projects_worked,
    -- Efficiency score: high accuracy + low review time = best score
    ROUND(
        (AVG(accuracy_rate) * 100) /
        (AVG(avg_review_time_sec) / 30.0), 2
    )                                                   AS efficiency_score
FROM annotations
GROUP BY annotator_id, annotator_name, annotator_level
ORDER BY efficiency_score DESC;


-- =============================================================
-- QUERY 3: Task Type Complexity Analysis
-- Business Question: Which task types create the most bottleneck?
-- Used in: Task Complexity Breakdown view
-- =============================================================
SELECT
    task_type,
    project_name,
    COUNT(DISTINCT annotator_id)                        AS annotator_count,
    SUM(annotations_count)                              AS total_annotations,
    ROUND(AVG(avg_review_time_sec), 1)                  AS avg_review_time_sec,
    ROUND(MIN(avg_review_time_sec), 1)                  AS min_review_time_sec,
    ROUND(MAX(avg_review_time_sec), 1)                  AS max_review_time_sec,
    ROUND(AVG(accuracy_rate) * 100, 2)                  AS avg_accuracy_pct,
    ROUND(
        CAST(SUM(flagged_count) AS FLOAT) /
        CAST(SUM(annotations_count) AS FLOAT) * 100, 2
    )                                                   AS flag_rate_pct
FROM annotations
GROUP BY task_type, project_name
ORDER BY avg_review_time_sec DESC;


-- =============================================================
-- QUERY 4: Monthly Trend — Accuracy vs Volume Trade-off
-- Business Question: Does accuracy drop as volume scales up? (Fatigue analysis)
-- Used in: Quality Trend line chart
-- =============================================================
SELECT
    month,
    project_name,
    annotator_level,
    SUM(annotations_count)                              AS monthly_volume,
    ROUND(AVG(accuracy_rate) * 100, 2)                  AS avg_accuracy_pct,
    ROUND(AVG(avg_review_time_sec), 1)                  AS avg_review_time_sec,
    SUM(flagged_count)                                  AS monthly_flagged,
    -- Month-over-month flag rate
    ROUND(
        CAST(SUM(flagged_count) AS FLOAT) /
        CAST(SUM(annotations_count) AS FLOAT) * 100, 2
    )                                                   AS flag_rate_pct
FROM annotations
GROUP BY month, project_name, annotator_level
ORDER BY month, project_name;


-- =============================================================
-- QUERY 5: Bottleneck Detection — Low Accuracy + High Volume Days
-- Business Question: Which days had quality issues that need review?
-- Used in: Operational alerts / QA flagging
-- =============================================================
SELECT
    date,
    annotator_name,
    annotator_level,
    project_name,
    task_type,
    annotations_count,
    ROUND(accuracy_rate * 100, 2)                       AS accuracy_pct,
    avg_review_time_sec,
    flagged_count,
    CASE
        WHEN accuracy_rate < 0.82 AND annotations_count > 150
            THEN 'HIGH RISK — Volume + Quality Issue'
        WHEN accuracy_rate < 0.82
            THEN 'QUALITY ALERT'
        WHEN annotations_count > 200 AND accuracy_rate < 0.87
            THEN 'FATIGUE RISK'
        ELSE 'Normal'
    END                                                 AS alert_status
FROM annotations
WHERE accuracy_rate < 0.85 OR annotations_count > 200
ORDER BY accuracy_rate ASC, annotations_count DESC
LIMIT 50;


-- =============================================================
-- BONUS QUERY: Project Completion Forecast
-- Business Question: At current pace, when will each project hit its target?
-- Note: Targets defined in projects.csv
-- =============================================================
WITH project_totals AS (
    SELECT
        project_id,
        project_name,
        SUM(annotations_count)              AS completed,
        MIN(date)                           AS start_date,
        MAX(date)                           AS last_date,
        CAST(
            julianday(MAX(date)) -
            julianday(MIN(date)) AS FLOAT
        )                                   AS days_elapsed
    FROM annotations
    GROUP BY project_id, project_name
)
SELECT
    pt.project_name,
    pt.completed,
    p.target_annotations,
    pt.completed * 100 / p.target_annotations       AS pct_complete,
    ROUND(pt.completed / pt.days_elapsed, 0)        AS daily_rate,
    ROUND(
        (p.target_annotations - pt.completed) /
        (pt.completed / pt.days_elapsed), 0
    )                                               AS est_days_remaining
FROM project_totals pt
JOIN projects p ON pt.project_id = p.project_id
ORDER BY pct_complete DESC;
