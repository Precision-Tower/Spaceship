"""CodeGo browser driver.

Wraps Selenium around CodeGo's dedicated Chrome session. CodeGo owns
ensuring that Chrome session exists before attachment; OperatorShell owns
where the external Chrome window is positioned and whether it is visible.

This is a port of the old nitro CodeGo browser layer. The old layer
talked to a bridge; this one talks to nothing -- execution lives in
executor.py. What remains here is the DOM interaction, which is
site-shape knowledge that took time to get right and is worth
keeping verbatim where possible.
"""

import subprocess
import time

import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import config


# Selectors tried, in order, when hunting for the chat input box.
INPUT_SELECTORS = [
    "textarea",
    "div[contenteditable='true']",
    "rich-textarea div[contenteditable='true']",
    "[class*='input'] textarea",
    "#chat-input",
]

# Selectors tried, in order, when hunting for the Send button.
SEND_SELECTORS = [
    "#chat-input-send-button",
    "div[class*='send-button']",
    "div[class*='send']",
    "button[type='submit']",
    "button[class*='send']",
    ".ds-icon-button",
    "[aria-label*='Send']",
    "[aria-label*='send']",
]

# Selectors tried, in order, when hunting for a Copy button on the
# latest assistant message.
COPY_SELECTORS = [
    "div[class*='ds-icon-button']",
    "button[class*='copy']",
    "div[class*='copy']",
    "[aria-label*='Copy']",
    "[aria-label*='copy']",
    ".ds-icon-button",
]

# Selectors tried, in order, when hunting for a Stop / Cancel button
# (which is how we know the model is still generating).
STOP_SELECTORS = [
    "button[class*='stop']",
    "div[class*='stop']",
    "[aria-label*='Stop']",
    "[aria-label*='stop']",
]

# Fallback text containers, in order, if the copy button path fails.
TEXT_SELECTORS = [
    ".ds-markdown",
    ".qwen-markdown",
    ".markdown-body",
    "div[class*='message-content']",
    "div[class*='assistant']",
]


class ChatDriver(object):
    """Attach to a running Chrome and drive a chat UI."""

    def __init__(self, debug_address=None, profile_dir=None):
        self.debug_address = debug_address or config.CHROME_DEBUG_ADDRESS
        self.profile_dir = profile_dir or config.CHROME_PROFILE_DIR
        self.driver = None

    # ------------------------------------------------------------------
    # Attachment
    # ------------------------------------------------------------------

    def ensure_chrome(self):
        """Ensure CodeGo's dedicated Chrome exists before Selenium attaches."""
        try:
            subprocess.run(
                ["pgrep", "-f", "^/opt/google/chrome/chrome .*--user-data-dir={}".format(self.profile_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            pass

        try:
            subprocess.Popen(
                [
                    "google-chrome",
                    "--remote-debugging-port={}".format(config.CHROME_DEBUG_PORT),
                    "--user-data-dir={}".format(self.profile_dir),
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--password-store=basic",
                    "about:blank",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            self.last_attach_error = "Chrome launch failed: {}".format(e)
            return False

        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                import urllib.request
                with urllib.request.urlopen(
                    "http://{}/json/version".format(self.debug_address),
                    timeout=0.5,
                ) as response:
                    if response.status == 200:
                        return True
            except Exception:
                time.sleep(0.25)

        self.last_attach_error = "Chrome debug endpoint did not become ready"
        return False

    def attach(self):
        """Ensure CodeGo Chrome exists, then attach Selenium. True on success."""
        if not self.ensure_chrome():
            return False
        try:
            opts = Options()
            opts.add_experimental_option("debuggerAddress", self.debug_address)
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--user-data-dir={}".format(self.profile_dir))
            self.driver = webdriver.Chrome(options=opts)
            return True
        except Exception as e:
            self.driver = None
            self.last_attach_error = str(e)
            return False

    def current_url(self):
        if not self.driver:
            return ""
        try:
            return self.driver.current_url or ""
        except Exception:
            return ""

    def navigate(self, url):
        """Point the attached tab at `url`. True on success."""
        if not self.driver:
            return False
        try:
            self.driver.get(url)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Input box / Send button
    # ------------------------------------------------------------------

    def find_input(self):
        """Return the visible, enabled chat input element, or None."""
        if not self.driver:
            return None
        for sel in INPUT_SELECTORS:
            try:
                elems = self.driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                continue
            for elem in reversed(elems):
                try:
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
                except Exception:
                    continue
        return None

    def is_generating(self):
        """True if a Stop / Cancel button is visible somewhere."""
        if not self.driver:
            return False
        for sel in STOP_SELECTORS:
            try:
                elems = self.driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                continue
            for elem in elems:
                try:
                    if elem.is_displayed():
                        return True
                except Exception:
                    continue
        return False

    def _clear_and_paste(self, text):
        """Focus the input, clear it, paste `text` via clipboard.

        Returns True when the element accepted the paste gesture.
        The actual content landing is verified by the caller when it
        matters (send path checks the box drains).
        """
        pyperclip.copy(text)
        for _ in range(3):
            elem = self.find_input()
            if not elem:
                time.sleep(0.5)
                continue
            try:
                elem.click()
                time.sleep(0.3)
                elem.send_keys(Keys.CONTROL, "a")
                elem.send_keys(Keys.DELETE)
                time.sleep(0.3)
                elem.send_keys(Keys.CONTROL, "v")
                time.sleep(0.5)
                return True
            except Exception:
                time.sleep(0.5)
        return False

    def _composer_text(self, elem=None):
        """Return the actual current composer contents."""
        elem = elem or self.find_input()
        if elem is None:
            return ""
        try:
            value = elem.get_attribute("value")
            if value is not None:
                return value
        except Exception:
            pass
        try:
            return elem.get_attribute("textContent") or ""
        except Exception:
            return ""

    def _click_send(self):
        """Submit the current composer once and verify that it drained."""
        if not self.driver:
            return False

        # Deliberately exclude generic .ds-icon-button / div[class*=send].
        # Those can identify unrelated controls in DeepSeek.
        selectors = [
            "div[role='button'].ds-button--primary.ds-button--filled.ds-button--circle",
            "#chat-input-send-button",
            "button[type='submit']",
            "button[class*='send']",
            "[aria-label*='Send']",
            "[aria-label*='send']",
        ]

        for sel in selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                continue

            for button in reversed(buttons):
                try:
                    if not (button.is_displayed() and button.is_enabled()):
                        continue
                    button.click()

                    deadline = time.time() + 5.0
                    while time.time() < deadline:
                        time.sleep(0.20)
                        if not self._composer_text().strip():
                            return True
                except Exception:
                    continue

        print("[!] No verified Send action drained the composer.")
        return False

    def paste_and_send(self, text):
        """Type without newline-submit side effects, then explicitly Send."""
        if not self.driver:
            return False

        elem = self.find_input()
        if elem is None:
            print("[!] No usable visible chat input found.")
            return False

        try:
            elem.click()
            elem.send_keys(Keys.CONTROL, "a")
            elem.send_keys(Keys.DELETE)

            # Never pass embedded newlines directly to send_keys().
            # In chat UIs they are keyboard Enter events and may submit.
            lines = text.splitlines()
            for index, line in enumerate(lines):
                if index:
                    elem.send_keys(Keys.SHIFT, Keys.ENTER)
                if line:
                    elem.send_keys(line)

            # Confirm the composer actually contains material before Send.
            if text.strip() and not self._composer_text(elem).strip():
                print("[!] Composer did not retain entered text.")
                return False

        except Exception as exc:
            print("[!] Could not enter chat text: {}".format(exc))
            return False

        return self._click_send()
    def wait_for_ui_settle(self, timeout=config.UI_SETTLE_TIMEOUT_SEC):
        """Block until the input box is present and no Stop button shows.

        This is the gate we use both before pasting (make sure the
        page is idle) and after sending (make sure the reply is done).
        """
        if not self.driver:
            return False
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self.find_input() and not self.is_generating():
                    time.sleep(1)
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def last_reply(self):
        """Return the most recent assistant reply directly from the DOM."""
        if not self.driver:
            return ""

        for sel in TEXT_SELECTORS:
            try:
                msgs = self.driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                continue

            filtered = []
            for msg in msgs:
                try:
                    text = (msg.text or "").strip()
                except Exception:
                    continue
                if text and len(text) > 5:
                    filtered.append(text)

            if filtered:
                return filtered[-1]

        return ""

    def wait_for_reply(self, timeout_sec=config.REPLY_TIMEOUT_SEC, previous_reply=None):
        """Wait for a NEW completed assistant reply, then return it."""
        if not self.driver:
            return ""

        baseline = self.last_reply() if previous_reply is None else previous_reply
        deadline = time.time() + timeout_sec

        while time.time() < deadline:
            try:
                current = self.last_reply()
                if current and current != baseline and not self.is_generating():
                    time.sleep(1.0)
                    settled = self.last_reply()
                    if settled and settled != baseline and not self.is_generating():
                        return settled
            except Exception:
                pass
            time.sleep(0.25)

        return ""


def attach_default():
    """Convenience: attach a ChatDriver to the session Chrome.

    Returns (driver, ok). Callers that only want the boolean can
    ignore the first element.
    """
    cd = ChatDriver()
    ok = cd.attach()
    return cd, ok
