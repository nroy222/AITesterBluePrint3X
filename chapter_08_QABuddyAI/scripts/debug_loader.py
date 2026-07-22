"""Debug: test framework code loader directly."""
import sys
sys.path.insert(0, ".")

from pathlib import Path
from app.ingestion.loaders import load_code

# Test Selenium
root1 = Path("data/01_selenium_framework")
docs1 = load_code(root1, "selenium_framework", "ATB13xSeleniumAdvanceFramework")
print(f"Selenium files found: {len(docs1)}")
for d in docs1[:3]:
    print(f"  path={d.payload.get('path')} unit={d.payload.get('unit')} title={d.payload.get('title')}")

# Test Playwright
root2 = Path("data/02_playwright_framework")
docs2 = load_code(root2, "playwright_framework", "Advance-Playwright-Framework")
print(f"\nPlaywright files found: {len(docs2)}")
for d in docs2[:3]:
    print(f"  path={d.payload.get('path')} unit={d.payload.get('unit')} title={d.payload.get('title')}")