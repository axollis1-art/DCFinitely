# DCFinitely

DCFinitely is an interactive, transparent discounted cash flow (DCF) valuation
platform for public companies. Enter a ticker to inspect sourced annual
financials, adjust operating and capital-market assumptions, and review the
full bridge from unlevered free cash flow to an implied share price.

It is designed as a portfolio-quality Python project: the Streamlit interface,
financial-data provider, valuation model, charts, and tests are intentionally
separate so the valuation logic is easy to audit.

> Educational use only. DCFinitely is not investment advice and must not be
> used as the sole basis for an investment decision.

## Screenshot

The application UI is ready for a representative screenshot. See the
[screenshot placeholder instructions](docs/screenshots/README.md), then add
`docs/screenshots/dcfinitely-dashboard.png` after a stable example valuation
has been reviewed. Do not include credentials, private data, or temporary
artefacts in screenshots.

## Features

- Public, no-key company-data retrieval through Yahoo Finance via `yfinance`
- Sourced annual historical financials, with derived values explicitly labelled
- Five-year editable forecast for revenue growth, operating margin, tax, D&A,
  Capex, and net working capital
- CAPM cost of equity and a transparent, market-value-weighted WACC
- Gordon Growth terminal value with guardrails for invalid WACC/growth pairs
- Enterprise-value to equity-value bridge and implied share price
- Interactive WACC versus terminal-growth sensitivity table with highlighted
  base case and unavailable invalid cells
- Plotly charts for revenue, operating performance, UFCF, and the DCF bridge
- Deterministic pytest coverage without live provider calls

## How the valuation works

### 1. Historical financials

The provider normalises annual income statement, cash flow, balance sheet, and
market-data fields where available. Sourced values are shown separately from
derived values, such as effective tax rate and net working capital.

### 2. Five-year forecast and UFCF

The model forecasts revenue, EBIT, D&A, Capex, and net working capital for five
explicit years. The starting assumptions are derived from the latest available
history when possible, but every forecast input is editable in the sidebar.

Unlevered free cash flow is calculated as:

```text
UFCF = EBIT * (1 - tax rate) + D&A - Capex - change in NWC
```

Capex is represented as a positive cash outflow. A positive change in net
working capital is also an outflow.

### 3. WACC

Cost of equity uses the Capital Asset Pricing Model (CAPM):

```text
Cost of equity = risk-free rate + beta * equity risk premium
```

WACC then uses market-value capital weights and the debt tax shield:

```text
WACC = E/(D+E) * cost of equity + D/(D+E) * cost of debt * (1 - tax rate)
```

Risk-free rate, equity risk premium, cost of debt, and capital structure are
visible, editable modelling assumptions. The application does not claim they
are live market data.

### 4. Terminal value and implied price

The initial release uses the Gordon Growth Method:

```text
Terminal value = UFCF in year n * (1 + g) / (WACC - g)
```

The model rejects combinations where `WACC <= g`. Enterprise value is the sum
of discounted explicit cash flows and discounted terminal value. Equity value
then equals enterprise value less debt plus cash; dividing by diluted shares
outstanding produces the implied share price.

### 5. Sensitivity analysis

The sensitivity table recalculates implied share price across editable WACC and
terminal-growth ranges. The central, highlighted cell matches the current base
case. Invalid Gordon Growth pairs are shown as `N/A`, never as a fabricated
price.

## Architecture

```text
app.py                         Streamlit presentation and user input
src/
  data/                        Provider contract and yfinance adapter
  financials/                  UFCF calculation and five-year forecasts
  valuation/                   WACC, terminal value, DCF, workflow, sensitivity
  visualisation/               Plotly chart builders
  utils/                       Shared model validation
tests/                         Deterministic unit and workflow tests
.devcontainer/                 VS Code Dev Container configuration
```

The Streamlit layer does not implement finance formulae. It collects inputs,
invokes the pure workflow/model modules, and renders their outputs. Provider
tests inject fake ticker clients, so normal tests do not call Yahoo Finance.

## Getting started

### Prerequisites

- Git
- Python 3.12 for the supported local workflow
- Or Docker and VS Code with the Dev Containers extension

### Local setup

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/axollis1-art/DCFinitely.git
cd DCFinitely
python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Install dependencies and run the application:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit (normally `http://localhost:8501`). Enter
a supported public-company ticker, such as `AAPL`, then review and edit the
assumptions in the sidebar.

### VS Code Dev Container

1. Clone the repository and open it in VS Code.
2. Choose **Dev Containers: Reopen in Container**.
3. Wait for the Python 3.12 container and dependency installation to complete.
4. Run `streamlit run app.py` from the integrated terminal.

The container includes Git, Python tooling, pytest support, useful Python VS
Code extensions, and forwards Streamlit port `8501`.

## Tests

Run the deterministic test suite with:

```bash
pytest
```

Tests cover UFCF, forecasts, discounting, present value, CAPM/WACC, terminal
value, enterprise-to-equity bridge, sensitivity generation, provider
normalisation, missing-data behaviour, and provider failures. Tests use fixtures
and mocked ticker responses; they do not depend on a live network connection.

## Data source, assumptions, and limitations

The initial provider uses [yfinance](https://ranaroussi.github.io/yfinance/), an
open-source wrapper around Yahoo Finance's publicly available endpoints. No API
key is required. Yahoo Finance data is intended for personal/educational use;
availability, reporting dates, statement labels, units, and coverage can vary
by company and market.

Important limitations of this initial release:

- Missing statement or market fields are surfaced for review, not silently
  invented. The user may need to supply an assumption manually.
- The risk-free rate, equity risk premium, and cost of debt start as editable
  model defaults rather than sourced live market inputs.
- The model uses annual historic data and a single-stage Gordon Growth terminal
  value; it does not yet offer quarterly forecasts or an exit-multiple method.
- The initial forecast model does not support companies with negative net
  working capital. It will show a clear error instead of producing a misleading
  valuation.
- DCF is particularly sensitive to WACC, terminal growth, margins, and capital
  expenditure. The sensitivity table illustrates only part of that uncertainty.
- Financial institutions, early-stage companies, and businesses with unusual
  cash-flow economics may require a different valuation approach.

## Configuration and security

Copy `.env.example` only if you need to configure a future provider. Never
commit `.env` files, API keys, cached data, virtual environments, or downloaded
datasets. The repository's `.gitignore` excludes these local artefacts.

## Future improvements

- Alternative financial-data providers and a provider-selection setting
- Exit-multiple terminal valuation alongside Gordon Growth
- Scenario save/load and valuation comparison
- Better support for negative working-capital business models
- More explicit data-quality diagnostics and source links
- CI workflow for automated tests and linting

## License

This project is available under the [MIT License](LICENSE).
