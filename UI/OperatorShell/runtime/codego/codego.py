#!/usr/bin/env python3
"""CodeGo -- local LLM relay for the CE-OS OperatorShell.

Old CodeGo ran on nitro and POSTed commands to an HTTP bridge. This
version runs inside the repo on the operator's own machine and
executes bash locally via subprocess (see executor.py).

Flow:
  1. Operator picks a provider from the menu.
  2. CodeGo ensures its dedicated Chrome session exists, attaches to it,
     navigates to the provider, and sends prompts/bootstrap.md.
  3. Loop: scrape the latest assistant reply, pull out the first
     PIXEL_START..PIXEL_END block, run it, paste the output back.
     STOP_SYSTEM in a reply returns to the menu.
"""

import argparse
import os
import signal
import sys
import time
from pathlib import Path

import config
import executor
from browser import ChatDriver

# ---------------------------------------------------------------------------
# SIGTSTP (Ctrl+Z) -- print a banner and yield to the operator menu.
# ---------------------------------------------------------------------------

_PAUSED = {"flag": False}
_MISSION_PENDING = {"flag": False}
CODEGO_STATE_DIR = Path.home() / ".ce-os" / "codego"
MISSION_INBOX = CODEGO_STATE_DIR / "mission.txt"
CONTROL_FILE = CODEGO_STATE_DIR / "control"
STATUS_FILE = CODEGO_STATE_DIR / "status"
PID_FILE = CODEGO_STATE_DIR / "pid"


def write_status(state, provider="-", mission="-", result="-"):
    CODEGO_STATE_DIR.mkdir(parents=True, exist_ok=True)
    mission = " ".join((mission or "-").splitlines()).strip() or "-"
    STATUS_FILE.write_text(
        "GO=READY\n"
        "WORKER=CodeGo\n"
        "STATE={}\n"
        "PROVIDER={}\n"
        "MISSION={}\n"
        "LAST_RESULT={}\n".format(state, provider, mission, result),
        encoding="utf-8",
    )


def write_pid():
    CODEGO_STATE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()) + "\n", encoding="utf-8")


def clear_pid():
    try:
        if PID_FILE.exists() and PID_FILE.read_text().strip() == str(os.getpid()):
            PID_FILE.unlink()
    except OSError:
        pass


def submit_mission_cli(mission: str) -> int:
    mission = mission.strip()
    if not mission:
        print("[!] mission is empty.", file=sys.stderr)
        return 2

    CODEGO_STATE_DIR.mkdir(parents=True, exist_ok=True)
    MISSION_INBOX.write_text(mission + "\n", encoding="utf-8")

    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        os.kill(pid, signal.SIGUSR1)
    except (OSError, ValueError) as exc:
        print("[!] no running CodeGo worker: {}".format(exc), file=sys.stderr)
        return 1

    print("[*] Operator mission submitted to CodeGo pid={}.".format(pid))
    return 0


def _handle_sigusr1(signum, frame):
    _MISSION_PENDING["flag"] = True


def _handle_sigtstp(signum, frame):
    _PAUSED["flag"] = True
    print()
    print("=" * 60)
    print(" [||] OPERATOR PAUSE (Ctrl+Z)")
    print(" Relay frozen. Chrome session stays alive.")
    print("=" * 60)


signal.signal(signal.SIGTSTP, _handle_sigtstp)
signal.signal(signal.SIGUSR1, _handle_sigusr1)


def consume_pending_mission(driver):
    if not _MISSION_PENDING["flag"]:
        return False

    _MISSION_PENDING["flag"] = False

    try:
        mission = MISSION_INBOX.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return False
    except Exception as exc:
        print("[!] Mission inbox read failed: {}".format(exc))
        return False

    if not mission:
        try:
            MISSION_INBOX.unlink()
        except FileNotFoundError:
            pass
        return False

    print("[*] Sending operator mission ({} chars)...".format(len(mission)))
    write_status("BUSY", mission=mission)

    try:
        sent = driver.paste_and_send(mission)
    except Exception as exc:
        result = "SEND_EXCEPTION: {}".format(exc)
        write_status("ERROR", mission=mission, result=result)
        print("[!] Operator mission submission exception: {}".format(exc))
        return False

    if not sent:
        write_status("ERROR", mission=mission, result="SEND_FAILED")
        print("[!] Operator mission submission failed.")
        return False

    try:
        MISSION_INBOX.unlink()
    except FileNotFoundError:
        pass

    print("[*] Operator mission submitted.")
    return True


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def print_menu():
    print()
    print("=== CodeGo ===")
    for key in config.MENU_ORDER:
        info = config.PROVIDERS[key]
        print("{}) {}".format(key, info["name"]))
    print("Select provider [1-{}]:".format(len(config.MENU_ORDER)))


def pick_provider():
    """Prompt until the operator gives a valid menu key. Returns key."""
    while True:
        print_menu()
        try:
            choice = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return None
        if choice in config.PROVIDERS:
            return choice
        print("[!] Invalid selection: {!r}. Try again.".format(choice))


# ---------------------------------------------------------------------------
# Provider session
# ---------------------------------------------------------------------------

def start_session(driver, provider_key):
    """Initialize one provider inside the conversation opened by Go on."""
    info = config.PROVIDERS[provider_key]

    print("[*] Navigating to {} ({})".format(info["name"], info["url"]))
    if not driver.navigate(info["url"]):
        print("[!] navigate() failed.")
        return False

    if not driver.wait_for_ui_settle(timeout=config.UI_SETTLE_TIMEOUT_SEC):
        print("[!] Provider UI did not settle.")
        return False

    bootstrap = config.load_prompt("bootstrap")
    if not bootstrap:
        print("[!] prompts/bootstrap.md missing or empty.")
        return False

    print("[*] Sending bootstrap prompt...")
    if not driver.paste_and_send(bootstrap):
        print("[!] Failed to send bootstrap prompt.")
        return False

    reply = driver.wait_for_reply(timeout_sec=config.REPLY_TIMEOUT_SEC)
    if not reply:
        print("[!] Bootstrap produced no readable reply.")
        return False

    print("[*] Bootstrap reply length: {} chars".format(len(reply)))
    return True


def relay_loop(driver):
    """Poll for new assistant replies; execute PIXEL blocks.

    Exits when a reply contains STOP_SYSTEM or Ctrl+Z is pressed.
    Returns "STOP" on STOP_SYSTEM, "PAUSE" on SIGTSTP.
    """
    last_seen = ""

    while True:
        if _MISSION_PENDING["flag"]:
            _MISSION_PENDING["flag"] = False
            try:
                mission = MISSION_INBOX.read_text(encoding="utf-8").strip()
            except Exception as e:
                print("[!] Mission inbox read failed: {}".format(e))
                mission = ""
            if mission:
                print("[*] Sending operator mission ({} chars)...".format(len(mission)))
                write_status("BUSY", mission=mission)
                if driver.paste_and_send(mission):
                    print("[*] Operator mission submitted.")
                else:
                    write_status("ERROR", mission=mission, result="SEND_FAILED")
                    print("[!] Operator mission submission failed.")
            else:
                print("[!] Mission inbox empty.")

        if _PAUSED["flag"]:
            _PAUSED["flag"] = False
            return "PAUSE"

        try:
            reply = driver.wait_for_reply(timeout=config.REPLY_TIMEOUT_SEC)
        except Exception as e:
            print("[!] wait_for_reply error: {}".format(e))
            time.sleep(config.POLL_INTERVAL_SEC)
            continue

        if not reply or reply == last_seen:
            time.sleep(config.POLL_INTERVAL_SEC)
            continue

        last_seen = reply
        print("[*] New reply ({} chars)".format(len(reply)))

        if executor.is_stop(reply):
            write_status("IDLE", result="PASS")
            print("[*] STOP_SYSTEM detected.")
            return "STOP"

        block = executor.extract_block(reply)
        if not block:
            print("[*] No command block in reply. Polling again.")
            time.sleep(config.POLL_INTERVAL_SEC)
            continue

        print("[*] Executing block:")
        print(block)
        result = executor.run_bash(block)
        out = executor.format_output(result)
        print("[*] Result:")
        print(out)

        payload = "{}\n{}".format(config.COMMAND_OUTPUT_HEADER, out)
        if not driver.paste_and_send(payload):
            print("[!] Failed to send command output back.")


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_check():
    """--check mode. Attach to Chrome, report status, exit 0 either way."""
    print("[check] Attaching to Chrome at {}...".format(
        config.CHROME_DEBUG_ADDRESS))
    driver = ChatDriver()
    ok = driver.attach()
    if not ok:
        reason = getattr(driver, "last_attach_error", "unknown error")
        print("FAIL: could not attach -- {}".format(reason))
        return 0
    print("OK: attached")
    print("URL: {}".format(driver.current_url()))
    return 0


def run_menu_loop():
    """Persistent CodeGo worker controlled explicitly by Go."""
    write_pid()
    write_status("IDLE")
    driver = ChatDriver()

    if not driver.attach():
        reason = getattr(driver, "last_attach_error", "unknown error")
        print("[!] Could not attach to Chrome: {}".format(reason))
        clear_pid()
        return 1

    print("[*] Attached to Chrome. URL: {}".format(driver.current_url()))

    provider_key = None
    provider_name = "-"

    while True:
        if not _MISSION_PENDING["flag"]:
            time.sleep(0.20)
            continue

        _MISSION_PENDING["flag"] = False

        try:
            command = CONTROL_FILE.read_text(encoding="utf-8").strip().upper()
            CONTROL_FILE.unlink()
        except FileNotFoundError:
            continue
        except Exception as exc:
            write_status("ERROR", provider=provider_name,
                         result="CONTROL_READ_FAILED: {}".format(exc))
            continue

        if command.startswith("PROVIDER:"):
            provider_key = command.split(":", 1)[1].strip()

            if provider_key not in config.PROVIDERS:
                write_status("ERROR", result="UNKNOWN_PROVIDER: {}".format(provider_key))
                continue

            provider_name = config.PROVIDERS[provider_key]["name"]

            if not driver.navigate(config.PROVIDERS[provider_key]["url"]):
                provider_key = None
                provider_name = "-"
                write_status("ERROR", result="PROVIDER_NAVIGATE_FAILED")
                continue

            write_status("IDLE", provider=provider_name, result="NEW_CONVERSATION")
            print("[*] {} selected.".format(provider_name))
            continue

        if command == "SYSTEM":
            if provider_key is None:
                write_status("ERROR", result="PROVIDER_REQUIRED")
                continue

            write_status("BUSY", provider=provider_name)

            bootstrap = config.load_prompt("bootstrap")
            if not bootstrap:
                write_status("ERROR", provider=provider_name,
                             result="BOOTSTRAP_MISSING")
                continue

            previous_reply = driver.last_reply()
            if not driver.paste_and_send(bootstrap):
                write_status("ERROR", provider=provider_name,
                             result="BOOTSTRAP_SEND_FAILED")
                continue

            reply = driver.wait_for_reply(
                timeout_sec=config.REPLY_TIMEOUT_SEC,
                previous_reply=previous_reply)
            if not reply:
                write_status("ERROR", provider=provider_name,
                             result="BOOTSTRAP_REPLY_MISSING")
                continue

            write_status("READY", provider=provider_name,
                         result="SYSTEM_READY")
            continue

        if command == "MISSION":
            if provider_key is None:
                write_status("IDLE", result="SYSTEM_REQUIRED")
                continue

            try:
                mission = MISSION_INBOX.read_text(encoding="utf-8").strip()
                MISSION_INBOX.unlink()
            except FileNotFoundError:
                write_status("READY", provider=provider_name,
                             result="MISSION_MISSING")
                continue
            except Exception as exc:
                write_status("ERROR", provider=provider_name,
                             result="MISSION_READ_FAILED: {}".format(exc))
                continue

            if not mission:
                write_status("READY", provider=provider_name,
                             result="MISSION_EMPTY")
                continue

            write_status("BUSY", provider=provider_name, mission=mission)

            previous_reply = driver.last_reply()
            try:
                sent = driver.paste_and_send(mission)
            except Exception as exc:
                write_status("ERROR", provider=provider_name, mission=mission,
                             result="SEND_EXCEPTION: {}".format(exc))
                continue

            if not sent:
                write_status("ERROR", provider=provider_name, mission=mission,
                             result="SEND_FAILED")
                continue

            print("[*] Operator mission submitted.")

            # One mission owns one reply cycle. STOP_SYSTEM ends the mission,
            # not the conversation/provider session.
            last_seen = previous_reply
            while True:
                try:
                    reply = driver.wait_for_reply(
                        timeout_sec=config.REPLY_TIMEOUT_SEC,
                        previous_reply=last_seen)
                except Exception as exc:
                    write_status("ERROR", provider=provider_name,
                                 mission=mission,
                                 result="REPLY_EXCEPTION: {}".format(exc))
                    break

                if not reply or reply == last_seen:
                    time.sleep(config.POLL_INTERVAL_SEC)
                    continue

                last_seen = reply

                block = executor.extract_block(reply)
                if block:
                    result = executor.run_bash(block)
                elif executor.is_stop(reply):
                    report = reply.replace(config.STOP_SYSTEM, "").strip()
                    report_file = CODEGO_STATE_DIR / "report.txt"
                    report_file.write_text(report + "\n", encoding="utf-8")
                    write_status("READY", provider=provider_name,
                                 result="PASS_REPORT_READY")
                    print("[*] STOP_SYSTEM detected. Mission complete.")
                    print("[*] Report saved to {}.".format(report_file))
                    break
                else:
                    time.sleep(config.POLL_INTERVAL_SEC)
                    continue

                out = executor.format_output(result)
                payload = "{}\n{}".format(config.COMMAND_OUTPUT_HEADER, out)

                if not driver.paste_and_send(payload):
                    write_status("ERROR", provider=provider_name,
                                 mission=mission,
                                 result="COMMAND_OUTPUT_SEND_FAILED")
                    break

            continue

        write_status("ERROR", provider=provider_name,
                     result="UNKNOWN_CONTROL: {}".format(command))


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def _cli():
    argv = sys.argv[1:]
    if not argv:
        return None

    if argv[0] in ("mission", "go"):
        if len(argv) < 2:
            print("usage: codego.py mission <mission>", file=sys.stderr)
            return 2
        mission = " ".join(argv[1:]).strip()
        return submit_mission_cli(mission)

    return None



def main():
    cli_result = _cli()
    if cli_result is not None:
        return cli_result

    ap = argparse.ArgumentParser(prog="codego")
    ap.add_argument("--check", action="store_true",
                    help="Attach to Chrome, report status, exit.")
    args = ap.parse_args()

    if args.check:
        return run_check()

    return run_menu_loop()



if __name__ == "__main__":
    sys.exit(main())
