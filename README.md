# DTF to PNT Converter

Converts binary survey `.DTF` point files (MBF-encoded, 1,500 slots) into space-separated `.PNT` text files:

```
point_number X Y Z
1 168939.240 144808.430 852.25
```

Empty slots are dropped; original point numbers are kept. Output uses CR LF line endings.

## Use

Requires Python 3.8+ (no extra packages).

```
python dtf2pnt.py                    # opens the window
python dtf2pnt.py A1933.DTF          # one file
python dtf2pnt.py A1.DTF A2.DTF      # several files
python dtf2pnt.py C:\Surveys\Folder  # every .DTF in a folder
```

## Windows .exe

Download `DTF2PNT-windows` from the latest run in the **Actions** tab, or build locally:

```
pip install pyinstaller
pyinstaller --onefile --windowed --name DTF2PNT dtf2pnt.py
```

## DTF format

40-byte header (16 name, 4 slot count LE, 20 date/place) + count x 20-byte records
(MBF double X, MBF double Y, MBF single Z). Point number = slot position (1-based).
Slots with X and Y below 1 are empty. Not an officially documented format.
