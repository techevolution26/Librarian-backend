# Circle Identity Checkpoint

Added persistent `circles.icon_key` for Circle identity.

Supported keys:
- book-open
- book-marked
- library
- users
- globe
- heart
- sparkles
- landmark
- scroll
- graduation-cap

The Circle owner/admin remains the existing User identity and exposes `full_name` and `avatar_url` through Circle owner schemas.

Migration: `e1f2a3b4c5d6_add_circle_icon_key.py`

Backend source compilation: `BACKEND_COMPILE_OK`.
