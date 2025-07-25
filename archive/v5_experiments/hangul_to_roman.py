#!/usr/bin/env python3
"""Simple Hangul to Roman converter for round-trip testing"""

import csv

class HangulToRoman:
    def __init__(self):
        # Load reverse mapping from RR table
        self.hangul_to_rr = {}
        with open('data/rr_table.csv', 'r', encoding='utf-8') as f:
            for row in csv.reader(f):
                if len(row) == 2:
                    hangul, roman = row[0], row[1]
                    self.hangul_to_rr[hangul] = roman
    
    def convert(self, hangul_text):
        """Convert Hangul text to romanization"""
        result = []
        for char in hangul_text:
            if char in self.hangul_to_rr:
                result.append(self.hangul_to_rr[char])
            else:
                result.append(char)  # Keep non-Hangul as is
        return ''.join(result)

# Global instance
converter = HangulToRoman()

def hangul_to_roman(hangul):
    """Convert Hangul to romanization"""
    return converter.convert(hangul)