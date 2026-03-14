"""python -m agent [--dry-run] [--date YYYY-MM-DD]"""
import asyncio
from agent.runner import main
asyncio.run(main())
