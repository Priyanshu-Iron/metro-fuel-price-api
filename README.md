# India Metro Fuel-Price Time-Series API

A FastAPI-based REST API that provides time-series analysis of retail petrol and diesel prices across major Indian metro cities (Delhi, Mumbai, Chennai, and Kolkata).

## Features

- **Raw Price Data**: Get exact daily fuel prices
- **Moving Average**: Smoothed price trends using configurable rolling windows
- **Anomaly Detection**: Identify unusual price spikes/drops using Z-score analysis
- **Flexible Filtering**: Filter by date ranges, cities, and fuel types
- **OpenAPI Documentation**: Auto-generated Swagger UI documentation

## Project Structure

```
.
├── main.py                 # FastAPI application
├── data/                   # Dataset directory
│   └── Retail Selling Price (RSP) of Petrol and Diesel in Metro Cities.csv
├── metro-fuel-prices-api.yaml  # OpenAPI specification
├── pyproject.toml         # Poetry dependencies
├── Dockerfile             # Docker configuration
├── LICENSE                # MIT license
└── README.md              # This file
```

## Prerequisites

- Python 3.12+
- Poetry (for dependency management)
- Docker (optional, for containerized deployment)

## Installation & Setup

### Method 1: Local Development with Poetry

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Install Poetry** (if not already installed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```

4. **Place the dataset**
   - Create a `data/` directory in the project root
   - Place the CSV file: `Retail Selling Price (RSP) of Petrol and Diesel in Metro Cities.csv` in the `data/` directory

5. **Run the server**
   ```bash
   poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```


### Method 2: Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t fuel-price-api .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 fuel-price-api
   ```

### Method 3: GitHub Codespaces (Cloud, No Local Docker Needed)

1. Open this repository in GitHub Codespaces (via the green "Code" button → "Codespaces").
2. In the Codespaces terminal, build the Docker image:
   ```bash
   docker build -t fuel-price-api .
   ```
3. Run the container:
   ```bash
   docker run -p 8000:8000 fuel-price-api
   ```
4. Use the "Ports" tab to open port 8000 in your browser and access the API.

## API Reference

Once the server is running, interactive docs are available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

The OpenAPI spec (`metro-fuel-prices-api.yaml`) is also included in the repository root and can be imported into Postman or Swagger Editor.

All endpoints share these parameters:
- `city` (required): Delhi, Mumbai, Chennai or Kolkata
- `product` (required): Petrol or Diesel
- `from` (optional): Start date (YYYY-MM-DD)
- `to` (optional): End date (YYYY-MM-DD)

#### 1. Raw Price Data - `/ts/raw`
Get exact daily retail prices.

**Example:**
```bash
curl "http://localhost:8000/ts/raw?city=Delhi&product=Petrol&from=2024-01-01&to=2024-01-31"
```

#### 2. Moving Average - `/ts/ma`
Get smoothed price trends using rolling averages.

**Additional Parameters:**
- `window` (optional): Rolling window size (e.g., "7d" for 7 days, "2w" for 2 weeks). Default: "7d"

**Example:**
```bash
curl "http://localhost:8000/ts/ma?city=Mumbai&product=Diesel&window=14d"
```

#### 3. Anomaly Detection - `/ts/anomaly`
Identify unusual price movements using Z-score analysis.

**Additional Parameters:**
- `window` (optional): Rolling window for statistics calculation. Default: "7d"
- `z` (optional): Z-score threshold for anomaly detection. Default: 2.5

**Example:**
```bash
curl "http://localhost:8000/ts/anomaly?city=Chennai&product=Petrol&z=2.0&window=10d"
```

## Testing the API

### Using curl
```bash
# Test basic connectivity
curl http://localhost:8000/

# Get raw petrol prices for Delhi
curl "http://localhost:8000/ts/raw?city=Delhi&product=Petrol"

# Get 14-day moving average for Mumbai diesel
curl "http://localhost:8000/ts/ma?city=Mumbai&product=Diesel&window=14d"

# Detect anomalies in Chennai petrol prices
curl "http://localhost:8000/ts/anomaly?city=Chennai&product=Petrol&z=2.0"
```

### Using Python requests
```python
import requests

base_url = "http://localhost:8000"

# Get raw data
response = requests.get(f"{base_url}/ts/raw", params={
    "city": "Delhi",
    "product": "Petrol",
    "from": "2024-01-01",
    "to": "2024-01-31"
})
data = response.json()
print(f"Found {len(data)} price points")
```

## Data Format

The API expects a CSV file with the following structure:
- Date column (calendar day)
- City column (metro cities)
- Product column (fuel type)
- Price column (retail selling price in INR/L)

Missing price values are treated as 0.

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Formatting
```bash
poetry run black main.py
poetry run isort main.py
```

### Adding Dependencies
```bash
poetry add <package-name>
```

## Docker Commands

```bash
# Build image
docker build -t fuel-price-api .

# Run container
docker run -p 8000:8000 fuel-price-api

# Run in background
docker run -d -p 8000:8000 --name fuel-api fuel-price-api

# View logs
docker logs fuel-api

# Stop container
docker stop fuel-api
```

## API Response Examples

### Raw Price Response
```json
[
  {
    "date": "2024-01-31",
    "price": 94.77,
    "unit": "INR/L"
  },
  {
    "date": "2024-01-30",
    "price": 94.77,
    "unit": "INR/L"
  }
]
```

### Moving Average Response
```json
[
  {
    "date": "2024-01-31",
    "price": 94.77,
    "ma": 94.65
  }
]
```

### Anomaly Detection Response
```json
[
  {
    "date": "2024-01-31",
    "price": 94.77,
    "z": 0.1,
    "isAnomaly": false
  },
  {
    "date": "2024-01-15",
    "price": 98.00,
    "z": 3.2,
    "isAnomaly": true
  }
]
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Kill process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

2. **CSV file not found**
   - Ensure the CSV file is placed in the `data/` directory
   - Check the exact filename matches the expected name

3. **Permission errors in Docker**
   - The Dockerfile creates a non-root user for security
   - Ensure file permissions are correct

### Logs and Debugging

- Check server logs for column detection and data loading information
- Use the `/docs` endpoint to test API calls interactively
- Verify CSV data format and column names

## Tech Stack

- **FastAPI** – web framework and OpenAPI docs
- **Pandas** – data loading, rolling statistics and anomaly detection
- **Poetry** – dependency management
- **Docker** – containerized deployment

## License

This project is licensed under the MIT License – see [LICENSE](LICENSE) for details.
