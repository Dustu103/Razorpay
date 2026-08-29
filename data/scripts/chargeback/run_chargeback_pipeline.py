import os
import subprocess
import sys

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED!\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
        sys.exit(res.returncode)
    else:
        print(f"SUCCESS!\n{res.stdout}")

if __name__ == "__main__":
    print("Step 1: Running generate_chargeback_data.py")
    run_cmd([sys.executable, "datasets/scripts/generate_chargeback_data.py"])
    
    print("Step 2: Running clean_chargeback_data.py")
    run_cmd([sys.executable, "datasets/scripts/clean_chargeback_data.py"])
    
    print("Step 3: Running train_chargeback_model.py")
    run_cmd([sys.executable, "datasets/scripts/train_chargeback_model.py"])
    
    print("Pipeline run completed successfully!")
