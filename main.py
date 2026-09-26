# main.py
import re
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="India Metro Fuel-Price Time-Series API", version="1.0.0")

# Load and prepare the dataset
try:
    df = pd.read_csv(
        "data/Retail Selling Price (RSP) of Petrol and Diesel in Metro Cities.csv"
    )

    # Clean up column names (strip spaces and handle variations)
    df.columns = [c.strip() for c in df.columns]

    # Print columns for debugging
    print("Original columns:", df.columns.tolist())

    # Handle different possible column name variations
    date_col = None
    city_col = None
    product_col = None
    price_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "calendar" in col_lower or "date" in col_lower:
            date_col = col
        elif "metro" in col_lower or "cities" in col_lower or "city" in col_lower:
            city_col = col
        elif "product" in col_lower:
            product_col = col
        elif (
            "retail selling price" in col_lower
            or "rsp" in col_lower
            or "price" in col_lower
        ):
            price_col = col

    # Rename columns for easier access
    column_mapping = {}
    if date_col:
        column_mapping[date_col] = "Date"
    if city_col:
        column_mapping[city_col] = "City"
    if product_col:
        column_mapping[product_col] = "Fuel_Type"
    if price_col:
        column_mapping[price_col] = "Price"

    df = df.rename(columns=column_mapping)

    # Convert date column to datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Treat missing prices as 0
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)

    # Remove any rows with invalid dates
    df = df.dropna(subset=["Date"])

    print("Final columns:", df.columns.tolist())
    print("Data shape:", df.shape)
    print("Sample data:")
    print(df.head())

except Exception as e:
    print(f"Error loading data: {e}")
    # Create empty dataframe as fallback
    df = pd.DataFrame(columns=["Date", "City", "Fuel_Type", "Price"])

# Constants as per OpenAPI spec
CITIES = ["Delhi", "Mumbai", "Chennai", "Kolkata"]
PRODUCTS = ["Petrol", "Diesel"]


def parse_window(window: str = "7d") -> int:
    """Parse window parameter like '7d' or '2w' into number of days"""
    if not window:
        return 7

    match = re.match(r"^(\d+)([dw])$", window.lower())
    if not match:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window format: {window}. Use format like '7d' or '2w'",
        )

    value, unit = int(match.group(1)), match.group(2)
    if value <= 0:
        raise HTTPException(status_code=400, detail="Window value must be positive")

    return value if unit == "d" else value * 7


def validate_date(date_str: str) -> datetime:
    """Validate and parse date string in YYYY-MM-DD format"""
    try:
        return pd.to_datetime(date_str)
    except:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD format",
        )


def filter_data(
    city: str,
    product: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> pd.DataFrame:
    """Filter dataframe by city, product and date range"""
    # Case-insensitive product matching as per spec
    data = df[(df["City"] == city) & (df["Fuel_Type"].str.lower() == product.lower())]

    if data.empty:
        return data

    if from_date:
        from_dt = validate_date(from_date)
        data = data[data["Date"] >= from_dt]

    if to_date:
        to_dt = validate_date(to_date)
        data = data[data["Date"] <= to_dt]

    return data


@app.get("/ts/raw")
def get_raw_prices(
    city: str = Query(..., enum=CITIES, description="4 supported metros"),
    product: str = Query(
        ..., enum=PRODUCTS, description="Petrol or Diesel. (Case-insensitive.)"
    ),
    from_date: Optional[str] = Query(
        None, alias="from", description="Start date inclusive (YYYY-MM-DD)"
    ),
    to_date: Optional[str] = Query(
        None, alias="to", description="End date inclusive (YYYY-MM-DD)"
    ),
):
    """
    Raw daily price series

    Returns one point per calendar day for the chosen city & product.
    Use it when you need exact prices (e.g. a table view or an unsmoothed chart).
    """
    try:
        data = filter_data(city, product, from_date, to_date)

        if data.empty:
            return []

        # Sort by date descending (newest first) as per spec
        data = data.sort_values(by="Date", ascending=False)

        result = []
        for _, row in data.iterrows():
            result.append(
                {
                    "date": row["Date"].strftime("%Y-%m-%d"),
                    "price": float(row["Price"]),
                    "unit": "INR/L",
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/ts/ma")
def get_moving_average(
    city: str = Query(..., enum=CITIES, description="4 supported metros"),
    product: str = Query(
        ..., enum=PRODUCTS, description="Petrol or Diesel. (Case-insensitive.)"
    ),
    from_date: Optional[str] = Query(
        None, alias="from", description="Start date inclusive (YYYY-MM-DD)"
    ),
    to_date: Optional[str] = Query(
        None, alias="to", description="End date inclusive (YYYY-MM-DD)"
    ),
    window: str = Query(
        "7d",
        description="Rolling window for MA calcs. Format: <number><unit> where unit ∈ {d, w}",
    ),
):
    """
    Moving-average series

    Calculates a rolling average to smooth the raw data—super useful for trend lines.
    The window query param sets how wide the averaging bucket is.
    """
    try:
        days = parse_window(window)
        data = filter_data(city, product, from_date, to_date)

        if data.empty:
            return []

        # Sort by date ascending for rolling calculation
        data = data.sort_values("Date").copy()

        # Calculate moving average
        data["MA"] = data["Price"].rolling(window=days, min_periods=1).mean()

        result = []
        for _, row in data.iterrows():
            result.append(
                {
                    "date": row["Date"].strftime("%Y-%m-%d"),
                    "price": float(row["Price"]),
                    "ma": round(float(row["MA"]), 2),
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/ts/anomaly")
def get_anomalies(
    city: str = Query(..., enum=CITIES, description="4 supported metros"),
    product: str = Query(
        ..., enum=PRODUCTS, description="Petrol or Diesel. (Case-insensitive.)"
    ),
    from_date: Optional[str] = Query(
        None, alias="from", description="Start date inclusive (YYYY-MM-DD)"
    ),
    to_date: Optional[str] = Query(
        None, alias="to", description="End date inclusive (YYYY-MM-DD)"
    ),
    window: str = Query(
        "7d",
        description="Rolling window for anomaly calcs. Format: <number><unit> where unit ∈ {d, w}",
    ),
    z: float = Query(
        2.5,
        ge=0,
        description="Z-score threshold for anomaly detection. Higher values ⇒ fewer anomalies",
    ),
):
    """
    Anomaly-flagged series

    Uses a simple Z-score test to mark unusual spikes/dips.
    A point is an anomaly if abs(price − mean_of_window) / std_dev_of_window >= z.
    """
    try:
        days = parse_window(window)
        data = filter_data(city, product, from_date, to_date)

        if data.empty:
            return []

        # Sort by date ascending for rolling calculation
        data = data.sort_values("Date").copy()

        # Calculate rolling statistics
        data["Mean"] = data["Price"].rolling(window=days, min_periods=1).mean()
        data["Std"] = data["Price"].rolling(window=days, min_periods=1).std()

        # Handle cases where std is 0 or NaN (constant prices in window)
        data["Std"] = data["Std"].fillna(0.01)  # Small value to avoid division by zero
        data["Std"] = data["Std"].replace(0, 0.01)  # Replace exact zeros

        # Calculate Z-score
        data["Z"] = abs((data["Price"] - data["Mean"]) / data["Std"])
        data["isAnomaly"] = data["Z"] >= z

        result = []
        for _, row in data.iterrows():
            result.append(
                {
                    "date": row["Date"].strftime("%Y-%m-%d"),
                    "price": float(row["Price"]),
                    "z": round(float(row["Z"]), 2),
                    "isAnomaly": bool(row["isAnomaly"]),
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "title": "India Metro Fuel-Price Time-Series API",
        "version": "1.0.0",
        "description": "Read-only service that exposes daily retail Petrol & Diesel prices for Delhi, Mumbai, Chennai, and Kolkata.",
        "endpoints": {
            "/ts/raw": "Raw daily price series",
            "/ts/ma": "Moving-average series",
            "/ts/anomaly": "Anomaly-flagged series",
        },
        "supported_cities": CITIES,
        "supported_products": PRODUCTS,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
