import numpy as np
def obtener_max(ancho_banda_canal,snr):

        return round(ancho_banda_canal*np.log2(1+snr),2)
    
