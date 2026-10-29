# ROADMAP.md

# The Splipperverse

> "GitHub is not a website. It is a universe."
>
> The Splipperverse transforms repositories into spatial entities within mixed reality, allowing developers to explore, understand and manage software ecosystems as physical spaces rather than lists and dashboards.

---

# Vision

The Splipperverse is an AR/MR experience for Meta Quest where source repositories exist as floating entities within a persistent room-scale environment.

The system visualises:

- Repository size
- Activity
- Relationships
- Health
- Ownership
- History
- Attention

The primary design principle is:

> Repositories should physically reflect the amount of attention they receive.

The Splipperverse is not a code editor.

It is a developer command centre.

---

# Core Concepts

## Repository Bubbles

Every repository becomes a floating sphere.

### Bubble Size

Represents repository scale.

Possible metrics:

- Lines of code
- File count
- Disk size
- Complexity score

### Bubble Colour

| State | Colour |
|---------|---------|
| Active | White / Cyan |
| Focused | Electric Blue |
| Healthy | Green |
| Warning | Amber |
| Failing | Red |
| Experimental | Purple |
| Dormant | Pale Grey |

### Bubble Motion

Motion communicates life.

- Active repositories gently pulse
- Highly active repositories emit particles
- Dormant repositories remain still
- Archived repositories become almost motionless

---

# Spatial Attention System

The room itself becomes a representation of attention.

## Floor Level (0m - 0.5m)

Dormant repositories.

Characteristics:

- Pale grey
- Low opacity
- Minimal movement
- No particle effects

These represent:

- Stubs
- Abandoned projects
- Historical archives
- One-off experiments

The floor becomes a fossil record of development history.

---

## Knee Height (0.5m - 1.0m)

Occasionally maintained repositories.

Projects that still matter but are not currently receiving significant attention.

---

## Chest Height (1.0m - 1.5m)

Healthy maintained repositories.

Projects that remain relevant and receive ongoing updates.

---

## Eye Level (1.5m - 2.0m)

Primary active development.

These are the projects currently occupying mental bandwidth.

The visual goal:

> You should know what matters immediately after entering the room.

---

## Above Head Height (2.0m+)

Mission-critical items.

Examples:

- Current sprint
- Failing builds
- Production incidents
- Immediate priorities

These should be impossible to ignore.

---

# Activity-Based Elevation

Height is never manually assigned.

Instead:

Activity creates buoyancy.

Metrics influencing elevation:

- Recent commits
- Commit frequency
- Branch activity
- Pull requests
- Issue activity
- Build status

Projects naturally rise and fall over time.

A neglected repository gradually sinks.

A revived repository rises back into view.

---

# Room Regions

The room becomes a memory palace.

## Desk Zone

Current work.

Projects actively under development.

## Wall Zones

Long-term maintained projects.

## Corner Zones

Experiments and prototypes.

## Near Floor

Historical projects and dormant repositories.

---

# MVP (Phase 1)

Goal:

Visualise repositories as interactive mixed-reality entities.

## Features

- GitHub authentication
- Repository discovery
- Bubble generation
- Bubble scaling
- Basic colour states
- Hand tracking selection
- Metadata panels
- Room persistence

### Deliverable

Walk into room and see all repositories floating in space.

---

# Phase 2: Activity Intelligence

Goal:

Visualise repository health and activity.

## Features

- Commit ingestion
- Activity scoring
- Dynamic height system
- Colour transitions
- Status indicators
- Recent activity feed

### Deliverable

Projects rise and fall automatically based on real-world usage.

---

# Phase 3: Repository Expansion

Goal:

Allow repositories to be explored spatially.

## Features

- Pinch to select
- Expand repository
- Directory visualisation
- File hierarchy display
- Search capabilities

### Deliverable

Walk through a repository as a 3D structure.

---

# Phase 4: Commit Trees

Goal:

Visualise repository history.

## Features

- Branch rendering
- Commit nodes
- Merge visualisation
- Commit metadata
- Time navigation

### Deliverable

Browse git history in three-dimensional space.

---

# Phase 5: Constellations

Goal:

Reveal hidden relationships.

## Features

- Topic clustering
- Dependency mapping
- Shared technology clustering
- Contributor overlap
- Organisation grouping

### Deliverable

Repositories form meaningful constellations.

---

# Phase 6: Splipper AI Core

Goal:

Replace menus with conversation.

## Features

- Central AI orb
- Voice commands
- Repository search
- Activity summaries
- Issue summaries
- Project recommendations

Examples:

"Show active projects."

"Show neglected repositories."

"Show BeamMP-related repositories."

"What needs my attention today?"

### Deliverable

The room becomes conversational.

---

# Phase 7: Development Analytics

Goal:

Understand where engineering time is spent.

## Features

- Attention heatmaps
- Coding trends
- Activity scoring
- Repository growth tracking
- Technical debt indicators

### Deliverable

Software effort becomes visible.

---

# Phase 8: Live Development Overlay

Goal:

Connect real development workflows.

## Features

- Open pull requests
- CI/CD integration
- Build status
- GitHub Actions
- Issue tracking
- Deployment status

### Deliverable

The Splipperverse becomes a live operational dashboard.

---

# Phase 9: Living Code

Goal:

Visualise behaviour rather than structure.

## Features

- Function relationships
- Runtime execution flows
- API visualisation
- Event streams
- Data movement

### Deliverable

Watch software operate in physical space.

---

# Phase 10: JARVIS Mode

Goal:

Achieve the complete Tony Stark experience.

## Features

- Full voice control
- AI-assisted navigation
- Context-aware recommendations
- Dynamic room orchestration
- Intelligent focus mode

Example Session:

> "Splipper, status report."

Response:

- Active repositories highlighted
- Failing projects elevated
- Recent commits summarised
- Relevant projects moved closer
- Dormant projects faded

### Deliverable

Software management becomes an immersive spatial experience.

---

# Technical Architecture

```text
GitHub API
      |
      V
Splipperverse Backend
(FastAPI)
      |
      V
Activity Engine
      |
      V
WebSocket Event Stream
      |
      V
Unity Application
      |
      V
Meta XR SDK
      |
      V
Meta Quest 3
```

---

# Technology Stack

## Backend

- Python
- FastAPI
- PostgreSQL
- Redis
- GitHub GraphQL API

## XR Client

- Unity
- Meta XR SDK
- OpenXR

## AI Layer

- Local LLM support
- OpenAI-compatible endpoints
- Voice transcription
- Semantic repository search

## Infrastructure

- Eddie (Ubuntu)
- Docker
- WebSockets
- GitHub Webhooks

---

# Success Criteria

A successful Splipperverse experience means:

- Repository importance is understood without reading text.
- Current priorities are obvious within five seconds.
- Neglected projects are immediately visible.
- Activity naturally reshapes the room.
- Developers navigate by spatial memory rather than menus.
- GitHub feels like a place.

---

# Long-Term Vision

The Splipperverse becomes a persistent mixed-reality operating environment for software development.

Developers do not browse repositories.

They enter them.

Developers do not open dashboards.

They walk through them.

Developers do not search for project status.

They look around the room.

The Splipperverse transforms software from information into architecture.
