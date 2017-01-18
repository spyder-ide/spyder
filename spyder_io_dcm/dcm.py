# -*- coding:utf-8 -*-
"""Example of I/O plugin for loading DICOM files"""

import os.path as osp

try:
    try:
        # pydicom 0.9
        import dicom as dicomio
    except ImportError:
        # pydicom 1.0
        from pydicom import dicomio
    def load_dicom(filename):
        try:
            name = osp.splitext(osp.basename(filename))[0]
            try:
                data = dicomio.read_file(filename, force=True)
            except TypeError:
                data = dicomio.read_file(filename)                
            arr = data.pixel_array
            return {name: arr}, None
        except Exception as error:
            return None, str(error)
except ImportError:
    load_dicom = None

