import _sqlite3
import requests
import pandas as pd

# 1. Initialize SQLite Database & Tables
conn = _sqlite3.connect("maintenance.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS official_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    nhtsa_validated INTEGER DEFAULT 0,
    epa_annual_fuel_cost REAL,
    annual_maintenance_cost REAL,
    reliability_score REAL
);
""")
conn.commit()

# 2. Fetch Open Maintenance Benchmarks from CSV
df_maintenance = pd.read_csv("maintenance_benchmarks.csv")

# 3. Enrich Each Record using Public Government APIs
for _, row in df_maintenance.iterrows():
    make = row['make']
    model = row['model']
    year = int(row['year'])
    maint_cost = float(row['annual_repair_avg'])
    reliability = float(row['reliability_score'])

    # A. Query NHTSA vPIC API (Validate Year/Make?model)
    nhtsa_url = f"https://vpic.nhtsa.dot.gov/api/vehicles/getmodelsformakeyear/make/{make}/modelyear/{year}?format=json"
    nhtsa_valid = 0
    try:
        res = requests.get(nhtsa_url, timeout=5).json()
        models_found = [m['Model_Name'].lower() for m in res.get('Results', [])]
        if model.lower() in models_found:
            nhtsa_valid = 1
    except Exception as e:
        print(f"NHTSA API call warning for {make} {model}: {e}")

    # B. Query EPA FuelEconomy.gov API (Retrieve Official Fuel Expenses)
    epa_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/menu/options?year={year}&make={make}&model={model}"
    epa_fuel_cost = 0.0
    try:
        # EPA API accepts JSON header
        epa_res = requests.get(epa_url, headers={"Accept": "application/json"}, timeout=5)
        if epa_res.status_code == 200 and epa_res.text:
            menu_data = epa_res.json()
            # If valid EPA vehicle menu items exist
            if "menuItem" in menu_data:
                items = menu_data["menuItem"]
                vehicle_id = items[0]["value"] if isinstance(items, list) else items["value"]

                # Fetch specific vehicle spec record for annual fuel estimate
                spec_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/{vehicle_id}"
                spec_res = requests.get(spec_url, headers={"Accept": "application/json"}, timeout=5).json()
                epa_fuel_cost = float(spec_res.get("fuelCost08", 0.0))
    except Exception as e:
        print(f"EPA API call warning for {make} {model}: {e}")

    # C. Insert Enriched Data into SQLite
    cursor.execute("""
    INSERT INTO official_vehicles
    (make, model, year, nhtsa_validated, epa_annual_fuel_cost, annual_maintenance_cost, reliability_score)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (make, model, year, nhtsa_valid, epa_fuel_cost, maint_cost, reliability))

    conn.commit()

    #4. Run Analysis Query: Total 10-Year Operating Cost (Fuel + Maintenance)
    query = """
    SELECT
        make,
        model,
        year,
        nhtsa_validated,
        annual_maintenance_cost AS avg_annual_maint,
        epa_annual_fuel_cost AS avg_annual_fuel,
        ROUND((annual_maintenance_cost + epa_annual_fuel_cost) * 10, 2) AS estimated_10yr_total_operating_cost,
        reliability_score
    FROM official_vehicles
    ORDER BY estimated_10yr_total_operating_cost ASC;
    """

    cursor.execute(query)
    results = cursor.fetchall()

    print("\n--- Legal & Open Data Automotive 10-Year Ownership Projections ---")
print(f"{'MAKE':<10} | {'MODEL':<10} | {'YEAR':<5} | {'NHTSA OK':<8} | {'10-YR MAINT':<12} | {'10-YR FUEL':<12} | {'10-YR TOTAL':<12}")
print("-" * 85)
for row in results:
    make, model, yr, nhtsa, maint, fuel, total_10yr, score = row
    print(f"{make:<10} | {model:<10} | {yr:<5} | {nhtsa:<8} | ${maint*10:<11.2f} | ${fuel*10:<11.2f} | ${total_10yr:<12.2f}")

conn.close()