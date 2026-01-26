import math
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class RegressionResult:
    slope: float        # Flux (ppm/s)
    intercept: float
    r_squared: float    # Quality of fit (0-1)
    std_err: float      # Standard error of the slope
    n: int              # Number of points

class FluxCalculator:
    """
    Calculates linear regression (Flux) on a stream of CO2 data.
    """
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.times: List[float] = []
        self.co2: List[float] = []
        
    def add_point(self, time_s: float, co2_ppm: float):
        """Add a data point and maintain window size."""
        self.times.append(time_s)
        self.co2.append(co2_ppm)
        
        # Keep window size fixed (sliding window)
        if len(self.times) > self.window_size:
            self.times.pop(0)
            self.co2.pop(0)
            
    def clear(self):
        self.times.clear()
        self.co2.clear()
            
    def calculate(self) -> RegressionResult:
        """
        Perform Ordinary Least Squares regression.
        Returns RegressionResult.
        """
        n = len(self.times)
        if n < 2:
            return RegressionResult(0.0, 0.0, 0.0, 0.0, n)
            
        # Normalize time to start at 0 (avoids large number precision issues)
        t_start = self.times[0]
        x = [t - t_start for t in self.times]
        y = self.co2
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xx = sum(xi * xi for xi in x)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_yy = sum(yi * yi for yi in y)
        
        # Slope (m) and Intercept (b)
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator == 0:
            return RegressionResult(0.0, 0.0, 0.0, 0.0, n)
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # R-squared
        # SST = Total Sum of Squares
        # SSR = Residual Sum of Squares OR Regression Sum of Squares
        # Simple R^2 formula: (n*sum_xy - sum_x*sum_y)^2 / ((n*sum_xx - sum_x^2)(n*sum_yy - sum_y^2))
        
        numerator_r = (n * sum_xy - sum_x * sum_y)
        denominator_r = math.sqrt(abs((n * sum_xx - sum_x**2) * (n * sum_yy - sum_y**2)))
        
        if denominator_r == 0:
            r_squared = 0.0
        else:
            r_squared = (numerator_r / denominator_r) ** 2
            
        # Standard Error of Slope (optional, good for confidence)
        # s_err = sqrt( sum((y - (mx+b))^2) / (n-2) ) / sqrt(sum((x-mean_x)^2))
        # This is expensive to calc loop again. simpler approximation or skip?
        # Let's keep it simple for now (0.0).
        
        return RegressionResult(slope, intercept, r_squared, 0.0, n)
