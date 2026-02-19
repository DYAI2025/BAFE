# BaZi Engine (BAFE) - Project Documentation

## Project Overview

**BaZi Engine** (also known as BAFE - BaZodiac Fusion Engine) is an advanced astronomical calculation engine for Chinese astrology (Four Pillars of Destiny / 八字). The engine calculates birth chart pillars (Year, Month, Day, Hour) based on precise astronomical solar-term boundaries rather than simple calendar dates, ensuring accuracy according to traditional Chinese astrological principles.

### Key Features

- **Swiss Ephemeris Integration**: Uses pyswisseph for Sun apparent longitude and solstice calculations with high precision
- **IANA Timezone Support**: With strict DST validation options for accurate time handling
- **Flexible Time Standards**: Supports both CIVIL (modern timezones) and Local Mean Time (LMT) based on longitude
- **Astronomical Boundaries**: 
  - Year boundary at LiChun (Start of Spring, 315° solar longitude)
  - Month boundaries from exact Jie solar term crossings (315° + 30°*k)
  - Day pillar from Julian Day Number (JDN) based sexagenary day index
  - Hour pillar from 2-hour branches with optional Zi hour day-boundary
- **Fusion Astrology**: Advanced integration of Western and Chinese astrological systems
- **Contract-first Validation**: API with JSON Schema validation for deterministic results
- **Containerization**: Ready for deployment with Docker and Fly.io

### Architecture

The engine consists of several core modules:

1. **bazi.py** - Main calculation logic for the BaZi chart
2. **types.py** - Data structures using TypedDict and dataclasses
3. **constants.py** - Heavenly Stems and Earthly Branches definitions
4. **time_utils.py** - Time parsing and conversion utilities
5. **ephemeris.py** - Swiss Ephemeris backend integration
6. **jieqi.py** - Solar term (Jie Qi) calculation logic
7. **cli.py** - Command-line interface
8. **app.py** - FastAPI web application
9. **western.py** - Western astrology calculation (complementary features)
10. **fusion.py** - Fusion astrology analysis combining Western and Chinese systems

### Core Algorithms

#### Year Pillar Calculation
- Uses LiChun (Start of Spring) at 315° solar longitude as the year boundary
- If birth date is before LiChun in the calendar year, the previous year's stem-branch is used
- Calculated using astronomical position rather than lunar calendar

#### Month Pillar Calculation
- Uses Jie solar terms (12 of the 24 solar terms) as month boundaries
- Each month begins at its respective Jie term
- Formula: 315° + 30°*k where k = 0,1,2...11
- Month stem is derived from year stem using traditional formula

#### Day Pillar Calculation
- Based on Julian Day Number converted to sexagenary cycle (60-day cycle)
- Uses configurable day anchor (default: 1949-10-01 as Jia-Zi day)
- Can be customized with different anchor dates for verification

#### Hour Pillar Calculation
- Based on 2-hour time periods (Earthly Branches)
- Uses traditional Chinese hours (Zi, Chou, Yin, etc.)
- Hour stem derived from day stem using traditional formula

## Building and Running

### Prerequisites
- Python 3.10+
- Swiss Ephemeris files (automatically downloaded during installation)

### Installation
```bash
# Install dependencies
pip install -e .

# For development with tests
pip install -e ".[dev]"
```

### Running the CLI
```bash
# Basic usage
python -m bazi_engine.cli 2024-02-10T14:30:00 --tz Europe/Berlin --lon 13.405 --lat 52.52

# With JSON output
python -m bazi_engine.cli 2024-02-10T14:30:00 --tz Europe/Berlin --lon 13.405 --lat 52.52 --json
```

### Running the Web API
```bash
# Start FastAPI server
uvicorn bazi_engine.app:app --host 0.0.0.0 --port 8080

# Or using the module approach
python -m bazi_engine.app
```

### Docker Containerization
```bash
# Build the image
docker build -t bazi_engine .

# Run the container
docker run -p 8080:8080 bazi_engine
```

## API Endpoints

- `GET /` - Health check
- `GET /health` - Health check
- `POST /validate` - Contract-first validator endpoint
- `POST /calculate/bazi` - Calculate BaZi chart
- `POST /calculate/western` - Calculate Western astrology chart
- `POST /calculate/fusion` - Fusion astrology analysis
- `POST /calculate/wuxing` - Calculate Wu-Xing element vector
- `POST /calculate/tst` - Calculate True Solar Time
- `GET /info/wuxing-mapping` - Get planet to Wu-Xing element mapping
- `POST /api/webhooks/chart` - ElevenLabs webhook for astrology charts

## Development Conventions

### Code Style
- Python 3.10+ with type hints
- Dataclasses for immutable data structures
- Functional approach to calculations
- Error handling with proper exceptions

### Testing Strategy
- Golden vector testing with known correct results
- Invariant validation to ensure consistent behavior
- Test-driven development approach
- Multiple test cases covering edge conditions

### Dependencies
- `pyswisseph` for astronomical calculations
- `fastapi` and `uvicorn` for web API
- `pytest` for testing
- `skyfield` (optional) as alternative ephemeris backend

## Fusion Astrology Features

The engine includes advanced fusion astrology capabilities that combine Western and Chinese astrological systems:

- **Planet-to-Element Mapping**: Maps Western planets to Chinese Wu-Xing (Five Elements)
- **Wu-Xing Vectors**: Represents elemental distributions as normalized vectors
- **Harmony Index**: Calculates compatibility between Western and Chinese charts
- **True Solar Time**: Accurate time calculations accounting for longitude and equation of time
- **Elemental Comparison**: Detailed analysis of element strengths in both systems

## Deployment

The application is configured for deployment on Fly.io with the following specifications:
- Primary region: fra (Frankfurt)
- VM: 1 shared CPU, 256MB RAM
- Auto-scaling enabled
- HTTPS enforced

## Performance

The engine is optimized for performance with:
- Efficient algorithms for astronomical calculations
- Caching mechanisms for repeated queries
- Asynchronous processing capabilities
- Containerized deployment for consistent performance

## Testing

Run all tests:
```bash
pytest -q
```

The test suite includes golden vector tests with predetermined inputs and expected outputs to ensure calculation accuracy.