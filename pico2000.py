#
# Copyright (C) 2018 Pico Technology Ltd. See LICENSE file for terms.
#
# PS2000A BLOCK MODE EXAMPLE
# This example opens a 2000a driver device, sets up two channels and a trigger then collects a block of data.
# This data is then plotted as mV against time in ns.

import ctypes
import numpy as np
from picosdk.ps2000 import ps2000 as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico2000_ok, mV2adc
from pico2000_admissible_settings import*
import helper_functions
import time

class Channel():
    def __init__(self,scope,source='A',**kwargs):
        self.chandle = scope.chandle
        self.status = {}
        assert source in ['A','B'], 'channel name should be either A or B'
        self.source = source
        self.settings = {'coupling_type':'DC',#default values
                        'chRange':2.}
        self.set_channel(**kwargs)
        
    def set_channel(self, **kwargs):
        # Set up channel
        settings = {} #in case of failure, settings is updated only at the end
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
            
        #checks
        check_kwargs_scope(**kwargs)
        
        # handle = chandle
        _channel = ctypes.c_int16(ps.PS2000_CHANNEL[channel_index[self.source]])
        _coupling_type = ctypes.c_int16(ps.PICO_COUPLING[coupling_type_index[settings['coupling_type']]])
        _chRange = ctypes.c_int16(ps.PS2000_VOLTAGE_RANGE[range_index[settings['chRange']]])
        self.status["setCh"] = ps.ps2000_set_channel(self.chandle, _channel, 1, 
                                                _coupling_type,_chRange) 
        assert_pico2000_ok(self.status["setCh"])
        self.settings = settings
        self._chRange = _chRange
        
class Trigger():
    
    def __init__(self,scope,**kwargs):
        self.scope = scope
        self.chandle = scope.chandle
        self.settings =  {'enabled':True,
                          'source':'A',
                          'threshold':0.,
                          'direction':'rising',
                          'delay_s':0.,              
                          'auto_trigger_ms':1000,
                          'preTrigger':0.5, #50%
                          'segmentIndex':0}
        self.status = {}
        self.set_trigger(scope,**kwargs)

    def set_trigger(self,scope,**kwargs):
        # Set up single trigger
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        
        check_kwargs_scope(**kwargs)
        possible_sources = ['A','B']
        possible_sources.append('Ext')
        assert settings['source'] in possible_sources, 'the trigger source channel should be enabled'
        source = scope.channels[settings['source']]
        if 'timeIntervalSeconds' in settings:
            delay = int(settings['delay_s']/scope.settings['timeIntervalSeconds'])
        else:
            delay = 0
        _source = ctypes.c_int16(ps.PS2000_CHANNEL[channel_index[settings['source']]])
        _chRange = ps.PS2000_VOLTAGE_RANGE[range_index[source.settings['chRange']]]
        _threshold = ctypes.c_int16(int(mV2adc(1e3*settings['threshold'],_chRange, scope._maxADC)))
        _direction = ctypes.c_int16(int(direction_index[settings['direction']]))
        _delay = ctypes.c_int16(delay)
        _autoTrigger_ms = ctypes.c_int16(settings['auto_trigger_ms'])
        # direction = PS5000A_RISING = 2
        # delay = 0 s
        # auto Trigger = 1000 ms
        self.status["trigger"] = ps.ps2000_set_trigger(self.chandle, 
                                                       _source, 
                                                       _threshold, _direction, 
                                                       _delay, _autoTrigger_ms)
        assert_pico2000_ok(self.status["trigger"])
        self.settings = settings
    
    
    def runBlock(self,scope,**kwargs): 
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        check_kwargs_scope(**kwargs)  
        _noSamples = int(scope.settings['noSamples'])
        _timebase = scope.settings['timebase']
        _timeIndisposeMs = ctypes.c_int32()
        _oversample = ctypes.c_int16(scope.settings['oversample'])
        #additional callback options here, use isready instead
        self.status["runBlock"] = ps.ps2000_run_block(self.chandle, _noSamples, 
                                                _timebase, _oversample, ctypes.byref(_timeIndisposeMs))
        assert_pico2000_ok(self.status["runBlock"])
        self.settings = settings


class Function_generator():
    def __init__(self,scope):
        self.chandle = scope.chandle
        self.scope = scope
        self.settings = {'offsetVoltage': 0., #defaults values
                          'pkToPk': 1.,
                          'waveType':'sine',
                          'freq': [1e3,1e3],
                          'increment':0,
                          'dwellTime':1,
                          'sweepType':'up',
                          'sweeps':0}
        self.status = {}
        
    
    def set_builtin(self,**kwargs):
        '''
        sets the scope built-in arbitrary generator:
        arguments: none
        keyword arguments:
            offsetVoltage: (in V)
            pkToPk:        (in V)
            waveType:      sine/square/triangle/dc_voltage
            freq:          start and stop frequencies, for sweep (List, in Hz)
                           from 100 mHz up to 100 kHz
            ---Advanced----
            increment:     frequency increment (in Hz)
            dwellTime:     frequency increment rate (in Hz/s)
            sweepType:     up/down/updown/downup   the type of frequency sweep
            sweeps:        number of sweeps to output
        '''
        #handles default values
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        check_kwargs_scope(**kwargs)
        assert settings['pkToPk'] <= 2.0, 'max pkToPk is 2 Vpp'
        assert settings['offsetVoltage'] <= 2.0, 'max offset is 2 V'
        assert (min(settings['freq'])>100e-3 and max(settings['freq'])<100e3), 'freq can range from 100 mHz up to 100 kHz'
        _offsetVoltage = ctypes.c_int32(int(settings['offsetVoltage']*1e6))
        _pkToPk = ctypes.c_uint32(int(settings['pkToPk']*1e6))        
        _waveType = ctypes.c_int32(wave_index[settings['waveType']])
        _freqMin = ctypes.c_float(settings['freq'][0])
        _freqMax = ctypes.c_float(settings['freq'][-1])
        _increment = ctypes.c_float(settings['increment'])
        _dwellTime = ctypes.c_float(settings['dwellTime'])        
        _sweepType = ctypes.c_int32(sweep_type_index[settings['sweepType']])
        _sweeps = ctypes.c_uint32(settings['sweeps'])
        
        
        self.status["setSigGenBuiltIn"] = ps.ps2000_set_sig_gen_built_in(self.chandle, 
                                                                    _offsetVoltage, 
                                                                    _pkToPk, 
                                                                    _waveType, 
                                                                    _freqMin, _freqMax, 
                                                                    _increment,
                                                                    _dwellTime, 
                                                                    _sweepType,  
                                                                    _sweeps)
        assert_pico2000_ok(self.status["setSigGenBuiltIn"])
        self.settings = settings




class Pico2000():
    def __init__(self):
        # Create status ready for use
        self.status = {}
        self.settings = {'timebase':8,
                         'noSamples':2000,
                         'segmentIndex':0,
                         'oversample':1}
        self.channels = {}
        self._maxADC = ctypes.c_int16(32767)
        # Open 2000 series PicoScope
        # Returns handle to chandle for use in future API functions
        self.status["openUnit"] = ps.ps2000_open_unit()
        assert_pico2000_ok(self.status["openUnit"])
        
        # Create chandle for use
        self.chandle = ctypes.c_int16(self.status["openUnit"])
        self.add_channel(source='A')
        self.add_channel(source='B')
        self.trigger = Trigger(self)
        self.set_timeBase()
        self.awg = Function_generator(self)
        
            
            
    def close(self):
        # Close unit Disconnect the scope
        # Stop the scope
        # handle = chandle
        self.status["stop"] = ps.ps2000_stop(self.chandle)
        assert_pico2000_ok(self.status["stop"])
        
        # Close unitDisconnect the scope
        # handle = chandle
        self.status["close"] = ps.ps2000_close_unit(self.chandle)
        assert_pico2000_ok(self.status["close"])
        # display status returns
        print('The scope was successfully closed')

    def __enter__(self):
        return self
    
    def __exit__(self,type,value,traceback):
        self.close()
        
    def add_channel(self,source='A',**kwargs):
        self.channels[source]=Channel(self,source=source,**kwargs)


    def _timeBase(self,settings,timebase):
        assert type(timebase) is int
        _timeInterval = ctypes.c_int32()
        _timeUnits = ctypes.c_int32()
        _oversample = ctypes.c_int16(settings['oversample'])
        _maxSamples = ctypes.c_int32()
        self.status["getTimebase"] = ps.ps2000_get_timebase(self.chandle, timebase,
                                                settings['noSamples'], ctypes.byref(_timeInterval), 
                                                ctypes.byref(_timeUnits), _oversample, 
                                                ctypes.byref(_maxSamples))
        assert_pico2000_ok(self.status["getTimebase"])
        timeIntervalSeconds = 1e-9*_timeInterval.value
        out = {'sampleRate':1./timeIntervalSeconds,
               'noSamples':_maxSamples.value,
               'timeIntervalSeconds':timeIntervalSeconds,
               '_timeUnits':_timeUnits}
        return out
    
    @property
    def info(self):
        '''
        returns a dictionary containing driver_version, usb_version, hardware_version, variant_info, batch_and_serial, cal_date, error_code and kernel_driver_version
        '''
        info_out = {}
        _string = (ctypes.c_char*100)() #info output buffer
        _stringLength = ctypes.c_int16(100) #max info buffer length
        for key,value in info_index.items():
            _line = ctypes.c_int16(value)
            status = ps.ps2000_get_unit_info(self.chandle,_string,_stringLength,_line)
            assert_pico2000_ok(status)
            info_out[key]=_string.value.decode('utf-8')
        return info_out
            
        
    def set_timeBase(self,**kwargs):
        '''
        sets the timebase options. Several options are available:
        - directly set the timebase (0 up 23, machine option)
        - set the sampling rate
        - set the time interval between samples
        arguments: none
        keyword arguments (defaults in self.settings):
            timebase: the timebase to use (not recommended),
            noSamples: the desired number of samples (the actual number of samples may differ),
            oversample: the scope averages many samples in a single point in order to increase the resolution (number of points to average),
            ***
            sampleRate: the desired sample rate (in samples/s)  (the actual sample rate may differ),
            --or--
            timeIntervalSeconds: the desired time interval between samples (in s) (the actual time interval rate may differ),
            ***
        after successfully setting the trigger,  self.settings is updated and contains:
            sampleRate: the actual sample rate (in samples/s),
            timeIntervalSeconds: the actual time interval between samples (in s),
        '''
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        #overwrites the timebase with either timeIntervalNanoseconds or sampleRate
        #if these two parameters are provided, the conflict is raised
        assert not ('sampleRate' in kwargs and 'timeIntervalSeconds' in kwargs)
        if 'sampleRate' in kwargs:
            value = kwargs['sampleRate']
            timeBaseFunction = lambda timebase: self._timeBase(settings,timebase)['sampleRate']
            growing = False
        if 'timeIntervalSeconds' in kwargs:
            value = kwargs['timeIntervalSeconds']
            timeBaseFunction = lambda timebase: self._timeBase(settings,timebase)['timeIntervalSeconds']
            growing = True
        if 'sampleRate' in kwargs or 'timeIntervalSeconds' in kwargs:
            settings['timebase'] = helper_functions.dichotomic_search(timeBaseFunction,len(self.channels),23,f0=value,tol=1,growing=growing)
        out = self._timeBase(settings,settings['timebase'])
        settings['sampleRate'] = out['sampleRate']
        settings['timeIntervalSeconds'] = out['timeIntervalSeconds']
        settings['noSamples'] = settings['noSamples']
        self.settings = settings
        
    def runBlock(self,**kwargs):
        self.trigger.runBlock(self,**kwargs)
    
    
    @property
    def isBusy(self):
        '''
        returns True if the scope is busy and False otherwise
        '''
        check = ctypes.c_int16(0)   
        self.status["isReady"] = ps.ps2000_ready(self.chandle)
        ready = ctypes.c_int16(self.status["isReady"])
        return ready.value==check.value
    
    
    
    def waitUntilReady(self,timeout=1.):
        '''
        waits until the scope is ready
        '''
        start_time = time.time()
        while self.isBusy:
            time.sleep(0.01)
            if time.time()-start_time>timeout: raise TimeoutError('The scope did not respond')
    
    def read(self,**kwargs):
        '''
        reads the scope results:
        arguments: none
        keyword arguments: none
        the results (in V) are returned in a dictionary:
            time:                   the time (in s)
            A (V):   channel A voltage (in V)
            B (V):   channel B voltage (in V)
        '''
        #handles default values
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        check_kwargs_scope(**kwargs)  
        # Create buffers ready for data
        _bufferA = (ctypes.c_int16 * self.settings['noSamples'])()
        _bufferB = (ctypes.c_int16 * self.settings['noSamples'])()
        #_bufferC = None
        #_bufferD = None
        # create overflow loaction
        _overflow = ctypes.c_int16()
        # create converted type maxSamples
        cmaxSamples = ctypes.c_int32(self.settings['noSamples'])
        self.status["getValues"] = ps.ps2000_get_values(self.chandle, ctypes.byref(_bufferA),  
                                                        ctypes.byref(_bufferB), None, None,
                                                        ctypes.byref(_overflow), cmaxSamples)
        assert_pico2000_ok(self.status["getValues"])

        self.settings = settings
        
        # Create time data
        time = np.linspace(0, (cmaxSamples.value) * self.settings['timeIntervalSeconds'], cmaxSamples.value)

        results = {'time (s)':time}
        # convert ADC counts data to mV
        adc2mVChA =  adc2mV(_bufferA, self.channels['A']._chRange.value, self._maxADC)
        adc2mVChB =  adc2mV(_bufferB, self.channels['B']._chRange.value, self._maxADC)
        results['A (V)']=1e-3*np.array(adc2mVChA).reshape(-1,1)
        results['B (V)']=1e-3*np.array(adc2mVChB).reshape(-1,1)
        return results    

    def save_config(self):
        '''
        return a dictionnary describing the scope configuration,
        to use with recall_config
        '''
        config = {'scope':self.settings,
                    'trigger':self.trigger.settings,
                    'awg':self.awg.settings}
        for channelName, channel in self.channels.items():
            config[channelName]=channel.settings
        return config
    
    def recall_config(self,config):
        '''
        recall the scope configuration from a config dictionnary,
        config dictionnary can be generated with save_config
        '''
        for channelName, channelSettings in config.items():
            if channelName in ['A','B','C','D']:
                self.channels[channelName].set_channel(**channelSettings)
        self.set_timeBase(**config['scope'])
        self.trigger.set_trigger(self,**config['trigger'])
        self.awg.set_builtin(**config['awg'])
        
if __name__ =='__main__':
    
    with Pico2000() as scope:
        #scope.set_timeBase(timebase = 8)
        print(scope.info)
        scope.set_timeBase(timeIntervalSeconds = 1e-6)
        scope.awg.set_builtin()
        scope.runBlock()
        print(scope.isBusy)
        time.sleep(2)
        print(scope.isBusy)
        results = scope.read()
        results = scope.read()
        plt.figure()
        plt.plot(1e6*results['time (s)'],results['A (V)'])
        plt.show()