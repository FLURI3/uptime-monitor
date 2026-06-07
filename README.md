# Uptime Monitor

Lightweight self-hosted uptime monitor with an asynchronous checker, response-time history, a web dashboard, and Telegram alerts.

## Highlights

- Concurrent HTTP checks with `aiohttp`
- Availability and latency history stored in SQLite
- Flask dashboard with Chart.js response-time charts
- Telegram notifications when a service changes state
- Simple configuration suitable for small self-hosted environments

## Stack

Python, asyncio, aiohttp, Flask, SQLite, Chart.js

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.example.yaml config.yaml
python checker.py
```

In a second terminal:

```bash
python app.py
```

Open `http://localhost:8000`.

## Architecture

`checker.py` performs asynchronous checks and records state changes. `app.py` exposes the dashboard and history API. Both processes share the local SQLite database.

## Status

Functional pet project. Planned improvements include Docker packaging, authentication, webhook notifications, and automated tests.
