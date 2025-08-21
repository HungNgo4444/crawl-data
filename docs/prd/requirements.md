# Requirements

## Functional Requirements

**FR1**: Hệ thống sẽ crawl từ 200+ domains được configure qua **React web interface** với database storage

**FR2**: **GWEN-3 8B model sẽ analyze page structure first** để determine optimal extraction strategy cho mỗi domain

**FR3**: **Ollama GWEN-3 8B (local deployment)** với 16GB RAM allocation sẽ thực hiện intelligent content extraction

**FR4**: Crawl4AI sẽ execute extraction based trên GWEN-3's structural analysis recommendations  

**FR5**: React admin dashboard sẽ cho phép users add/edit/delete domains với real-time preview

**FR6**: GWEN-3 sẽ learn từ successful extractions để improve parsing accuracy over time

**FR7**: **GWEN-3 chạy 1 lần/ngày cho MỖI domain** - analysis structure từng domain individually

**FR8**: **Per-domain parsing templates**: Database lưu unique parsing template cho mỗi domain từ daily GWEN-3 analysis

**FR9**: **Staggered AI analysis**: 200+ domains được phân bổ analysis throughout the day (không cùng lúc)

**FR10**: **Crawl4AI per-domain execution**: Lookup specific parsing template cho domain trước khi crawl

## Non-Functional Requirements

**NFR1**: **GWEN-3 8B model phải run stable trên 16GB RAM** với optimal performance

**NFR2**: **GWEN-3 per-domain analysis**: < 5 minutes per domain (including model load/unload)

**NFR3**: **Daily analysis distribution**: 200 domains spread across 20 hours (10 domains/hour)

**NFR4**: **Template lookup performance**: < 10ms per domain template retrieval

**NFR5**: **React interface phải responsive** và support real-time domain status updates

**NFR6**: GWEN-3 analysis accuracy target: >85% cho Vietnamese news domains

**NFR7**: System architecture: **16GB RAM total** (8GB cho GWEN-3, 8GB cho other services)

**NFR8**: Web interface phải handle concurrent domain management từ multiple admin users

## Compatibility Requirements

**CR1**: **GWEN-3 8B Integration**: Model deployment phải tương thích với Ollama container trong existing Docker Compose

**CR2**: **React Frontend**: Phải integrate với existing monitoring APIs và authentication system

**CR3**: **Database Schema**: Domain analysis results phải extend PostgreSQL schema với JSON storage cho GWEN-3 outputs

**CR4**: **API Consistency**: React frontend APIs phải follow existing OpenAPI 3.0 specifications

---
