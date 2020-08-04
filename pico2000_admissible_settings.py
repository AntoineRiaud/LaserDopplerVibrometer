import numpy as np
from picosdk.ps2000 import ps2000 as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc


channel_index = {'A':"PS2000_CHANNEL_A",
                 'B':"PS2000_CHANNEL_B"}

coupling_type_index = {'DC':"DC",
                       'AC':"AC"}

range_index = {2e-2:"PS2000_20MV",
               5e-2:"PS2000_50MV",
               0.1:"PS2000_100MV",
               0.2:"PS2000_200MV",
               0.5:"PS2000_500MV",
               1.:"PS2000_1V",
               2.:"PS2000_2V",
               5.:"PS2000_5V",
              10.:"PS2000_10V",
              20.:"PS2000_20V"}

direction_index = {'rising':0,
                      'falling':1,
                       'gate_high':2,
                       'gate_low':3,
                       'trig_type':4}

wave_index = {'sine':0,
                'square':1,
                'triangle':2,
                'dc_voltage':8}

sweep_type_index = {'up':0,
                     'down':1,
                     'updown':2,
                     'downup':3,
                     'max_sweep_types':4}

info_index = {'driver_version':0,
              'usb_version':1,
              'hardware_version':2,
              'variant_info':3,
              'batch_and_serial':4,
              'cal_date':5,
              'error_code':6,
              'kernel_driver_version':7}

def check_kwargs_scope(**kwargs):
    if 'enabled' in kwargs: 
        assert type(kwargs['enabled']) is bool, 'enabled must be True or False'
    if 'coupling_type' in kwargs:
        assert kwargs['coupling_type'] in coupling_type_index, 'coupling type should be either {0}'.format(coupling_type_index.keys())
    if 'chRange' in kwargs:
        assert kwargs['chRange'] in range_index, 'chRange should belong to {0}'.format(range_index.keys())
    #analogueOffset has to be checked with the scope
    if 'source' in kwargs:
        assert kwargs['source'] in channel_index, 'source should belong to {0}'.format(channel_index.keys())
    if 'threshold' in kwargs:
        assert type(kwargs['threshold']) is float, 'threshold should be a float'
    if 'direction' in kwargs:
        assert kwargs['direction'] in direction_index, 'direction should belong to {0}'.format(direction_index.keys())
    if 'delay_s' in kwargs:
        assert type(kwargs['delay_s']) is float, 'delay should be a float'
    if 'auto_trigger_ms' in kwargs:
        assert type(kwargs['auto_trigger_ms']) is int, 'auto_trigger_ms should be a float'
    if 'preTrigger' in kwargs:
        assert type(kwargs['preTrigger']) is float, 'preTrigger should be a float'
        assert (kwargs['preTrigger']<=1 and kwargs['preTrigger']>=0), 'preTrigger should be between 0(0%) and 1(100%)'
    if 'oversample' in kwargs:
        assert type(kwargs['oversample']) is int, 'oversample should be an int'
    if 'waveType' in kwargs:
        assert kwargs['waveType'] in wave_index, 'waveType should belong to {0}'.format(wave_index.keys())
    if 'sweepType' in kwargs:
        assert kwargs['sweepType'] in sweep_type_index, 'sweepType should belong to {0}'.format(sweep_type_index.keys())
    if 'sweeps' in kwargs:
        assert type(kwargs['sweeps']) is int, 'sweeps should be an int'