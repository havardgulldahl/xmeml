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

AUDIOTHRESHOLD=0.0001

class XmemlFileError(Exception):
    pass

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
        return 'Ranges: '+repr(self.r)

    def __str__(self):
        return u'<Ranges: %i ranges, totalling %.2d frames>' % (len(self.r), 
                                                                len(self))

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
        try:
            self.timebase = float(tree.findtext('rate/timebase'))
        except TypeError:
            self.timebase = None

class Item(BaseObject):
    """Base class for ClipItem, TransitionItem, GeneratorItem"""
    def __init__(self, tree):
        super(Item, self).__init__(tree)
        self.start = float(tree.findtext('start'))
        self.end = float(tree.findtext('end'))
        self.id = tree.get('id')
        try:
            self.ntsc = tree.findtext('rate/ntsc') == 'TRUE'
        except TypeError:
            self.ntsc = None

    def getframerate(self):
        """Return a tuple(float, string): actual framerate and common video type. E.g. (23.976, '24P')

        Note that actual framerate is not always the same as timebase, hence this method.

        Implemented as spec'ed on p. 160 at:
        https://developer.apple.com/library/mac/documentation/AppleApplications/Reference/FinalCutPro_XML/FinalCutPro_XML.pdf
        """
        if self.timebase is None:
            return (None, None)
        elif self.timebase == 24:
            if self.ntsc: return (23.976, '24P')
            else: return (24, 'Film')
        elif self.timebase == 25:
            return (25, 'PAL')
        elif self.timebase == 30:
            if self.ntsc: return (29.97, 'NTSC/HD')
            else: return (30, 'Video/HD')
        elif self.timebase == 50:
            return (50, 'HD (50Hz)')
        elif self.timebase == 60:
            if self.ntsc: return (59.94, 'HD (59.94Hz)')
            else: return (60, 'HD (60Hz)')

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
        self.duration = self.end - self.start
        self.centerframe = self.start+(self.duration/2)

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
        if self.inpoint > self.outpoint:
            # clip is reversed, just flip it back
            self.inpoint, self.outpoint = self.outpoint, self.inpoint
        self.duration = self.outpoint-self.inpoint
        if self.start == -1.0: # start is within a transition
            self.start = self.getprevtransition().centerframe
        if self.end == -1.0: # end is within a transition
            self.end = self.getfollowingtransition().centerframe
        try:
            self.file = File.filelist[tree.find('file').get('id')]  
        except AttributeError:
            #print self.name
            self.file = None # there might be a nested <sequence> instead of a file
        self.mediatype = tree.findtext('sourcetrack/mediatype')
        self.trackindex = int(tree.findtext('sourcetrack/trackindex'))
        self.linkedclips = [Link(el) for el in tree.iter('link')]
        self.isnestedsequence = tree.find('sequence/media') is not None

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

    def audibleframes(self, threshold=AUDIOTHRESHOLD):
        "Returns list of (start, end) pairs of audible chunks"
        if not self.mediatype == 'audio': return None # is video
        if isinstance(threshold, Volume) and threshold.gain is not None:
            threshold = threshold.gain
        levels = self.getlevels()
        keyframelist = list(levels.parameters)
        if not len(keyframelist):
            # no list of params, use <value>
            if levels.value > threshold:
                return Ranges(Range( (self.start, self.end) ) )
            else:
                return Ranges()

        # add our subclip inpoint to the keyframelist if it's not in it already.
        #
        if self.inpoint < keyframelist[0][0]:
            keyframelist.insert(0, (self.inpoint, keyframelist[0][1]))
        else:
            i = 0
            while self.inpoint > keyframelist[i][0]:
                try: 
                    if self.inpoint < keyframelist[i+1][0]:
                        # add inpoint keyframe with volume of next keyframe
                        #print ' add inpoint keyframe with volume of next keyframe'
                        keyframelist.insert(i+1, (self.inpoint, keyframelist[i+1][1]))
                except IndexError:
                    # all keyframes in keyframelist are _before_ inpoint
                    #print ' all keyframes in keyframelist are _before_ inpoint'
                    keyframelist.append((self.inpoint, keyframelist[i][1]))
                i = i + 1
            del i

        # add our sublicp outpoint to the keyframelist, too
        if self.outpoint > keyframelist[-1][0]:
            # last existing keyframe is earlier than outpoint, add last keyframe volume
            keyframelist.append((self.outpoint, keyframelist[-1][1]))
        else:
            i = len(keyframelist) - 1
            while self.outpoint < keyframelist[i][0]:
                try:
                    if self.outpoint > keyframelist[i-1][0]:
                        # add outpoint keyframe with volume of previous keyframe
                        #print ' add outpoint keyframe with volume of previous keyframe'
                        keyframelist.insert(i, (self.outpoint, keyframelist[i][1]))
                except IndexError:
                    # TODO: properly diagnose and fix this
                    #print self.name, keyframelist, i
                    raise
                i = i - 1
            del i

        # now, run through the keyframelist and keep the keyframes that are within
        # our audible range (self.inpoint - self.outpoint), whose volume is
        # at or above our current gain level ('threshold' method argument)
        #
        audible = False
        ranges = Ranges()
        for keyframe, volume in keyframelist:
            # discard everything outside .inpoint and .outpoint
            if keyframe < self.inpoint:
                # keyframe falls outside of the current clip, to the left
                continue
            if keyframe > self.outpoint:
                # keyframe falls outside of the current clip, to the right
                break # we're finished
            # store this frame, and translate the keyframe from local to the clip
            # to global to the full sequence
            thisframe = self.start + (keyframe - self.inpoint)
            if volume >= threshold:
                if audible is True: continue # previous frame was also audible
                audible = True
                prevframe = thisframe
            else:
                if audible is False: continue # previous frame was also inaudible
                # level has gone below threshold, write out range so far
                ranges.extend(Range( (prevframe, thisframe) ) )
                audible = False
        #write out the last frame if it hasn't been written
        if audible is True:
            ranges.extend(Range( (prevframe, thisframe) ) )
        return ranges

class Link(object):
    """<link> elements"""
    def __init__(self, tree):
        self.linkclipref = tree.findtext('linkclipref')
        self.mediatype = tree.findtext('mediatype')
        self.trackindex = tree.findtext('trackindex')
        self.clipindex = tree.findtext('clipindex')

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
        try:
            self.tree = etree.parse(filename)
        except AttributeError:
            raise XmemlFileError('Parsing xml failed. Seems like a broken XMEML file.')
        if not self.tree.getroot().tag == 'xmeml':
            raise XmemlFileError('xmeml tag not found. This is not a XMEML file.')

        if self.tree.getroot().find('sequence') is not None: # fcp7 exports per sequence
            self.root = self.tree.getroot()
        elif self.tree.getroot().find('project/children/sequence') is not None: # Premiere cs6 (and others?) encodes the whole project
            self.root = self.tree.getroot().find('project/children')
        try:
            self.version = self.root.get('version')
            self.name = self.root.find('sequence').get('id')
        except AttributeError:
            raise XmemlFileError('No sequence found. Seems like a broken XMEML file.')
        # find all file references
        File.filelist = {f.get('id'):File(f) for f in self.root.iter('file') if f.findtext('name') is not None}

    def iteraudioclips(self, onlypureaudio=True):
        """Iterator to get all audio clips. 
        
        onlypureaudio parameter controls whether to limit to clips that have no video 
        clip assosiated with it (i.e. music, sound effects). Defaults to true.
        """
        audio = self.root.find('sequence/media/audio')
        for track in audio.iterchildren(tag='track'):
            for clip in track.iterchildren(tag='clipitem'):
                ci = ClipItem(clip)
                if ci.isnestedsequence:
                    #print clip.find('sequence').get('name')
                    for nestedtrack in clip.find('sequence/media/audio').iterchildren(tag='track'):
                        for nestedclip in nestedtrack.iterchildren(tag='clipitem'):
                            nestedci = ClipItem(nestedclip)
                            if not onlypureaudio:
                                yield nestedci
                            elif nestedci.file.mediatype == 'audio':
                                yield nestedci
                    continue
                if not onlypureaudio:
                    yield ci
                elif ci.file is not None and ci.file.mediatype == 'audio':
                    yield ci

    def audibleranges(self, threshold=AUDIOTHRESHOLD):
        clips = {}
        files = {}
        for clip in self.iteraudioclips():
            if clips.has_key(clip.name):
                clips[clip.name] += clip.audibleframes(threshold)
            else:
                clips[clip.name] = clip.audibleframes(threshold)
            files.update( {clip.name: clip.file} )
        return clips, files
            

if __name__ == '__main__':
    import sys
    from pprint import pprint as pp
    xmeml = XmemlParser(sys.argv[1])
    #pp( [cl.name for cl in xmeml.iteraudioclips() if cl.name.startswith('SCD0')])
    clips, files = xmeml.audibleranges(0.0300)
    pp([(clip,r) for (clip,r) in clips.iteritems()])# if clip.startswith('SCD048720')])

