#!/usr/bin/env python3
"""Walks the key journey in a real browser. usage: e2e_browser.py [BASE_URL] [SCREENSHOT_DIR]"""

import random
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def money_value(text):
    return int(re.sub(r"[^0-9]", "", text))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    shots = Path(sys.argv[2] if len(sys.argv) > 2 else "e2e-screenshots")
    shots.mkdir(parents=True, exist_ok=True)
    name = f"Browser Test {random.randrange(10**6)}"
    amount = 12_500

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 760})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def total_savings():
            page.goto(f"{base}/#dashboard")
            stat = page.locator(".stat", has_text="Total savings").locator("dd")
            expect(stat).to_contain_text("UGX")
            return money_value(stat.inner_text())

        before = total_savings()
        page.screenshot(path=shots / "dashboard.png")

        page.goto(f"{base}/#members")
        page.get_by_label("Full name").fill(name)
        page.get_by_label("Phone").fill(f"+2564{random.randrange(10**8):08d}")
        page.get_by_role("button", name="Add member").click()
        expect(page.locator("#status")).to_have_text("Member added.")
        expect(page.locator("tbody")).to_contain_text(name)
        page.screenshot(path=shots / "members.png")

        page.goto(f"{base}/#contributions")
        page.get_by_label("Member").select_option(label=name)
        page.get_by_label("Amount").fill(str(amount))
        page.get_by_role("button", name="Record contribution").click()
        expect(page.locator("#status")).to_have_text("Contribution recorded.")
        expect(page.locator("tbody")).to_contain_text(name)
        page.screenshot(path=shots / "contributions.png")

        page.goto(f"{base}/#loans")
        expect(page.locator(".badge-late").first).to_contain_text("Late")
        page.screenshot(path=shots / "loans.png")

        after = total_savings()
        if after != before + amount:
            sys.exit(f"FAIL savings went from {before} to {after}, expected +{amount}")

        # A rejected entry must explain itself on screen, not fail silently.
        page.goto(f"{base}/#members")
        page.get_by_label("Full name").fill(name)
        page.get_by_label("Phone").fill("not-a-phone")
        page.get_by_role("button", name="Add member").click()
        expect(page.locator("#status")).to_contain_text("phone")

        if errors:
            sys.exit(f"FAIL JavaScript errors: {errors}")
        browser.close()
    print("ok   the journey works in a real browser")


if __name__ == "__main__":
    main()
