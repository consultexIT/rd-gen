"""
Runs incoming terminal sessions silently in the background.

Terminal sessions never start the connection manager: no window, no
accept/reject prompt for the local user. In exchange they always need the
password - the click-to-accept fallback is gone for them, and with
approve-mode "click" (no password access at all) terminal is refused.
Desktop, file transfer, camera and port forward sessions are unchanged.

Anchors instead of a fixed diff, so it survives upstream churn
(checked against 1.4.5 - 1.4.9 and 1.5.0/master).
"""
import sys

PATH = "src/server/connection.rs"

MARKER = "rdgen silentTerminal"

# (description, anchor, replacement); each anchor must match exactly once.
EDITS = [
    (
        "refuse terminal when only click-approve is allowed",
        "            // https://github.com/rustdesk/rustdesk-server-pro/discussions/646\n",
        "            // rdgen silentTerminal: terminal never asks the local user, so it needs password access.\n"
        "            if self.terminal && password::approve_mode() == ApproveMode::Click {\n"
        "                self.send_login_error(\"Terminal requires password access on this device\")\n"
        "                    .await;\n"
        "                sleep(1.).await;\n"
        "                return false;\n"
        "            }\n"
        "\n"
        "            // https://github.com/rustdesk/rustdesk-server-pro/discussions/646\n",
    ),
    (
        "no click-approve fallback for terminal without a valid password",
        "                || password::approve_mode() == ApproveMode::Both && !password::has_valid_password()\n",
        "                || !self.terminal\n"
        "                    && password::approve_mode() == ApproveMode::Both\n"
        "                    && !password::has_valid_password()\n",
    ),
    (
        "no connection manager window for terminal",
        "    fn try_start_cm(&mut self, peer_id: String, name: String, authorized: bool) {\n",
        "    fn try_start_cm(&mut self, peer_id: String, name: String, authorized: bool) {\n"
        "        // rdgen silentTerminal\n"
        "        if self.terminal {\n"
        "            return;\n"
        "        }\n",
    ),
    (
        "do not launch the connection manager process for terminal",
        "    fn try_start_cm_ipc(&mut self) {\n",
        "    fn try_start_cm_ipc(&mut self) {\n"
        "        // rdgen silentTerminal\n"
        "        if self.terminal {\n"
        "            return;\n"
        "        }\n",
    ),
]


def main():
    with open(PATH, "r", encoding="utf-8", newline="") as f:
        src = f.read()

    if MARKER in src:
        print("silent_terminal: already applied")
        return

    # Windows checkouts may use CRLF; normalize for matching, restore on write.
    crlf = "\r\n" in src
    src = src.replace("\r\n", "\n")

    for desc, anchor, repl in EDITS:
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"silent_terminal: anchor found {n}x, expected 1 ({desc}) in {PATH}")
        src = src.replace(anchor, repl)
        print(f"silent_terminal: {desc}")

    if crlf:
        src = src.replace("\n", "\r\n")
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(src)


if __name__ == "__main__":
    main()
