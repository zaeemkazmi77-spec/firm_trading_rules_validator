"""
Test script to verify the dashboard functionality
"""
import subprocess
import sys
import os

def test_rule_execution():
    """Test that rules can be executed from the app's perspective"""
    
    python_exe = sys.executable
    test_file = "Trades121.csv"
    
    if not os.path.exists(test_file):
        print("❌ Test file not found:", test_file)
        return False
    
    print("Testing rule execution with Python executable:", python_exe)
    print("=" * 80)
    
    # Test Rule 1
    print("\n1. Testing Rule 1 (Hedging Ban)...")
    cmd = [python_exe, "rules/Rule_1.py", test_file, "100000"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0:
        print("   ✅ Rule 1 executed successfully")
        if "PASSED" in result.stdout or "VIOLATED" in result.stdout:
            print("   ✅ Status detected in output")
        else:
            print("   ⚠️ Status not clearly detected")
    else:
        print("   ❌ Rule 1 failed with error:")
        print("   ", result.stderr)
        return False
    
    # Test Rule 13 (with account type)
    print("\n2. Testing Rule 13 (Max Margin)...")
    cmd = [python_exe, "rules/Rule_13.py", test_file, "100000", "Funded Phase"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0:
        print("   ✅ Rule 13 executed successfully")
        if "PASSED" in result.stdout or "VIOLATED" in result.stdout:
            print("   ✅ Status detected in output")
    else:
        print("   ❌ Rule 13 failed with error:")
        print("   ", result.stderr)
        return False
    
    # Test Rule 23 (with account type only)
    print("\n3. Testing Rule 23 (Min Trading Days)...")
    cmd = [python_exe, "rules/Rule_23.py", test_file, "Funded Phase"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0:
        print("   ✅ Rule 23 executed successfully")
        if "PASSED" in result.stdout or "VIOLATED" in result.stdout:
            print("   ✅ Status detected in output")
    else:
        print("   ❌ Rule 23 failed with error:")
        print("   ", result.stderr)
        return False
    
    print("\n" + "=" * 80)
    print("✅ All rule execution tests passed!")
    print("\nThe dashboard should now work correctly.")
    print("Open http://localhost:8501 in your browser and:")
    print("  1. Click 'Load Sample Data' button")
    print("  2. Click 'Analyze Trades' button")
    print("  3. Check the Results tab")
    
    return True


if __name__ == "__main__":
    success = test_rule_execution()
    sys.exit(0 if success else 1)
