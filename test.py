import sys
from xmeml import VideoSequence

v1 = VideoSequence(file=sys.argv[1])
for z in [v for v in v1.track_items if v.track.type == "audio"]:
    print "%s (%s): " % (z.name, z.track.type)
    print z.audibleframes()

