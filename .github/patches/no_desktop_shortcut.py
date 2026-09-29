"""
Windows: never create a desktop shortcut on install.

Covers the exe install (install page and --silent-install) and the MSI:
the "Create desktop icon" checkbox is removed from both installers and the
shortcut is no longer copied to the public desktop. Start menu shortcuts are
unchanged. An MSI upgrade removes a desktop shortcut left by an older build.

Anchors instead of a fixed diff, so it survives upstream churn
(checked against 1.3.9 - 1.4.9 and 1.5.0/master).
"""
import sys

MARKER = "rdgen noDesktopShortcut"

# path -> [(description, anchor, replacement)]; each anchor must match exactly once.
EDITS = {
    "src/platform/windows.rs": [
        (
            "do not copy the shortcut to the public desktop",
            '    if options.contains("desktopicon") {\n',
            "    // rdgen noDesktopShortcut\n"
            '    if false && options.contains("desktopicon") {\n',
        ),
    ],
    "flutter/lib/desktop/pages/install_page.dart": [
        (
            "desktop icon option off",
            "    desktopicon.value = installOptions['DESKTOPSHORTCUTS'] != '0';\n",
            "    desktopicon.value = false; // rdgen noDesktopShortcut\n",
        ),
        (
            "hide the desktop icon checkbox",
            "              Option(desktopicon, label: 'Create desktop icon')\n"
            "                  .marginOnly(bottom: 7),\n",
            "",
        ),
    ],
    "res/msi/Package/Fragments/ShortcutProperties.wxs": [
        (
            "MSI desktop shortcut off by default",
            '<Property Id="DESKTOPSHORTCUTS" Value="1" Secure="yes"></Property>',
            '<Property Id="DESKTOPSHORTCUTS" Secure="yes"></Property><!-- rdgen noDesktopShortcut -->',
        ),
    ],
    "res/msi/Package/UI/MyInstallDirDlg.wxs": [
        (
            "hide the MSI desktop shortcut checkbox",
            '<Control Id="ChkBoxDesktopShortcuts" Type="CheckBox" X="20" Y="160" Width="290" Height="17" '
            'Property="DESKTOPSHORTCUTS" CheckBoxValue="1" Text="!(loc.MyInstallDirDlgDesktopShortcuts)" />',
            "<!-- rdgen noDesktopShortcut: ChkBoxDesktopShortcuts removed -->",
        ),
    ],
}


def patch(path, edits):
    with open(path, "r", encoding="utf-8", newline="") as f:
        src = f.read()

    if MARKER in src:
        print(f"no_desktop_shortcut: {path} already patched")
        return

    # Windows checkouts may use CRLF; normalize for matching, restore on write.
    crlf = "\r\n" in src
    src = src.replace("\r\n", "\n")

    for desc, anchor, repl in edits:
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"no_desktop_shortcut: anchor found {n}x, expected 1 ({desc}) in {path}")
        src = src.replace(anchor, repl)
        print(f"no_desktop_shortcut: {desc}")

    if crlf:
        src = src.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(src)


def main():
    for path, edits in EDITS.items():
        patch(path, edits)


if __name__ == "__main__":
    main()
