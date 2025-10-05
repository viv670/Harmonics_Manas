# Pattern Detection Files - Final Structure

## The 4 Core Pattern Detection Files

### 1. **formed_abcd.py**
- **Function**: `detect_strict_abcd_patterns()`
- **Purpose**: Detects complete FORMED ABCD patterns (4 points: A, B, C, D)
- **Validation**: Strict price containment validation

### 2. **unformed_abcd.py**
- **Function**: `detect_strict_unformed_abcd_patterns()`
- **Purpose**: Detects UNFORMED ABCD patterns (3 points: A, B, C with projected D)
- **Validation**: Strict price containment validation
- **Note**: Self-contained implementation

### 3. **formed_xabcd.py**
- **Function**: `detect_xabcd_patterns()`
- **Purpose**: Detects complete FORMED XABCD patterns (5 points: X, A, B, C, D)
- **Validation**: Basic structure validation (no strict price containment)

### 4. **unformed_xabcd.py**
- **Function**: `detect_strict_unformed_xabcd_patterns()`
- **Purpose**: Detects UNFORMED XABCD patterns (4 points: X, A, B, C with projected D)
- **Validation**: Strict price containment validation

## Supporting Files

- **pattern_ratios_2_Final.py** - Contains all pattern ratio definitions
- **pattern_data_standard.py** - Pattern standardization utilities
- **extremum.py** - Extremum point detection functions

## Usage Example

```python
import pandas as pd
from extremum import detect_extremum_points
from formed_abcd import detect_strict_abcd_patterns
from unformed_abcd import detect_strict_unformed_abcd_patterns
from formed_xabcd import detect_xabcd_patterns
from unformed_xabcd import detect_strict_unformed_xabcd_patterns

# Load data
data = pd.read_csv('price_data.csv')

# Get extremum points
extremum_points = detect_extremum_points(data)

# Detect patterns
formed_abcd = detect_strict_abcd_patterns(extremum_points, data)
unformed_abcd = detect_strict_unformed_abcd_patterns(extremum_points, data)
formed_xabcd = detect_xabcd_patterns(extremum_points)
unformed_xabcd = detect_strict_unformed_xabcd_patterns(extremum_points, data)
```

## File Naming Convention

- **formed_** = Complete patterns with all points formed
- **unformed_** = Patterns with last point (D) projected
- **abcd** = 4-point patterns (A, B, C, D)
- **xabcd** = 5-point patterns (X, A, B, C, D)