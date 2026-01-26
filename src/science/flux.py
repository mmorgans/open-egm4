import statistics
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class FluxResult:
    slope: float        # dC/dt (ppm/s)
    intercept: float    # Initial CO2 (ppm)
    r_squared: float    # Coefficient of determination (0-1)
    flux: float         # Calculated flux (gCO2/m2/h or user defined unit)
    valid_points: int   # Number of points used

class FluxCalculator:
    def __init__(self, chamber_volume_liters: float = 1.171, surface_area_cm2: float = 78.5):
        """
        Initialize calculator with SRC-1 dimensions.
        Default: V=1.171 L (1171 cm3), A=78.5 cm2 (10cm diameter)
        """
        self.volume_m3 = chamber_volume_liters / 1000.0
        self.area_m2 = surface_area_cm2 / 10000.0

    def calculate(self, times: List[float], co2_ppm: List[float], temp_c: float = 25.0, pressure_mb: float = 1013.0) -> Optional[FluxResult]:
        """
        Calculate flux using linear regression.
        
        Args:
            times: List of timestamps (seconds from start)
            co2_ppm: List of CO2 concentrations
            temp_c: Air temperature in chamber (Celsius)
            pressure_mb: Atmospheric pressure (millibars/hPa)
            
        Returns:
            FluxResult or None if insufficient data
        """
        if len(times) < 3 or len(times) != len(co2_ppm):
            return None

        # 1. Linear Regression (Least Squares)
        try:
            slope, intercept = statistics.linear_regression(times, co2_ppm)
            
            # Calculate R-squared
            # R2 = 1 - (SS_res / SS_tot)
            # SS_tot = sum((y - mean_y)^2)
            # SS_res = sum((y - (slope*x + intercept))^2)
            
            mean_y = statistics.mean(co2_ppm)
            ss_tot = sum((y - mean_y)**2 for y in co2_ppm)
            
            if ss_tot == 0:
                r_squared = 0.0 if len(set(co2_ppm)) > 1 else 1.0 # Flat line = perfect fit or no variance
            else:
                predicted = [slope * x + intercept for x in times]
                ss_res = sum((y - pred)**2 for y, pred in zip(co2_ppm, predicted))
                r_squared = 1 - (ss_res / ss_tot)

        except statistics.StatisticsError:
            return None

        # 2. Calculate Flux
        # Ideal Gas Law adjustment for molar volume
        # PV = nRT -> n/V = P/RT (moles per cubic meter)
        
        # dC/dt is in ppm/s = (µmol/mol) / s
        # Flux (F) = (dC/dt) * (V/A) * (P / (R * T))
        
        # Constants
        R_GAS = 8.314462  # J / (mol * K)
        temp_k = temp_c + 273.15
        pressure_pa = pressure_mb * 100.0
        
        # Air molar density (mol/m3) = P / (RT)
        molar_density = pressure_pa / (R_GAS * temp_k)
        
        # Slope is ppm/s = 1e-6 mol_CO2/mol_Air / s
        slope_mol = slope * 1e-6 
        
        # Flux in mol_CO2 / m2 / s
        flux_mol_m2_s = slope_mol * molar_density * (self.volume_m3 / self.area_m2)
        
        # Convert to common unit: µmol/m2/s (Instantaneous)
        flux_umol = flux_mol_m2_s * 1e6
        
        # Or gCO2/m2/h (often used in soil respiration)
        # Molar mass CO2 = 44.01 g/mol
        # g/m2/s = flux_mol_m2_s * 44.01
        # g/m2/h = g/m2/s * 3600
        flux_g_h = flux_mol_m2_s * 44.01 * 3600

        return FluxResult(
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            flux=flux_g_h, # Returning g/m2/h as default 'flux'
            valid_points=len(times)
        )
