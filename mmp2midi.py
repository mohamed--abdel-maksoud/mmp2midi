#!/usr/bin/python

"""
a standalone utility to convert plain mmp to midi files
(basically used to tinker with the mmp format)
"""

import sys
import getopt
import zlib
import xml.etree.ElementTree as etree
from midiutil.MidiFile import MIDIFile

MMP_EXT = "mmp"
MMPZ_EXT = "mmpz"
MID_EXT = "mid"
DATA_LENGTH_OFFSET = 4
DIV = 48


def parse_command_line():
    success = True

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "h", ["help"])
    except getopt.GetoptError:
        usage()
        success = False

    if success:
        if not opts:
            if not args:
                usage()
        else:
            for opt, arg in opts:
                if opt in ("-h", "--help"):
                    usage()
            
    if success:
        arg_count = len(args)
        can_parse = True
        if arg_count is not 1:
            can_parse = False
        
        if can_parse:
            file_full_path_name = args[0]

    return file_full_path_name


def usage():
    print ("mm2midi - converts mmp or mmpz file to midi file")
    print ("Usage: mm2midi.py inputfile ")
    exit(0)
    
    
def read_mmp_file(file_path):
    """ Loads an uncompressed LMMS file """
    mmpz_file = open(file_path, mode='rb')
    file_data = mmpz_file.read()
    mmpz_file.close()
    return file_data


def read_mmpz_file(file_path):
    """ Loads a compressed LMMS file (4-byte header + Zip format) """
    mmpz_file = open(file_path, mode='rb')
    mmpz_file.seek(DATA_LENGTH_OFFSET)
    file_data = mmpz_file.read()
    mmpz_file.close()
    uncompressed_data = zlib.decompress(file_data)
    return uncompressed_data


if __name__ == '__main__':
    input_file_path = parse_command_line()
    mmp_ext = "." + MMP_EXT
    mmpz_ext = "." + MMPZ_EXT
    is_mmp_file = input_file_path.endswith(mmp_ext) \
        or input_file_path.endswith(mmp_ext.upper())
    if is_mmp_file:
        file_data = read_mmp_file(input_file_path)
    else:
        file_data = read_mmpz_file(input_file_path)
        
    is_error = False
    try:
        root = etree.fromstring(file_data)
    except Exception as ex:
        is_error = True
        print("Input file decoding error : " + str(ex))
        
    if not is_error:
        
        head = root.find('.//head').attrib
        
        # MidiFile does not seem to handle time signature.
        # How unfortunate...
        timesig_numerator = int(head["timesig_numerator"])
        timesig_denominator = int(head["timesig_denominator"])

        bpm = 120.0
        if "bpm" in head:
            bpm = float(head['bpm'])
        else:
            bpm_tag = root.find(".//head//bpm")
            if bpm_tag is not None and 'value' in bpm_tag.attrib:
                bpm = float(bpm_tag.attrib["value"])

        #print(timesig_numerator, timesig_denominator, bpm)

        # collect sensible tracks
        tracks = []
        for t in root.findall('song//track'):
            #print ("testing track ", t.attrib)
            if t.find('instrumenttrack') is not None and \
                t.find('pattern/note') is not None:
                tracks.append(t)
        
        midif = MIDIFile(len(tracks))
        channel = 0
        print "%d tracks" %(len(tracks))
        thistrack = 0
        for track in tracks:
            track_name = track.attrib["name"]
            midif.addTrackName(thistrack, 0, track_name)
            midif.addTempo(thistrack, channel, bpm)
            midif.addProgramChange(thistrack, channel, 0, 0)
            print "adding track ", track_name
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
            
            # increments channel - avoids drumkit channel (channel #9)
            channel += 1
            if channel is 9:
                channel = 10
            if channel is 16:
                channel = 0
            
        midi_ext = "." + MID_EXT
        if is_mmp_file:
            foutname = input_file_path.replace(mmp_ext, '') + midi_ext
        else:
            foutname = input_file_path.replace(mmpz_ext, '') + midi_ext
            
        with open(foutname, 'wb') as f: midif.writeFile(f)
        print "MIDI file written to %s" %(foutname)
