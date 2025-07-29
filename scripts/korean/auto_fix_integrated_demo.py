#!/usr/bin/env python3
"""
Integrated demonstration of the auto-fix system showing:
1. Pattern detection from failures
2. Automated fix generation
3. Testing fixes before applying
4. Learning from results
"""

import sys
import pathlib
import tempfile
import shutil
import subprocess

# Add parent directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from auto_fix_system import PatternAnalyzer, FixGenerator, LearningSystem, SafetyChecker


class AutoFixDemo:
    """Demonstrates the complete auto-fix workflow"""
    
    def __init__(self):
        self.analyzer = PatternAnalyzer()
        self.fix_generator = FixGenerator(self.analyzer)
        self.learning = LearningSystem()
        self.safety = SafetyChecker()
        
    def demonstrate_workflow(self):
        """Run complete workflow demonstration"""
        print("=" * 80)
        print("AUTOMATED FIX SYSTEM - COMPLETE WORKFLOW DEMONSTRATION")
        print("=" * 80)
        
        # Example failures from real testing
        known_failures = [
            {
                'name': 'Chun_Baekjin',
                'expected': '천백진',
                'actual': '전백진',
                'type': 'eng→kor',
                'description': 'FST has incorrect mapping for "chun"'
            },
            {
                'name': 'Yom_Ha-Rim',
                'expected': '염하림', 
                'actual': '욤하림',
                'type': 'eng→kor',
                'description': 'Missing mapping for surname "yom"'
            },
            {
                'name': 'Pae_Soonjung',
                'expected': '배순정',
                'actual': '패순정', 
                'type': 'eng→kor',
                'description': 'Incorrect FST mapping for "pae"'
            },
            {
                'name': 'Boo_Kyungmin',
                'expected': '부경민',
                'actual': None,
                'type': 'eng→kor',
                'description': 'No mapping exists for "boo"'
            },
            {
                'name': 'Jee_Sungmin',
                'expected': '지성민',
                'actual': None,
                'type': 'eng→kor',
                'description': 'No mapping exists for "jee"'
            }
        ]
        
        print("\n1. PATTERN ANALYSIS PHASE")
        print("-" * 60)
        print("Analyzing failure patterns to identify root causes...")
        
        analyzed = []
        for failure in known_failures:
            print(f"\n• {failure['name']}: {failure['description']}")
            analysis = self.analyzer.analyze_failure(
                failure['name'],
                failure['expected'],
                failure['actual'],
                failure['type']
            )
            analyzed.append(analysis)
            
            print(f"  Confidence: {analysis['confidence']:.2%}")
            if analysis['suggestions']:
                print(f"  Best suggestion: {analysis['suggestions'][0]['reason']}")
        
        print("\n2. FIX GENERATION PHASE")
        print("-" * 60)
        print("Generating fixes based on pattern analysis...")
        
        fixes = self.fix_generator.generate_fixes(analyzed)
        
        # Group fixes by type
        mapping_fixes = [f for f in fixes if f['type'] == 'add_mapping']
        
        print(f"\nGenerated {len(fixes)} total fixes:")
        print(f"- Mapping additions: {len(mapping_fixes)}")
        
        print("\n3. SAFETY CHECK PHASE")
        print("-" * 60)
        print("Checking if fixes would break existing working names...")
        
        safe_fixes = self.safety.check_safety(fixes)
        
        safe_count = sum(1 for f in safe_fixes if f['safety_score'] >= 0.9)
        risky_count = len(safe_fixes) - safe_count
        
        print(f"\nSafety analysis:")
        print(f"- Safe fixes: {safe_count}")
        print(f"- Potentially risky: {risky_count}")
        
        for fix in safe_fixes:
            if fix['safety_score'] < 0.9:
                print(f"\n⚠️  {fix['romanization']} → {fix['hangul']}")
                print(f"   Risk: {fix.get('warning', 'Unknown risk')}")
        
        print("\n4. TEST SIMULATION PHASE")
        print("-" * 60)
        print("Simulating the effect of applying fixes...")
        
        # Simulate applying fixes
        test_results = self._simulate_fixes(safe_fixes, known_failures)
        
        print(f"\nSimulation results:")
        print(f"- Failures before fixes: {len(known_failures)}")
        print(f"- Failures after fixes: {test_results['remaining_failures']}")
        print(f"- Success rate: {test_results['success_rate']:.1%}")
        
        print("\n5. IMPLEMENTATION OPTIONS")
        print("-" * 60)
        
        print("\nOption A: Quick Override (Immediate)")
        print("Add this to converter.py for immediate effect:")
        print("-" * 40)
        override_code = self.fix_generator.generate_python_override(safe_fixes)
        print(override_code)
        
        print("\nOption B: Permanent Fix (Recommended)")
        print("Commands to update mapping files:")
        print("-" * 40)
        commands = self.fix_generator.generate_fix_commands(safe_fixes)
        for cmd in commands[:5]:
            print(cmd)
        
        print("\n6. LEARNING PHASE")
        print("-" * 60)
        print("Recording successful patterns for future use...")
        
        # Simulate recording successes
        for fix in safe_fixes[:3]:
            if fix['confidence'] > 0.8:
                self.learning.record_correction(
                    fix['romanization'],
                    fix['hangul'],
                    success=True
                )
                print(f"✓ Recorded: {fix['romanization']} → {fix['hangul']}")
        
        print("\n7. CONTINUOUS IMPROVEMENT")
        print("-" * 60)
        print("The system improves over time by:")
        print("• Learning from successful corrections")
        print("• Adjusting confidence scores based on outcomes")
        print("• Building a knowledge base of common patterns")
        print("• Identifying new failure patterns automatically")
        
        print("\n8. SUMMARY")
        print("=" * 80)
        print("The automated fix system provides a systematic approach to:")
        print("✓ Identify patterns in conversion failures")
        print("✓ Generate context-aware fixes")
        print("✓ Test fixes before applying")
        print("✓ Learn from corrections over time")
        print("✓ Maintain safety by checking for conflicts")
        print("\nThis eliminates the need for manual hard-coding of individual cases")
        print("and provides a scalable solution for improving conversion accuracy.")
        
    def _simulate_fixes(self, fixes, original_failures):
        """Simulate applying fixes and test the results"""
        # Create a mapping override dict
        overrides = {}
        for fix in fixes:
            if fix['type'] == 'add_mapping':
                overrides[fix['romanization']] = fix['hangul']
        
        # Test each failure with overrides
        fixed_count = 0
        for failure in original_failures:
            # Extract the problematic romanization
            name_parts = failure['name'].lower().split('_')
            
            # Check if any part would be fixed
            would_be_fixed = any(part in overrides for part in name_parts)
            
            if would_be_fixed:
                fixed_count += 1
        
        return {
            'remaining_failures': len(original_failures) - fixed_count,
            'success_rate': fixed_count / len(original_failures) if original_failures else 0
        }


def main():
    """Run the demonstration"""
    demo = AutoFixDemo()
    demo.demonstrate_workflow()


if __name__ == "__main__":
    main()