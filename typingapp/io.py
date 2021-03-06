
import os
import numpy as np

import ztfidr
from ztfidr import io

# DataBase
DB_PATH = os.path.join(io.IDR_PATH, "typingapp.db")

# DataSource
SAMPLE = ztfidr.get_sample()



# =============== #
#                 #
#  Data For App   #
#                 #
# =============== #
def get_target_lightcurve(name):
    """ the target lightcurve. """
    return SAMPLE.get_target_lightcurve(name)

def get_target_spectra(name):
    """ list of spectra for the given target. """
    return np.atleast_1d( SAMPLE.get_target_spectra(name) )

def get_target_data(name):
    """ values associated for the target (e.g. redshift, stretch, t0 etc). """
    return SAMPLE.data.loc[name]


# =============== #
#                 #
#  Target Data    #
#                 #
# =============== #
def get_input_targetdata():
    """ reads data from the ztfcosmoidr using ztfidr and returns 
    a dataframe """
    data = io.get_targets_data()
    host = io.get_host_data().xs("global", axis=1)[["host_ra","host_dec","host_dlr"]]
    autotyping = io.get_autotyping()

    sndata = data[["ra","dec",
                  "redshift","redshift_err",
                  "redshift_source",
                  "x1","x1_err",
                  "c","c_err",
                  "fitprob", "iau_name"
                 ]]
    
    extra = host.merge(autotyping, left_index=True, 
                       right_index=True, how="outer")
    alldata = sndata.merge(extra, left_index=True, 
                       right_index=True, how="left")
    return alldata.reset_index().rename({"index":"name"}, axis=1
                 ).reset_index().rename({"index":"id"}, axis=1
                 ).rename({"type":"auto_type",
                             "type": "auto_type", 
                             "subtype": "auto_subtype",
                             "p(type)": "auto_type_prob", 
                             "p(subtype|type)": "auto_subtype_prob",
                             "iau_name":"name_iau"
                            }, axis=1)
    data = io.get_targets_data()
    host = io.get_host_data().xs("global", axis=1)[["host_ra","host_dec","host_dlr"]]
    autotyping = io.get_autotyping()

    sndata = data[["ra","dec",
                  "redshift","redshift_err",
                  "redshift_source",
                  "x1","x1_err",
                  "c","c_err",
                  "fitprob", "iau_name"
                 ]]
    extra = host.merge(autotyping, left_index=True, right_index=True, how="outer")
    alldata = sndata.merge(sndata, left_index=True, right_index=True, how="outer")
    return alldata

def build_targets_db():
    """ """
    data = get_input_targetdata()
    
    import sqlite3
    connew = sqlite3.connect(DB_PATH)
    data.to_sql("targets", connew, if_exists="replace")
    
