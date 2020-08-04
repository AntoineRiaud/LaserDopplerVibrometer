import pico2000
import numpy as np
import time
import matplotlib.pyplot as plt
from Galvomirrors_config import*


class MotorError(Exception):
    pass

class Motor():
    '''
    motor object, controlled by the picoscope2000 (scope) with (possibly) an amplifier
    channel A: position
    channel B: error*5
    channel AWG: command
    '''
    def __init__(self,scope):
        '''
        initializes the motor.
        arguments:
            scope (a Scope instance)
        returns:
            motor
        '''
        self.scope = scope
        self.scope.recall_config(pico2000_config)
        if self.scope.info['batch_and_serial'] == motors_config['X']['SN']:
            self.dir = 'X'
            self.config = motors_config['X']
        elif self.scope.info['batch_and_serial'] == motors_config['Y']['SN']:
            self.dir = 'Y'
            self.config = motors_config['Y']
        else:
            raise KeyError('This scope should not be connected to a motor')
        self.gain = self.config['volts_per_deg']/self.config['gain']
        self.max_range = 2./self.gain
        
    def _move(self,angle):
        '''
        starts moving the motor
        arguments:
            angle (in degrees)
        returns:
            None
        '''
        v = self.gain*angle + self.config['offset']
        assert(np.abs(v)<=2.),'motor range exceeded'
        self.scope.awg.set_builtin(offsetVoltage= v)
        
    def move_simple(self,angle):
        '''
        moves the motor to angle and waits until the motor is stable, checks position and stability
        arguments:
            angle (in degrees)
        returns:
            None
        '''
        self._move(angle)
        start_time = time.time()
        timeout = 2*self.config['fullscale_response(ms)']/1000
        while self.isMoving:
            time.sleep(self.config['step_response(ms)']/1000.)
            if time.time() - start_time > timeout: raise TimeoutError('for some reason the motors took too long to respond')
        assert(np.abs(angle - self.position) < 10*self.config['moving_tol(deg)'])
        
    @property
    def position(self):
        '''
        returns the motor angle in degrees
        arguments: 
            None
        returns:
            motor angle in degrees
        '''
        self.scope.runBlock()
        self.scope.waitUntilReady()
        results = self.scope.read()
        return np.mean(results['A (V)'])/self.config['output_deg_per_volts']-self.config['offset']/self.gain
    
    @property
    def error(self):
        '''
        returns the motor angle error in degrees
        arguments: 
            None
        returns:
            motor angle error in degrees
        '''
        self.scope.runBlock()
        self.scope.waitUntilReady()
        results = self.scope.read()
        return np.mean(results['B (V)'])*self.config['output_error_deg_per_volts']
    
    @property
    def isMoving(self):
        '''
        based on the positioning error, indicates whether the motor has completed its motion.
        arguments: 
            None
        returns:
            boolean (True if the error is below motor.config['moving_tol(deg)'] )
        '''
        self.scope.runBlock()
        self.scope.waitUntilReady()
        results = self.scope.read()
        return np.max(np.abs(results['B (V)']))*self.config['output_error_deg_per_volts']>self.config['moving_tol(deg)']  
    
    @property
    def diagnose(self):
        '''
        runs a diagnostic on the motor status, may require moving the mirrors
        input:
            None
        output:
            None
        raises MotorError when the diagnostic is bad
        '''
        print('checking motor '+self.dir)
        angle = 5.
        bigsleep = 10*self.config['fullscale_response(ms)']/1000
        time.sleep(bigsleep)
        if self.isMoving:
            raise MotorError('the position is not stable, check for external forces such as vibrations')
        try:
            self.move_simple(angle)
        except TimeoutError:
            raise MotorError('the motor is probably stalled')
        except AssertionError:
            raise MotorError('the motor error voltage is 0, but the position is wrong, check the motor connections.')
        try:
            self.move_simple(-angle)
        except TimeoutError:
            raise MotorError('the motor is probably stalled')
        except AssertionError:
            raise MotorError('the motor error voltage is 0, but the position is wrong, check the motor connections.')
        
        
class Galvosystem():
    '''
    combines the two motors and the optics to handle the positioning of the laser beam on the sample
    '''
    def __init__(self,scopes,lens_name='4x'):
        '''
        initializes the galvosystem
        arguments:
            scopes: a list of Scopes instances, each connected to a motor. 
                    The validity of the scopes is checked based on the Serial Number of the scopes. Update if replacement is needed.
            lens_name: the lens used to image the sample (usually microscope objective 4x
        returns:
            galvosystem instance
        '''
        self.set_lens(lens_name=lens_name)
        self.motor = {}
        for scope in scopes:
            if scope.info['batch_and_serial'] == motors_config['X']['SN']:
                self.motor['X'] = Motor(scope)
            elif scope.info['batch_and_serial'] == motors_config['Y']['SN']:
                self.motor['Y'] = Motor(scope)
        assert('X' in self.motor.keys()), 'motor X not found, check that the scope {0} is connected'.format(motors_config['X']['SN'])
        assert('Y' in self.motor.keys()), 'motor Y not found, check that the scope {0} is connected'.format(motors_config['Y']['SN'])
        self.max_range = min([self.optics_range,
                              self.angle2pos(np.deg2rad(self.motor['X'].max_range)),
                              self.angle2pos(np.deg2rad(self.motor['Y'].max_range))])
        print('scanner magnification: {0},\n max range (mm): +/- {1}'.format(self.magn,1e3*self.max_range))
           
        
    def set_lens(self,lens_name='4x'):
        '''
        sets the system lens
        arguments:
            lens_name: the lens used to image the sample (usually microscope objective 4x
        returns
            None
        '''
        self.lens = lens_specs[lens_name]
        self.magn = lens_specs['100mm']['effectiveFocalLength(mm)']/self.lens['effectiveFocalLength(mm)']
        self.magn_cam = lens_specs['camLens']['effectiveFocalLength(mm)']/self.lens['effectiveFocalLength(mm)']
        self.optics_range = self.angle2pos(np.deg2rad(10.6))
        
    def angle2pos(self,angle):
        '''
        converts angle (rad) to position (m) depending on the system optics
        arguments:
            angle (rad)
        returns:
            position (m)
        '''
        pos1 = lens_specs['scan']['effectiveFocalLength(mm)']*np.tan(angle)
        pos2 = 2.*pos1/self.magn #the mirror is at 45 degrees so the deflection is doubled
        return pos2*1e-3
    
    def pos2angle(self,pos):
        '''
        converts position (m) to angle (rad) depending on the system optics
        arguments:
            position (m)
        returns:
            angle (rad)
        '''
        angle = np.arctan(0.5*self.magn*pos*1e3/(lens_specs['scan']['effectiveFocalLength(mm)'])) #the mirror is at 45 degrees so the deflection is doubled
        return angle
    
    def move(self,posx,posy, n_attempts = 3):
        '''
        moves the laser beam, waits until motion is complete
        arguments:
            posx: position along x-axis (m), as defined by the motor X
            posy: position along y-axis (m), as defined by the motor Y
        returns:
            None
        '''
        anglex = self.pos2angle(posx)
        assert(np.rad2deg(np.abs(anglex))<=10.6), 'the required position is outside the optics range'
        angley = self.pos2angle(posy)
        assert(np.rad2deg(np.abs(angley))<=10.6), 'the required position is outside the optics range'
        fail = True
        while fail and n_attempts>0:
            try:
                self.motor['X']._move(np.rad2deg(anglex))
                self.motor['Y']._move(np.rad2deg(angley))
                timeout = 10*all_motors_config['fullscale_response(ms)']/1000
                start_time = time.time()
                while self.motor['X'].isMoving or self.motor['Y'].isMoving:
                    time.sleep(all_motors_config['step_response(ms)']/1000.)
                    if time.time()-start_time>timeout:  raise TimeoutError('for some reason the motors took too long to respond')
                if np.abs(np.rad2deg(anglex) - self.motor['X'].position) > 10*all_motors_config['moving_tol(deg)']:
                    raise ValueError
                if np.abs(np.rad2deg(angley) - self.motor['Y'].position) > 10*all_motors_config['moving_tol(deg)']:
                    raise ValueError
                fail = False
            except TimeoutError:
                n_attempts-=1
            except ValueError:
                n_attempts-=1
        if np.abs(np.rad2deg(anglex) - self.motor['X'].position) > 10*all_motors_config['moving_tol(deg)']:
            self.motor['X']. diagnose 
            self.motor['X'].move_simple(np.rad2deg(anglex))  
        if np.abs(np.rad2deg(angley) - self.motor['Y'].position) > 10*all_motors_config['moving_tol(deg)']:
            self.motor['Y']. diagnose
            self.motor['X'].move_simple(np.rad2deg(anglex))   
            
if __name__ == '__main__':
    with pico2000.Pico2000() as scope1, pico2000.Pico2000() as scope2:
        #motor = Motor(scope1)
        #motor.move_simple(1.0) 
        galvo = Galvosystem([scope1,scope2],lens_name='4x') 
        r = 0.5e-3
        theta = np.linspace(0,10*np.pi,200)
        x = r*np.cos(theta)
        y = r*np.sin(theta)
        for i in range(len(x)):
            try:
                galvo.move(x[i],y[i])
                time.sleep(0.1)#(3./len(x))
            except TimeoutError:
                print(galvo.motor['X'].error)
                print(galvo.motor['Y'].error)
        galvo.move(0,0)
        print('finished')