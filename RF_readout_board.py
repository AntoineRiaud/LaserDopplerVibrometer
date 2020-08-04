import pico5000
import PLL
from RF_board_config import*
import numpy as np
import time
import matplotlib.pyplot as plt
import scipy.signal as signal


class ReadoutBoard():
    '''
    channel A: Photodiode readout = pll input
    channel B: circuit output (after mixing and filtering)
    channel C: pll output (shift 235 degrees to A optimally)
    channel D: NC
    '''
    def __init__(self,scope,skip_calibration=False):
        self.scope = scope #pico5000.Pico5000()
        self.scope.recall_config(pico5000_configPLL)
        print(self.scope.enabledChannels)
        self.pll = PLL.PLL()
        if not skip_calibration:
            self._synchronize_PLL()
    
    def _find_noise_distrib(self,n_estimates = 10,threshold=0.):
        '''
        randomly attempts to reduce the system noise by turning on and off the pll
        arguments: none
        keyword arguments: 
            n_estimates: maximum attempts
            threshold: minimum noise to reach to stop the iteration
        returns: _max: the sorted max values
                 found: whether the search stopped because a point was successfully found
        '''
        
        _max = []
         #recalls pll state 1
        self.pll.state = 1
        i = 0
        found = False
        while i < n_estimates and not found:
            self.pll.turn_on = False
            time.sleep(0.05)
            self.pll.turn_on = True
            while not self.pll.lock:
                time.sleep(0.05)
            self.scope.runBlock()
            self.scope.waitUntilReady()
            results = self.scope.read()
            boardOut = results['B (V)']
            F = np.abs(np.fft.fft(boardOut,axis=0))
            _max.append(np.max(F))
            found = _max[-1]<=threshold  
            i+=1   
            print(i)
        return np.sort(_max),found
            
    def _synchronize_PLL(self):
        #angle 235 degrees, between channel A (PLL input)
        #1st step, estimate the possible outcomes over 50 random attempts
        #then attempts to rank in the top 5% (among the 3 best outcomes)
        input('Calibrating system board, make sure the transducer is disconnected. Press any key to continue.')
        _max,found = self._find_noise_distrib()
        threshold = _max[1]
        _max,found = self._find_noise_distrib(n_estimates = 50, threshold=threshold)  
        self._max_noise = _max[0]
        if found:
            print('calibration successful, max noise {0} mV'.format(1e3*_max[-1]))
            
            
    def read(self,n_attempts=3,timeBetweenSegments=1e-3):
        '''
        reads the board readout
        arguments:
            None
        keyword arguments: 
            n_attempts: maximum attempts to collect the output
        returns:
            results: raw oscilloscope readout (in V). See RF_readout_board to config trigger, frames and so on.
        '''
        n_attempts0=n_attempts
        fail = True
        while fail and n_attempts>0:
            try:
                self.scope.runBlock()
                for i in range(self.scope.trigger.settings['nSegments']):
                    self.scope.awg.softTrig(True)
                    time.sleep(timeBetweenSegments)
                self.scope.waitUntilReady(timeout=0.1)
                results = self.scope.read()
                fail=False
            except TimeoutError:
                n_attempts-=1
                print('no scope response: remaining attempts: {0}'.format(n_attempts))
                results=None
        if results==None:
            raise TimeoutError('no successful measurements despite {0} attempts'.format(n_attempts0))
        return results 
    

class VirtualPLL():
    '''
    Emulates a PLL (finds the signal strongest frequency and synthesizes
    a monochromatic signal with this frequency.
    The pll can be called as a function:
    output = pll(input,t)
    y should be ns*nc with ns the number of samples (over time) and nc the number of channels
    t should be ns*1
    '''
    def __call__(self,y,t):
        '''
        isolates the strongest frequency in y(t)
        arguments:
            y: time-dependent signal
            t: time
        returns:
            zR: isolated frequency (in phase with y)
            zI: isolated frequency (in quadrature with y)
        '''
        t=t.reshape(-1,1)
        #find the main frequency component
        y = y - np.mean(y)
        freqs = np.fft.fftfreq(len(t), np.mean(np.diff(t,axis=0)))
        F = np.fft.fft(y,axis=0)
        q0 = np.argmax(np.abs(F),axis=0)
        f0 = np.abs(freqs[q0])
        #synthesizes a monochromatic signal with only this component
        synthesized = []
        for i,qi in enumerate(q0):
            fi = F[qi,i]/np.abs(F[qi,i])
            synthesized.append(fi*np.exp(1j*2*np.pi*f0[i] *t))
        synthesized = np.hstack(synthesized)
        zR = np.real(synthesized)
        zI = np.imag(synthesized)
        return zR,zI

class VirtualFilter():
    '''
    Numerical Butterworth filter
    The filter can be called as a function:
    output = filter(input,t)
    y should be ns*nc with ns the number of samples (over time) and nc the number of channels
    t should be ns*1
    '''
    def __init__(self,Fcut,fs,order=8):
        Fcut = Fcut/1e9 #internally in GHz
        fs = fs/1e9 #internally in GHz
        Wn = 2*np.pi*Fcut
        self.b,self.a = signal.butter(order, Wn=0.5*Fcut/fs, btype='low', fs=fs, output='ba')

    def _apodize(self,t):
        W = signal.windows.tukey(len(t), alpha=0.2, sym=True).reshape(-1,1)
        return W

    def __call__(self,y,t):
        W = self._apodize(t)
        out = signal.filtfilt(self.b,self.a, W*y, axis=0,method='gust')
        return out

class VirtualBoard():
    def __init__(self,Fcut,fs,order=8):
        self.pll = VirtualPLL()
        self.filter = VirtualFilter(Fcut,fs,order=order)

    def __call__(self,y,t):
        _,synthesized = self.pll(y,t)
        mixed = y*synthesized
        out = self.filter(mixed,t)
        return out
    
class HilbertBoard():
    def __init__(self,Fcut,fs,order=8):
        self.filter = VirtualFilter(Fcut,fs,order=order)
    
    def __call__(self,y,t):
        analytical = signal.hilbert(y,axis=0)
        #amplitude = np.abs(analytical)
        fs = 1./np.mean(np.diff(t,axis=0))
        phase = np.unwrap(np.angle(analytical),axis=0)
        instant_freq = (np.diff(phase,axis=0)/(2.0*np.pi) * fs) #instantaneous frequency
        instant_freq = np.vstack([instant_freq[0,:],instant_freq])
        return self.filter(instant_freq-np.mean(instant_freq,axis=0),t)
    
    
class ReadoutDigital():
    '''
    channel A: Photodiode readout = pll input
    channel B: digital output (after mixing and filtering)
    channel C: pll output (shift 235 degrees to A optimally)
    channel D: NC
    -----------------------
    When using this digital readout, the signal to noise ratio will be lower than the analog readout
    The scope resolution should be set to 12 bits
    Also, the sampling rate should be higher than 250 MS/s
    '''
    def __init__(self,scope):
        self.scope = scope #pico5000.Pico5000()
        self.scope.recall_config(pico5000_configPLL)
        print(self.scope.enabledChannels) 
        self.board = HilbertBoard(50e6,500e6,order=8)#VirtualBoard(50e6,500e6,order=8) 

    def _process(self,results):
        return self.board(results['A (V)'],results['time (s)'])
            
    def read(self,n_attempts=3,timeBetweenSegments=1e-3):
        '''
        returns the digital readout
        arguments:
            None
        keyword arguments: 
            n_attempts: maximum attempts to collect the output
        returns:
            results: processed oscilloscope readout (in V). See RF_readout_board to config trigger, frames and so on.
        '''
        n_attempts0=n_attempts
        fail = True
        while fail and n_attempts>0:
            try:
                self.scope.runBlock()
                for i in range(self.scope.trigger.settings['nSegments']):
                    self.scope.awg.softTrig(True)
                    time.sleep(timeBetweenSegments)
                self.scope.waitUntilReady(timeout=0.1)
                results = self.scope.read()
                fail=False
            except TimeoutError:
                n_attempts-=1
                print('no scope response: remaining attempts: {0}'.format(n_attempts))
                results=None
        if results==None:
            raise TimeoutError('no successful measurements despite {0} attempts'.format(n_attempts0))
        results['B (V)'] = self._process(results)
        return results   
        
if __name__=='__main__':
    with pico5000.Pico5000() as scope:
        board = ReadoutBoard(scope)
        board.scope.awg.set_builtin(pkToPk  = 0.1)
        board.scope.runBlock()
        board.scope.waitUntilReady()
        results = board.scope.read()
        boardOut = results['B (V)']
        t = results['time (s)']
        #boardOut = np.sin(20e6*time)
        F = np.abs(np.fft.fft(boardOut,axis=0))
        d = t[1]-t[0]
        fftfreq = np.fft.fftfreq(len(F), d)
        plt.figure()
        plt.plot(1e6*t,boardOut)
        plt.xlabel('time (us)')
        plt.show()
        plt.figure()
        plt.plot(1e-6*fftfreq,20*np.log10(F))
        plt.xlabel('freq (MHz)')
        plt.show()
        board.scope.recall_config(pico5000_configLDV)
        results = board.read()
        plt.figure() ; plt.plot(1e6*results['time (s)'],results['A (V)']) ;plt.show()
    
