""" A collection of equation for modelling sun position, sun irradiance and sky irradiance

C. Fournier, 2015
"""

import numpy

# Sun models and equations

def ecliptic_longitude(dayofyear):
    """ Ecliptic longitude (radians)
      Approximation formula by Grebet (1993), in Crop structure and light microclimate
    """
    omega = 0.017202 * (dayofyear - 3.244)
    return omega + 0.03344 * numpy.sin(omega) * (1 + 0.021 * numpy.cos(omega)) - 1.3526
        
def declination(dayofyear, method = "default"):
    """ Sun declination angle(rad) as a function of day of year
    
    Parameters:
        - method: a string indicating the method for computing (either 'Spencer' or 'default')
    """  
    if method == "Spencer": # usefull for checking time equation
        # Approx Spencer 1971
        # J. W. Spencer, Fourier series representation of the sun, Search, vol. 2, p. 172, 1971
        x = 2 * numpy.pi * (dayofyear - 1) / 365.
        dec = 0.006918\
                - 0.399912 * numpy.cos(x) + 0.070257 * numpy.sin(x)\
                - 0.006758 * numpy.cos(2 * x) + 0.000907 * numpy.sin(2 * x)\
                - 0.002697 * numpy.cos(3 * x) + 0.001480 * numpy.sin(3 * x)
    else:
        #  'true' declination (provided that the obliquity of the ecliptic and the ecliptic longitude are exact)
        # Michalsky, J. J. "The Astronomical Almanac's Algorithm for Approximate Solar Position (1950-2050)". Solar Energy. Vol. 40, No. 3, 1988; pp. 227-235, USA
        obliquity = 23.44 # constant approximation
        sidec = numpy.sin(numpy.radians(obliquity)) * numpy.sin(ecliptic_longitude(dayofyear))
        dec = numpy.arcsin(sidec)
    return dec

def eot(dayofyear):
    """ equation of time (hours) :discrepancy between true solar time and local solar time
        Approximation formula by Grebet (1993), in Crop structure and light microclimate
    """
    omega = 0.017202 * (dayofyear - 3.244)
    eclong = ecliptic_longitude(dayofyear)
    tanphi = 0.91747 * numpy.sin(eclong) / numpy.cos(eclong)
    phi = numpy.arctan(tanphi) - omega + 1.3526
    phi = numpy.where((phi + 1) <= 0, numpy.mod(phi + 1 + 1000 * numpy.pi, numpy.pi) - 1, phi)
    return phi * 229.2 / 60
    
    
def solar_time(hUTC, dayofyear, longitude):
    """ Local solar time(hour)
    
        hUTC : universal time (hour)
        longitude is in degrees
    """
    return numpy.mod(hUTC + longitude / 15. - eot(dayofyear), 24)
    
def hour_angle(hUTC, dayofyear, longitude):
    """ Local solar hour angle (radians)   
    """
    return 2 * numpy.pi / 24. * (solar_time(hUTC, dayofyear, longitude) - 12)
    
    
def day_length(latitude, dayofyear):
    """ daylength (hours)"""
    lat = numpy.radians(latitude)
    decli = declination(dayofyear)
    d = numpy.arccos(-numpy.tan(decli) * numpy.tan(lat))
    d = numpy.where(d < 0, d + numpy.pi, d)    
    return 2 * d / numpy.pi * 12

    
def sinh(hUTC, dayofyear, longitude, latitude):
    """ Sine of sun elevation angle (= cosine of the zenith angle)
    """
    lat = numpy.radians(latitude)
    decli = declination(dayofyear)
    omega = hour_angle(hUTC, dayofyear, longitude)
    
    return numpy.sin(latitude) * numpy.sin(decli) + numpy.cos(latitude) * numpy.cos(decli) * numpy.cos(omega)
    
def sun_elevation(hUTC, dayofyear, longitude, latitude):
    """ sun elevation angle (degrees)
    """
    sinel = sinh(hUTC, dayofyear, longitude, latitude)
    
    return numpy.degrees(numpy.arcsin(sinel))

    
def sun_azimuth(hUTC, dayofyear, longitude, latitude, origin='North'):
    """ sun azimuth angle (degrees)
    
        sun azimuth is positive clockwise, starting at orgigin (North or South)
    """
    lat = numpy.radians(latitude)
    decli = declination(dayofyear)
    omega = hour_angle(hUTC, dayofyear, longitude)
    
    D = numpy.sin(lat) * numpy.cos(omega) - numpy.cos(lat) * numpy.sin(decli) / numpy.cos(decli)
    # azimuth counted from south, same sign as hour angle
    az = numpy.where(omega < 0, -1, 1) * numpy.where(D == 0, numpy.pi / 2, numpy.abs(numpy.arctan(numpy.sin(omega) / D)))
    
    if origin == 'North':
        az = az + numpy.pi
    
    return numpy.degrees(az)
    
def sun_extraterrestrial_radiation(dayofyear, method='Spencer'):
    """ Extraterrestrial radiation (W.m2) at the top of the earth atmosphere
    """
    
    if method == 'asce':
        #R. G. Allen, Environmental, and E. Water Resources institute . Task Committee on Standardization of Reference, 
        #The ASCE standardized reference evapotranspiration equation. Reston, Va.: American Society of Civil Engineers, 2005.
        Io = 1367.7 * (1 + 0.033 * numpy.cos(2 * numpy.pi * dayofyear / 365.))
    else:
        # Approx Spencer 1971
        # J. W. Spencer, Fourier series representation of the sun, Search, vol. 2, p. 172, 1971
        x = 2 * numpy.pi * (dayofyear - 1) / 365.
        Io = 1366.1 * (1.00011 \
                       + 0.034221 * numpy.cos(x) + 0.00128 * numpy.sin(x)\
                       - 0.000719 * numpy.cos(2* x) + 0.000077 * numpy.sin(2 * x))                      
    return Io

  
def sun_irradiance(hUTC, dayofyear, longitude, latitude):
    """ sun irradiance (W.m2) at the top of the atmosphere through a plane perpendicular
        to sun direction at a given time and location
    """
    Io = sun_extraterrestrial_radiation(dayofyear)
    sinel = sinh(hUTC, dayofyear, longitude, latitude)
    return Io * sinel
    
def sun_clear_sky_direct_normal_irradiance(hUTC, dayofyear, longitude, latitude):
    """ Direct normal irradiance (W.m2) of the sun reaching the soil on a clear day
        
        Direct normal irradiance means through a plane perpendicular to sun direction
        Atmospheric attenuation is computed using the simple geometric approximation of Meinel (1976)
        
        A. B. Meinel and M. P. Meinel, Applied solar energy. Reading, MA: Addison-Wesley Publishing Co., 1976
    """
    Io = sun_extraterrestrial_radiation(dayofyear)
    sinel = sinh(hUTC, dayofyear, longitude, latitude)
    AM = 1 / sinel
    return Io * sinel * numpy.power(0.7, numpy.power(AM, 0.678))

def horizontal_irradiance(normal_irradiance, elevation):
    """ irradiance measured on an horizontal surface from a source with known elevation (degrees) and known normal irradiance
    """
    return normal_irradiance * numpy.sin(numpy.radians(elevation))
  
def normal_irradiance(horizontal_irradiance, elevation):
    """ irradiance measured on an surface perpendicular to a source with known elevation (degrees) and horizontal irradiance
    """  
    return horizontal_irradiance / numpy.sin(numpy.radians(elevation))    
    
# sky models / equations
    
    
def cie_luminance_gradation(sky_elevation, a, b):
    """ function giving the dependance of the luminance of a sky element to its elevation angle
    
    CIE, 2002, Spatial distribution of daylight CIE standard general sky, CIE standard, CIE Central Bureau, Vienna
    
    elevation : elevation angle of the sky element (rad)
    a, b : coefficient for the type of sky
    """
    z = numpy.pi / 2 - numpy.array(sky_elevation)
    phi_0 = 1 + a * numpy.exp(b)
    phi_z = numpy.where(sky_elevation == 0, 1, 1 + a * numpy.exp(b / numpy.cos(z)))
    return phi_z / phi_0
    
def cie_scattering_indicatrix(sun_azimuth, sun_elevation, sky_azimuth, sky_elevation, c, d, e):
    """ function giving the dependance of the luminance of a sky element to its azimuth distance to the sun
    
    CIE, 2002, Spatial distribution of daylight CIE standard general sky, CIE standard, CIE Central Bureau, Vienna
    
    elevation : elevation angle of the sky element (rad)
    d, e : coefficient for the type of sky
    """
    z = numpy.pi / 2 - numpy.array(sky_elevation)
    zs = numpy.pi / 2 - numpy.array(sun_elevation)
    alpha = numpy.array(sky_azimuth)
    alpha_s = numpy.array(sun_azimuth)
    ksi = numpy.arccos(numpy.cos(zs) * numpy.cos(z) + numpy.sin(zs) * numpy.sin(z) * numpy.cos(numpy.abs(alpha- alpha_s)))
    
    f_ksi = 1 + c * (numpy.exp(d * ksi) - numpy.exp(d * numpy.pi / 2)) + e * numpy.power(numpy.cos(ksi), 2)
    f_zs = 1 + c * (numpy.exp(d * zs) - numpy.exp(d * numpy.pi / 2)) + e * numpy.power(numpy.cos(zs), 2)
    
    return f_ksi / f_zs
    
def cie_relative_luminance(sky_elevation, sky_azimuth=None, sun_elevation=None, sun_azimuth=None, type='soc'):
    """ cie relative luminance of a sky element relative to the luminance at zenith
    
    angle in radians
    type is one of 'soc' (standard overcast sky), 'uoc' (uniform luminance) or 'clear_sky' (standard clear sky low turbidity)
    """
    
    if type == 'clear_sky' and (sun_elevation is None or sun_azimuth is None or sky_azimuth is None):
        raise ValueError, 'Clear sky requires sun position'
    
    if type == 'soc':
        return cie_luminance_gradation(sky_elevation, 4, -0.7)
    elif type == 'uoc':
        return cie_luminance_gradation(sky_elevation, 0, -1)
    elif type == 'clear_sky':
        return cie_luminance_gradation(sky_elevation, -1, -0.32) * cie_scattering_indicatrix(sun_azimuth, sun_elevation, sky_azimuth, sky_elevation, 10, -3, 0.45)
    else:
        raise ValueError, 'Unknown sky type'
    
def diffuse_light_irradiance(sky_elevation, sky_azimuth, sky_fraction, sky_type = 'soc', irradiance = 'horizontal', sun_elevation=None, sun_azimuth=None):
    """ compute normalised diffuse light irradiance (sum(irradiances) = 1) for a sky reprsented by a given set of directions
    
        - elevation, azimuth : elevation and azimuth angle (degrees) of directions sampling the sky hemisphere
        - sky_fraction: relative proportion of sky represented by the directions (or any vector proportinal to these fraction)
        - sky_type : the type of sky (see alinea.astk.sun_and_sky.cie_relative_luminance)
        - irradiance : convention for irradiance. 'normal' returns irradiance normal to the direction of incidence, 
         'horizontal' (default) return the irradiance measured on an horizontal surface
        - sun_elevation, sun_azimuth: sun position (degrees): only needed for clear_sky distribution
    """    
    el = numpy.radians(sky_elevation)
    az = numpy.radians(sky_azimuth)
    sky_fraction = numpy.array(sky_fraction) / numpy.sum(sky_fraction)
    
    if sun_elevation is not None:
        sun_elevation = numpy.radians(sun_elevation)
    if sun_azimuth is not None:
        sun_azimuth = numpy.radians(sun_azimuth)
        
    lum = cie_relative_luminance(el, az, sun_elevation, sun_azimuth, type=sky_type)
    
    if irradiance == 'horizontal':
        lum = lum * numpy.sin(el)
        
    lum = lum * sky_fraction
    
    return lum / sum(lum)
    
def diffuse_fraction(Ghi, hUTC, dayofyear, longitude, latitude, model='Spitters'):
    """ Estimate the diffuse fraction of the global horizontal irradiance (GHI)
        measured at ground level
        
        Estimated after Spitters (1986)
    """
    Io = sun_extraterrestrial_radiation(dayofyear)
    costheta = sinh(hUTC, dayofyear, longitude, latitude)
    So = Io * costheta 
    RsRso = Ghi / So
    R = 0.847 - 1.61 * costheta + 1.04 * costheta * costheta
    K = (1.47 - R) / 1.66
    RdRs = numpy.where(RsRso <= 0.22, 1, 
        numpy.where(RsRso <= 0.35, 1 - 6.4 * (RsRso - 0.22)**2,
        numpy.where(RsRso <= K, 1.47 - 1.66 * RsRso, R)))
    return RdRs
      
  
def sky_discretisation(type='turtle46', nb_az=None, nb_el=None):
    elevations46 = [9.23] * 10 + [10.81] * 5 + [26.57] * 5 + [31.08] * 10 + [47.41] * 5 + [52.62] * 5 + [69.16] * 5 +  [90]
    azimuths46 = [12.23, 59.77, 84.23, 131.77, 156.23, 203.77, 228.23, 275.77, 300.23, 347.77, 36, 108, 180, 252, 324, 0, 72, 144, 216, 288, 23.27, 48.73, 95.27, 120.73,167.27, 192.73, 239.27, 264.73, 311.27, 336.73, 0, 72, 144, 216, 288, 36, 108, 180, 252, 324, 0, 72, 144, 216, 288, 180]
    steradians46 = [0.1355] * 10 + [0.1476] * 5 + [0.1207] * 5 + [0.1375] * 10 + [0.1364] * 5 + [0.1442] * 5 + [0.1378] * 5 + [0.1196]

    return elevations46, azimuths46, steradians46

    
# def RgH (Rg,hTU,DOY,latitude) :
    # """ compute hourly value of Rg at hour hTU for a given day at a given latitude
    # Rg is in J.m-2.day-1
    # latidude in degrees
    # output is J.m-2.h-1
    # """
    
    # dec = DecliSun(DOY)
    # lat = radians(latitude)
    # pi = 3.14116
    # a = sin(lat) * sin(dec)
    # b = cos(lat) * cos(dec)
    # Psi = numpy.pi * Rg / 86400 / (a * acos(-a / b) + b * sqrt(1 - (a / b)^2))
    # A = -b * Psi
    # B = a * Psi
    # RgH = A * cos (2 * pi * hTU / 24) + B
    #Note that this formula works for h beteween hsunset eand hsunrise
    # hsunrise = 12 - 12/pi * acos(-a / b)
    # hsunset = 12 + 12/pi * acos (-a / b)
    # return RgH
     
