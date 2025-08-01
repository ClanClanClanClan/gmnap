#!/usr/bin/env python3
"""
Systematic Improvement Framework for Korean Regional Processor
Deterministic way to add new names without introducing regressions
"""
import json
import csv
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import sys

class SystematicImprovementFramework:
    def __init__(self):
        self.base_path = Path(".")
        self.mapping_file = "resources/rr_syllable_map.csv"
        self.results_dir = Path("data/improvement_tracking")
        self.results_dir.mkdir(exist_ok=True)
        
        # Performance thresholds (must maintain these levels)
        self.performance_thresholds = {
            "math_dataset": 94.0,      # Must maintain ≥94% on math dataset
            "diverse_dataset": 96.0,   # Must maintain ≥96% on diverse dataset  
            "independent_dataset": 92.0 # Must maintain ≥92% on independent dataset
        }
    
    def capture_baseline_performance(self):
        """Capture current performance baseline before any changes"""
        print("=== CAPTURING BASELINE PERFORMANCE ===")
        
        baseline = {
            "timestamp": datetime.now().isoformat(),
            "mapping_file_backup": f"baselines/rr_syllable_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "performance": {}
        }
        
        # Create baseline backup
        baseline_dir = Path("baselines")
        baseline_dir.mkdir(exist_ok=True)
        shutil.copy(self.mapping_file, baseline["mapping_file_backup"])
        
        # Test all datasets
        datasets = {
            "math_dataset": "scripts/validate.py",
            "diverse_dataset": "scripts/correct_diverse_evaluation.py", 
            "independent_dataset": "scripts/test_expanded_independent_dataset.py"
        }
        
        for dataset_name, test_script in datasets.items():
            print(f"Testing {dataset_name}...")
            try:
                result = subprocess.run(
                    ["python3", test_script], 
                    capture_output=True, 
                    text=True
                )
                
                # Parse performance from output
                performance = self._parse_performance(result.stdout, dataset_name)
                baseline["performance"][dataset_name] = performance
                
                print(f"  {dataset_name}: {performance['accuracy']:.2f}% ({performance['success']}/{performance['total']})")
                
            except Exception as e:
                print(f"  ERROR testing {dataset_name}: {e}")
                baseline["performance"][dataset_name] = {"error": str(e)}
        
        # Save baseline
        baseline_file = self.results_dir / f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(baseline_file, "w") as f:
            json.dump(baseline, f, indent=2)
        
        print(f"✅ Baseline captured: {baseline_file}")
        return baseline
    
    def add_systematic_mappings(self, category, mappings, rationale=""):
        """Add mappings systematically with full validation"""
        print(f"=== ADDING SYSTEMATIC MAPPINGS: {category} ===")
        print(f"Rationale: {rationale}")
        
        # 1. Capture current baseline
        baseline = self.capture_baseline_performance()
        
        # 2. Backup current mappings
        backup_file = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(self.mapping_file, backup_file)
        print(f"Created backup: {backup_file}")
        
        # 3. Add new mappings
        try:
            self._add_mappings_to_csv(mappings, category)
            print(f"Added {len(mappings)} mappings to {category}")
            
            # 4. Rebuild FSTs
            print("Rebuilding FSTs...")
            subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)
            
            # 5. Validate performance
            print("Validating performance after changes...")
            validation_result = self._validate_all_datasets(baseline)
            
            if validation_result["passed"]:
                print("✅ VALIDATION PASSED - Changes accepted")
                
                # Log successful improvement
                self._log_improvement(category, mappings, rationale, baseline, validation_result)
                
                return True
            else:
                print("❌ VALIDATION FAILED - Rolling back changes")
                
                # Rollback
                shutil.copy(backup_file, self.mapping_file)
                subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)
                
                print("Rollback complete - original performance restored")
                return False
                
        except Exception as e:
            print(f"❌ ERROR during improvement: {e}")
            
            # Emergency rollback
            shutil.copy(backup_file, self.mapping_file)
            subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)
            
            print("Emergency rollback complete")
            return False
    
    def _add_mappings_to_csv(self, mappings, category):
        """Add mappings to CSV file with category tracking"""
        rows = []
        with open(self.mapping_file, "r", encoding="utf8") as f:
            rows = list(csv.reader(f))
        
        # Add new mappings with category comment
        category_comment = f"# {category} - {datetime.now().strftime('%Y-%m-%d')}"
        rows.append([category_comment])
        
        for hangul, roman, weight in mappings:
            rows.append([hangul, roman, weight])
        
        # Write updated file
        with open(self.mapping_file, "w", encoding="utf8", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
    
    def _validate_all_datasets(self, baseline):
        """Validate performance maintains thresholds across all datasets"""
        validation_result = {
            "timestamp": datetime.now().isoformat(),
            "passed": True,
            "results": {},
            "threshold_violations": []
        }
        
        datasets = {
            "math_dataset": "scripts/validate.py",
            "diverse_dataset": "scripts/correct_diverse_evaluation.py",
            "independent_dataset": "scripts/test_expanded_independent_dataset.py"
        }
        
        for dataset_name, test_script in datasets.items():
            try:
                result = subprocess.run(
                    ["python3", test_script],
                    capture_output=True,
                    text=True
                )
                
                performance = self._parse_performance(result.stdout, dataset_name)
                validation_result["results"][dataset_name] = performance
                
                # Check threshold
                threshold = self.performance_thresholds[dataset_name]
                if performance["accuracy"] < threshold:
                    validation_result["passed"] = False
                    validation_result["threshold_violations"].append({
                        "dataset": dataset_name,
                        "required": threshold,
                        "actual": performance["accuracy"],
                        "violation": threshold - performance["accuracy"]
                    })
                
                # Check regression from baseline
                baseline_accuracy = baseline["performance"][dataset_name]["accuracy"]
                regression = baseline_accuracy - performance["accuracy"]
                if regression > 1.0:  # Allow 1% regression tolerance
                    validation_result["passed"] = False
                    validation_result["threshold_violations"].append({
                        "dataset": dataset_name,
                        "type": "regression",
                        "baseline": baseline_accuracy,
                        "actual": performance["accuracy"],
                        "regression": regression
                    })
                
            except Exception as e:
                validation_result["passed"] = False
                validation_result["results"][dataset_name] = {"error": str(e)}
        
        return validation_result
    
    def _parse_performance(self, output, dataset_name):
        """Parse performance metrics from test script output"""
        lines = output.split('\n')
        
        if dataset_name == "math_dataset":
            # Look for "691/733 = 94.27% round‑trip"
            for line in lines:
                if "/" in line and "%" in line and "round" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        fraction = parts[0]  # "691/733"
                        success, total = map(int, fraction.split('/'))
                        accuracy = (success / total) * 100
                        return {"success": success, "total": total, "accuracy": accuracy}
        
        elif dataset_name == "diverse_dataset":
            # Look for "DIVERSE DATASET: 194/200 = 97.00%"
            for line in lines:
                if "DIVERSE DATASET:" in line and "/" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "/" in part:
                            fraction = part
                            success, total = map(int, fraction.split('/'))
                            accuracy = (success / total) * 100
                            return {"success": success, "total": total, "accuracy": accuracy}
        
        elif dataset_name == "independent_dataset":
            # Look for "Overall Performance: 153/165 = 92.73%"
            for line in lines:
                if "Overall Performance:" in line and "/" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "/" in part:
                            fraction = part
                            success, total = map(int, fraction.split('/'))
                            accuracy = (success / total) * 100
                            return {"success": success, "total": total, "accuracy": accuracy}
        
        # Fallback - return error
        return {"error": f"Could not parse performance from {dataset_name}"}
    
    def _log_improvement(self, category, mappings, rationale, baseline, validation_result):
        """Log successful improvement for tracking"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "rationale": rationale,
            "mappings_added": len(mappings),
            "mappings": mappings,
            "baseline_performance": baseline["performance"],
            "final_performance": validation_result["results"],
            "improvement_summary": self._calculate_improvements(baseline, validation_result)
        }
        
        log_file = self.results_dir / f"improvement_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)
        
        print(f"📝 Improvement logged: {log_file}")
    
    def _calculate_improvements(self, baseline, validation_result):
        """Calculate performance changes"""
        improvements = {}
        
        for dataset_name in baseline["performance"]:
            if "error" not in baseline["performance"][dataset_name] and "error" not in validation_result["results"][dataset_name]:
                baseline_acc = baseline["performance"][dataset_name]["accuracy"]
                final_acc = validation_result["results"][dataset_name]["accuracy"]
                improvements[dataset_name] = {
                    "baseline": baseline_acc,
                    "final": final_acc,
                    "change": final_acc - baseline_acc
                }
        
        return improvements

def main():
    """Command line interface for systematic improvements"""
    if len(sys.argv) < 2:
        print("Usage: python3 systematic_improvement_framework.py [command] [args...]")
        print("Commands:")
        print("  baseline                     - Capture current performance baseline")
        print("  add [category] [mappings]    - Add systematic mappings")
        print("  validate                     - Validate current performance")
        return
    
    framework = SystematicImprovementFramework()
    command = sys.argv[1]
    
    if command == "baseline":
        framework.capture_baseline_performance()
    
    elif command == "validate":
        baseline = framework.capture_baseline_performance()  # Acts as validation
    
    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: add [category] - then provide mappings interactively")
            return
        
        category = sys.argv[2]
        print(f"Adding mappings for category: {category}")
        print("Enter mappings in format: hangul,roman,weight")
        print("Enter empty line to finish:")
        
        mappings = []
        while True:
            line = input("> ").strip()
            if not line:
                break
            
            try:
                parts = line.split(',')
                if len(parts) == 3:
                    hangul, roman, weight = parts
                    mappings.append((hangul.strip(), roman.strip(), weight.strip()))
                else:
                    print("Invalid format. Use: hangul,roman,weight")
            except Exception as e:
                print(f"Error parsing: {e}")
        
        if mappings:
            rationale = input("Rationale for these mappings: ").strip()
            success = framework.add_systematic_mappings(category, mappings, rationale)
            
            if success:
                print("✅ Systematic improvement completed successfully!")
            else:
                print("❌ Systematic improvement failed - changes rolled back")
        else:
            print("No mappings provided")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()