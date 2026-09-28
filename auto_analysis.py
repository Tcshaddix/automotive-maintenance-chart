import sqlite3


def run_real_data_analysis():
    conn = sqlite3.connect("maintenance.db")
    cursor = conn.cursor()

    # Verify official_vehicles table exists and contains data
    cursor.execute("SELECT COUNT(*) FROM official_vehicles;")
    record_count = cursor.fetchone()[0]

    if record_count == 0:
        print("⚠️ 'official_vehicles' table is empty!")
        print("Run 'python fet_open_data.py' first to populate real vehicle data.")
        conn.close()
        return

    # Query real API/benchmark data
    query = """
    SELECT 
        make,
        model,
        year,
        vehicle_class,
        annual_maintenance_cost AS annual_maint,
        epa_annual_fuel_cost AS annual_fuel,
        ROUND(annual_maintenance_cost * 10, 2) AS maint_10yr,
        ROUND(epa_annual_fuel_cost * 10, 2) AS fuel_10yr,
        ROUND((annual_maintenance_cost + epa_annual_fuel_cost) * 10, 2) AS total_10yr,
        reliability_score
    FROM official_vehicles
    ORDER BY total_10yr ASC;
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    print(f"\n--- Real 10-Year Automotive Cost Analysis ({record_count} Vehicles Analyzed) ---")
    print(
        f"{'MAKE':<10} | {'MODEL':<15} | {'YEAR':<5} | {'CLASS':<22} | {'10YR MAINT':<11} | {'10YR FUEL':<11} | {'10YR TOTAL':<11}")
    print("-" * 102)

    for row in rows:
        make, model, yr, v_class, a_maint, a_fuel, maint_10yr, fuel_10yr, total_10yr, score = row
        v_class_str = (v_class[:20] + "..") if v_class and len(v_class) > 22 else (v_class or "N/A")

        print(
            f"{make:<10} | "
            f"{model:<15} | "
            f"{yr:<5} | "
            f"{v_class_str:<22} | "
            f"${maint_10yr:<10,.2f} | "
            f"${fuel_10yr:<10,.2f} | "
            f"${total_10yr:<10,.2f}"
        )

    conn.close()


if __name__ == "__main__":
    run_real_data_analysis()