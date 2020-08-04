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

for_test= False #for code development only





class LDV_scanner():
    
    def __init__(self,scopes2000,scope5000,scan_path={'type':'circle','radius (mm)':0.5,'resolution (um)':100},
                 lens_name='4x',centering_test=True,readout='analog',results_folder = './'):
        timeStr = time.asctime( time.localtime(time.time()) ).replace(':','-')
        self.results_folder = os.path.join(results_folder,timeStr)
        os.mkdir(self.results_folder)
        self.galvo = Galvosystem(scopes2000,lens_name=lens_name)
        self.scan_path = self._design_path(scan_path)
        self.wind = pg.GraphicsWindow()
        self.scan_ax = self.wind.addPlot(title='scanning head position')
        self.scan_ax.setLabel('left', "y", units='mm')
        self.scan_ax.setLabel('bottom', "x", units='mm')
        self.wind.nextRow()
        self.scope_ax = self.wind.addPlot(title = 'scope signal - channel B (V)')
        self.scope_ax.setLabel('left', "B", units='V')
        self.scope_ax.setLabel('bottom', "t", units='us')
        self.path_preview(centering_test=centering_test)
        self.scope5000 = scope5000
        self.scopes2000 = scopes2000
        if readout=='analog':
            self.board = ReadoutBoard(scope5000,skip_calibration = for_test)
        else:
            self.board = ReadoutDigital(scope5000)
        self.board.scope.recall_config(pico5000_configLDV)
        self.current_fileID = 0
        self.lens_name = lens_name
        self.results = [{}]
        self.saveConfig()
    
    def __enter__(self):
        return self
    
    def __exit__(self,type,value,traceback):
        self.saveData()
        self.saveConfig()
        
    def _move(self,point,n_attempts=3):
        fail = True
        while fail and n_attempts>0:
            try:
                self.galvo.move(point[0],point[1])
                fail = False
            except MotorError:
                n_attempts-=1
        #plt.sca(self.scan_ax)
        time.sleep(0.1)
        self.scan_ax.plot([1e3*point[0]],[1e3*point[1]],symbol='o',
                               pen=None,symbolBrush=(2,2))
        QApplication.processEvents()
    
    def scan(self,n_attempts=3,autosave_every=100,timeBetweenSegments=1e-3):
        for i,p in enumerate(self.scan_path):
            self._move(p,n_attempts=n_attempts)
            readout = self.board.read(n_attempts=n_attempts,timeBetweenSegments=timeBetweenSegments)
            readout.update({'x':p[0],'y':p[1]})
            self.results.append(readout)
            if i>0 and np.mod(i,autosave_every)==0:
                self.saveData()
            try:
                self.scope_ax.removeItem(self.previous_scope_ax)
            except AttributeError:
                pass #this is the first iteration of the loop
            finally:
                self.previous_scope_ax = self.scope_ax.plot(1e6*readout['time (s)'],np.mean(readout['B (V)'],axis=1))
            QApplication.processEvents()
        self.saveData()
        print('scan completed successfully')
        
    def set_scan_path(self,scan_path={'type':'circle','radius (mm)':0.5,'resolution (um)':100}):
        if type(scan_path) is np.ndarray:
                assert path.shape[1]==2, 'custom scan_path must be an m*2 numpy array'
                self.scan_path = scan_path
        else:
            assert scan_path['type'] in ['circle','rectangle'], 'scan_path types can only be circles and rectangles'
            self.scan_path = self._design_path(scan_path)
            
  
    def _design_path(self,scan_path):
        if scan_path['type']=='circle':
            theta = np.linspace(0, 2*np.pi, 1000) #the number of points will be changed later
            x = 1e-3*scan_path['radius (mm)']*np.cos(theta)
            y = 1e-3*scan_path['radius (mm)']*np.sin(theta)
            if 'xoffset' in scan_path.keys():
                x = x+scan_path['xoffset']*1e-3
            if 'yoffset' in scan_path.keys():
                y = y+scan_path['yoffset']*1e-3
                
        elif scan_path['type']=='rectangle':
            xl = scan_path['xlength (mm)']
            yl = scan_path['ylength (mm)']
            x = [-xl,xl,xl,-xl,-xl]
            y = [-yl,-yl,yl,yl,-yl]
        #discretization
        h = scan_path['resolution (um)']*1e-6*np.sqrt(3.)/2.
        xi1 = np.arange(np.min(x),np.max(x),h)
        yi1 = np.arange(np.min(y),np.max(y),2*h)
        xi2 = 0.5*h+np.arange(np.min(x),np.max(x),h)
        yi2 = h+np.arange(np.min(y),np.max(y),2*h)
        xi1,yi1 = np.meshgrid(xi1,yi1)
        xi2,yi2 = np.meshgrid(xi2,yi2)
        xi = np.hstack([xi1.ravel(),xi2.ravel()])
        yi = np.hstack([yi1.ravel(),yi2.ravel()])
        border = Path([(xp,yp) for xp,yp in zip(x,y)])
        points = [(xp,yp) for xp,yp in zip(xi,yi)]
        inside = border.contains_points(points)
        scan_path = np.array([xi[inside],yi[inside]]).T
        return scan_path
    
    def path_preview(self,centering_test=True):
        ch = ConvexHull(self.scan_path)
        border = self.scan_path[ch.vertices,:]
        #plt.figure()
        self.scan_ax.plot(1e3*self.scan_path[:,0],1e3*self.scan_path[:,1], pen=None, symbol='o',symbolBrush=(1,2))
        #plt.plot(self.scan_path[:,0],self.scan_path[:,1],'.k')
        #plt.plot(border[:,0],border[:,1],'k')
        self.scan_ax.plot(1e3*border[:,0],1e3*border[:,1], pen=(1,2), symbol=None)
        #plt.axis('equal')
        #plt.show()
        if centering_test:
            user_input = 'n'
            while user_input=='n':
                for i in range(5):
                    for p in border:
                        self._move(p)
                user_input = input('is the scanner well-centered? [y/n]')
        
    
    def saveData(self,fname = 'data'):
        '''
        saves the current scan data
        arguments:
            None
        output:
            None
        '''
        fname = os.path.join(self.results_folder,fname+'_'+str(self.current_fileID))
        with h5py.File(fname, "w") as f:
            for i,data in enumerate(self.results):
                for k,v in data.items():
                    dset = f.create_dataset(k+'_'+str(i), data=v)
        self.current_fileID+=1
        self.results = [{}]
    
    def saveConfig(self,fname='config'):
        '''
        saves the current scan config
        arguments:
            None
        output:
            None
        '''
        fname = os.path.join(self.results_folder,fname)
        with h5py.File(fname, "w") as f:
            dset = f.create_dataset('lens_name', data=self.lens_name)
            dset = f.create_dataset('scan_path', data=self.scan_path)
            #dset = f.create_dataset('pico5000config', data=self.scope5000.save_config())
            #dset = f.create_dataset('pico2000_0_config', data=self.scopes2000[0].save_config())
            #dset = f.create_dataset('pico2000_1_config', data=self.scopes2000[1].save_config())
        save_dict_to_hdf5(self.scope5000.save_config(), fname+'_pico5000')
        save_dict_to_hdf5(self.scopes2000[0].save_config(), fname+'_pico2000_0')
        save_dict_to_hdf5(self.scopes2000[1].save_config(), fname+'_pico2000_1')
        
    
if __name__ == '__main__':
    #ldv = LDV_scanner([0,0],0) #for test only
    with pico2000.Pico2000() as scope1, pico2000.Pico2000() as scope2, pico5000.Pico5000() as scope:
        ldv = LDV_scanner([scope1,scope2],scope)
        if for_test: scope.set_trigger(threshold=0.4) #using the AOM driver as a proxy for the acoustic signal
        scope.add_channel(source='D',chRange=1.)
        scope.set_trigger(threshold_mV=1000,source='D')
        scope.set_timeBase(sampleRate=10e6)
        scope.awg.set_builtin(freq=[7e6, 7e6],pkToPk=1.)
        ldv.scan()