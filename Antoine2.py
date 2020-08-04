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

freqs = np.array([20])*1e6
for freqi in freqs:
    print(freqi)
    #ldv = LDV_scanner([0,0],0) #for test only
    with pico2000.Pico2000() as scope1, pico2000.Pico2000() as scope2, pico5000.Pico5000() as scope:
        with LDV_scanner([scope1,scope2],scope,readout='digital', scan_path={'type':'circle','radius (mm)':0.90,'resolution (um)':50.}) as ldv: #= 25.#TODO change folder options 
            if for_test: scope.set_trigger(threshold=0.4) #using the AOM driver as a proxy for the acoustic signal
            #scope.add_channel(source='D',chRange=5.)
            scope.channels['A'].set_channel(chRange=1.0,coupling_type='AC')
            scope.channels['B'].set_channel(enabled=False)
            scope.set_trigger(threshold_mV=500,source='Ext',direction='gate_high')
            scope.set_timeBase(noSamples=int(6e3),sampleRate=500e6)
            scope.awg.set_builtin(freq=[freqi, freqi],pkToPk=2.,offsetVoltage=0.,shots=20)
            scope.resolution='12BIT'
            print('Scope resolution: {0}'.format(scope.resolution))
            print(scope.enabledChannels)
            ldv.scan(timeBetweenSegments=1e-3)