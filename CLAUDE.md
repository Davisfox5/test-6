# CLAUDE.md

SportsCode-style video clip tagging. Flask backend (`app.py`), a single-page
vanilla JS frontend in `templates/index.html` plus `static/`, and an
orchestrator (`orchestrator.py`) that drives a self-healing codegen loop.

## Design

Stack: Flask with one Jinja template, vanilla CSS and JS. No framework, no build
step. Screens are `div.screen` elements toggled by an `.active` class rather than
routed.

### Tokens (from static/css/style.css)
- Background `#0f1117`, foreground `#e0e0e0`, headings `#fff`, secondary `#888`
- System font stack, 0.9rem on controls, 2.4rem on the project-list title with
  2px letter-spacing
- Dark only. There is no light theme.

### Layout
- `.screen` with `.screen.active` is the only navigation primitive
- Project list is centered, `max-width: 700px`, 60px top padding
- `.project-controls` is a 10px-gap flex row

### Rules
- Tagging is a keyboard task. Every action a user repeats during a match needs a
  key binding, and the binding is visible on screen.
- The video is the primary surface. Chrome shrinks, video does not.
- Timeline and clip state survive a reload. Losing tags mid-match is the worst
  possible failure.
- Every screen ships loading, empty, and error states.
- No new styling dependencies.

## Runtime model routing

- Runtime uses only **Haiku, Sonnet, or Opus**. **Fable is never called at
  runtime.** It is a build-time tool in Claude Code only.
- No model id is hardcoded at a call site. Resolve it from one config value.
- Every call declares its tier, a max token budget, and what happens on failure.
- High-volume paths (per request, per row, per frame) never default to Opus.

`orchestrator.py` currently calls OpenAI `gpt-4` directly with the id inline.
That predates this policy. It is flagged in the fleet routing audit and needs a
deliberate decision before anyone changes it.
