#!/usr/bin/env python3
"""Quick test if ephemeris files are working"""
import os
import sys

# Check env
ephe_path = os.environ.get('SE_EPHE_PATH', '/app/ephe')
print(f"SE_EPHE_PATH: {ephe_path}")

# Check files
required_files = ['sepl_18.se1', 'semo_18.se1', 'seas_18.se1', 'seplm06.se1']
for f in required_files:
    path = os.path.join(ephe_path, f)
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    print(f"  {f}: {'✓' if exists else '✗'} ({size} bytes)")

# Try import
try:
    import swisseph as swe
    print(f"\nSwisseph version: {swe.version}")
    
    # Test calculation
    swe.set_ephe_path(ephe_path)
    jd = swe.julday(2024, 1, 1, 12)
    result = swe.calc_ut(jd, swe.SUN)
    print(f"Test calculation: Sun at {result[0][0]:.2f}°")
    print("\n✅ All checks passed!")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
