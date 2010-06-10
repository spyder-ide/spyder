# -*- coding:utf-8 -*-
"""Example of I/O plugin for loading DICOM files"""

import os.path as osp

try:
    import dicom
    def load_dicom(filename):
        try:
            name = osp.splitext(osp.basename(filename))[0]
            return {name: dicom.ReadFile(filename).PixelArray}, None
        except Exception, error:
            return None, str(error)
except ImportError:
    load_dicom = None

FORMAT_NAME = "DICOM images"
FORMAT_EXT  = ".dcm"
FORMAT_LOAD = load_dicom
FORMAT_SAVE = None
