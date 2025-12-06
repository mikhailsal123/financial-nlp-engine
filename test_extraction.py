"""
Comprehensive test script to validate section extraction accuracy.
Tests all files and validates:
- Section boundaries
- Content accuracy
- Word counts
- Section completeness
"""

import os
import sys
from pathlib import Path

sys.path.append('src')
from src.parsing.section_extractor import SectionExtractor
from src.parsing.report_cleaner import ReportCleaner

def count_words(text):
    return len(text.split())

def validate_section_extraction(file_path):
    """Validate extraction for a single file."""
    print(f"\n{'='*80}")
    print(f"Testing: {os.path.basename(file_path)}")
    print('='*80)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    original_word_count = count_words(original_text)
    print(f"Original file: {original_word_count:,} words")
    
    # Extract sections
    extractor = SectionExtractor()
    sections = extractor.extract_sections(original_text)
    
    if not sections:
        print("❌ ERROR: No sections extracted!")
        return False
    
    print(f"\n✅ Extracted {len(sections)} sections:")
    for name in sections.keys():
        print(f"   - {name}")
    
    # Validate each section
    cleaner = ReportCleaner(remove_boilerplate=True)
    total_extracted_words = 0
    issues = []
    
    for section_name, section in sections.items():
        print(f"\n📋 Validating: {section_name}")
        
        # Check section has content
        if not section.content or len(section.content.strip()) < 50:
            issues.append(f"{section_name}: Content too short or empty")
            print(f"   ⚠️  Content too short: {len(section.content)} chars")
            continue
        
        # Check word count
        raw_words = count_words(section.content)
        cleaned_content = cleaner.clean_text(section.content)
        cleaned_words = count_words(cleaned_content)
        
        print(f"   Raw: {raw_words:,} words")
        print(f"   Cleaned: {cleaned_words:,} words")
        
        # Check for common issues
        content_lower = section.content.lower()
        
        # Check if section starts with correct header
        # Note: MD&A may skip header to get to quarterly summary - this is intentional
        if section_name == 'MD&A':
            # Check if it has financial content (quarterly summary, revenue, etc.)
            has_financial = any(phrase in content_lower[:1000] for phrase in [
                'revenue', 'quarter', 'fiscal year', 'net income', 'operating income',
                'data center', 'gaming', 'summary'
            ])
            if not has_financial and 'management' not in content_lower[:500] and 'discussion' not in content_lower[:500]:
                issues.append(f"{section_name}: May not have expected MD&A content")
                print(f"   ⚠️  Warning: Doesn't have expected MD&A/financial keywords")
        
        if section_name == 'Risk Factors':
            if 'risk' not in content_lower[:500] and 'factor' not in content_lower[:500]:
                issues.append(f"{section_name}: May not start with risk content")
                print(f"   ⚠️  Warning: Doesn't start with 'risk' keyword")
        
        # Check for truncated content (ends abruptly)
        if section.content.strip().endswith('...') or len(section.content) < 200:
            issues.append(f"{section_name}: Content may be truncated")
            print(f"   ⚠️  Warning: Content may be truncated")
        
        # Check section boundaries make sense
        if section.start_pos >= section.end_pos:
            issues.append(f"{section_name}: Invalid boundaries (start >= end)")
            print(f"   ❌ ERROR: Invalid boundaries")
        
        total_extracted_words += raw_words
    
    # Summary
    print(f"\n{'='*80}")
    print("EXTRACTION SUMMARY")
    print('='*80)
    print(f"Original words: {original_word_count:,}")
    print(f"Extracted words: {total_extracted_words:,}")
    coverage = (total_extracted_words / original_word_count * 100) if original_word_count > 0 else 0
    print(f"Coverage: {coverage:.1f}%")
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} potential issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ All validations passed!")
        return True

def test_all_files():
    """Test all files in the raw directory."""
    raw_dir = Path('data/raw/earnings_reports')
    
    if not raw_dir.exists():
        print(f"❌ Directory not found: {raw_dir}")
        return
    
    # Find all text files
    files = list(raw_dir.glob('*.txt'))
    
    if not files:
        print(f"❌ No .txt files found in {raw_dir}")
        return
    
    print(f"Found {len(files)} files to test")
    
    results = {}
    for file_path in sorted(files):
        try:
            result = validate_section_extraction(str(file_path))
            results[file_path.name] = result
        except Exception as e:
            print(f"\n❌ ERROR processing {file_path.name}: {e}")
            results[file_path.name] = False
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL TEST SUMMARY")
    print('='*80)
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for filename, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {filename}")
    
    print(f"\nResults: {passed}/{total} files passed")
    
    return passed == total

if __name__ == '__main__':
    test_all_files()

