#!/usr/bin/python

"""
a standalone utility to convert plain mmp to midi files
(basically used to tinker with the mmp format)
"""

import IPython
import sys
import xml.etree.ElementTree as ET
from midiutil.MidiFile import MIDIFile



if __name__ == '__main__':
    doc = ET.parse(sys.argv[1])
    head = doc.find('.//head').attrib
    # collect sensible tracks
    tracks = []
    for t in doc.getroot().findall('song//track'):
        #IPython.embed()
        print "testing track ", t.attrib
        if t.find('instrumenttrack') is not None and t.find('pattern/note') is not None:
            tracks.append(t)
    
    midif = MIDIFile(len(tracks))
    print "%d tracks" %(len(tracks))
    thistrack = 0
    for track in tracks: #doc.findall('song//track'):
        channel = 0
        midif.addTrackName(thistrack, 0, track.attrib['name'])
        midif.addTempo(thistrack, channel, float(head['bpm']) )
        midif.addProgramChange(thistrack, channel, 0, 0)
        #print "> adding track ", track.attrib['name']
        
        for p in track.iter('pattern'):
            tstart = float(p.attrib['pos'])/48
            for note in p.findall('note'):
                attr = dict([(k, float(v)) for (k,v) in note.attrib.items()])
                key = int(attr['key'])
                dur = attr['len']/48
                time = tstart + attr['pos']/48
                vol = attr['vol']
                if dur <= 0 or vol <= 0 or time < 0: continue
                #print ">> adding note key %d @ %0.2f for %0.2f" %(key, time, dur)
                assert(0 <= key <= 127)
                assert(dur > 0)
                vol = min(vol, 127)
                midif.addNote(track=thistrack, channel=channel,
                    pitch=key, time=time , duration=dur, volume=vol)
        thistrack += 1
    foutname = sys.argv[1].replace('.mmp', '') + '.mid'
    with open(foutname, 'wb') as f: midif.writeFile(f)
    print "MIDI file written to %s" %(foutname)
