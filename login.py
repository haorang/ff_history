"""Open a real browser window, let the user log in to NFL.com, then save the
authenticated session to auth.json for the headless crawler to reuse.

Run:  python login.py
A Chromium window opens on the NFL fantasy league page. Log in normally.
The script auto-detects a successful login, saves the session, and exits.
"""
import asyncio
from playwright.async_api import async_playwright
from config import LEAGUE_ID, AUTH_FILE, LOGGED_IN_MARKER

TARGET = (
    f"https://fantasy.nfl.com/league/{LEAGUE_ID}"
    "/history/2018/standings?historyStandingsType=final"
)
TIMEOUT_S = 600  # give up to 10 minutes to complete login


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(">>> A browser window is opening. Log in to NFL.com in that window.")
        print(">>> Waiting for login to be detected (up to 10 min)...")
        try:
            await page.goto(TARGET, wait_until="domcontentloaded")
        except Exception as e:
            print(f"initial navigation issue (ok, will keep polling): {e}")

        loops = TIMEOUT_S // 3
        for i in range(loops):
            authed = False
            try:
                if page.url.startswith(f"https://fantasy.nfl.com/league/{LEAGUE_ID}"):
                    if await page.get_by_text(LOGGED_IN_MARKER, exact=False).count() > 0:
                        authed = True
            except Exception:
                pass

            if authed:
                await context.storage_state(path=str(AUTH_FILE))
                print(f"\n✅ Login detected. Session saved to {AUTH_FILE}")
                await browser.close()
                return

            # Every ~30s, nudge back to the target page in case a post-login
            # redirect landed somewhere else.
            if i and i % 10 == 0:
                try:
                    await page.goto(TARGET, wait_until="domcontentloaded")
                except Exception:
                    pass
            await asyncio.sleep(3)

        print("\n❌ Timed out waiting for login. Re-run `python login.py` and try again.")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
