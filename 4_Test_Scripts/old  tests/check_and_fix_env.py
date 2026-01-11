#!/usr/bin/env python3
"""
Check and fix .env file parsing issues
"""
import os
from pathlib import Path

def check_and_fix_env():
    """Check .env file and fix common parsing issues"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print(f"❌ .env file not found at: {env_path}")
        return False
    
    print(f"Checking .env file: {env_path}")
    print("=" * 60)
    
    # Read the file
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    issues_found = []
    
    for i, line in enumerate(lines, start=1):
        original_line = line
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            fixed_lines.append(line)
            continue
        
        # Skip comment lines
        if line_stripped.startswith('#'):
            # Ensure comment starts at beginning (no leading spaces before #)
            if line.startswith(' '):
                fixed_line = line_stripped + '\n'
                issues_found.append((i, "Comment had leading spaces", original_line, fixed_line))
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
            continue
        
        # Process key=value lines
        if '=' in line_stripped:
            parts = line_stripped.split('=', 1)
            key = parts[0].strip()
            value = parts[1].strip()
            
            # Fix: Remove spaces around =
            if ' = ' in line_stripped or line_stripped.startswith(' ') or (line_stripped.endswith(' ') and not value.endswith(' ')):
                fixed_line = f"{key}={value}\n"
                if original_line != fixed_line:
                    issues_found.append((i, "Spaces around = or trailing spaces", original_line.rstrip(), fixed_line.rstrip()))
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        else:
            # Line without = and not a comment - might be issue
            if not line_stripped.startswith('#'):
                issues_found.append((i, "Line without = or #", original_line.rstrip(), None))
            fixed_lines.append(line)
    
    # Check for API_FOOTBALL_KEY
    api_key_found = False
    api_key_line = None
    for i, line in enumerate(fixed_lines, start=1):
        if 'API_FOOTBALL_KEY' in line and not line.strip().startswith('#'):
            api_key_found = True
            api_key_line = (i, line.strip())
            break
    
    print(f"\nIssues Found: {len(issues_found)}")
    if issues_found:
        print("\nDetails:")
        for line_num, issue, original, fixed in issues_found:
            print(f"  Line {line_num}: {issue}")
            print(f"    Original: {repr(original)}")
            if fixed:
                print(f"    Fixed:    {repr(fixed)}")
            print()
    
    print(f"\nAPI_FOOTBALL_KEY Status:")
    if api_key_found:
        line_num, line_content = api_key_line
        print(f"  ✓ Found on line {line_num}")
        if '=' in line_content:
            key, value = line_content.split('=', 1)
            value = value.strip()
            if value:
                print(f"  ✓ Value: {value[:10]}...{value[-4:] if len(value) > 14 else value} (length: {len(value)})")
            else:
                print(f"  ⚠ Value is EMPTY")
        else:
            print(f"  ⚠ Line format might be incorrect: {line_content}")
    else:
        print(f"  ❌ API_FOOTBALL_KEY not found in .env file!")
        print(f"  Adding it...")
        # Add API_FOOTBALL_KEY if missing
        fixed_lines.append("API_FOOTBALL_KEY=b41227796150918ad901f64b9bdf3b76\n")
        issues_found.append(("END", "Added missing API_FOOTBALL_KEY", None, "API_FOOTBALL_KEY=b41227796150918ad901f64b9bdf3b76"))
    
    if issues_found:
        print("\n" + "=" * 60)
        print("Creating backup and fixing .env file...")
        print("=" * 60)
        
        # Create backup
        backup_path = env_path.with_suffix('.env.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✓ Backup created: {backup_path}")
        
        # Write fixed file
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print(f"✓ Fixed .env file written")
        print("\n⚠ Please restart your backend server for changes to take effect!")
        return True
    else:
        print("\n✓ No issues found! .env file looks good.")
        return True

if __name__ == '__main__':
    check_and_fix_env()

