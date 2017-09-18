# =============================================================================
# The following statements are required to register this I/O plugin:
# =============================================================================
from .dcm import load_dicom

FORMAT_NAME = "DICOM images"
FORMAT_EXT  = ".dcm"
FORMAT_LOAD = load_dicom
FORMAT_SAVE = None