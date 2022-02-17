
import requests
import numpy as np



PANSTARRS_SOURCE = "http://ps1images.stsci.edu/cgi-bin/"
def get_ps_color_filelocation(ra, dec, color=["y","g","i"], type="stack"):
    """  """
    if len(color) != 3:
        raise ValueError("color must have exactly 3 entries ('g','r','i','z','y')")
        
    pslink = PANSTARRS_SOURCE+ 'ps1filenames.py?ra='+str(ra)+'&dec='+str(dec)+'&type=%s'%type
    d =  [l.split(" ")[-2] for l in requests.get(pslink).content.decode("utf-8").splitlines()[1:]]
    return np.asarray([[d_ for d_ in d if ".%s."%b in d_] for b in color ]).flatten()

def get_rgb_ps_stamp_url(ra, dec, size=240, color=["y","g","i"]):
    """ build the link url where you can download the RGB stamps centered on RA-Dec with a `size`. 
    The RGB color is based on the given color [R,G,B] you set in.
    
    Returns
    -------
    link (str)
    """
    red, blue, green = get_ps_color_filelocation(ra, dec, color=color)
    return PANSTARRS_SOURCE+'fitscut.cgi?red='+red+'&blue='+blue+'&green='+green+'&x='+str(ra)+'&y='+str(dec)+'&size=%d'%size+'&wcs=1&asinh=True&autoscale=99.75&format=png&download=True'
