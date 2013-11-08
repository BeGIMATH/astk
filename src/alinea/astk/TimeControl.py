"""
Provides utilities for scheduling models in simulation
"""

class TimeControlSet:

    def __init__(self, **kwd):
        """  Create a TimeControlSet , that is a simple class container for named object"""
        self.__dict__.update(kwd)

    def check(self,attname,defaultvalue):
        """ Check if an attribute exists. If not create it with default value """
        if not hasattr(self,attname):
            setattr(self,attname,defaultvalue)


def simple_delay_timing(delay = 1, steps =1):
    return (TimeControlSet(dt=delay) if not i % delay  else TimeControlSet(dt=0) for i in range(steps))
            
            
class TimeControl:

    def __init__(self, delay=None, steps=None, model=None, weather=None, start_date=None):
        """ create a generator-like timecontrol object """
        self.delay = delay
        self.steps = steps
        self.model = model
        self.weather = weather
        self.start_date = start_date

        try:
            self._timing = model.timing(delay=delay, steps=steps, weather=weather, start_date=start_date)
        except:
            if model is not None:
                print('Warning : not able to call model.timing correctly !!!')
            try:
                self._timing =  simple_delay_timing(delay=delay, steps=steps)# a generator of timecontrolset objects to be used during a simulation
            except:
                self._timing = simple_delay_timing()

    def __iter__(self):
        return TimeControl(delay=self.delay, steps=self.steps, model=self.model, weather=self.weather, start_date=self.start_date) 

    def next(self):
        return self._timing.next()
                  
            
class TimeControler:

    def __init__(self, **kwd):
        """ create a controler for parallel run of time controls
            Allows to emulate 'discrete event'-like evaluation of timecontrol objects in a script
        """
        self._timedict = dict(kwd)
        self.numiter = 0
        
    def __iter__(self):
        self._timedict = dict((k,iter(v)) for k,v in self._timedict.iteritems())
        self.numiter = 0
        return self
    
    def next(self):
        d = dict((k,v.next()) for k,v in self._timedict.iteritems())
        if len(d) == 0:
            raise StopIteration
        self.numiter += 1
        return d
        

# new approach


class TimingElement:

    def __init__(self, data):
        self.data = data
        
    def __nonzero__(self):
        if self.data is not False:
            return True
        else:
            return False
    
    
def delay_to_timing(delays, datas = None):
    if datas is not None:
        timing = [[dat if i == 0 else False for i in range(int(d))] for d,dat in zip(delays,datas)]
    else :
        timing = [[True if i == 0 else False for i in range(int(d))] for d in delays]
    return reduce(lambda x,y: x + y, timing)



class Timing:

    def __init__(self, delays, datas = None):
        self.delays = delays
        self.datas = datas
        self._timing = iter(map(TimingElement,delay_to_timing(delays, datas)))
        
    def __iter__(self):
        return Timing(self.delays, self.datas)
        
    def next(self):
        return self._timing.next()

    
  
def time_split(time_sequence, weather_data = None, delay = 1):
    """ split weather[time_sequence] into a list of tuple (delay, data), one tuple being a period of delay hours long
    
    :Parameters:
    ----------
    - `time_sequence` (panda dateTime index)
        A sequence of TimeStamps indicating the dates of interest in weather_data
    - `weather_data` (panda dataframe indexed by date)
        weather database (should contain rain column) 
    - `delay` (int)
        The duration of each period
    :Returns:
    ---------
    - a list of tuples [(delays), (datas)]
    """
    
    time = [(t - time_sequence[0]).total_seconds() / 3600 for t in time_sequence]
    filter = [t % delay == 0 for t in time]
    starts = time_sequence[filter]
    ends = starts[1:].tolist() + [time_sequence[-1] + 1]
    if weather_data is not None:
        events = [((end - start).total_seconds() / 3600, weather_data.truncate(before = start, after = end).ix[:-1,]) for start,end in zip(starts,ends)]
    else:
        events = [((end - start).total_seconds() / 3600, None) for start,end in zip(starts,ends)]
    delays, data = zip(*events)
    return delays, data
    
def rain_filter(time_sequence, weather_data):
    """ filter every date in the time sequence that is not a start of a rain event or a start of a dry event according to rain data found in weather
    :Parameters:
    ----------
    - `time_sequence` (panda dateTime index)
        A sequence of TimeStamps indicating the dates of interest in weather_data
    - `weather_data` (panda dataframe indexed by date)
        weather database (should contain rain column) 
    :Returns:
    ---------
    - 'time_sequence' (panda dateTime index)
        TimeStamps of date indicating a start of a rain or dry events
    """
    rain = weather_data.rain[time_sequence]
    rain[rain > 0] = 1
    filter = [True] +(rain[1:] != rain[:-1]).tolist()
    return time_sequence[filter]
    
def rain_split(time_sequence, weather_data):
    """ split weather[time_sequence] into a list of tuple (delay, data), one tuple being a period of contiguous rain or contiguous no rain
    
    :Parameters:
    ----------
    - `time_sequence` (panda dateTime index)
        A sequence of TimeStamps indicating the dates of interest in weather_data
    - `weather_data` (panda dataframe indexed by date)
        weather database (should contain rain column) 
    :Returns:
    ---------
   - a list of tuples [(delays), (datas)]
    """
    starts = rain_filter(time_sequence, weather_data).tolist()
    ends = starts[1:] + [time_sequence[-1] + 1]
    events = [((end - start).total_seconds() / 3600, weather_data.truncate(before = start, after = end).ix[:-1,]) for start,end in zip(starts,ends)]
    delays, data = zip(*events)
    return delays, data


#from datetime import datetime, timedelta
#import pytz
##import numpy as np

# class TimeSequence(object):
    # """ Create / manipulate 'actual time' sequences for simulations 
    # """
    # def __init__(self, start_date ='2000-10-01 01:00:00', time_step = 1, steps = 24):
        # """ Create a datetime sequence from start_date to start_date + steps days, every time step hours
        # datetime object are created as UTC
        # """
        # start = pytz.utc.localize(datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S"))
        # self.steps = steps
        # self.time_steps = [time_step for i in range(steps)]
        # self.time = [start + i * timedelta(hours=time_step) for i in range(steps)]
           
    # def as_localtime(self, local_tz  = pytz.timezone('Europe/Paris'), format = "%Y-%m-%d %H:%M:%S"):
        # return [utc_dt.astimezone(local_tz) for utc_dt in self.time]
        
    # def formated(self, time = None, format = "%Y-%m-%d %H:%M:%S"):
        # if time is None:
            # return [t.strftime(format) for t in self.time]
        # else:
            # return [t.strftime(format) for t in time]