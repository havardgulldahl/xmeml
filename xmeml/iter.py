#-*- encoding: utf-8 -*-

import lxml.etree as etree

class BaseObject(object):
    """Base class for *Item, File"""
    def __init__(self, tree):
        self.name = tree.findtext('name')
        self.timebase = float(tree.findtext('rate/timebase'))

class Item(BaseObject):
    """Base class for ClipItem, TransitionItem, GeneratorItem"""
    def __init__(self, tree):
        super(Item, self).__init__(tree)
        self.ntsc = tree.findtext('rate/ntsc', '') == 'TRUE'
        self.start = int(tree.findtext('start'))
        self.end = int(tree.findtext('end'))
        self.id = tree.get('id')

class ClipItem(Item):
    # (name | duration | rate | enabled | in  | out | start | end  | anamorphic | alphatype | alphareverse | compositemode | masterclipid  |  ismasterclip | labels | comments | stillframeoffset | sequence |  subclipinfo |  logginginfo | stillframe | timecode | syncoffset | file |  primarytimecode | marker  | filter |  sourcetrack | link | subframeoffset | pixelaspectratio | fielddominance)
    def __init__(self, tree):
        super(ClipItem, self).__init__(tree)
        self.tree = tree
        self.duration = float(tree.findtext('duration'))
        self.inpoint = int(tree.findtext('in'))
        self.outpoint = int(tree.findtext('out'))
        fileref = tree.find('file')
        if fileref.findtext('name'):
            self.file = File(fileref)
        else:
            self.file = File.filelist[fileref.get('id')]
        self.mediatype = tree.findtext('sourcetrack/mediatype')
        self.trackindex = int(tree.findtext('sourcetrack/trackindex'))

    def getfilters(self):
        return [ Effect(el) for el in self.tree.iterdescendants(tag='effect') ]

    def getlevels(self):
        for e in self.getfilters():
            if e.effectid == 'audiolevels': return e
        return None

    def audibleframes(self, threshold=0.05):
        "Returns list of (start, end) pairs of audible chunks"
        if not self.mediatype == 'audio': return None # is video
        if isinstance(threshold, Volume) and threshold.gain:
            threshold = threshold.gain
        f = []

        levels = self.getlevels()
        keyframelist = list(levels.parameters)
        if not len(keyframelist):
            # no list of params, use <value>
            if levels.value > threshold:
                return [ ( self.start, self.end ), ]
            else:
                return []
        prevframe = self.start
        thisvolume = 0.0
        audible = False
        keyframelist += ( (self.duration, keyframelist[-1][1]), )
        print keyframelist
        for keyframe, volume in keyframelist:
            thisframe = prevframe + keyframe
            if thisvolume > threshold:
                if audible is True: continue
                audible = True
            else:
                if audible is False: continue
                # level is below threshold, write out range so far
                audible = False
                f.append(  (prevframe, thisframe) )

        old = """
        else: # audiolevels is a list of (keyframe, level) tuples
            keyframelist = audiolevels[:]
            # add the (implicit) keyframe end point
            keyframelist += (self.duration, keyframelist[-1][1]),
            prevframe = float(self.start())
            thisvolume = 0.0
            audible = False
            for keyframe, volume in keyframelist:
                thisframe = prevframe+float(keyframe)
                thisvolume = float(volume)
                if thisvolume > threshold:
                    if audible is True: continue
                    audible = True
                else:
                    # level is below threshold, write out range so far
                    if audible is False: continue
                    audible = False
                    f.append( (prevframe, thisframe) )

        if isinstance(audiolevels, basestring): # single value = single level for whole clip
            if(float(audiolevels) > threshold):
                return [(self.start(), self.end()),]
        """
        # remove duplicates
        _f = {}
        for _e in f:
            _f[_e] = 1
        ff = _f.keys()
        ff.sort()
        return ff

class File(BaseObject):
    # <!ELEMENT file (name | rate | duration | media | timecode | pathurl | width | height | mediaSource)*>
    filelist = {}
    def __init__(self, tree):
        super(File, self).__init__(tree)
        self.id = tree.get('id')
        self.filelist[self.id] = self
        self.duration = float(tree.findtext('duration'))
        self.pathurl = tree.findtext('pathurl')
        if tree.find('media/video') is not None:
            self.mediatype = 'video'
        else:
            self.mediatype = 'audio'

class Effect(object):
    def __init__(self, tree):
        self.name = tree.findtext('name')
        self.effectid = tree.findtext('effectid')
        params = tree.find('parameter')
        self.parameters = self.getparameters(params)
        self.value = params.findtext('value', 0.0)
        self.max = float(tree.findtext('parameter/valuemax'))
        self.min = float(tree.findtext('parameter/valuemin'))

    def getparameters(self, tree):
        for el in tree.iterchildren(tag='keyframe'):
            yield ( float(el.findtext('when')), float(el.findtext('value')) )

class Volume(object):
    """Helper class to convert to and from gain and dB.

    Create an instance with your known value as keyword argument, and you'll be
    able get the unknown value from the object:

        v1 = Volume(gain=0.4)
        db = v1.decibel
        ...
        v2 = Volume(decibel=-60)
        gain = v2.gain

Quoting the dev library:
"The volume level for the audio track of a clip is encoded by the Audio Levels effect. 
The parameter Level expresses linear gain rather than decibels. 
To convert gain to decibels, use the formula 
                    decibels = 20 * log10(Level). 
Conversely, to convert decibels to gain, use 
                    Level = 10 ^ (decibels / 20)."

"""
    def __init__(self, gain=None, decibel=None):
        from math import log10
        self.gain = self.decibel = None
        if gain:
            self.gain = float(gain)
            self.decibel = 20 * log10(self.gain)
        if decibel:
            self.decibel = float(decibel)
            self.gain = 10 ** (self.decibel / 20)  

class XmemlParser(object):
    def __init__(self, filename):
        self.tree = etree.parse(filename)
        self.version = self.tree.getroot().get('version')

    def iteraudioclips(self):
        audio = self.tree.getroot().find('sequence/media/audio')
        for track in audio.iterchildren(tag='track'):
            for clip in track.iterchildren(tag='clipitem'):
                try:
                    yield ClipItem(clip)
                except KeyError:
                    # not audio clip
                    pass


if __name__ == '__main__':
    import sys
    xmeml = XmemlParser(sys.argv[1])
    for clip in xmeml.iteraudioclips():
        print clip.audibleframes()



