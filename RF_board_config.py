#connections
'''
channel A: Photodiode readout = pll input
channel B: circuit output (after mixing and filtering)
channel C: pll output (shift 235 degrees to A optimally)
channel D: NC
'''

import copy

#startup config
scope_settings = {'resolution':'8BIT',
                 'sampleRate':250e6,
                 'noSamples': int(1e6),
                 'segmentIndex':0,
                 'startIndex':0,
                 'down_sample_blocksize':0,
                 'reduction_mode':'none'}
channel_A_settings = {'enabled':True,
                    'coupling_type':'DC',
                    'chRange':1.,
                    'analogueOffset':0.,
                    'reduction_mode':'none'}
channel_B_settings = {'enabled':True,
                    'coupling_type':'DC',
                    'chRange':0.5,
                    'analogueOffset':0.,
                    'reduction_mode':'none'}
channel_C_settings = {'enabled':False,
                    'coupling_type':'DC',
                    'chRange':2.,
                    'analogueOffset':0.,
                    'reduction_mode':'none'}
channel_D_settings = {'enabled':False,
                    'coupling_type':'DC',
                    'chRange':2.,
                    'analogueOffset':0.,
                    'reduction_mode':'none'}
trigger_settings = {'enabled':True,
                  'source':'B',
                  'threshold':0.,
                  'direction':'rising',
                  'delay_s':0.,              
                  'auto_trigger_ms':10,
                  'preTrigger':0.2, #20%
                  'segmentIndex':0,
                  'nSegments':1}
awg_settings = {'offsetVoltage': 0.5, #to replace with a (high-quality) constant voltage source
              'pkToPk': 0.,
              'waveType':'dc_voltage',
              'freq': [20e6,20e6],
              'increment':0,
              'dwellTime':1,
              'sweepType':'up',
              'shots':0,
              'sweeps':0,
              'direction':'rising',
              'triggerSource':'none',
              'threshold':0.}

pico5000_configPLL = {'scope':scope_settings,
                   'trigger':trigger_settings,
                   'awg':awg_settings,
                   'A':channel_A_settings,
                   'B':channel_B_settings,
                   'C':channel_C_settings,
                   'D':channel_D_settings}



pico5000_configLDV = copy.deepcopy(pico5000_configPLL)

pico5000_configLDV['scope'].update({'noSamples': int(5e3)})
pico5000_configLDV['trigger'].update({'source':'A',
                                      'threshold':0.5,
                                      'direction':'gate_high',
                                      'auto_trigger_ms':0,
                                      'nSegments':32})
pico5000_configLDV['awg'].update({'triggerSource':'soft_trig',
                                      'direction':'rising',
                                      'waveType':'sine',
                                      'pkToPk': 0.1,
                                      'shots':10})


pico5000_config_virtualBoard = copy.deepcopy(pico5000_configPLL)
pico5000_config_virtualBoard['scope'].update({'resolution':'12BIT',
                                    'sampleRate':500e6})