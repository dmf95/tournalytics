"""
This __init__.py file initializes the tabs package and makes individual tab modules
available for import. Each tab represents a specific section or functionality
within the Tournaments page.
"""

from .standings import render as standings_render
from .league import render as league_render
from .playoffs import render as playoffs_render
from .finals import render as finals_render
from .setup import render as setup_render

__all__ = [
  "standings_render", 
  "league_render", 
  "playoffs_render", 
  "finals_render",
  "setup_render"
  ]
