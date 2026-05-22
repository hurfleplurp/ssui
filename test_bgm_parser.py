#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from app.main import StyleSwitcherConfigParser

# Path to your StyleSwitcher.ini file
ini_file = "StyleSwitcher.ini"

def test_bgm_parser():
    print(f"Testing StyleSwitcherConfigParser with file: {ini_file}")
    
    if not os.path.exists(ini_file):
        print(f"Error: File {ini_file} not found")
        return
        
    # Create the parser
    parser = StyleSwitcherConfigParser(strict=False)
    
    # Read the file
    print("Reading configuration file...")
    parser.read(ini_file)
    
    # Check if the BGM array was preserved
    if parser.bgm_data:
        print("\nBGM array data found:")
        lines = parser.bgm_data.strip().split("\n")
        print(f"- Array contains {len(lines)} lines")
        print(f"- First line: {lines[0]}")
        if len(lines) > 1:
            print(f"- Last line: {lines[-1]}")
    else:
        print("No BGM array data found in the file")
        
    # Check if SOUND section was parsed
    if 'SOUND' in parser.sections():
        print("\nSOUND section found with keys:")
        for key in parser['SOUND']:
            if key != "BGM[]":
                print(f"- {key} = {parser['SOUND'][key]}")
    else:
        print("No SOUND section found")
        
    # Write to a test file
    test_output = "test_output.ini"
    print(f"\nWriting configuration to {test_output}...")
    with open(test_output, 'w') as f:
        parser.write(f)
    
    print(f"Wrote file successfully. Check {test_output} to verify BGM[] array was preserved.")

if __name__ == "__main__":
    test_bgm_parser()
