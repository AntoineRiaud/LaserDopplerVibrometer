#
# Copyright (C) 2018 Pico Technology Ltd. See LICENSE file for terms.
#
# PS5000A BLOCK MODE EXAMPLE
# This example opens a 5000a driver device, sets up two channels and a trigger then collects a block of data.
# This data is then plotted as mV against time in ns.

import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
from pico5000_admissible_settings import*
import helper_functions
import time



class Channel():
    def __init__(self,scope,source='A',**kwargs):
        self.chandle = scope.chandle
        self.scope = scope
        self.status = {}
        assert source in ['A','B','C','D'], 'channel name should be either A,B,C or D'
        self.source = source
        self.settings = {'enabled':True, #default values
                        'coupling_type':'DC',
                        'chRange':2.,
                        'analogueOffset':0.,
                        'reduction_mode':'none'}
        self.set_channel(**kwargs)
        
    def set_channel(self, **kwargs):
        '''
        set-up an oscilloscope channel. 
        arguments: none
        keyword arguments (defaults in channel.settings):
            enabled: True/False
            coupling_type: DC/AC
            chRange: channel voltage range (from 10mV up to 50V)
            analogueOffset: channel analogue offset (roughly -chRange up to +chRange) 
        after successfully setting the channel,  self.settings is updated
        '''
        # Set up channel
        settings = {} #in case of failure, settings is updated only at the end
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        
        #checks
        check_kwargs_scope(**kwargs)
        if 'analogueOffset' in kwargs:
            self.check_analogueOffset(settings)
        
        # handle = chandle
        self._source = ps.PS5000A_CHANNEL[channel_index[self.source]]
        _enabled = int(settings['enabled'])
        _coupling_type = ps.PS5000A_COUPLING[coupling_type_index[settings['coupling_type']]]
        _chRange = ps.PS5000A_RANGE[range_index[settings['chRange']]]
        _analogueOffset = ctypes.c_float(settings['analogueOffset']) #V
        self.status["setCh"] = ps.ps5000aSetChannel(self.chandle, self._source, _enabled, 
                                                _coupling_type, _chRange, _analogueOffset)
        assert_pico_ok(self.status["setCh"])
        self.settings = settings
        
    def check_analogueOffset(self,settings):
        #queries maximum allowable analogueOffset range
        _chRange = ps.PS5000A_RANGE[range_index[settings['chRange']]]
        _coupling_type = ps.PS5000A_COUPLING[coupling_type_index[settings['coupling_type']]]
        minOffset = ctypes.c_float()
        maxOffset = ctypes.c_float()
        status = ps.ps5000aGetAnalogueOffset(self.chandle, _chRange,_coupling_type, ctypes.byref(maxOffset),ctypes.byref(minOffset))
        assert_pico_ok(status)
        assert_msg = 'analogue offset should be within [{0}, {1}]V'.format(minOffset.value,maxOffset.value)
        assert (settings['analogueOffset']<=maxOffset.value and settings['analogueOffset']>=minOffset.value), assert_msg
        
    def _setDataBuffers(self,**kwargs):
        '''
        sets the data reduction method.
        arguments: none
        keyword arguments (defaults in channel.settings):
        reduction_mode:     'none':          no data reduction,
                            'aggregate':     min and max over block,
                            'decimate':      just the first value in the block
                            'average':       average over block
        segmentIndex: the segment to read (mostly useful for rapidBlock)
        '''
        settings = {} #in case of failure, settings is updated only at the end
        settings['segmentIndex'] = self.scope.settings['segmentIndex'] #default value
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        
        #checks
        check_kwargs_scope(**kwargs)
        
        maxSamples = self.scope.settings['noSamples']
        # Create buffers ready for assigning pointers for data collection
        _ratio_mode = ratio_mode_index[settings['reduction_mode']]
        self._bufferMax = [(ctypes.c_int16 * maxSamples)() for i in range(self.scope.trigger.settings['nSegments'])]
        self._bufferMin = [(ctypes.c_int16 * maxSamples)() for i in range(self.scope.trigger.settings['nSegments'])] # used for downsampling which isn't in the scope of this example
        for _bufferMax,_bufferMin,i in zip(self._bufferMax,self._bufferMin,range(self.scope.trigger.settings['nSegments'])):
            # Set data buffer location for data collection from channel
            # handle = chandle
            #source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
            # pointer to buffer max = ctypes.byref(bufferMax)
            # pointer to buffer min = ctypes.byref(bufferMin)
            # buffer length = maxSamples
            # segment index = 0
            # ratio mode = PS5000A_RATIO_MODE_NONE = 0
            self.status["setDataBuffers"] = ps.ps5000aSetDataBuffers(self.chandle, self._source, 
                                                                     ctypes.byref(_bufferMax), ctypes.byref(_bufferMin), 
                                                                     maxSamples, settings['segmentIndex']+i, _ratio_mode)
            assert_pico_ok(self.status["setDataBuffers"])
        self.settings = settings
    

    
    
    @property
    def data_max(self):
        _chRange = ps.PS5000A_RANGE[range_index[self.settings['chRange']]]
        out =[]
        for _bufferMax in self._bufferMax:
            out.append(1e-3*np.array(adc2mV(_bufferMax, _chRange, self.scope._maxADC)))
        return np.vstack(out).T
    
    @property
    def data_min(self):
        _chRange = ps.PS5000A_RANGE[range_index[self.settings['chRange']]]
        out =[]
        for _bufferMin in self._bufferMin:
            out.append(1e-3*np.array(adc2mV(_bufferMin, _chRange, self.scope._maxADC)))
        return np.vstack(out).T

class Trigger():
    
    def __init__(self,scope,**kwargs):
        self.chandle = scope.chandle
        self.scope = scope
        self.settings =  {'enabled':True,
                          'source':'A',
                          'threshold':0.,
                          'direction':'rising',
                          'delay_s':0.,              
                          'auto_trigger_ms':1000,
                          'preTrigger':0.5, #50%
                          'segmentIndex':0,
                          'nSegments':1}
        self.status = {}
        self.set_trigger(**kwargs)

    def set_trigger(self,**kwargs):
        '''
        set-up the oscilloscope trigger. 
        arguments: none
        keyword arguments (defaults in self.settings):
            enabled:         True/False
            source:          A/B/C/D/Ext
            direction:       rising/falling/gate_high/gate_low (only the latter two are available when using source: Ext)
            threshold:       trigger threshold (in V)
            delay_s:         post-trigger delay before recording (in s)
            auto_trigger_ms: trigger auto re-arming delay after recording (in ms), set to 0 for REPEAT and SINGLE modes
        after successfully setting the trigger,  self.settings is updated
        '''
        # Set up single trigger
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        
        check_kwargs_scope(**kwargs)
        possible_sources = self.scope.enabledChannels
        possible_sources.append('Ext')
        assert settings['source'] in possible_sources, 'the trigger source channel should be enabled'
        delay = int(settings['delay_s']/self.scope.settings['timeIntervalSeconds'])
        _source = ps.PS5000A_CHANNEL[channel_index[settings['source']]]
        _enabled = int(settings['enabled'])
        if settings['source'] in ['A','B','C','D']: #analog channels
            source = self.scope.channels[settings['source']]
            _chRange = ps.PS5000A_RANGE[range_index[source.settings['chRange']]]
        else: #source is Ext, range is -5V+5V
            allowed_directions = ['gate_high','gate_low']
            assert settings['direction'] in allowed_directions, 'direction should belong to {0}'.format(allowed_directions)
            _chRange = ps.PS5000A_RANGE[range_index[5.]]
        _threshold = int(mV2adc(int(1e3*settings['threshold']),_chRange, self.scope._maxADC))
        _direction = int(direction_index[settings['direction']])
        _delay = ctypes.c_uint32(delay)
        _autoTrigger_ms = ctypes.c_int16(settings['auto_trigger_ms'])
        time.sleep(0)
        # direction = PS5000A_RISING = 2
        # delay = 0 s
        # auto Trigger = 1000 ms
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, 
                                                       _enabled,_source, 
                                                       _threshold, _direction, 
                                                       _delay, _autoTrigger_ms)
        assert_pico_ok(self.status["trigger"])
        self.settings = settings
    
    
    def runBlock(self,**kwargs): 
        '''
        arms the trigger, block mode is close to repeat (with re-arm) or single mode (without re-arm)
        rapid block accumulates several events (similar to fast frame modes on other scopes)
        arguments: none
        keyword arguments (defaults in self.trigger.settings):
            preTrigger: fraction of samples before the trigger occurs (0 to 1)
            segmentIndex: scope memory segment to store the run result
        after successfully arming the trigger, self.trigger.settings is updated
        after triggering, the channel records the noSamples and then stops (until re-arming) 
        '''
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        check_kwargs_scope(**kwargs) 
        
        
        cmaxSamples = ctypes.c_int32(self.scope.settings['noSamples'])
        self.status["MemorySegments"] = ps.ps5000aMemorySegments(self.chandle, settings['nSegments'], ctypes.byref(cmaxSamples))
        assert_pico_ok(self.status["MemorySegments"])
        
        # sets number of captures
        self.status["SetNoOfCaptures"] = ps.ps5000aSetNoOfCaptures(self.chandle, settings['nSegments'])
        assert_pico_ok(self.status["SetNoOfCaptures"])
         
        _preTriggerSamples = int(self.scope.settings['noSamples']*settings['preTrigger'])
        _postTriggerSamples = self.scope.settings['noSamples'] - _preTriggerSamples
        _timebase = self.scope.settings['timebase']
        _timeIndisposeMs = ctypes.c_int32()
        _segmentIndex = settings['segmentIndex']
        #additional callback options here, use isready instead
        self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, _preTriggerSamples, _postTriggerSamples, 
                                                _timebase, ctypes.byref(_timeIndisposeMs), _segmentIndex, None, None)
        assert_pico_ok(self.status["runBlock"])
        self.settings = settings
        
    def runRapidBlock(self,**kwargs):
        '''
        arms the trigger, block mode is close to repeat (with re-arm) or single mode (without re-arm)
        rapid block accumulates several events (similar to fast frame modes on other scopes)
        arguments: none
        keyword arguments (defaults in self.trigger.settings):
            preTrigger: fraction of samples before the trigger occurs (0 to 1)
            segmentIndex: scope memory segment to store the run result
            nSegments: number of samples to capture
        after successfully arming the trigger, self.trigger.settings is updated
        after triggering, the channel records the noSamples and then stops (until re-arming) 
        '''
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        check_kwargs_scope(**kwargs)  
        # Handle = Chandle
        # nSegments = 10
        # nMaxSamples = ctypes.byref(cmaxSamples)
        cmaxSamples = ctypes.c_int32(self.scope.settings['noSamples'])
        self.status["MemorySegments"] = ps.ps5000aMemorySegments(self.chandle, settings['nSegments'], ctypes.byref(cmaxSamples))
        assert_pico_ok(self.status["MemorySegments"])
        
        # sets number of captures
        self.status["SetNoOfCaptures"] = ps.ps5000aSetNoOfCaptures(self.chandle, settings['nSegments'])
        assert_pico_ok(self.status["SetNoOfCaptures"])
        
        # Starts the block capture
        # Handle = chandle
        # Number of prTriggerSamples
        # Number of postTriggerSamples
        # Timebase = 2 = 4ns (see Programmer's guide for more information on timebases)
        # time indisposed ms = None (This is not needed within the example)
        # Segment index = 0
        # LpRead = None
        # pParameter = None
        _preTriggerSamples = int(self.scope.settings['noSamples']*settings['preTrigger'])
        _postTriggerSamples = self.scope.settings['noSamples'] - _preTriggerSamples
        _timebase = self.scope.settings['timebase']
        _timeIndisposeMs = ctypes.c_int32()
        _segmentIndex = settings['segmentIndex']
        self.status["runblock"] = ps.ps5000aRunBlock(self.chandle, _preTriggerSamples, _postTriggerSamples, 
                                                _timebase, ctypes.byref(_timeIndisposeMs), _segmentIndex, None, None)
        assert_pico_ok(self.status["runblock"])
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
                          'shots':0,
                          'sweeps':0,
                          'direction':'rising',
                          'triggerSource':'none',
                          'threshold':0.}
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
                           from 30 mHz up to 20 MHz
            ---Advanced----
            increment:     frequency increment (in Hz)
            dwellTime:     frequency increment rate (in Hz/s)
            sweepType:     up/down/updown/downup   the type of frequency sweep
            shots:         number of waveform cycles to output, set 0 for continuous generation
                           for shots>0, sweeps should be 0
            sweeps:        number of sweeps to output, set 0 to use shots
            ---Trigger options---
            direction:     the direction of the trigger (rising/falling/gate_high/gate_low)
            triggerSource: the source that triggers the signal generator (none/scope_trig/ext_in/soft_trig)
                           if not 'none', either sweep or shots must be nonzero 
            threshold:     external trigger level (in V)
        '''
        #handles default values
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        check_kwargs_scope(**kwargs)
        assert settings['pkToPk'] <= 2.0, 'max pkToPk is 2 Vpp'
        assert settings['offsetVoltage'] <= 2.0, 'max offset is 2 V'
        assert (min(settings['freq'])>=30e-3 and max(settings['freq'])<=20e6), 'freq can range from 30 mHz up to 20 MHz'
        assert settings['shots']*settings['sweeps']==0, 'only sweeps or shots can be nonzero'
        if not settings['triggerSource'] is 'none':
            if settings['direction'] in ['gate_high','gate_low']:
                assert settings['shots']==0 and settings['sweeps']==0, 'when triggerSource is not none, and direction is gate_high or gate_low, shots and sweeps must be zero'
        _offsetVoltage = ctypes.c_int32(int(settings['offsetVoltage']*1e6))
        _pkToPk = ctypes.c_uint32(int(settings['pkToPk']*1e6))        
        _waveType = ctypes.c_int32(wave_index[settings['waveType']])
        _freqMin = ctypes.c_double(settings['freq'][0])
        _freqMax = ctypes.c_double(settings['freq'][-1])
        _increment = ctypes.c_double(settings['increment'])
        _dwellTime = ctypes.c_double(settings['dwellTime'])        
        _sweepType = ctypes.c_int32(sweep_type_index[settings['sweepType']])
        _operation = 0 #(not available on 5000A)
        _shots = ctypes.c_uint32(settings['shots'])
        _sweeps = ctypes.c_uint32(settings['sweeps'])
        _triggerType = ctypes.c_int32(direction_index[settings['direction']])
        _triggerSource = ctypes.c_int32(trigger_source_index[settings['triggerSource']])
        _chRange = ps.PS5000A_RANGE[range_index[5.]]
        _extInThreshold = ctypes.c_int16(int(mV2adc(int(1e3*settings['threshold']),_chRange, self.scope._maxADC)))
        
        self.status["setSigGenBuiltInV2"] = ps.ps5000aSetSigGenBuiltInV2(self.chandle, 
                                                                    _offsetVoltage, 
                                                                    _pkToPk, 
                                                                    _waveType, 
                                                                    _freqMin, _freqMax, 
                                                                    _increment,
                                                                    _dwellTime, 
                                                                    _sweepType, 
                                                                    _operation, 
                                                                    _shots, 
                                                                    _sweeps,
                                                                    _triggerType, 
                                                                    _triggerSource, 
                                                                    _extInThreshold)
        assert_pico_ok(self.status["setSigGenBuiltInV2"])
        self.settings = settings
           
    def softTrig(self,state):
        '''
        activates the AWG with the soft trigger
        only triggerSouce = soft_trig can allow using software trigger
        '''
        assert self.settings['triggerSource']=='soft_trig', 'only triggerSouce = soft_trig can allow using software trigger. See help(set_builtin())'
        if self.settings['direction']=='gate_low':
            state = 1-int(state)
        self.status["softTrig"] = ps.ps5000aSigGenSoftwareControl(self.chandle,state)
        assert_pico_ok(self.status["softTrig"])    

class Pico5000():
    microvolts = 1e6
    def __init__(self,resolution_bits=8):
        # Create chandle and status ready for use
        self.chandle = ctypes.c_int16()
        self.status = {}
        self.channels = {}
        self.settings = {'resolution':'8BIT',
                         'timebase':8,
                         'noSamples':5000,
                         'segmentIndex':0,
                         'startIndex':0,
                         'down_sample_blocksize':0,
                         'reduction_mode':'none',
                         'nSegments':1}
        # Open 5000 series PicoScope
        self.__open__()
        #for some reason the channels are on at startup
        self.add_channel(source='A',enabled=True)
        self.add_channel(source='B',enabled=False)
        self.add_channel(source='C',enabled=False)
        self.add_channel(source='D',enabled=False)
        self.set_timeBase()
        self.trigger = Trigger(self)
        self.awg = Function_generator(self)
        
            
    def close(self):
        # Close unit Disconnect the scope
        # handle = chandle
        self.status["close"]=ps.ps5000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])
        # display status returns
        print('The scope was successfully closed')

    def __enter__(self):
        return self
    
    def __exit__(self,type,value,traceback):
        self.close()

    def __open__(self):
        # set resolution
        res = ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_"+self.settings['resolution']]
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, res)
        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:
            powerStatus = self.status["openunit"]
            if powerStatus == 286:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
            elif powerStatus == 282:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
            else:
                raise
            assert_pico_ok(self.status["changePowerSource"])
        
    
    
    @property
    def info(self):
        '''
        returns a dictionary containing driver_version, usb_version, hardware_version, variant_info, batch_and_serial, cal_date, error_code and kernel_driver_version
        '''
        info_out = {}
        _string = (ctypes.c_char*100)() #info output buffer
        _stringLength = ctypes.c_int16(100) #max info buffer length
        _requiredSize = ctypes.c_int16()
        for key,value in info_index.items():
            status = ps.ps5000aGetUnitInfo(self.chandle,_string,_stringLength,ctypes.byref(_requiredSize),value)
            assert_pico_ok(status)
            info_out[key]=_string.value.decode('utf-8')
        return info_out
    
        
    def add_channel(self,source='A',**kwargs):
        self.channels[source]=Channel(self,source=source,**kwargs)
        
    
    @property
    def _maxADC(self):
        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(maxADC))
        assert_pico_ok(self.status["maximumValue"])
        return maxADC
    
    @property
    def _resolution(self):
        res = ctypes.c_int16()
        status = ps.ps5000aGetDeviceResolution(self.chandle,ctypes.byref(res))
        assert_pico_ok(status)
        return res
    
    @property
    def resolution(self):
        '''
        prompts or set the scope resolution (in bits)
        '''
        res = self._resolution
        for key, rescode in ps.PS5000A_DEVICE_RESOLUTION.items():
            if rescode == res.value:                                      
                s = key.find('DR_')
                return key[s+3:]
    
    @resolution.setter
    def resolution(self,value,at_startup=False):
        value = value.upper()
        possible_values = [str(r)+'BIT' for r in [8,12,14,15,16]]
        assert value in possible_values, 'resolution can be 8,12,14, 15 or 16BIT'
        res = ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_"+value.upper()]
        status = ps.ps5000aSetDeviceResolution(self.chandle,res)
        assert_pico_ok(status)
        self.settings['resolution'] = value
    
    @property
    def _minTimeBase(self):
        #find fastest available timebase
        enabled_channels = len(self.enabledChannels)
        #don't forget to disable the channels to reach max resolution
        if self.resolution=='8BIT':
            return 0 if enabled_channels<=1 else 1
        if self.resolution=='12BIT':
            return 1 if enabled_channels<=1 else 2
        if self.resolution=='14BIT':
            return 3
        if self.resolution=='15BIT':
            return 3 if enabled_channels<=2 else 4
        if self.resolution=='16BIT':
            return 4 if enabled_channels<=1 else 5
    
    def set_timeBase(self,**kwargs):
        '''
        sets the timebase options. Several options are available:
        - directly set the timebase (0 up 2**32-1, machine option)
        - set the sampling rate
        - set the time interval between samples
        arguments: none
        keyword arguments (defaults in self.settings):
            timebase: the timebase to use (not recommended),
            noSamples: the desired number of samples (the actual number of samples may differ),
            segmentIndex: scope memory segment to store the run result,
            ***
            sampleRate: the desired sample rate (in samples/s)  (the actual sample rate may differ),
            --or--
            timeIntervalSeconds: the desired time interval between samples (in s) (the actual time interval rate may differ),
            ***
        after successfully setting the trigger,  self.settings is updated and contains:
            sampleRate: the actual sample rate (in samples/s),
            timeIntervalSeconds: the actual time interval between samples (in s),
        '''
        #handles default values
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        #overwrites the timebase with either timeIntervalNanoseconds or sampleRate
        #if these two parameters are provided, the conflict is raised
        assert not ('sampleRate' in kwargs and 'timeIntervalSeconds' in kwargs)
        if 'sampleRate' in kwargs:
            value = kwargs['sampleRate']
            settings['timebase'] = helper_functions.dichotomic_search(sample_rate[self.resolution],self._minTimeBase,2**32-1,f0=value,tol=1,growing=False)
        if 'timeIntervalSeconds' in kwargs:
            value = kwargs['timeIntervalSeconds']
            settings['timebase'] = helper_functions.dichotomic_search(lambda x: 1./sample_rate[self.resolution](x),self._minTimeBase,2**32-1,f0=value,tol=1,growing=True)

        assert type(settings['timebase']) is int, 'timeBase must be an int, use sampleRate or timeIntervalSeconds for convenient setting'
        assert settings['timebase'] >= self._minTimeBase and settings['timebase']<2**32
        _timebase = settings['timebase']
        _noSamples = int(settings['noSamples'])
        _timeIntervalNanoseconds = ctypes.c_float()
        _maxSamples = ctypes.c_int32()
        _segmentIndex = ctypes.c_uint32(settings['segmentIndex'])
        self.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.chandle, 
                                                        _timebase, _noSamples, 
                                                        ctypes.byref(_timeIntervalNanoseconds), 
                                                        ctypes.byref(_maxSamples), _segmentIndex)
        assert_pico_ok(self.status["getTimebase2"])
        settings['timeIntervalSeconds'] = 1e-9*_timeIntervalNanoseconds.value
        settings['maxSamples'] = _maxSamples.value
        self.settings = settings
    
    def set_trigger(self,**kwargs):
        '''
        set-up the oscilloscope trigger. 
        arguments: none
        keyword arguments (defaults in trigger.settings):
            enabled: True/False
            source: A/B/C/D/Ext
            threshold_mV: trigger threshold in mV
            direction: rising/falling/gate_high/gate_low (only the latter two are available when using source: Ext) 
            delay_s: post-trigger delay before recording (in s)
            auto_trigger_ms: trigger auto re-arming delay after recording (in ms), set to 0 for REPEAT and SINGLE modes
        after successfully setting the trigger,  self.settings is updated
        '''
        self.trigger.set_trigger(**kwargs)
    
    def runBlock(self,**kwargs):
        '''
        arms the trigger, block mode is close to repeat (with re-arm) or single mode (without re-arm)
        rapid block accumulates several events (similar to fast frame modes on other scopes)
        arguments: none
        keyword arguments (defaults in self.trigger.settings):
            preTrigger: fraction of samples before the trigger occurs (0 to 1)
            segmentIndex: scope memory segment to store the run result
            nSegments: number of samples to capture
        after successfully arming the trigger, self.trigger.settings is updated
        after triggering, the channel records the noSamples and then stops (until re-arming) 
        '''
        # defaults
        settings = {}
        for key,current_value in self.trigger.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        if settings['nSegments']==1:
            self.trigger.runBlock(**kwargs)
        else:
            self.trigger.runRapidBlock(**kwargs)
        self.trigger.settings = settings
        
    def streaming(self,**kwargs):
        raise NotImplementedError
     
    @property
    def isBusy(self):
        '''
        returns True if the scope is busy and False otherwise
        '''
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)   
        self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))
        return ready.value==check.value
    
    
    
    def waitUntilReady(self,timeout=1.):
        '''
        waits until the scope is ready
        '''
        start_time = time.time()
        while self.isBusy:
            time.sleep(0.01)
            if time.time()-start_time>timeout: raise TimeoutError('The scope did not respond')
    
    @property
    def enabledChannels(self):
        '''
        returns a list of the enabled channels
        '''
        out = []
        for channel in self.channels.values():
            if channel.settings['enabled']:
                out.append(channel.source)
        return out
    
    def read(self,**kwargs):
        '''
        reads the scope results:
        arguments: none
        keyword arguments (defaults in scope.settings):
            source: the channel(s) to read. If no channels are given, all the channels are read,
            startIndex: the sample to start reading,
            down_sample_blocksize: the number of samples to group for the data reduction (see Channel()._setDataBuffers),
            reduction_mode: the reduction_mode for the data reduction (see Channel()._setDataBuffers),
        the results (in V) are stored in scope.channels['channe_name'].data_max and scope.channels['channe_name'].data_min
        a results structure is returned:
            time:                   the time (in s)
            channel+' (V)':          channel voltage (in V)
        ***in reduction_mode == aggregate, two keys are returned instead:***
            channel+'_{max} (V)':   channel max voltage (in V)
            channel+'_{min} (V)':   channel min voltage (in V)
        channel voltage (including max/min) are returned as noSamples*nSegments arrays 
        '''
        #handles default values
        settings = {}
        for key,current_value in self.settings.items():
            settings[key] = kwargs[key] if key in kwargs else current_value
        if not 'source' in kwargs:
            settings['source'] = self.enabledChannels
        for channel in settings['source']:
            self.channels[channel]._setDataBuffers(reduction_mode = settings['reduction_mode'])
        check_kwargs_scope(**kwargs)  
        # create overflow loaction
        overflow = (ctypes.c_int16 *self.trigger.settings['nSegments'])()
        # create converted type maxSamples
        cmaxSamples = ctypes.c_int32(self.settings['noSamples'])
        _ratio_mode = ratio_mode_index[settings['reduction_mode']]
        _segmentIndex = ctypes.c_uint32(self.settings['segmentIndex'])
        # Retried data from scope to buffers assigned above
        # handle = chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(cmaxSamples)
        # downsample ratio = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))
        if self.trigger.settings['nSegments']==1:
            self.status["getValues"] = ps.ps5000aGetValues(self.chandle, settings['startIndex'], ctypes.byref(cmaxSamples), 
                                                           settings['down_sample_blocksize'], _ratio_mode, _segmentIndex, ctypes.byref(overflow))
            assert_pico_ok(self.status["getValues"])
        else:
            _fromSegmentIndex = self.trigger.settings['segmentIndex']
            _toSegmentIndex = _fromSegmentIndex+self.trigger.settings['nSegments']-1
            self.status["getValuesBulk"] = ps.ps5000aGetValuesBulk(self.chandle, ctypes.byref(cmaxSamples), 
                                                                   _fromSegmentIndex,_toSegmentIndex,
                                                           settings['down_sample_blocksize'], _ratio_mode,
                                                           ctypes.byref(overflow))
            assert_pico_ok(self.status["getValuesBulk"])
        self.settings = settings
        
        # Create time data
        time = np.linspace(0, (cmaxSamples.value) * self.settings['timeIntervalSeconds'], cmaxSamples.value)

        results = {'time (s)':time}
        # convert ADC counts data to mV
        for channel in settings['source']:
            if self.channels[channel].settings['reduction_mode']=='aggregate':
                results[channel+'_{max} (V)']=self.channels[channel].data_max
                results[channel+'_{min} (V)']=self.channels[channel].data_min
            else:
                results[channel+' (V)']=self.channels[channel].data_max
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
        self.trigger.set_trigger(**config['trigger'])
        self.awg.set_builtin(**config['awg'])
        
        
if __name__ =='__main__':
    with Pico5000() as scope:
        print(scope.info)
        scope.set_timeBase(timeIntervalSeconds=1e-6)
        scope.add_channel(source='A',chRange=1.)
        scope.add_channel(source='B',chRange=1.)
        print(scope.enabledChannels)
        scope.awg.set_builtin(triggerSource='soft_trig',
                              direction = 'rising',
                              shots=1)
        scope.set_trigger(source='A',direction = 'gate_high',auto_trigger_ms=0)
        scope.runBlock(nSegments=3)
        for i in range(3):
            print(scope.isBusy)
            time.sleep(0.5)
            print(scope.isBusy)
            scope.awg.softTrig(True)
            time.sleep(0.5)
            print(scope.isBusy)
        results = scope.read()
        plt.figure()
        plt.plot(1e6*results['time (s)'],results['A (V)'])
        #plt.imshow(results['A_{max} (V)'])
        #plt.plot(x='time (s)',y='A_{max} (V)',data=results)
        plt.show()
        scope.runBlock(nSegments=1)
        print(scope.isBusy)
        time.sleep(0.5)
        print(scope.isBusy)
        scope.awg.softTrig(True)
        time.sleep(0.5)
        print(scope.isBusy)
        results = scope.read()
        plt.figure()
        plt.plot(1e6*results['time (s)'],results['A (V)'])
        #plt.imshow(results['A_{max} (V)'])
        #plt.plot(x='time (s)',y='A_{max} (V)',data=results)
        plt.show()
        config = scope.save_config()
        
    time.sleep(3)
    #----simulates another day of hard experiments---    
    with Pico5000() as scope:
        scope.recall_config(config)
        scope.runBlock()
        print(scope.isBusy)
        time.sleep(2)
        print(scope.isBusy)
        scope.awg.softTrig(True)
        time.sleep(1)
        print(scope.isBusy)
        results = scope.read()
        plt.figure()
        plt.plot(1e6*results['time (s)'],results['A (V)'])
        #plt.imshow(results['A_{max} (V)'])
        #plt.plot(x='time (s)',y='A_{max} (V)',data=results)
        plt.show()