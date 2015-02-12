An utility to convert LMMS files to MIDI format.

Requirements
---------------
Python 2.7+ with xml and midiutil packages installed.
Should also work with Python 3.3+.

Usage
-------
- make sure you save your LMMS project with .mmp or .mmpz extension.
- with project file "song.mmp", the following command will output the MIDI file "song.mid":
        python mmp2midi.py song.mmp

