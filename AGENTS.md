# AGENTS.md

## Project goal
Build a lightweight, premium-looking admin panel for a single Xray/VLESS VPN server on one VPS.

## Stack
- Backend: FastAPI
- ORM/validation: SQLAlchemy + Pydantic
- Frontend: React + TypeScript + Vite
- UI: Tailwind CSS + shadcn/ui
- Charts: Recharts
- Database: SQLite
- Containerization: Docker Compose

Do not replace this stack.

## Product boundaries
- Xray/VLESS only
- Single server only
- No billing
- No multi-tenant logic
- No public user cabinet
- No generic ugly admin template

## Required pages
- Dashboard
- VLESS Links
- Clients
- Server Settings

## UI rules
- Russian UI labels
- English code identifiers
- Dark theme by default
- Calm premium style
- Clean spacing
- Rounded cards
- Soft shadows
- Subtle borders
- Polished tables, badges, modals, empty states, loading states

## Data rules
Seed demo data with:
- 6 VLESS links
- 2 active connections
- realistic IPs
- realistic traffic
- realistic timestamps
- recent activity/events
- at least one disabled link
- at least one idle link

## Architecture rules
- Use provider abstraction
- Default provider: MockProvider
- Real integration scaffold: XrayProvider
- Mock mode must work out of the box

## Engineering rules
- Keep code readable
- Avoid over-abstraction
- Validate payloads
- Require confirmation for destructive actions
- Keep README accurate
- Prefer shipping a coherent MVP over adding extra scope

## Finish line
The result must be a runnable, polished MVP, not just mockups or partial code.
