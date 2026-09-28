import sqlite3
import requests

# Target consumer makes (Leave empty [] if you want to pull EVERY make dynamically)
TARGET_MAKES = ["Toyota", "Honda", "Ford", "Chevrolet", "Subaru", "BMW", "Audi", "Volkswagen"]

YEARS_TO_FETCH = [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]


def setup_catalog_db():
    conn = sqlite3.connect("maintenance.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_catalog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        UNIQUE(year, make, model) ON CONFLICT IGNORE
    );
    """)
    conn.commit()
    conn.close()


def fetch_dynamic_catalog():
    setup_catalog_db()
    conn = sqlite3.connect("maintenance.db")
    cursor = conn.cursor()

    headers = {"Accept": "application/json"}
    total_added = 0

    print("🚀 Starting dynamic vehicle discovery via EPA API...")

    for year in YEARS_TO_FETCH:
        # 1. Fetch available makes for the year from EPA
        makes_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/menu/make?year={year}"
        try:
            res = requests.get(makes_url, headers=headers, timeout=5)
            if res.status_code != 200 or not res.text:
                continue

            menu_data = res.json().get("menuItem", [])
            # Handle single item vs list return formats from XML/JSON wrappers
            if isinstance(menu_data, dict):
                menu_data = [menu_data]

            available_makes = [m["value"] for m in menu_data]

            # Filter for target makes if list is defined
            makes_to_process = [m for m in available_makes if not TARGET_MAKES or m in TARGET_MAKES]

            for make in makes_to_process:
                # 2. Fetch models for each make & year
                models_url = f"https://www.fueleconomy.gov/ws/rest/vehicle/menu/model?year={year}&make={make}"
                model_res = requests.get(models_url, headers=headers, timeout=5)

                if model_res.status_code == 200 and model_res.text:
                    model_data = model_res.json().get("menuItem", [])
                    if isinstance(model_data, dict):
                        model_data = [model_data]

                    for model_item in model_data:
                        model_name = model_item["value"]

                        # 3. Insert into SQLite catalog
                        cursor.execute("""
                        INSERT INTO vehicle_catalog (year, make, model)
                        VALUES (?, ?, ?);
                        """, (year, make, model_name))

                        if cursor.rowcount > 0:
                            total_added += 1

        except Exception as e:
            print(f"⚠️ Error fetching {year} data: {e}")

    conn.commit()

    # Verify total catalog size
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT make), COUNT(DISTINCT model) FROM vehicle_catalog;")
    total_vehicles, distinct_makes, distinct_models = cursor.fetchone()

    print(f"\n✅ Catalog Expansion Complete!")
    print(f"Total Unique Vehicle Entries: {total_vehicles}")
    print(f"Makes Covered: {distinct_makes}")
    print(f"Models Covered: {distinct_models}\n")

    # Sample query from catalog
    cursor.execute("SELECT year, make, model FROM vehicle_catalog ORDER BY RANDOM() LIMIT 5;")
    print("Sample Discovered Vehicles:")
    for y, mk, md in cursor.fetchall():
        print(f" • {y} {mk} {md}")

    conn.close()


if __name__ == "__main__":
    fetch_dynamic_catalog()