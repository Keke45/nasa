# 🚀 Autonomous Astronaut Health Intelligence System

A real-time, full-stack health telemetry ingestion and anomaly intelligence platform designed to monitor astronaut vital signs and mission readiness autonomously.

---

## 📋 Overview

Space missions demand continuous, low-latency oversight of crew health without relying solely on manual check-ins. The **Autonomous Astronaut Health Intelligence System** ingests live biometric telemetry, evaluates physiological baselines, detects anomalies using machine learning models, and presents actionable status indicators on a unified mission control dashboard.

---

## 🏗️ System Architecture

The platform integrates three core services working together seamlessly:

1. **Core Telemetry & Registration API (`backend/`)**
   - **Language & Framework:** Go (`net/http` standard library router with CORS middleware)
   - **Database:** SQLite (`astronaut_health.db`) for lightweight, high-reliability persistence
   - **Responsibilities:** Health checks (`/api/health`), real-time telemetry ingestion (`/api/telemetry`), and astronaut registration (`/api/astronauts`) bridged directly to the intelligence engine.

2. **Intelligence & Anomaly Engine (`intelligence-backend/`)**
   - **Language & Framework:** Python (Django / REST API)
   - **Capabilities:** Baseline physiological modeling, statistical trend prediction, and ML-driven anomaly detection across incoming telemetry streams.

3. **Mission Control Dashboard (`frontend/`)**
   - **Stack:** React, Vite, and Tailwind CSS
   - **Responsibilities:** Real-time visualization of astronaut vitals, telemetry status alerts, and crew onboarding.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | Go, SQLite |
| **Intelligence Service** | Python, Django, Scikit-Learn / Statistical ML |
| **Frontend UI** | React, Vite, Tailwind CSS |
| **Version Control** | Git & GitHub |

---

## 🚀 Getting Started

### Prerequisites
- **Go** (1.21+)
- **Node.js & npm** (18+)
- **Python** (3.10+)

### 1. Start the Go Telemetry Backend
```bash
cd backend
go mod tidy
go run main.go
