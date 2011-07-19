#-*- encoding: utf-8 -*-
#
# This is an xmeml parser that tries to be super fast, 
# using the lxml module for all xml stuff and python's 
# efficient iterative parsing whenever possible.
#
# This leads to a dramatic decrease of both mem and cpu
# usage compared to the minidom api of the standard xmeml
# code.
#
# This module is not a full replacement though, 
# and has a totally different api (it never made sense
# to keep it, since everything is done differently
# from the original parser.)
#
# (C) 2011 havard.gulldahl@nrk.no
# License: BSD

import lxml.etree as etree

class Range(object):

    def __init__(self, iterable=None):
        if iterable is not None:
            self.start, self.end = iterable
        else:
            self.start = None
            self.end = None

    def __repr__(self):
        return "Range"+repr(self.get())

    def __string__(self):
        return u'<Range: %.5(start)f–%.5(end)f>' % vars(self)
    
    def __add__(self, other):
        self.extend( (other.start, other.end) )
        return self

    def __len__(self):
        if None in (self.start, self.end):
            raise TypeError("Range is not complete")
        return self.end-self.start

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __iter__(self):
        for z in (self.start, self.end):
            yield z

    def extend(self, iterable):
        start, end = iterable
        if self.start is None or start < self.start:
            self.start = start
        if end > self.end:
            self.end = end

    def get(self):
        return (self.start, self.end)

    def overlaps(self, other):
        return other.start <= self.start <= other.end or \
                self.start <= other.start <= self.end

class Ranges(object):
    def __init__(self, range=None):
        self.r = []
        if range is not None:
            self.extend(range)

    def __repr__(self):
        return repr(self.r)

    def __str__(self):
        return u'<Ranges: %i ranges, totalling %.2d frames>' % (len(self.r), 
                                                                self.total())

    def __add__(self, other):
        for range in other.r:
            self.extend(range)
        return self

    def __len__(self):
        return sum([len(r) for r in self.r])

    def __iter__(self):
        return iter(self.r)

    def extend(self, otherrange):
        for range in self.r:
            if range == otherrange:
                return None
            elif range.overlaps(otherrange):
                range.extend(otherrange)
                return True
        self.r.append(otherrange)
        return True

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
        self.start = float(tree.findtext('start'))
        self.end = float(tree.findtext('end'))
        self.id = tree.get('id')

class TransitionItem(Item):
    """transitionitem
    Description: Encodes a transition in a track.
    Parent:      track
    Subelements: rate, *start, *end, *alignment, effect, *name
    """
    # <!ELEMENT transitionitem (name | rate | start | end | alignment | effect)*>

    def __init__(self, tree):
        super(TransitionItem, self).__init__(tree)
        # A string specifying an alignment for a transition. 
        # Valid entries are start, center, end, end-black, or start-black.
        self.alignment = tree.findtext('alignment')
        self.effect = Effect(tree.find('effect'))

class ClipItem(Item):
    """
    Description: Encodes a clip in a track.
    Parent:      track
    Subelements: +*name, +duration, +rate, +*start, +*end, link, syncoffset, 
                 *enabled, *in, *out, *masterclipid, *subclipmasterid, 
                 ismasterclip, *logginginfo, file, *timecode, *marker, 
                 *anamorphic, *alphatype, *alphareverse, *labels, *comments, 
                 sourcetrack, *compositemode, subclipinfo, *filter, stillframe,
                 *stillframeoffset, *sequence, multiclip,mediadelay,
                 subframeoffset, *mixedratesoffset,filmdata, pixelaspectratio,
                 fielddominance, gamma, primarytimecode*, itemhistory
     Attribute:  id
     Notes:      Note that start, end, link, syncoffset, and enabled are
                 subelements of clipitem, but not of clip.
    """
    # (name | duration | rate | enabled | in  | out | start | end  | anamorphic | alphatype | alphareverse | compositemode | masterclipid  |  ismasterclip | labels | comments | stillframeoffset | sequence |  subclipinfo |  logginginfo | stillframe | timecode | syncoffset | file |  primarytimecode | marker  | filter |  sourcetrack | link | subframeoffset | pixelaspectratio | fielddominance)
    def __init__(self, tree):
        super(ClipItem, self).__init__(tree)
        self.tree = tree
        self.inpoint = int(tree.findtext('in'))
        self.outpoint = int(tree.findtext('out'))
        self.duration = self.outpoint-self.inpoint
        if self.start == -1.0: # start is within a transition
            self.start = self.getprevtransition().end
        if self.end == -1.0: # end is within a transition
            self.end = self.getfollowingtransition().start
        fileref = tree.find('file')
        if fileref.findtext('name'): # is it a full <file> object?
            self.file = File(fileref) # yes
        else:
            self.file = File.filelist[fileref.get('id')] # no, just a reference to a previous obj.
        self.mediatype = tree.findtext('sourcetrack/mediatype')
        self.trackindex = int(tree.findtext('sourcetrack/trackindex'))

    def getfilters(self):
        return [ Effect(el) for el in self.tree.iterdescendants(tag='effect') ]

    def getlevels(self):
        for e in self.getfilters():
            if e.effectid == 'audiolevels': return e
        return None

    def getprevtransition(self):
        item = self.tree.xpath('./preceding-sibling::transitionitem[1]')[0]
        return TransitionItem(item)

    def getfollowingtransition(self):
        item = self.tree.xpath('./following-sibling::transitionitem[1]')[0]
        return TransitionItem(item)

    def audibleframes(self, threshold=0.0001):
        "Returns list of (start, end) pairs of audible chunks"
        if not self.mediatype == 'audio': return None # is video
        if isinstance(threshold, Volume) and threshold.gain:
            threshold = threshold.gain
        levels = self.getlevels()
        keyframelist = list(levels.parameters)
        if not len(keyframelist):
            # no list of params, use <value>
            if levels.value > threshold:
                return Ranges(Range( (self.start, self.end) ) )
            else:
                return Ranges()
        prevframe = self.start
        thisvolume = 0.0
        audible = False
        keyframelist += ( (self.duration, keyframelist[-1][1]), )
        ranges = Ranges()
        for keyframe, volume in keyframelist:
            thisframe = prevframe + keyframe
            if volume > threshold:
                if audible is True: continue
                audible = True
            else:
                if audible is False: continue
                # level is below threshold, write out range so far
                ranges.extend(Range( (prevframe, thisframe) ) )
                audible = False
        #write out the last frame if it hasn't been written
        if audible is True:
            ranges.extend(Range( (prevframe, thisframe) ) )
        return ranges

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
    """Eeffect
    Description: Encodes an effect or processing operation. 
    Parents:     transitionitem, filter, generatoritem
    Subelements: +*name, +*effectid, +*effecttype, +*mediatype, *effectcategory,
                parameter, keyframe, appspecificdata, wipecode, wipeaccuracy, rate,
                startratio, endratio, reverse, duration , privatestate, multiclip,
                effectclass
  
     """
    def __init__(self, tree):
        self.name = tree.findtext('name')
        self.effectid = tree.findtext('effectid')
        params = tree.find('parameter')
        if params is not None:
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
        self.name = self.tree.getroot().find('sequence').get('id')

    def iteraudioclips(self):
        audio = self.tree.getroot().find('sequence/media/audio')
        for track in audio.iterchildren(tag='track'):
            for clip in track.iterchildren(tag='clipitem'):
                try:
                    yield ClipItem(clip)
                except KeyError:
                    # not audio clip
                    continue

    def audibleranges(self):
        clips = {}
        files = {}
        for clip in self.iteraudioclips():
            if clips.has_key(clip.name):
                clips[clip.name] += clip.audibleframes()
            else:
                clips[clip.name] = clip.audibleframes()
            files.update( {clip.name: clip.file} )
        return clips, files
            

if __name__ == '__main__':
    import sys
    xmeml = XmemlParser(sys.argv[1])
    a = xmeml.audibleranges()
    print a

