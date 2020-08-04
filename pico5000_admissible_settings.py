import numpy as np
from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

channel_index = {'A':"PS5000A_CHANNEL_A",
                 'B':"PS5000A_CHANNEL_B",
                 'C':"PS5000A_CHANNEL_C",
                 'D':"PS5000A_CHANNEL_D",
                'Ext':"PS5000A_EXTERNAL",
                'Pulse':"PS5000A_PULSE_WIDTH_SOURCE"}
coupling_type_index = {'DC':"PS5000A_DC",
                       'AC':"PS5000A_AC"}
range_index = {1e-2:"PS5000A_10MV",
               2e-2:"PS5000A_20MV",
               5e-2:"PS5000A_50MV",
               0.1:"PS5000A_100MV",
               0.2:"PS5000A_200MV",
               0.5:"PS5000A_500MV",
               1.:"PS5000A_1V",
               2.:"PS5000A_2V",
               5.:"PS5000A_5V",
              10.:"PS5000A_10V",
              20.:"PS5000A_20V",
              50.:"PS5000A_50V",
              np.inf:"PS5000A_MAX_RANGES"}
wave_index = {'sine':0,
                'square':1,
                'triangle':2,
                'dc_voltage':8}
direction_index = {'rising':0,
                      'falling':1,
                       'gate_high':2,
                       'gate_low':3,
                       'trig_type':4}
trigger_source_index = {'none':0,
                       'scope_trig':1,
                       'ext_in':3,
                       'soft_trig':4,
                       'trig_source':5}
sweep_type_index = {'up':0,
                     'down':1,
                     'updown':2,
                     'downup':3,
                     'max_sweep_types':4}

sample_rate = {'8BIT': lambda n: 1e9/2**n if n<3 else 125e6/(n-2),
               '12BIT': lambda n: 500e6/2**n if n<3 else 62.5e6/(n-2),
               '14BIT': lambda n: 125e6/2**n if n==3 else 125e6/(n-2),
               '15BIT': lambda n: 125e6/2**n if n==3 else 125e6/(n-2),
               '16BIT': lambda n: 62.5e6/2**n if n==4 else 62.5e6/(n-2)}

ratio_mode_index = {'none':0,
                    'aggregate':1,
                    'decimate':2,
                    'average':4}

info_index = {'driver_version':0,
              'usb_version':1,
              'hardware_version':2,
              'variant_info':3,
              'batch_and_serial':4,
              'cal_date':5,
              'kernel_driver_version':6,
              'digital_hardware_version':7,
              'analog_hardware_version':8,
              'firmware_version1':9,
              'firmware_version1':10
              }


def check_kwargs_scope(**kwargs):
    if 'enabled' in kwargs: 
        assert type(kwargs['enabled']) is bool, 'enabled must be True or False'
    if 'noSamples' in kwargs: 
        assert type(kwargs['noSamples']) is int, 'noSamples must be an int'
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
        assert type(kwargs['auto_trigger_ms']) is int, 'auto_trigger_ms should be an int'
    if 'preTrigger' in kwargs:
        assert type(kwargs['preTrigger']) is float, 'preTrigger should be a float'
        assert (kwargs['preTrigger']<=1 and kwargs['preTrigger']>=0), 'preTrigger should be between 0(0%) and 1(100%)'
    if 'reduction_mode' in kwargs:
        assert kwargs['reduction_mode'] in ratio_mode_index, 'reduction_mode should belong to {0}'.format(ratio_mode_index.keys())
    if 'startIndex' in kwargs:
        assert type(kwargs['startIndex']) is int, 'startIndex should be an int'
    if 'down_sample_blocksize' in kwargs:
        assert type(kwargs['down_sample_blocksize']) is int, 'down_sample_blocksize should be an int'
    if 'nSegments' in kwargs:
        assert type(kwargs['nSegments']) is int, 'nSegments should be an int'
    if 'TriggerSource' in kwargs:
        assert kwargs['triggerSource'] in trigger_source_index, 'triggerSource should belong to {0}'.format(trigger_source_index.keys())
    if 'waveType' in kwargs:
        assert kwargs['waveType'] in wave_index, 'waveType should belong to {0}'.format(wave_index.keys())
    if 'sweepType' in kwargs:
        assert kwargs['sweepType'] in sweep_type_index, 'sweepType should belong to {0}'.format(sweep_type_index.keys())
    if 'shots' in kwargs:
        assert type(kwargs['shots']) is int, 'shots should be an int'
    if 'sweeps' in kwargs:
        assert type(kwargs['sweeps']) is int, 'sweeps should be an int'