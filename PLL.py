import pyvisa as visa

class PLL_Error(Exception):
    pass

class PLL():

    def __init__(self):
        self.inst = self.__find_pll__()
        if self.inst is None:
            raise PLL_Error('PLL was not found')
    
    
    def __find_pll__(self):
        rm = visa.ResourceManager()
        for instname in rm.list_resources():
            try:
                inst = rm.open_resource(instname)
                inst.write('*CLS')
                name = inst.query("*IDN?")
                if 'Pasternack' in name:
                    print('found PLL at ' + instname)
                    print(name)
                    return inst
            except:
                print('instrument '+instname+' did not respond to IDN query')
    
#request and set state (setting with gui and recalling here)    
    @property
    def state(self):
        return self.inst.query('syst:readstate?')
    @state.setter
    def state(self,state_num):
        self.inst.write('syst:loadstate '+str(state_num)+'\n')

#checks lock status        
    @property
    def lock(self):
        return self.inst.query('freq:lock?')=='1\n'

#set frequency    
    @property 
    def freq(self):
        return self.inst.query('freq:set?')
    @freq.setter
    def freq(self,value):
        self.inst.write('freq:set '+str(value)+'\n')

#check power on/off        
    @property
    def turn_on(self):
        return int(self.inst.query('powe:rf?'))==1.
    @turn_on.setter
    def turn_on(self,value):
        self.inst.write('powe:rf '+str(int(value))+'\n')

#set power level
    @property
    def power(self):
        return float(self.inst.query('powe:set?'))
    @power.setter
    def power(self,value):
        self.inst.write('powe:set '+str(value)+'\n')

#set reference frequency source to external (True) or internal (False)
    @property
    def ext_source(self):
        return int(self.inst.query('freq:ref:ext?'))==1.
    @ext_source.setter
    def ext_source(self,value):
        self.inst.write('freq:ref:ext '+str(int(value))+'\n')
        
if __name__ == '__main__':
    #init
    pll = PLL()
    #recalls state 1
    pll.state = 1
    #sets the pll frequency to 80 MHz:
    pll.freq = 80.
    #sets the output power to 10 dBm
    pll.power = 10.
    #turn on the power
    pll.turn_on = True