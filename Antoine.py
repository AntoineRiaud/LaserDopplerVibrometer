import h5py
import os
import time
from RF_readout_board import*
from galvomirrors import *
import pico2000
import pico5000
from scipy.spatial import ConvexHull
from matplotlib.path import Path
from hdf5_utils import *
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from LDV_scanner import *

for_test=False

#ldv = LDV_scanner([0,0],0) #for test only
with pico2000.Pico2000() as scope1, pico2000.Pico2000() as scope2, pico5000.Pico5000() as scope:
        ldv = LDV_scanner([scope1,scope2],scope) #TODO change folder options
        if for_test: scope.set_trigger(threshold=0.4) #using the AOM driver as a proxy for the acoustic signal
        scope.add_channel(source='D',chRange=1.)
        scope.set_trigger(threshold_mV=1000,source='D')
        scope.set_timeBase(noSamples=int(20e3),sampleRate=20e6)
        scope.awg.set_builtin(freq=[6.5e6, 6.5e6],pkToPk=2.)
        ldv.scan(timeBetweenSegments=3e-3)