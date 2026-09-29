"""
Adds a "cycle monitors" button to the remote toolbar.

RustDesk >= 1.4.8 ships its own monitor switch button (_MonitorCycle); there
it is only enabled via the default-settings in custom.txt (see views.py), so
the source is left untouched. Older versions get our own _CycleMonitorMenu,
inserted via anchors instead of a fixed diff so it survives upstream churn.
"""
import re
import sys

PATH = "flutter/lib/desktop/widgets/remote_toolbar.dart"

CYCLE_MONITOR_MENU = """
class _CycleMonitorMenu extends StatelessWidget {
  final String id;
  final FFI ffi;

  const _CycleMonitorMenu({
    Key? key,
    required this.id,
    required this.ffi,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final pi = ffi.ffiModel.pi;

    return TextButton(
      onPressed: () {
        RxInt display = CurrentDisplayState.find(id);
        display.value = display.value + 1;
        if (display.value >= pi.displays.length) {
          display.value = 0;
        }
        openMonitorInTheSameTab(display.value, ffi, pi);
        pi.currentDisplay = display.value;
      },
      child: Stack(children: [
        Container(
            child: Align(
                alignment: Alignment.center,
                child: const Icon(
                  Icons.personal_video,
                  color: _ToolbarTheme.blueColor,
                  size: 20.0,
                ))),
        Container(
            child: Align(
                alignment: Alignment(0.0, -0.4),
                child: Text(
                  '  ${CurrentDisplayState.find(id).value + 1}/${pi.displays.length}',
                  style: const TextStyle(
                      color: _ToolbarTheme.blueColor, fontSize: 8),
                ))),
      ]),
    );
  }
}
"""

# (description, pattern, replacement); each pattern must match exactly once.
EDITS = [
    (
        "pass ffi to _DraggableShowHide",
        r"(_DraggableShowHide\(\n(\s*)id: widget\.id,\n)",
        r"\1\2ffi: widget.ffi,\n",
    ),
    (
        "add ffi field to _DraggableShowHide",
        r"(class _DraggableShowHide extends StatefulWidget \{\n(\s*)final String id;\n)",
        r"\1\2final FFI ffi;\n",
    ),
    (
        "add ffi to _DraggableShowHide constructor",
        r"(const _DraggableShowHide\(\{\n\s*Key\? key,\n(\s*)required this\.id,\n)",
        r"\1\2required this.ffi,\n",
    ),
    (
        "insert _CycleMonitorMenu after drag handle",
        r"(\n(\s*)_buildDraggable\(context\),\n)",
        r"\1\2_CycleMonitorMenu(id: widget.id, ffi: widget.ffi),\n",
    ),
]


def main():
    with open(PATH, "r", encoding="utf-8", newline="") as f:
        src = f.read()

    if "class _MonitorCycle" in src:
        print("Native monitor switch found, enabled via default-settings; no source patch needed.")
        return

    # Windows checkouts may use CRLF; normalize for matching, restore on write.
    crlf = "\r\n" in src
    src = src.replace("\r\n", "\n")

    for desc, pattern, repl in EDITS:
        src, n = re.subn(pattern, repl, src, count=1)
        if n != 1:
            sys.exit(f"cycle_monitor: anchor not found ({desc}) in {PATH}")
        print(f"cycle_monitor: {desc}")

    src = src.rstrip("\n") + "\n" + CYCLE_MONITOR_MENU

    if crlf:
        src = src.replace("\n", "\r\n")
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(src)


if __name__ == "__main__":
    main()
