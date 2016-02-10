import sys
from xmeml import VideoSequence
from xmeml.iter import XmemlParser

def test_read(f):
    'Read file'
    x = XmemlParser(f)
    assert x


def test_audibleranges(f):
    x = XmemlParser(f)
    for cl in x.iteraudioclips(onlypureaudio=True):
        cl.audibleframes()



"""
  v1 = VideoSequence(file=sys.argv[1])
  for z in [v for v in v1.track_items if v.track.type == "audio"]:
      print z.name, z.audibleframes()

"""

if __name__ == '__main__':
    test_read(sys.argv[1])
    test_audibleranges(sys.argv[1])
