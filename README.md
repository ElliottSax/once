# Automated YouTube Explainer Video System

A production-ready system for generating high-quality educational explainer videos automatically from text topics.

**Status:** 🚧 In Development (Phase 1 - Infrastructure Setup)

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **FFmpeg** with GPU support (NVIDIA NVENC recommended)
- **PostgreSQL 14+**
- **Redis 7+**
- **CUDA-capable GPU** (optional, for faster rendering)

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/yourusername/youtube-explainer-automation.git
cd youtube-explainer-automation
```

#### 2. Set up Python environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_trf
```

#### 3. Set up Remotion/TypeScript

```bash
cd remotion
npm install
cd ..
```

#### 4. Configure environment variables

```bash
# Copy template
cp .env.template .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

**Required API Keys:**
- OpenAI API key (for GPT-4 and DALL-E 3)
- Replicate API token (for Stable Diffusion XL)
- ElevenLabs API key (for voice synthesis)
- AWS credentials (for storage and rendering)

#### 5. Set up databases

```bash
# PostgreSQL
createdb video_automation

# Redis (should be running)
redis-server
```

### Usage

#### Generate a video from a topic

```bash
# Using Python CLI (coming soon)
python -m src.cli generate "Quantum Computing Explained"

# Or using the API
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Quantum Computing Explained", "duration": 300}'
```

#### Preview with Remotion

```bash
cd remotion
npm run dev
```

Open http://localhost:3000 to see the preview.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Content Intelligence                        │
│  (GPT-4 + spaCy NLP → Scene Graph Generation)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Asset Generation                             │
│  Images: DALL-E 3 + SDXL  |  Audio: ElevenLabs + Whisper    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Video Composition (Remotion)                     │
│  React-based animation → Scene sequencing → Sync             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Rendering (FFmpeg + NVENC)                         │
│  GPU acceleration → H.264 encoding → Quality validation      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 YouTube Upload + Analytics                    │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
.
├── src/                          # Python source code
│   ├── content_intelligence/     # NLP & scene generation
│   ├── script_processing/        # GPT-4 script generation
│   ├── asset_generation/         # Image & audio generation
│   ├── audio_processing/         # Whisper synchronization
│   ├── rendering/                # FFmpeg rendering pipeline
│   ├── qa/                       # Quality assurance
│   ├── orchestration/            # Temporal workflows
│   └── utils/                    # Shared utilities
│
├── remotion/                     # TypeScript/React video framework
│   └── src/
│       ├── components/           # Reusable components
│       ├── compositions/         # Video compositions
│       ├── animations/           # Animation library
│       └── utils/                # Helpers
│
├── config/                       # Configuration files
├── scripts/                      # Utility scripts
├── tests/                        # Test suite
├── docs/                         # Documentation
└── .github/workflows/            # CI/CD pipelines
```

## Development Roadmap

### ✅ Phase 1: Foundation (Weeks 1-4) - **IN PROGRESS**
- [x] Infrastructure setup
- [x] Project structure
- [x] Environment configuration
- [ ] CI/CD pipeline
- [ ] Core framework setup

### 📋 Phase 2: Content Intelligence (Weeks 5-7)
- [ ] spaCy NLP pipeline
- [ ] Concept extraction
- [ ] Visual metaphor mapping
- [ ] Scene graph generation

### 📋 Phase 3: Asset Generation (Weeks 8-11)
- [ ] Multi-provider image generation
- [ ] Character consistency system
- [ ] Audio synthesis integration
- [ ] Caching layer

### 📋 Phase 4: Animation & Composition (Weeks 12-14)
- [ ] Animation pattern library
- [ ] Remotion composition engine
- [ ] Audio-visual synchronization

### 📋 Phase 5: Rendering & QA (Weeks 15-17)
- [ ] GPU-accelerated rendering
- [ ] Quality validation automation
- [ ] Error handling & recovery

### 📋 Phase 6: Production Hardening (Weeks 18-20)
- [ ] Cost optimization
- [ ] Analytics feedback loop
- [ ] Load testing
- [ ] Production deployment

## Performance Targets

**Production Goals:**
- **Pipeline time:** 30-45 minutes per 5-8 minute video
- **Cost:** $6-12 per video (at scale)
- **Success rate:** 90-95% full automation
- **Quality:** YouTube-ready, 1080p, professional narration

**Current Status (Phase 1):**
- Infrastructure: ✅ Complete
- Development environment: ✅ Ready
- First test render: 🚧 Pending

## Cost Breakdown

Estimated cost per 5-minute video:

| Component | Provider | Cost |
|-----------|----------|------|
| Script generation | GPT-4 | $0.06 |
| Voice synthesis | ElevenLabs Turbo | $0.90 |
| Image generation (hybrid) | DALL-E 3 + SDXL | $0.56 |
| Rendering | Remotion Lambda | $0.50 |
| Storage & bandwidth | AWS S3 | $0.15 |
| **Total** | | **~$2.17** |

*Note: Costs increase with premium providers and longer videos*

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/test_content_intelligence.py
```

## Documentation

- [Production Guide](PRODUCTION_GUIDE_V2.md) - Complete technical architecture
- [API Documentation](docs/api.md) - API reference
- [Deployment Guide](docs/deployment.md) - Production deployment
- [Troubleshooting](docs/troubleshooting.md) - Common issues

## License

MIT License - see [LICENSE](LICENSE) for details

## Support

- **Issues:** https://github.com/yourusername/youtube-explainer-automation/issues
- **Discussions:** https://github.com/yourusername/youtube-explainer-automation/discussions
- **Email:** support@example.com

---

**Version:** 1.0.0-alpha
**Last Updated:** 2025-11-12
**Status:** Active Development
