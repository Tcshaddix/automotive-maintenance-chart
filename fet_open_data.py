import sqlite3
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Brand benchmark fallbacks for maintenance and reliability
BRAND_BENCHMARKS = {
    "Toyota": (380.00, 4.8),
    "Honda": (420.00, 4.7),
    "Subaru": (510.00, 4.3),
    "Mazda": (460.00, 4.5),
    "Ford": (650.00, 4.1),
    "Chevrolet": (640.00, 4.1),
    "Nissan": (520.00, 4.0),
    "Volkswagen": (680.00, 3.8),
    "BMW": (1150.00, 3.2),
    "Mercedes-Benz": (1200.00, 3.1),
    "Audi": (1100.00, 3.3),
    "Lexus": (450.00, 4.7),
    "Acura": (480.00, 4.5),
    "Hyundai": (470.00, 4.2),
    "Kia": (470.00, 4.2),
}
DEFAULT_BENCHMARK = (550.00, 4.0)


def create_resilient_session():
    """Configures a requests Session with automated retry logic and custom headers."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "AutoMaintenanceAnalyzer/1.0"
    })
    return session


def process_catalog_in_batches(batch_size=50, delay_per_request=0.1):
    conn = sqlite3.connect("maintenance.db", timeout=20)
    cursor = conn.cursor()

    # 1. Ensure target table exists with UNIQUE constraint
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS official_vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        vehicle_class TEXT,
        epa_annual_fuel_cost REAL DEFAULT 0.0,
        annual_maintenance_cost REAL DEFAULT 550.0,
        reliability_score REAL DEFAULT 4.0,
        UNIQUE(year, make, model) ON CONFLICT REPLACE
    );
    """)
    conn.commit()

    # 2. Select catalog entries that are missing or 'Unclassified' in official_vehicles
    cursor.execute("""
    SELECT c.year, c.make, c.model 
    FROM vehicle_catalog c
    LEFT JOIN official_vehicles o 
        ON c.year = o.year AND c.make = o.make AND c.model = o.model
    WHERE o.vehicle_class IS NULL OR o.vehicle_class = 'Unclassified';
    """)
    unprocessed = cursor.fetchall()
    total_unprocessed = len(unprocessed)

    if total_unprocessed == 0:
        print("✅ All vehicles in 'vehicle_catalog' have already been processed into 'official_vehicles'.")
        conn.close()
        return

    print(f"📦 Found {total_unprocessed} catalog entries requiring EPA enrichment.")
    print(f"⚙️ Running in batches of {batch_size} with a {delay_per_request}s delay between API calls...\n")

    session = create_resilient_session()
    processed_count = 0

    for i in range(0, total_unprocessed, batch_size):
        batch = unprocessed[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_unprocessed + batch_size - 1) // batch_size

        print(f"🚀 Processing Batch {batch_num}/{total_batches} ({len(batch)} vehicles)...")

        for year, make, model in batch:
            maint_cost, reliability = BRAND_BENCHMARKS.get(make, DEFAULT_BENCHMARK)

            epa_menu_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/menu/options?year={year}&make={make}&model={model}"
            epa_fuel_cost = 0.0
            v_class = "Unclassified"

            try:
                res = session.get(epa_menu_url, timeout=5)
                if res.status_code == 200 and res.text:
                    menu_data = res.json().get("menuItem", [])
                    if isinstance(menu_data, dict):
                        menu_data = [menu_data]

                    if menu_data:
                        vehicle_id = menu_data[0]["value"]
                        spec_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/{vehicle_id}"
                        spec_res = session.get(spec_url, timeout=5)

                        if spec_res.status_code == 200 and spec_res.text:
                            spec_json = spec_res.json()
                            epa_fuel_cost = float(spec_json.get("fuelCost08", 0.0))
                            v_class = spec_json.get("vClass", "Unclassified")
            except Exception as e:
                # Catch connection blips gracefully
                pass

            # Insert/replace record
            cursor.execute("""
            INSERT OR REPLACE INTO official_vehicles 
            (year, make, model, vehicle_class, epa_annual_fuel_cost, annual_maintenance_cost, reliability_score)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (year, make, model, v_class, epa_fuel_cost, maint_cost, reliability))

            processed_count += 1
            time.sleep(delay_per_request)  # Rate limiting delay

        # Commit SQLite transaction after every batch
        conn.commit()
        print(f"  ✓ Saved batch {batch_num}. Progress: {processed_count}/{total_unprocessed} vehicles done.")

    conn.close()
    print("\n🎉 Complete dataset ingestion finished successfully!")


if __name__ == "__main__":
    process_catalog_in_batches(batch_size=50, delay_per_request=0.1)