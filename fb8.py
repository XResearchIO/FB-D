import time
import asyncio
import random
import traceback
import sys
import os
import logging
import threading

from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ for accurate EST time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException, NoSuchElementException

from rich.text import Text
from rich.table import Table

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Center
from textual.widgets import (
    Button, Static, DataTable, Footer, Header, Label, Input, Log, ProgressBar,
    Pretty
)
from textual.scroll_view import ScrollView
from textual.widget import Widget
from textual.reactive import var
from textual import events, work

from dotenv import load_dotenv
load_dotenv()
FB_USERNAME = os.getenv("FB_USERNAME")
FB_PASSWORD = os.getenv("FB_PASSWORD")

# ==== CONFIGURATION ====
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
CHROMEDRIVER_PATH = r"chromedriver.exe"
MAX_RETRIES = 5
WAIT_BETWEEN_RETRIES = 180
RATE_LIMIT_WAIT = 900

# Section Exclusion/Protection
PROTECTED_SECTIONS = [
    "Photos", "Albums", "Friends", "Connections", "Groups", "Story archive", "Marketplace"
]
PROTECTED_SUBSECTIONS = [
    "Your photos", "Albums", "Friends", "Connections", "Archived stories", "Marketplace listings", "Groups", "Story archive"
]

# ==== SECTION/SUBSECTION TREE ====
SECTIONS = {
    "Comments and reactions": {
        "sub": ["Comments", "Likes and reactions"]
    },
    "Posts": {
        "sub": [
            "Your posts, photos and videos",
            "Check-ins",
            "Posts hidden from profile",
            "Other people's posts to your feed",
            "Videos you've watched",
            "Live videos you've watched",
            "Reviews",
            "Articles you've read",
            "Facebook Editor",
            "Collaborations"
        ]
    },
    "Activity you're tagged in": {
        "sub": ["Photos and videos you're tagged in"]
    },
    "Saved items and collections": {
        "sub": []
    },
    "Messages": {
        "sub": [
            "Channels",
            "Received channel invites",
            "Sent channel invites",
            "Received chat invites",
            "Sent chat invites"
        ]
    },
    "Groups": {
        "sub": [],
        "skip": True
    },
    "Reels": {
        "sub": [
            "Your reels",
            "Audio you've saved",
            "Effects you've saved",
            "Giphy clips you've saved",
            "Effects you've searched for"
        ]
    },
    "Stories": {
        "sub": [
            "Your stories",
            "Stories activity",
            "Archived stories",
            "AI stickers you've created"
        ]
    },
    "Events": {
        "sub": [
            "Your Events",
            "Your event responses",
            "Event invitations",
            "Events you've hidden"
        ]
    },
    "Pages": {
        "sub": [
            "Pages, page likes and interests",
            "Followed info centers"
        ]
    },
    "Polls": {
        "sub": [
            "Video polls you've taken"
        ]
    },
    "Facebook Marketplace": {
        "sub": [
            "Marketplace listings",
            "Your seller responses",
            "Marketplace ratings you've given",
            "Your seller information"
        ],
        "skip": True
    },
    "Shops": {
        "sub": [
            "Products",
            "Products you wanted",
            "Questions & answers"
        ]
    },
    "Meta AI": {
        "sub": [
            "Voice interactions"
        ]
    },
    "Facebook Gaming": {
        "sub": [
            "Your gaming app search history",
            "Created tournaments",
            "Your tournament matches"
        ]
    },
    "Fantasy games": {
        "sub": [
            "Fantasy Games picks"
        ]
    },
    "Volunteering": {
        "sub": [
            "Volunteering"
        ]
    },
    "Fundraisers": {
        "sub": [
            "Donations you've made",
            "Fundraisers you help manage",
            "Fundraiser matches you've created",
            "Reminders to donate"
        ]
    },
    "Live videos": {
        "sub": [
            "Your live videos"
        ]
    },
    "Other activity": {
        "sub": [
            "Other records",
            "Pokes"
        ]
    },
    "Logged information": {
        "sub": [
            "Search",
            "Location",
            "Privacy Checkup",
            "Guidance on Meta Business Suite you've hidden"
        ]
    }
}
ALL_SUBSECTIONS = []
for main, data in SECTIONS.items():
    if data.get("skip"): continue
    for sub in data["sub"]:
        if sub not in PROTECTED_SUBSECTIONS:
            ALL_SUBSECTIONS.append((main, sub))

# TRASH COLUMN SETUP
ALL_TRASH = {(main, sub): 0 for (main, sub) in ALL_SUBSECTIONS}
ALL_DELETED = {(main, sub): 0 for (main, sub) in ALL_SUBSECTIONS}

TOTAL_STEPS = 5 + len(ALL_SUBSECTIONS)*2 + 3

# Animation frames and paused art
ANIM_FRAMES = [
"""[bold red]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold white]""",
"""[bold white]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold blue]""",
"""[bold blue]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold red]""",
"""[bold red]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold white]""",
"""[bold white]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold blue]""",
"""[bold blue]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold blue]""",
]
ANIM_PAUSED = """[bold red]
      ██╗  ██╗
      ╚██╗██╔╝
       ╚███╔╝
       ██╔██╗
      ██╔╝ ██╗
      ╚═╝  ╚═╝
[/bold red]"""

def est_time():
    dt = datetime.now(ZoneInfo("US/Eastern"))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def enable_ansi_colors_on_windows():
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

enable_ansi_colors_on_windows()

progress_count = 0
item_delete_counts = {(main, sub): 0 for (main, sub) in ALL_SUBSECTIONS}
trash_counts = {(main, sub): 0 for (main, sub) in ALL_SUBSECTIONS}
deleted_counts = {(main, sub): 0 for (main, sub) in ALL_SUBSECTIONS}
error_log = []
actions_log = []
driver = None
actions = None

IS_PAUSED = False
IS_RUNNING = False
CURRENT_SECTION = "START"
CURRENT_SUBSECTION = ""
CURRENT_PASS = 1
CURRENT_ACTION = "Waiting..."
PROGRESS_PERCENT = 0
ANIM_IDX = 0
TIMER_SECONDS = 0
TIMER_TASK = None

BURN_READY = False
BURN_COUNTDOWN = 0
BURN_ACTIVE = False

# UI/UX state for trash/fire
TRASH_RUNNING_TALLY = 0
FIRE_RUNNING_TALLY = 0
TRASH_SECTION_TALLY = 0

# ==== Enhanced Textual Widgets with Robust State and Error Handling ====

class TrashBanner(Static):
    anim_idx = var(0)
    paused = var(False)
    def render(self):
        try:
            if self.paused:
                return Text.from_markup(ANIM_PAUSED)
            else:
                frame = ANIM_FRAMES[self.anim_idx % len(ANIM_FRAMES)]
                return Text.from_markup(frame)
        except Exception as e:
            return Text(f"Banner error: {e} at line {sys.exc_info()[-1].tb_lineno}", style="red")

class TrashFireBar(Horizontal):
    trash_tally = var(0)
    fire_tally = var(0)
    def compose(self) -> ComposeResult:
        yield Static(f"[bold magenta]🗑️ {self.trash_tally}  🔥 {self.fire_tally}[/bold magenta]", id="trashfirelabel")
    def update_counters(self, trash, fire):
        self.trash_tally = trash
        self.fire_tally = fire
        self.query_one("#trashfirelabel", Static).update(
            f"[bold magenta]🗑️ {self.trash_tally}  🔥 {self.fire_tally}[/bold magenta]"
        )

class PauseStartBar(Horizontal):
    paused = var(False)
    running = var(False)
    def compose(self) -> ComposeResult:
        yield Button("Start", id="btnstart", variant="success")
        yield Button("Pause", id="btnpause", variant="warning")
        yield Static("", id="clocklabel")

class StatusBar(Horizontal):
    section = var("START")
    progress = var(0)
    status = var("Idle")
    def compose(self) -> ComposeResult:
        yield Static("", id="sectionlabel")
        yield Static("", id="progresslabel")
        yield Static("", id="statuslabel")
    def update_labels(self):
        try:
            self.query_one("#sectionlabel", Static).update(
                f"[bold blue]Section:[/bold blue] [yellow]{self.section}[/yellow]"
            )
            self.query_one("#progresslabel", Static).update(
                f"[bold green]Progress:[/bold green] {self.progress:.1f}%"
            )
            self.query_one("#statuslabel", Static).update(
                f"[bold magenta]Status:[/bold magenta] [white]{self.status}[/white]"
            )
        except Exception as e:
            self.query_one("#statuslabel", Static).update(
                f"Status update error: {e} at line {sys.exc_info()[-1].tb_lineno}"
            )

class ActionLog(Static):
    def render(self):
        try:
            if not actions_log:
                return Text("No actions yet.", style="dim")
            t = Text()
            for ts, msg, col in actions_log[-15:]:
                t.append(f"{ts} {msg}\n", style=col)
            return t
        except Exception as e:
            return Text(f"ActionLog error: {e} at line {sys.exc_info()[-1].tb_lineno}", style="red")

class ErrorLog(Static):
    def render(self):
        try:
            if not error_log:
                return Text("No errors.", style="dim")
            t = Text()
            for e in error_log[-7:]:
                t.append(e + "\n", style="red")
            return t
        except Exception as e:
            return Text(f"ErrorLog error: {e} at line {sys.exc_info()[-1].tb_lineno}", style="red")

class DeletionTally(DataTable):
    def on_mount(self):
        try:
            self.add_columns("Section", "Subsection", "Trash", "Deleted")
            if not self.rows:
                for (main, sub) in ALL_SUBSECTIONS:
                    self.add_row(main, sub, "0", "0")
        except Exception as e:
            error_log.append(f"DeletionTally on_mount error: {e} line {sys.exc_info()[-1].tb_lineno}")

    def update_counts(self):
        try:
            if not self.rows:
                return
            for idx, (main, sub) in enumerate(ALL_SUBSECTIONS):
                try:
                    self.update_cell(idx, 2, str(trash_counts.get((main, sub), 0)))
                    self.update_cell(idx, 3, str(deleted_counts.get((main, sub), 0)))
                except Exception:
                    continue
        except Exception as e:
            error_log.append(f"DeletionTally update_counts error: {e} line {sys.exc_info()[-1].tb_lineno}")

class BurnBar(Static):
    burn_ready = var(False)
    burn_active = var(False)
    burn_countdown = var(0)
    def compose(self) -> ComposeResult:
        yield Button("BURN", id="btnburn", variant="error", disabled=not self.burn_ready)
        yield Static("", id="burncountdown")

# ==== UI Main App and Life Cycle Logic ====

class FBDeleteApp(App):
    CSS_PATH = None
    BINDINGS = [("q", "quit", "Quit")]
    paused = var(False)
    running = var(False)
    anim_idx = var(0)
    timer_seconds = var(0)
    timer_task = None
    deletion_task = None
    current_section = var("START")
    current_pass = var(1)
    current_action = var("Waiting...")
    progress_percent = var(0)
    burn_ready = var(False)
    burn_active = var(False)
    burn_countdown = var(0)
    trash_counter = var(0)
    fire_counter = var(0)
    successful = var(False)

    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal():
                with Vertical():
                    yield PauseStartBar(id="pausestartbar")
                    yield Static("", id="toplefttimer")
                    yield Static("", id="sectionlabeltop")
                yield TrashFireBar(id="trashfirebar")
            yield TrashBanner(id="trashbanner")
            with Horizontal(id="maincontent"):
                with Vertical():
                    yield DeletionTally(id="tally")
                    yield ActionLog(id="actionlog")
                    yield ErrorLog(id="errorlog")
            yield Static("", id="timerlabel")
            with Center():
                yield BurnBar(id="burnbar")
                yield Static("", id="successlabel")
            yield Footer()

    # ============ UI LIFECYCLE & EVENTS =============

    async def on_mount(self, event):
        try:
            self.query_one(TrashBanner).anim_idx = 0
            self.query_one(TrashBanner).paused = self.paused
            self.set_interval(0.7, self._animate_trash)
            self.set_interval(1.0, self._update_time)
            await self.reset_timer()
            await self.update_statusbar()
            await self.update_tally()
            self.query_one(BurnBar).burn_ready = self.burn_ready
            self.query_one(BurnBar).burn_active = self.burn_active
            self.query_one(BurnBar).burn_countdown = self.burn_countdown
            self.query_one(TrashFireBar).update_counters(self.trash_counter, self.fire_counter)
        except Exception as e:
            error_log.append(f"on_mount error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def _animate_trash(self):
        try:
            trash = self.query_one(TrashBanner)
            if self.running and not self.paused:
                self.anim_idx = (self.anim_idx + 1) % len(ANIM_FRAMES)
                trash.anim_idx = self.anim_idx
                trash.paused = False
            else:
                trash.paused = True
            trash.refresh()
        except Exception as e:
            error_log.append(f"_animate_trash error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def _update_time(self):
        try:
            clock = self.query_one(PauseStartBar).query_one("#clocklabel", Static)
            clock.update(f"[bold blue]USA Eastern:[/bold blue] [white]{est_time()}[/white]")
            timer_lbl = self.query_one("#timerlabel", Static)
            mins, secs = divmod(self.timer_seconds, 60)
            timer_lbl.update(f"[bold magenta]Elapsed:[/bold magenta] {mins:02}:{secs:02}")
            await self.update_statusbar()
            if self.running and not self.paused:
                self.timer_seconds += 1
        except Exception as e:
            error_log.append(f"_update_time error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def reset_timer(self):
        self.timer_seconds = 0

    async def update_statusbar(self):
        try:
            sb = self.query_one(StatusBar)
            sb.section = self.current_section
            sb.progress = self.progress_percent
            if not self.running:
                sb.status = "Idle"
            elif self.paused:
                sb.status = "Paused"
            else:
                sb.status = "Running"
            sb.update_labels()
        except Exception as e:
            error_log.append(f"update_statusbar error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def update_tally(self):
        try:
            self.query_one(DeletionTally).update_counts()
        except Exception as e:
            error_log.append(f"update_tally error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def action_quit(self) -> None:
        self.exit(0)

    # ============ BUTTON EVENTS =============

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        try:
            if event.button.id == "btnstart":
                await self.start_deletion()
            elif event.button.id == "btnpause":
                await self.pause_deletion()
            elif event.button.id == "btnburn":
                await self.start_burn_countdown()
        except Exception as e:
            append_error(f"on_button_pressed error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def start_deletion(self):
        try:
            if not self.running:
                self.running = True
                self.paused = False
                self.current_action = "Starting process..."
                await self.reset_timer()
                await self.update_statusbar()
                self.deletion_task = asyncio.create_task(self.deletion_main())
            elif self.paused:
                self.paused = False
                self.current_action = "Resuming..."
                await self.update_statusbar()
            self.query_one(PauseStartBar).paused = self.paused
            self.query_one(PauseStartBar).running = self.running
        except Exception as e:
            append_error(f"start_deletion error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def pause_deletion(self):
        try:
            if self.running and not self.paused:
                self.paused = True
                self.current_action = "Paused."
                await self.update_statusbar()
            self.query_one(PauseStartBar).paused = self.paused
            self.query_one(PauseStartBar).running = self.running
        except Exception as e:
            append_error(f"pause_deletion error: {e} line {sys.exc_info()[-1].tb_lineno}")

    async def start_burn_countdown(self):
        try:
            if not self.burn_ready or self.burn_active:
                return
            self.burn_active = True
            self.burn_countdown = 5

            burnbar = self.query_one(BurnBar)
            burnbar.burn_active = True
            burnbar.burn_countdown = 5
            burnbar.query_one("#burncountdown", Static).update(
                f"[bold red]{burnbar.burn_countdown if burnbar.burn_active else ''}[/bold red]"
            )
            burnbar.refresh()

            for i in range(5, 0, -1):
                self.burn_countdown = i
                burnbar.burn_countdown = i
                burnbar.query_one("#burncountdown", Static).update(
                    f"[bold red]{burnbar.burn_countdown if burnbar.burn_active else ''}[/bold red]"
                )
                burnbar.refresh()
                await asyncio.sleep(1)

            self.burn_active = False
            self.burn_countdown = 0
            burnbar.burn_active = False
            burnbar.burn_countdown = 0
            burnbar.query_one("#burncountdown", Static).update("")
            burnbar.refresh()
            await self.permanently_delete_trash()
        except Exception as e:
            append_error(f"start_burn_countdown error: {e} line {sys.exc_info()[-1].tb_lineno}")

    # ============ LOGIC: MAIN DELETION PROCESS =============

    async def deletion_main(self):
        global driver, actions, progress_count, item_delete_counts, actions_log, error_log
        try:
            append_action("ACTION REQUIRED: Log in manually in the opened Brave window.", "cyan")
            await self.async_update_logs()
            # ---- Manual login: open browser and wait for user confirmation ----
            driver, actions = await asyncio.to_thread(self.robust_driver_start_manual)
            append_action("Login confirmed. Beginning deletion process...", "green")
            await self.async_update_logs()
            await asyncio.sleep(1)
            await self.remove_profile_info_async()
            await self.remove_apps_and_websites_async()
            await self.clear_login_history_async()
            await self.remove_friend_suggestions_async()
            await asyncio.to_thread(go_to_activity_log)
            idx = 0
            for main, data in SECTIONS.items():
                if data.get("skip"): continue
                for sub in data["sub"]:
                    if sub in PROTECTED_SUBSECTIONS:
                        continue
                    idx += 1
                    await self.delete_all_in_subsection_async(main, sub, idx, passes=3)
                    await asyncio.sleep(1)
            await self.empty_trash_async(passes=3)
            await self.clear_archive_async(passes=3)
            self.current_section = "BURN"
            self.current_action = (
                "[WARNING] All deletions complete. Ready to permanently erase trash.\n"
                "Press and HOLD the BURN button for 5 seconds to proceed."
            )
            self.burn_ready = True
            self.query_one(BurnBar).burn_ready = True
            await self.update_statusbar()
            append_action("ALL DELETIONS COMPLETE. Awaiting permanent trash empty confirmation.", "red")
            await self.async_update_logs()
        except Exception as e:
            append_error(f"deletion_main error: {e} line {sys.exc_info()[-1].tb_lineno}\n{traceback.format_exc()}")
        self.running = False
        self.paused = False
        await self.update_statusbar()

    # ============ LOGIC: BURN/PERMANENT DELETE =============

    async def permanently_delete_trash(self):
        append_action("BURN: Beginning permanent deletion of all trash...", "red")
        await self.async_update_logs()
        try:
            await asyncio.to_thread(permanently_empty_trash)
            self.current_action = "[SUCCESS] Trash permanently deleted. ALL DATA REMOVED."
            append_action("ALL DATA IN TRASH PERMANENTLY REMOVED.", "red")
            self.successful = True
            self.query_one("#successlabel", Static).update("[bold green]Successful![/bold green]")
            # Update fire emoji counter
            self.fire_counter = self.trash_counter
            self.trash_counter = 0
            self.query_one(TrashFireBar).update_counters(self.trash_counter, self.fire_counter)
            await self.async_update_logs()
        except Exception as e:
            append_error(f"permanently_delete_trash error: {e} line {sys.exc_info()[-1].tb_lineno}\n{traceback.format_exc()}")

    # ============ LOGIC: ASYNC WRAPPERS =============

    async def async_update_logs(self):
        try:
            self.query_one(ActionLog).refresh()
            self.query_one(ErrorLog).refresh()
            await self.update_tally()
        except Exception as e:
            append_error(f"async_update_logs error: {e} line {sys.exc_info()[-1].tb_lineno}")

    # Manual login browser launch
    def robust_driver_start_manual(self):
        global driver, actions
        for attempt in range(MAX_RETRIES):
            try:
                options = webdriver.ChromeOptions()
                options.binary_location = BRAVE_PATH
                options.add_argument("--start-maximized")
                # NO headless mode for manual login!
                options.add_argument("--window-size=1920,1080")
                service = Service(CHROMEDRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
                actions = ActionChains(driver)

                # --- MANUAL LOGIN ONLY ---
                driver.get("https://www.facebook.com/login")
                print("\nLog in to Facebook in the opened browser window, then return and press Enter here.")
                input("After logging in, press Enter to continue...")
                # --- END MANUAL LOGIN ---

                return driver, actions
            except Exception as e:
                append_error(f"Could not start browser. Attempt {attempt+1}/{MAX_RETRIES}\n{traceback.format_exc()}")
                time.sleep(WAIT_BETWEEN_RETRIES)
        append_error("[FATAL] Could not start browser after multiple attempts.")
        sys.exit(1)

    async def prompt_input(self, msg):
        append_action(msg, "yellow")
        self.query_one(ActionLog).refresh()
        self.query_one(ErrorLog).refresh()
        self.query_one("#timerlabel", Static).update(f"[bold yellow]{msg}  (Press Enter to continue)[/bold yellow]")
        event = await self.wait_for(events.Key)
        self.query_one("#timerlabel", Static).update("")
        return

    async def remove_profile_info_async(self):
        await asyncio.to_thread(remove_profile_info)
        self.current_section = "Profile Info"
        self.progress_percent += 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

    async def remove_apps_and_websites_async(self):
        await asyncio.to_thread(remove_apps_and_websites)
        self.current_section = "Apps & Websites"
        self.progress_percent += 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

    async def clear_login_history_async(self):
        await asyncio.to_thread(clear_login_history)
        self.current_section = "Login/Device History"
        self.progress_percent += 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

    async def remove_friend_suggestions_async(self):
        await asyncio.to_thread(remove_friend_suggestions)
        self.current_section = "Friend Suggestions"
        self.progress_percent += 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

    async def delete_all_in_subsection_async(self, section_name, subsection_name, idx, passes=3):
        await asyncio.to_thread(delete_all_in_subsection, section_name, subsection_name, idx, passes)
        self.current_section = section_name
        self.current_subsection = subsection_name
        self.progress_percent += 3 * 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

    async def empty_trash_async(self, passes=3):
        await asyncio.to_thread(empty_trash, passes)
        self.current_section = "Trash"
        self.progress_percent += 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

    async def clear_archive_async(self, passes=3):
        await asyncio.to_thread(clear_archive, passes)
        self.current_section = "Archive"
        self.progress_percent += 100 / TOTAL_STEPS
        await self.async_update_logs()
        await self.update_statusbar()

# ==== SUPPORT FUNCTIONS, LOGGING, AND WRAPPERS ====

def append_action(msg, color="white"):
    try:
        actions_log.append((est_time(), msg, color))
        if len(actions_log) > 40:
            actions_log.pop(0)
    except Exception as e:
        print(f"append_action error: {e} line {sys.exc_info()[-1].tb_lineno}")

def append_error(msg):
    append_action(msg, color="red")
    try:
        error_log.append(msg)
    except Exception as e:
        print(f"append_error error: {e} line {sys.exc_info()[-1].tb_lineno}")

def robust_driver_start():
    global driver, actions
    for attempt in range(MAX_RETRIES):
        try:
            options = webdriver.ChromeOptions()
            options.binary_location = BRAVE_PATH
            options.add_argument("--start-maximized")
            options.add_argument("--window-size=1920,1080")
            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)
            actions = ActionChains(driver)

            # --- MANUAL LOGIN ---
            driver.get("https://www.facebook.com/login")
            print("\nLog in to Facebook in the opened browser window, then return and press Enter here.")
            input("After logging in, press Enter to continue...")
            # --- END MANUAL LOGIN ---

            return driver, actions
        except Exception as e:
            append_error(f"Could not start browser. Attempt {attempt+1}/{MAX_RETRIES}\n{traceback.format_exc()}")
            time.sleep(WAIT_BETWEEN_RETRIES)
    append_error("[FATAL] Could not start browser after multiple attempts.")
    sys.exit(1)

def random_wait(base=1, spread=2):
    t = max(1.0, base + random.random() * spread)
    time.sleep(t)

def wait(seconds=2):
    time.sleep(seconds)

def handle_rate_limit():
    append_error(f"RATE LIMIT: Detected possible rate limit. Waiting {RATE_LIMIT_WAIT//60} minutes before retry...")
    wait(RATE_LIMIT_WAIT)

def error_with_retry(func):
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                append_error(f"{func.__name__} failed on attempt {attempt+1}/{MAX_RETRIES} (line {sys.exc_info()[-1].tb_lineno})\n{traceback.format_exc()}")
                if attempt == MAX_RETRIES - 1:
                    append_error(f"{func.__name__} could not complete after {MAX_RETRIES} attempts. Skipping this step.")
                    return None
                if "rate limit" in str(e).lower():
                    handle_rate_limit()
                else:
                    wait(WAIT_BETWEEN_RETRIES)
                robust_driver_start()
    return wrapper

@error_with_retry
def remove_profile_info():
    driver.get("https://www.facebook.com/me/about")
    random_wait(3, 3)
    try:
        elements = driver.find_elements(By.XPATH, "//span[contains(text(),'Edit') or contains(text(),'Remove')]")
        deleted = 0
        for el in elements:
            try:
                parent = el.find_element(By.XPATH, './ancestor::*[1]')
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                el.click()
                random_wait(1, 1)
                confirm = driver.find_elements(By.XPATH, "//span[contains(text(),'Remove') or contains(text(),'Delete') or contains(text(),'Save')]")
                if confirm:
                    confirm[0].click()
                    random_wait(1, 1)
                deleted += 1
                append_action(f"Removed profile info item #{deleted}.", "green")
            except Exception as e:
                append_error(f"remove_profile_info item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                continue
        append_action(f"Profile info scrubbed. Total: {deleted}", "green")
    except Exception as e:
        append_error(f"Error removing profile info:\n{traceback.format_exc()}")

@error_with_retry
def remove_apps_and_websites():
    driver.get("https://www.facebook.com/settings?tab=applications")
    random_wait(3, 3)
    total_removed = 0
    while True:
        removed_something = False
        remove_buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'Remove') or contains(text(),'Delete')]")
        if not remove_buttons:
            break
        for btn in remove_buttons:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                btn.click()
                random_wait(1, 2)
                confirm = driver.find_elements(By.XPATH, "//span[contains(text(),'Remove') or contains(text(),'Delete') or contains(text(),'Confirm')]")
                if confirm:
                    confirm[0].click()
                    random_wait(1, 1)
                removed_something = True
                total_removed += 1
                append_action(f"Removed app/website #{total_removed}.", "green")
            except Exception as e:
                append_error(f"remove_apps_and_websites item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                continue
        if not removed_something:
            break
    append_action(f"All apps/websites removed. Total: {total_removed}", "green")

@error_with_retry
def clear_login_history():
    driver.get("https://www.facebook.com/settings?tab=security")
    random_wait(3, 3)
    total_removed = 0
    while True:
        removed_something = False
        logout_buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'Log Out') or contains(text(),'Remove')]")
        if not logout_buttons:
            break
        for btn in logout_buttons:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                btn.click()
                random_wait(1, 1)
                removed_something = True
                total_removed += 1
                append_action(f"Logged out session/device #{total_removed}.", "cyan")
            except Exception as e:
                append_error(f"clear_login_history item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                continue
        if not removed_something:
            break
    append_action(f"Login/device history cleared. Total: {total_removed}", "green")

@error_with_retry
def remove_friend_suggestions():
    driver.get("https://www.facebook.com/friends/suggestions")
    random_wait(3, 2)
    total_removed = 0
    while True:
        removed_something = False
        remove_btns = driver.find_elements(By.XPATH, "//span[contains(text(),'Remove') or contains(text(),'Delete') or contains(text(),'Hide')]")
        if not remove_btns:
            break
        for btn in remove_btns:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                btn.click()
                random_wait(1, 1)
                removed_something = True
                total_removed += 1
                append_action(f"Removed friend suggestion #{total_removed}.", "yellow")
            except Exception as e:
                append_error(f"remove_friend_suggestions item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                continue
        if not removed_something:
            break
    append_action(f"Friend suggestions cleared. Total: {total_removed}", "green")

def go_to_activity_log():
    driver.get("https://www.facebook.com/me/allactivity?entry_point=www_top_menu_button")
    random_wait(7, 8)

def subsection_xpath(subsection):
    safe_sub = subsection.replace("'", "").strip()
    xpaths = [
        f"//span[text()='{subsection}']",
        f"//span[contains(text(),'{safe_sub}')]",
        f"//div[text()='{subsection}']",
        f"//div[contains(text(),'{safe_sub}')]",
        f"//*[text()='{subsection}']",
        f"//*[contains(text(),'{safe_sub}')]",
    ]
    return "|".join(xpaths)

def subsection_action_xpath(subsection):
    unlike_xpaths = [
        "//span[contains(text(),'Unlike')]",
        "//span[contains(text(),'Remove reaction')]",
        "//span[contains(text(),'Undo Like')]",
    ]
    delete_xpaths = [
        "//span[contains(text(),'Delete')]",
        "//span[contains(text(),'Remove')]",
        "//span[contains(text(),'Clear')]",
        "//span[contains(text(),'Move to trash')]",
        "//span[contains(text(),'Move to archive')]",
        "//span[contains(text(),'Unsave')]",
        "//span[contains(text(),'Unfollow')]",
        "//span[contains(text(),'Hide')]",
        "//span[contains(text(),'Decline')]",
    ]
    if "like" in subsection.lower() or "reaction" in subsection.lower():
        return "|".join(unlike_xpaths + delete_xpaths)
    return "|".join(delete_xpaths + unlike_xpaths)

def subsection_confirm_xpath():
    return ("//span[contains(text(),'Delete')]"
            "|//span[contains(text(),'Remove')]"
            "|//span[contains(text(),'Confirm')]"
            "|//span[contains(text(),'Unsave')]"
            "|//span[contains(text(),'Unfollow')]"
            "|//span[contains(text(),'Unlike')]"
            "|//span[contains(text(),'OK')]"
            "|//span[contains(text(),'Proceed')]"
            "|//button[contains(text(),'Delete')]"
            "|//button[contains(text(),'Remove')]"
            "|//button[contains(text(),'Confirm')]"
            "|//button[contains(text(),'Unlike')]"
            "|//button[contains(text(),'OK')]")

@error_with_retry
def delete_all_in_subsection(section, subsection, idx, passes=3):
    global progress_count
    append_action(f"[{section} > {subsection}] Navigating...", "magenta")
    random_wait(1.5, 2)
    try:
        go_to_activity_log()
        random_wait(1.5, 2)
        sub_xpath = subsection_xpath(subsection)
        found = False
        for _ in range(3):
            try:
                subnav = driver.find_elements(By.XPATH, sub_xpath)
                if subnav:
                    driver.execute_script("arguments[0].scrollIntoView(true);", subnav[0])
                    subnav[0].click()
                    found = True
                    break
                time.sleep(1.5)
            except Exception as e:
                append_error(f"delete_all_in_subsection nav error: {e} line {sys.exc_info()[-1].tb_lineno}")
                continue
        if not found:
            append_action(f"[WARN] Subsection '{subsection}' not found. Skipping.", "yellow")
            return
        random_wait(2, 2)
        for pass_num in range(1, passes+1):
            items_deleted = 0
            while True:
                for _ in range(10):
                    if not IS_RUNNING or IS_PAUSED:
                        time.sleep(0.5)
                action_xpath = subsection_action_xpath(subsection)
                delete_buttons = driver.find_elements(By.XPATH, action_xpath)
                if not delete_buttons:
                    break
                for btn in delete_buttons:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        btn.click()
                        random_wait(1, 2)
                        confirm_btns = driver.find_elements(By.XPATH, subsection_confirm_xpath())
                        if confirm_btns:
                            confirm_btns[0].click()
                            random_wait(1, 1)
                        items_deleted += 1
                        item_delete_counts[(section, subsection)] += 1
                        append_action(
                            f"{section} > {subsection}: Actioned item #{item_delete_counts[(section, subsection)]}.", "magenta"
                        )
                        random_wait(0.5, 1.2)
                    except Exception as e:
                        append_error(f"delete_all_in_subsection item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                        continue
            if items_deleted > 0:
                append_action(f"[{section} > {subsection}] (Pass {pass_num}) {items_deleted} deleted/unliked.", "green")
            else:
                append_action(f"[{section} > {subsection}] (Pass {pass_num}) No actionable items.", "yellow")
        progress_count += 1
    except Exception as e:
        append_error(f"Error deleting/unliking in {section}>{subsection}:\n{traceback.format_exc()}")

@error_with_retry
def empty_trash(passes=3):
    for pass_num in range(1, passes+1):
        driver.get("https://www.facebook.com/me/allactivity/trash")
        random_wait(3, 2)
        items_deleted = 0
        while True:
            delete_buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'Delete')]")
            if not delete_buttons:
                break
            for btn in delete_buttons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    btn.click()
                    random_wait(1, 2)
                    confirm_btns = driver.find_elements(By.XPATH, "//span[contains(text(),'Delete') or contains(text(),'Confirm')]")
                    if confirm_btns:
                        confirm_btns[0].click()
                        random_wait(1, 1)
                    items_deleted += 1
                    append_action(f"Trash: deleted item #{items_deleted}.", "red")
                except Exception as e:
                    append_error(f"empty_trash item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                    continue
        if items_deleted > 0:
            append_action(f"Trash emptied. Deleted {items_deleted} items this pass.", "green")
        else:
            append_action("Trash already empty this pass.", "yellow")

@error_with_retry
def clear_archive(passes=3):
    for pass_num in range(1, passes+1):
        driver.get("https://www.facebook.com/me/allactivity/archive")
        random_wait(3, 2)
        items_deleted = 0
        while True:
            delete_buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'Delete') or contains(text(),'Remove')]")
            if not delete_buttons:
                break
            for btn in delete_buttons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    btn.click()
                    random_wait(1, 2)
                    confirm_btns = driver.find_elements(By.XPATH, "//span[contains(text(),'Delete') or contains(text(),'Confirm')]")
                    if confirm_btns:
                        confirm_btns[0].click()
                        random_wait(1, 1)
                    items_deleted += 1
                    append_action(f"Archive: deleted item #{items_deleted}.", "red")
                except Exception as e:
                    append_error(f"clear_archive item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                    continue
        if items_deleted > 0:
            append_action(f"Archive cleared. Deleted {items_deleted} items this pass.", "green")
        else:
            append_action("Archive already clear this pass.", "yellow")

def permanently_empty_trash():
    driver.get("https://www.facebook.com/me/allactivity/trash")
    random_wait(2, 2)
    total_deleted = 0
    while True:
        delete_buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'Delete')]")
        if not delete_buttons:
            break
        for btn in delete_buttons:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                btn.click()
                random_wait(1, 2)
                confirm_btns = driver.find_elements(By.XPATH, "//span[contains(text(),'Delete') or contains(text(),'Confirm')]")
                if confirm_btns:
                    confirm_btns[0].click()
                    random_wait(1, 1)
                total_deleted += 1
                append_action(f"PERMANENTLY deleted trash item #{total_deleted}.", "bold red")
            except Exception as e:
                append_error(f"permanently_empty_trash item error: {e} line {sys.exc_info()[-1].tb_lineno}")
                continue
    append_action(f"ALL TRASH PERMANENTLY DELETED. Total: {total_deleted}", "bold red")

# ==== DIAGNOSTICS, LOGGING, AND ADVANCED ERROR HANDLING ====

DIAGNOSTICS_MODE = True  # Set True for verbose errors in UI and file

def setup_logging():
    """Set up logging to a file and the console for diagnostics."""
    log_fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        filename="fbdelete_diagnostics.log",
        filemode="a",
        level=logging.DEBUG,
        format=log_fmt
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(log_fmt)
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

setup_logging()

def log_diagnostics(msg, level="info"):
    """Log to file and optionally to the error_log UI."""
    if level == "info":
        logging.info(msg)
    elif level == "warning":
        logging.warning(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "debug":
        logging.debug(msg)
    # Optionally add to error_log for UI if diagnostics mode
    if DIAGNOSTICS_MODE:
        error_log.append(msg)
        # Keep only last 30 diagnostics messages
        while len(error_log) > 30:
            error_log.pop(0)

def robust_try(fn_name, fn, *args, **kwargs):
    """Wrapper for robust diagnostics with traceback, returns fn result or None."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        tb = traceback.format_exc()
        msg = f"[DIAGNOSTICS] {fn_name} failed at line {sys.exc_info()[-1].tb_lineno}:\n{tb}"
        log_diagnostics(msg, "error")
        return None

def diagnostics_decorator(fn):
    """Decorator for async/normal functions to log full error/trace."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"[DIAGNOSTICS] {fn.__name__} failed at line {sys.exc_info()[-1].tb_lineno}:\n{tb}"
            log_diagnostics(msg, "error")
            raise  # Still raise for UI to catch (but now it's logged everywhere)
    return wrapper

def diagnostics_async_decorator(fn):
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"[DIAGNOSTICS] {fn.__name__} failed at line {sys.exc_info()[-1].tb_lineno}:\n{tb}"
            log_diagnostics(msg, "error")
            raise
    return wrapper

# ==== ENHANCED UI WIDGETS FOR DIAGNOSTICS ====

class DiagnosticsBar(Static):
    """Displays diagnostics (last error and last action) at the bottom of the UI."""
    last_error = var("")
    last_action = var("")
    diagnostics_mode = var(DIAGNOSTICS_MODE)
    def compose(self) -> ComposeResult:
        yield Static("", id="diagnosticslabel")
        yield Button("Diagnostics: On" if self.diagnostics_mode else "Diagnostics: Off", id="btndiag", variant="primary")

    def update_status(self, error="", action=""):
        if error:
            self.last_error = error
        if action:
            self.last_action = action
        style = "red" if self.last_error else "green"
        msg = ""
        if self.last_error:
            msg += f"[{style}]Last Error: {self.last_error}[/]\n"
        if self.last_action:
            msg += f"[yellow]Last Action: {self.last_action}[/]"
        self.query_one("#diagnosticslabel", Static).update(msg)

    def toggle_diag(self):
        self.diagnostics_mode = not self.diagnostics_mode
        global DIAGNOSTICS_MODE
        DIAGNOSTICS_MODE = self.diagnostics_mode
        self.query_one("#btndiag", Button).label = "Diagnostics: On" if self.diagnostics_mode else "Diagnostics: Off"

# ==== UI Main App, Extended with Diagnostics ====

class FBDeleteAppDiagnostics(FBDeleteApp):
    """Extends FBDeleteApp with diagnostics bar and better error reporting."""
    def compose(self) -> ComposeResult:
        with Container():
            yield TrashBanner(id="trashbanner")
            yield PauseStartBar(id="pausestartbar")
            yield StatusBar(id="statusbar")
            with Horizontal(id="maincontent"):
                with Vertical():
                    yield DeletionTally(id="tally")
                    yield ActionLog(id="actionlog")
                    yield ErrorLog(id="errorlog")
            yield Static("", id="timerlabel")
            with Center():
                yield BurnBar(id="burnbar")
            yield DiagnosticsBar(id="diagnosticsbar")
            yield Footer()

    @diagnostics_async_decorator
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btndiag":
            bar = self.query_one(DiagnosticsBar)
            bar.toggle_diag()
            bar.update_status(error="Diagnostics toggled", action="")
            return
        await super().on_button_pressed(event)

    @diagnostics_async_decorator
    async def on_mount(self, event):
        await super().on_mount(event)
        try:
            self.query_one(DiagnosticsBar).update_status(error="", action="App Mounted")
        except Exception as e:
            log_diagnostics(f"DiagnosticsBar on_mount error: {e} line {sys.exc_info()[-1].tb_lineno}", "error")

    @diagnostics_async_decorator
    async def async_update_logs(self):
        await super().async_update_logs()
        if error_log:
            self.query_one(DiagnosticsBar).update_status(error=error_log[-1], action="")
        else:
            self.query_one(DiagnosticsBar).update_status(error="", action="Logs updated")

    @diagnostics_async_decorator
    async def update_statusbar(self):
        await super().update_statusbar()
        try:
            action = self.current_action if hasattr(self, 'current_action') else ""
            self.query_one(DiagnosticsBar).update_status(action=action)
        except Exception as e:
            log_diagnostics(f"DiagnosticsBar update_statusbar error: {e} line {sys.exc_info()[-1].tb_lineno}", "error")

    @diagnostics_async_decorator
    async def prompt_input(self, msg):
        bar = self.query_one(DiagnosticsBar)
        bar.update_status(error="", action=msg)
        await super().prompt_input(msg)

# ==== MAIN ENTRY POINT FOR DIAGNOSTICS ====

if __name__ == "__main__":
    try:
        FBDeleteAppDiagnostics().run()
    except Exception as e:
        tb = traceback.format_exc()
        log_diagnostics(f"FATAL error running FBDeleteAppDiagnostics: {e} line {sys.exc_info()[-1].tb_lineno}\n{tb}", "error")
        print(tb)

# ==== ADVANCED SELENIUM ROBUSTNESS + LOGGING TO FILE FOR ACTIONS ====

from functools import wraps

ACTIONS_LOG_FILE = "fbdelete_actions.log"

def log_action_file(msg, color="white"):
    """Log actions to both the main log and a separate actions file."""
    try:
        with open(ACTIONS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{est_time()} [{color}] {msg}\n")
    except Exception as e:
        log_diagnostics(f"Failed to write action to log file: {e}", "error")
    append_action(msg, color)  # Still add to UI/action_log

def selenium_safe(fn):
    """Decorator for Selenium actions, logs errors and retries driver if needed."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except WebDriverException as e:
                log_action_file(f"Selenium WebDriverException in {fn.__name__} (line {sys.exc_info()[-1].tb_lineno}) attempt {attempt}: {e}", "red")
                log_diagnostics(traceback.format_exc(), "error")
                if attempt == MAX_RETRIES:
                    raise
                robust_driver_start()
                wait(WAIT_BETWEEN_RETRIES)
            except Exception as e:
                log_action_file(f"Other Exception in {fn.__name__} (line {sys.exc_info()[-1].tb_lineno}) attempt {attempt}: {e}", "red")
                log_diagnostics(traceback.format_exc(), "error")
                if attempt == MAX_RETRIES:
                    raise
                robust_driver_start()
                wait(WAIT_BETWEEN_RETRIES)
    return wrapper

# Now wrap all critical Selenium functions

@selenium_safe
def robust_driver_start_logged():
    """Start a new Selenium driver with logging."""
    return robust_driver_start()

@selenium_safe
def go_to_activity_log_safe():
    go_to_activity_log()

@selenium_safe
def selenium_profile_info():
    remove_profile_info()

@selenium_safe
def selenium_apps_and_websites():
    remove_apps_and_websites()

@selenium_safe
def selenium_login_history():
    clear_login_history()

@selenium_safe
def selenium_friend_suggestions():
    remove_friend_suggestions()

@selenium_safe
def selenium_delete_all_in_subsection(section, subsection, idx, passes=3):
    delete_all_in_subsection(section, subsection, idx, passes)

@selenium_safe
def selenium_empty_trash(passes=3):
    empty_trash(passes)

@selenium_safe
def selenium_clear_archive(passes=3):
    clear_archive(passes)

@selenium_safe
def selenium_permanently_empty_trash():
    permanently_empty_trash()

# ==== ADVANCED UI AND HOTKEYS ====

from textual import on

class FBDeleteAppDiagnostics(FBDeleteAppDiagnostics):  # extend previously defined class
    @on("ctrl+s")
    async def _hotkey_start(self):
        """Hotkey to start or resume deletion process."""
        if not self.running:
            await self.start_deletion()
        elif self.paused:
            await self.start_deletion()

    @on("ctrl+p")
    async def _hotkey_pause(self):
        """Hotkey to pause deletion process."""
        if self.running and not self.paused:
            await self.pause_deletion()

    @on("ctrl+b")
    async def _hotkey_burn(self):
        """Hotkey to trigger BURN (if ready)."""
        if self.burn_ready and not self.burn_active:
            await self.start_burn_countdown()

    async def on_key(self, event: events.Key):
        """Custom key event handler for quick diagnostics and controls."""
        if event.key == "q":
            self.exit(0)
        elif event.key == "r":
            self.query_one(DiagnosticsBar).update_status(error="", action="UI Refreshed")
            await self.refresh()
        elif event.key == "d":
            bar = self.query_one(DiagnosticsBar)
            bar.toggle_diag()
            bar.update_status(error="", action="Diagnostics toggled")

# ==== USAGE BANNER ====

USAGE_BANNER = """
[bold blue]FBDelete Enhanced (fb6)
[/bold blue]
- [green]ctrl+s[/green]: Start or resume
- [yellow]ctrl+p[/yellow]: Pause
- [red]ctrl+b[/red]: BURN (permanent delete, when enabled)
- [magenta]q[/magenta]: Quit
- [cyan]d[/cyan]: Toggle diagnostics
- [white]r[/white]: Refresh UI

[bold]Instructions:[/bold]
1. Start the process, log in manually as prompted.
2. Let the script work through all sections/subsections.
3. When all trash is ready for permanent erase, hold [red]BURN[/red] or use [red]ctrl+b[/red] to permanently delete.
"""

def print_usage_banner():
    from rich.console import Console
    console = Console()
    console.print(USAGE_BANNER)

# ==== MAIN ENTRY POINT (ENHANCED) ====

if __name__ == "__main__":
    print_usage_banner()
    try:
        FBDeleteAppDiagnostics().run()
    except Exception as e:
        tb = traceback.format_exc()
        log_diagnostics(f"FATAL error running FBDeleteAppDiagnostics: {e} line {sys.exc_info()[-1].tb_lineno}\n{tb}", "error")
        print(tb)

# ==== END OF ENHANCED FBDELETE SCRIPT ====
