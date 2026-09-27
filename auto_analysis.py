import sqlite3

# 1. Connect to local SQLite database (creates maintenance.db)
conn = sqlite3.connect("maintenance.db")
cursor = conn.cursor()

# 2. Define Table Schema
cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicle_maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    annual_cost REAL NOT NULL,
    reliability_score REAL
);
""")

# 3. Insert Sample Data
sample_data = [
    ("Toyota", "Corolla", 2019, 380.00, 4.8),
    ("Toyota", "Corolla", 2019, 410.00, 4.8),
    ("Honda", "Civic", 2020, 450.00, 4.6),
    ("Honda", "Civic", 2020, 470.00, 4.6),
    ("BMW", "3 Series", 2018, 1100.00, 3.2),
    ("BMW", "3 Series", 2018, 1250.00, 3.2),
    ("Ford", "F-150", 2021, 650.00, 4.1),
    ("Ford", "F-150", 2021, 680.00, 4.1),
]

cursor.executemany("""
INSERT INTO vehicle_maintenance (make, model, year, annual_cost, reliability_score)
VALUES (?, ?, ?, ?, ?);
""", sample_data)

conn.commit()

# 4. Execute Analysis Query
query = """
SELECT 
    make,
    model,
    year,
    ROUND(AVG(annual_cost), 2) AS avg_annual_cost,
    ROUND(AVG(annual_cost) * 10, 2) AS estimated_10yr_cost,
    ROUND(AVG(reliability_score), 1) AS avg_reliability
FROM vehicle_maintenance
GROUP BY make, model, year
HAVING COUNT(*) >= 2
ORDER BY estimated_10yr_cost ASC;
"""

cursor.execute(query)
rows = cursor.fetchall()

# 5. Output Formatted Results
print("\n--- 10-Year Automotive Maintenance Cost Ranking ---")
print(f"{'MAKE':<10} | {'MODEL':<10} | {'YEAR':<5} | {'AVG ANNUAL':<10} | {'10-YR COST':<10} | {'SCORE':<5}")
print("-" * 65)
for make, model, year, avg_annual, est_10yr, score in rows:
    print(f"{make:<10} | {model:<10} | {year:<5} | ${avg_annual:<9} | ${est_10yr:<9} | {score:<5}")

conn.close()