"""
Runs selected incoming session types silently in the background.

Selected via environment variables (value "true"):
  SILENT_TERMINAL  terminal sessions
  SILENT_DESKTOP   remote control sessions (a login without a special session
                   type, i.e. not file transfer, camera, port forward/RDP
                   tunnel or terminal)

Silent sessions never start the connection manager: no window, no
accept/reject prompt for the local user. In exchange they always need the
password - the click-to-accept fallback is gone for them, and with
approve-mode "click" (no password access at all) they are refused.
Features that live in the connection manager (chat, voice call, copying
files via the clipboard) are not available in silent sessions.
All other session types are unchanged.

Anchors instead of a fixed diff, so it survives upstream churn
(checked against 1.4.5 - 1.4.9 and 1.5.0/master).
"""
import os
import sys

PATH = "src/server/connection.rs"

MARKER = "rdgen silent sessions"


def edits(condition):
    # (description, anchor, replacement); each anchor must match exactly once.
    return [
        (
            "add the silent session check",
            "    fn try_start_cm(&mut self, peer_id: String, name: String, authorized: bool) {\n",
            f"    // {MARKER}: no connection manager and no accept prompt for these session types.\n"
            "    fn rdgen_silent_session(&self) -> bool {\n"
            f"        {condition}\n"
            "    }\n"
            "\n"
            "    fn try_start_cm(&mut self, peer_id: String, name: String, authorized: bool) {\n"
            "        if self.rdgen_silent_session() {\n"
            "            return;\n"
            "        }\n",
        ),
        (
            "refuse silent sessions when only click-approve is allowed",
            "            // https://github.com/rustdesk/rustdesk-server-pro/discussions/646\n",
            f"            // {MARKER}: they never ask the local user, so they need password access.\n"
            "            if self.rdgen_silent_session() && password::approve_mode() == ApproveMode::Click {\n"
            "                self.send_login_error(\"This session type requires password access on this device\")\n"
            "                    .await;\n"
            "                sleep(1.).await;\n"
            "                return false;\n"
            "            }\n"
            "\n"
            "            // https://github.com/rustdesk/rustdesk-server-pro/discussions/646\n",
        ),
        (
            "no click-approve fallback for silent sessions without a valid password",
            "                || password::approve_mode() == ApproveMode::Both && !password::has_valid_password()\n",
            "                || !self.rdgen_silent_session()\n"
            "                    && password::approve_mode() == ApproveMode::Both\n"
            "                    && !password::has_valid_password()\n",
        ),
        (
            "do not launch the connection manager process for silent sessions",
            "    fn try_start_cm_ipc(&mut self) {\n",
            "    fn try_start_cm_ipc(&mut self) {\n"
            "        if self.rdgen_silent_session() {\n"
            "            return;\n"
            "        }\n",
        ),
    ]


def main():
    parts = []
    if os.environ.get("SILENT_TERMINAL") == "true":
        parts.append("self.terminal")
    if os.environ.get("SILENT_DESKTOP") == "true":
        parts.append("self.lr.union.is_none()")
    if not parts:
        print("silent_sessions: nothing selected (SILENT_TERMINAL / SILENT_DESKTOP)")
        return

    with open(PATH, "r", encoding="utf-8", newline="") as f:
        src = f.read()

    if MARKER in src:
        print("silent_sessions: already applied")
        return

    # Windows checkouts may use CRLF; normalize for matching, restore on write.
    crlf = "\r\n" in src
    src = src.replace("\r\n", "\n")

    for desc, anchor, repl in edits(" || ".join(parts)):
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"silent_sessions: anchor found {n}x, expected 1 ({desc}) in {PATH}")
        src = src.replace(anchor, repl)
        print(f"silent_sessions: {desc}")

    if crlf:
        src = src.replace("\n", "\r\n")
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(src)


if __name__ == "__main__":
    main()
