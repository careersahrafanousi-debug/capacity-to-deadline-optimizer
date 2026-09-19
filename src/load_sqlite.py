"""Loads cleaned scheduling tables into SQLite for the analysis queries."""

import os
import sqlite3

import pandas as pd

DB = os.path.join("data", "scheduling.db")
TABLES = {
    "appointments": ("data", "clean", "appointments.csv"),
    "waitlist": ("data", "clean", "waitlist_scored.csv"),
    "fill_simulation": ("data", "clean", "fill_simulation.csv"),
    "dq_exceptions": ("data", "clean", "dq_exceptions.csv"),
    "provider_capacity": ("data", "raw", "provider_capacity.csv"),
    "dim_provider": ("data", "raw", "dim_provider.csv"),
    "dim_specialty": ("data", "raw", "dim_specialty.csv"),
    "dim_date": ("data", "raw", "dim_date.csv"),
}


def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    for name, parts in TABLES.items():
        df = pd.read_csv(os.path.join(*parts))
        df.to_sql(name, con, if_exists="replace", index=False)
        print(f"{name:<22} {len(df):>6} rows")
    con.commit()
    con.close()
    print(f"\nwrote {DB}")


if __name__ == "__main__":
    main()
