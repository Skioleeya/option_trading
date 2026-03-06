# GEMINI.md: Project-Wide Standards & Architecture

This document defines the overarching technical vision and general engineering standards for the **SPY 0DTE Options Dashboard** (SPX Sentinel).

## 1. Project Mission
To provide a high-frequency, low-latency institutional-grade dashboard for monitoring and analyzing 0DTE option flows, GEX levels, and market microstructure signals.

## 2. Core Technology Stack
- **Frontend**: Next.js (App Router), Tailwind CSS, Framer Motion, TanStack Query.
- **Backend/Ingest**: Rust (Performance Layer) + Python (Async Processing & Analytics).
- **Inter-Process Communication**: Shared Memory (SHM) via Apache Arrow for zero-copy data transfer.
- **Cache/Pub-Sub**: Redis (High-throughput message bus).
- **Data Source**: Longport SDK / Custom TCP Gateways.

## 3. General Development Standards
- **Component-Driven UI**: All L4 (UI) elements must be modular, accessible, and follow the [Dashboard Layout Standards](file:///C:/Users/Lenovo/.gemini/antigravity/knowledge/dashboard_layout_standards/artifacts/ui_standards.md).
- **Type Safety**: TypeScript on the frontend; Type hints on the Python backend; Strict types in Rust.
- **E2E Traceability**: Every event must carry a timestamp and source identifier from L0 to L4 to enable latency profiling.
- **Documentation**: Use `OpenSpec` for major features. Maintain `walkthrough.md` for verifiable changes.

## 4. Repository Structure
- `/l0_ingest`: Rust-based raw market data collection.
- `/l1_compute`: Heavy computational logic (Greeks, GEX).
- `/l2_decision`: Signal generation and logic gates.
- `/l3_assembly`: Data aggregation and serialization.
- `/l4_ui`: React/Next.js visualization layer.
- `/rust_kernel`: Core shared Rust utilities.
