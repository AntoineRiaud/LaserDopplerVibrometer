#connections
'''
channel A: position
channel B: error*5
channel AWG: command
'''

import copy

#startup config
scope_settings = {'sampleRate':1e7, #1e3
                 'noSamples': int(2e3),
                 'segmentIndex':0,
                 'oversample':1}
channel_A_settings = {'coupling_type':'DC',
                    'chRange':10.}
channel_B_settings = {'coupling_type':'DC',
                    'chRange':0.05}
trigger_settings = {'enabled':True, #TODO
                  'source':'B',
                  'threshold':0.,
                  'direction':'rising',
                  'delay_s':0.,              
                  'auto_trigger_ms':10,
                  'preTrigger':0.2, #20%
                  'segmentIndex':0,
                  'nSegments':1}
awg_settings = {'offsetVoltage': 0., 
              'pkToPk': 0.,
              'waveType':'dc_voltage',
              'freq': [1e3,1e3],
              'increment':0,
              'dwellTime':1,
              'sweepType':'up',
              'shots':0,
              'sweeps':0,
              'direction':'rising',
              'triggerSource':'none',
              'threshold':0.}

pico2000_config = {'scope':scope_settings,
                   'trigger':trigger_settings,
                   'awg':awg_settings,
                   'A':channel_A_settings,
                   'B':channel_B_settings}

all_motors_config = {'volts_per_deg':0.8,
                     'output_deg_per_volts':0.5,
                     'output_error_deg_per_volts':2.5,
                     'step_response(ms)':0.3,
                     'fullscale_response(ms)':10.,
                     'moving_tol(deg)':0.05} #final error 0.26um with 4x objective 
                     
xconfig = copy.deepcopy(all_motors_config)
yconfig = copy.deepcopy(all_motors_config)
xconfig.update({'SN':'GO027/758','gain':5.0,'offset':-100e-3})
yconfig.update({'SN':'GO027/181','gain':5.0,'offset':-150e-3})
motors_config = {'X':xconfig,
                 'Y':yconfig}

#lenses
lens_specs = {'4x':{'product_ID':'RMS4X',
                'manufacturer':'Olympus',
                'manufacturerID':'1-U2B222',
                'tube_length (mm)':180.,
                'NA':0.1,'Magnification':4.,
                'effectiveFocalLength(mm)':45.},
         '100mm':{'product_ID':'AC254-100-A-ML',
                'manufacturer':'Thorlabs',
                'effectiveFocalLength(mm)':100.},
         'scan':{'product_ID':'LSM03-VIS',
                'manufacturer':'Thorlabs',
                'effectiveFocalLength(mm)':39.},
         'camLens':{'product_ID':'MVL75M23    ',
                'manufacturer':'Navitar',
                'effectiveFocalLength(mm)':75.}}

camera_specs = {'model':'DCC1645C',
                'sensor':'Aptina MT9M131(Color)',
                'resolution':(1280,1024),
                'sensitive_area (mm2)':(4.61,3.69),
                'pixel_size (um)':3.6}
