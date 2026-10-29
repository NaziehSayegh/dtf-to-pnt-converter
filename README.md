# DTF to PNT Converter

Converts binary survey `.DTF` point files (MBF-encoded, 1,500 slots) into space-separated `.PNT` text files:

```
point_number X Y Z
1 168939.240 144808.430 852.25
```

Empty slots are dropped; original point numbers are kept. Output uses CR LF line endings.

## Use

Requires Python 3.8+. Optional: `pip install tkinterdnd2` enables drag-and-drop of files and folders onto the window (the .exe includes it). Running with no arguments opens the window: add files or a folder, choose where to save, click **Convert all**.

```
python dtf2pnt.py                    # opens the window
python dtf2pnt.py A1933.DTF --out C:\Out   # one file
python dtf2pnt.py A1.DTF A2.DTF --out C:\Out
python dtf2pnt.py C:\Surveys\Folder --out C:\Out
```

## Install on Windows

Download **DTF2PNT-Setup.exe** from the [latest release](../../releases/latest) and run it.
It installs the app to `C:\Program Files\DTF to PNT Converter`, adds a Start Menu entry and
(optionally, ticked by default) a desktop shortcut, and registers an uninstaller in
Windows Settings > Apps. The installer is built automatically by GitHub Actions
(`installer.iss`, Inno Setup).

## DTF format

40-byte header (16 name, 4 slot count LE, 20 date/place) + count x 20-byte records
(MBF double X, MBF double Y, MBF single Z). Point number = slot position (1-based).
Slots with X and Y below 1 are empty. Not an officially documented format.
