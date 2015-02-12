#!/usr/bin/python

"""
a standalone utility to convert mmp or mmpz files to midi files
(basically used to tinker with the mmp format)
authors: Mohamed Abdel Maksoud (mohamed at amaksoud.com), Alexis Archambault
licence: GPL2
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
MAX_VEL = 127


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
    print("mm2midi - converts mmp or mmpz file to midi file")
    print("Usage: mm2midi.py inputfile ")
    exit(0)


def read_input_file(input_file_path):
    mmp_ext = "." + MMP_EXT
    mmpz_ext = "." + MMPZ_EXT
    is_mmp_file = input_file_path.endswith(mmp_ext) \
        or input_file_path.endswith(mmp_ext.upper())
    if is_mmp_file:
        file_data = read_mmp_file(input_file_path)
    else:
        file_data = read_mmpz_file(input_file_path)
    return is_mmp_file, file_data
    
    
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
    

def read_xml_tree(file_data):
    is_error = False
    root = None
    try:
        root = etree.fromstring(file_data)
    except Exception as ex:
        is_error = True
        print("Input file decoding error : " + str(ex))
    return root
    
    
def read_header(root):
    head = root.find('.//head').attrib
        
    # MidiFile does not seem to handle time signature.
    # How unfortunate...
    timesig_num = int(head["timesig_numerator"])
    timesig_den= int(head["timesig_denominator"])

    bpm = 120.0
    if "bpm" in head:
        bpm = float(head['bpm'])
    else:
        bpm_tag = root.find(".//head//bpm")
        if bpm_tag is not None and 'value' in bpm_tag.attrib:
            bpm = float(bpm_tag.attrib["value"])
            
    #print(timesig_num, timesig_den, bpm)
    return timesig_num, timesig_den, bpm
         

def collect_tracks(root):
    """ Collects sensible tracks """
    tracks = []
    for t in root.findall('song//track'):
        #print("testing track ", t.attrib)
        if t.find('instrumenttrack') is not None and \
            t.find('pattern/note') is not None:
            tracks.append(t)
    return tracks


def build_midi_file(bpm, tracks):
    midif = MIDIFile(len(tracks))
    channel = 0
    print("%d tracks" %(len(tracks)))
    thistrack = 0
    for track in tracks:
        track_name = track.attrib["name"]
        midif.addTrackName(thistrack, 0, track_name)
        midif.addTempo(thistrack, channel, bpm)
        midif.addProgramChange(thistrack, channel, 0, 0)
        print("adding track ", track_name)
        for p in track.iter('pattern'):
            tstart = float(p.attrib['pos'])/DIV
            for note in p.findall('note'):
                attr = dict([(k, float(v)) for (k,v) in note.attrib.items()])
                key = int(attr['key'])
                dur = attr['len']/DIV
                time = tstart + attr['pos']/DIV
                vol = attr['vol']
                if dur <= 0 or vol <= 0 or time < 0: continue
                #print(">> adding note key %d @ %0.2f for %0.2f" %(key, time, dur))
                assert(0 <= key <= MAX_VEL)
                assert(dur > 0)
                vol = min(vol, MAX_VEL)
                midif.addNote(track=thistrack, channel=channel,
                    pitch=key, time=time , duration=dur, volume=vol)
        thistrack += 1
        
        # increments channel - avoids drumkit channel (channel #9)
        channel += 1
        if channel is 9:
            channel = 10
        if channel is 16:
            channel = 0
            
    return midif


def save_midi_file(midif, input_file_path, is_mmp_file):
    mmp_ext = "." + MMP_EXT
    mmpz_ext = "." + MMPZ_EXT
    midi_ext = "." + MID_EXT
    if is_mmp_file:
        foutname = input_file_path.replace(mmp_ext, '') + midi_ext
    else:
        foutname = input_file_path.replace(mmpz_ext, '') + midi_ext
    with open(foutname, 'wb') as f: 
        midif.writeFile(f)
    print("MIDI file written to %s"%foutname)


if __name__ == '__main__':
    input_file_path = parse_command_line()
    is_mmp_file, file_data = read_input_file(input_file_path)
    root = read_xml_tree(file_data)
    if root is not None:
        timesig_num, timesig_den, bpm = read_header(root)
        tracks = collect_tracks(root)
        midif = build_midi_file(bpm, tracks)
        save_midi_file(midif, input_file_path, is_mmp_file)
