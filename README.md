# DCFinitely

An interactive discounted cash flow (DCF) valuation platform built with Python
and Streamlit. The application will make the assumptions and calculations behind
an equity valuation straightforward to inspect.

## Quick start with Dev Containers

1. Clone this repository and open it in VS Code.
2. Select **Dev Containers: Reopen in Container** when prompted.
3. Once the container has built, run:

   ```bash
   streamlit run app.py
   ```

Streamlit is exposed on port 8501. Run the test suite with:

```bash
pytest
```

## Project structure

```text
.
├── .devcontainer/     # Reproducible VS Code development environment
├── src/               # Application modules (data, financials, valuation, UI helpers)
├── tests/             # Automated tests
└── app.py             # Streamlit entry point
```

> This project is educational and does not constitute investment advice.

## Data source

The initial provider uses [yfinance](https://ranaroussi.github.io/yfinance/) to
retrieve publicly available Yahoo Finance data without API keys. It is intended
for educational and personal-use research; statement coverage, labels, and
reporting periods can vary by company. The app identifies unavailable fields so
they can be reviewed or overridden rather than silently guessed.
