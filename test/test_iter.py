# encoding: utf-8
# tests of xmeml logic

from __future__ import unicode_literals
from distutils import dir_util
from pytest import fixture
import os
import sys
import pytest

from xmeml import iter as xmemliter


## THANK YOU http://stackoverflow.com/a/29631801

@fixture
def datadir(tmpdir, request):
    '''
    Fixture responsible for searching a folder with the same name of test
    module and, if available, moving all contents to a temporary directory so
    tests can use them freely.
    '''
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)

    if os.path.isdir(test_dir):
        dir_util.copy_tree(test_dir, bytes(tmpdir))

    return tmpdir

def _fsdecode(b):
    try:
        return b.decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        pass

    try:
        return b.decode("iso-8859-15")
    except UnicodeEncodeError:
        return b.decode("utf-8", "replace")

def test_xmemlsamples(datadir):

    def load(f):
        print("test load {f}".format(f=_fsdecode(f.basename)))
        xmeml = xmemliter.XmemlParser(f.open())
        audioclips, audiofiles = xmeml.audibleranges()
        return xmeml

    #print datadir.listdir()
    for xml in datadir.listdir(fil=lambda x: _fsdecode(x.basename).upper().endswith(".XML")):
        _xmlbasename = _fsdecode(xml.basename)
        if _xmlbasename == 'EMPTY_SEQUENCE.xml':
            # empty sequence test, expect error raised
            with pytest.raises(xmemliter.XmemlFileError):
                load(xml)
            continue
        assert load(xml)

