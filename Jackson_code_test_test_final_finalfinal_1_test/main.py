from transformers import BertTokenizer, BertForSequenceClassification
import torch
import os
import sys
import json
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.parsing.report_cleaner import ReportCleaner
from src.parsing.section_extractor import SectionExtractor

# Load model when script starts
print("Loading FinBERT model...")
tokenizer = BertTokenizer.from_pretrained('ProsusAI/finbert')
model = BertForSequenceClassification.from_pretrained('ProsusAI/finbert')

def classify_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = outputs.logits.argmax(dim=1)
    
    sentiment_labels = list(model.config.id2label.values())
    return sentiment_labels[predictions.item()]

def count_words(text):
    """Count words in text"""
    return len(text.split())

def analyze_text_file(file_path, use_cleaner=True, save_cleaned=True):
    """Analyze sentiment by section (MD&A, Risk Factors, etc.)"""
    with open(file_path, 'r', encoding='utf-8') as file:
        original_text = file.read()
    
    original_word_count = count_words(original_text)
    
    # Extract sections
    section_extractor = SectionExtractor()
    sections = section_extractor.extract_sections(original_text)
    
    if not sections:
        print("⚠️  No sections found. Falling back to document-level analysis...")
        # Fallback to old method
        cleaner = ReportCleaner(extract_sections_only=True, remove_boilerplate=True)
        text = cleaner.clean_text(original_text)
        sentiment = classify_sentiment(text)
        print(f"📊 Document-level sentiment: {sentiment.upper()}")
        return
    
    print(f"\n📋 Found {len(sections)} section(s): {', '.join(sections.keys())}")
    print(f"Original word count: {original_word_count:,} words\n")
    
    # Clean and analyze each section
    cleaner = ReportCleaner(remove_boilerplate=True, extract_sections_only=False)
    section_results = {}
    
    priority_sections = section_extractor.get_priority_sections()
    
    # Track total word count
    total_cleaned_words = 0
    
    for section_name in priority_sections:
        if section_name not in sections:
            continue
        
        section = sections[section_name]
        section_content = section.content
        
        # Split long sections into subsections (max 2000 words each)
        subsections = section_extractor.split_into_subsections(section, max_words=2000)
        
        if len(subsections) > 1:
            print(f"📋 {section_name} split into {len(subsections)} subsections")
        
        # Analyze each subsection
        subsection_sentiments = []
        subsection_word_counts = []
        all_cleaned_content = []  # Store all cleaned content for saving
        
        for subsection in subsections:
            # Clean the subsection (aggressive preprocessing to reduce length)
            cleaned_content = cleaner.clean_text(subsection.content)
            cleaned_word_count = count_words(cleaned_content)
            
            if len(cleaned_content.strip()) < 50:
                continue  # Skip subsections that are too short after cleaning
            
            # For very long subsections, truncate intelligently
            if len(cleaned_content) > 3000:
                # Find last complete sentence before 3000 chars
                truncated = cleaned_content[:3000]
                last_period = max(
                    truncated.rfind('. '),
                    truncated.rfind('.\n'),
                    truncated.rfind('! '),
                    truncated.rfind('? ')
                )
                if last_period > 1500:  # Only truncate if we have substantial content
                    cleaned_content = cleaned_content[:last_period + 1]
                    cleaned_word_count = count_words(cleaned_content)
            
            # Analyze sentiment for this subsection
            sentiment = classify_sentiment(cleaned_content)
            
            subsection_sentiments.append(sentiment)
            subsection_word_counts.append(cleaned_word_count)
            all_cleaned_content.append(cleaned_content)  # Store for saving
            total_cleaned_words += cleaned_word_count
        
        if not subsection_sentiments:
            continue
        
        # Aggregate results (use most common sentiment, or weighted by word count)
        # For now, use the sentiment of the largest subsection
        max_idx = subsection_word_counts.index(max(subsection_word_counts))
        overall_sentiment = subsection_sentiments[max_idx]
        total_words = sum(subsection_word_counts)
        
        section_results[section_name] = {
            'sentiment': overall_sentiment,
            'word_count': total_words,
            'subsections': len(subsections),
            'content': ' '.join(all_cleaned_content),  # Full cleaned content from all subsections
            'item_number': section.item_number
        }
        
        # Display results
        if len(subsections) > 1:
            print(f"📊 {section_name} ({section.item_number}) - {len(subsections)} parts:")
            for i, (sent, wc) in enumerate(zip(subsection_sentiments, subsection_word_counts), 1):
                print(f"   Part {i}: {wc:,} words → {sent.upper()}")
            print(f"   Total: {total_words:,} words, Overall: {overall_sentiment.upper()}")
        else:
            print(f"📊 {section_name} ({section.item_number}):")
            print(f"   Word count: {total_words:,} words")
            print(f"   Sentiment: {overall_sentiment.upper()}")
            print(f"   Preview: {cleaned_content[:150] if 'cleaned_content' in locals() else ''}...")
        print()
    
    # Save cleaned sections to processed/sections directory
    if save_cleaned and section_results:
        # Get base filename
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Create processed/sections directory
        sections_dir = os.path.join('data', 'processed', 'sections')
        os.makedirs(sections_dir, exist_ok=True)
        
        # Save each section as a separate file
        for section_name, results in section_results.items():
            # Create safe filename
            safe_section_name = section_name.replace(' ', '_').replace('&', 'and')
            section_filename = f"{base_filename}_{safe_section_name}.txt"
            section_path = os.path.join(sections_dir, section_filename)
            
            # Save cleaned section content
            with open(section_path, 'w', encoding='utf-8') as f:
                f.write(f"SECTION: {section_name} ({results['item_number']})\n")
                f.write(f"SOURCE: {os.path.basename(file_path)}\n")
                f.write(f"WORD COUNT: {results['word_count']:,} words\n")
                f.write("=" * 80 + "\n\n")
                f.write(results['content'])
            
            print(f"💾 Saved section: {section_filename} ({results['word_count']:,} words)")
    
    # Save sentiment predictions to output directory
    if section_results:
        output_dir = os.path.join('data', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        output_filename = f"{base_filename}_sentiment.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # Prepare output data
        output_data = {
            'source_file': os.path.basename(file_path),
            'analysis_date': datetime.now().isoformat(),
            'original_word_count': original_word_count,
            'total_analyzed_words': sum(r['word_count'] for r in section_results.values()),
            'sections': []
        }
        
        for section_name, results in section_results.items():
            output_data['sections'].append({
                'name': section_name,
                'item_number': results['item_number'],
                'sentiment': results['sentiment'],
                'word_count': results['word_count'],
                'subsections': results['subsections']
            })
        
        # Save JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Also save a human-readable summary
        summary_filename = f"{base_filename}_sentiment_summary.txt"
        summary_path = os.path.join(output_dir, summary_filename)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SENTIMENT ANALYSIS RESULTS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Source File: {os.path.basename(file_path)}\n")
            f.write(f"Analysis Date: {output_data['analysis_date']}\n")
            f.write(f"Original Word Count: {original_word_count:,}\n")
            f.write(f"Total Analyzed: {output_data['total_analyzed_words']:,}\n\n")
            f.write("-" * 80 + "\n")
            f.write("SECTION SENTIMENT SUMMARY\n")
            f.write("-" * 80 + "\n\n")
            
            for section in output_data['sections']:
                subsections_info = f" ({section['subsections']} parts)" if section['subsections'] > 1 else ""
                f.write(f"{section['name']:30s} → {section['sentiment'].upper():10s} ({section['word_count']:,} words{subsections_info})\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        print(f"📊 Saved predictions to: {output_filename}")
        print(f"📄 Saved summary to: {summary_filename}")
    
    # Summary
    print("\n" + "="*80)
    print("SECTION SENTIMENT SUMMARY")
    print("="*80)
    total_analyzed_words = 0
    for section_name, results in section_results.items():
        subsections_info = f" ({results.get('subsections', 1)} parts)" if results.get('subsections', 1) > 1 else ""
        print(f"  {section_name:30s} → {results['sentiment'].upper():10s} ({results['word_count']:,} words{subsections_info})")
        total_analyzed_words += results['word_count']
    print("="*80)
    print(f"Total analyzed: {total_analyzed_words:,} words (from {original_word_count:,} original)")
    if total_analyzed_words > 0:
        reduction_pct = ((1 - total_analyzed_words/original_word_count) * 100)
        print(f"Reduction: {reduction_pct:.1f}% (removed boilerplate/redundant content)")

def main():
    # Analyze individual sentences
    texts = [
        "The company reported strong quarterly earnings growth.",
        "Terrible losses this quarter.",
        "Revenue remained flat compared to last year."
    ]
    
    for text in texts:
        sentiment = classify_sentiment(text)
        print(f"Text: {text}")
        print(f"Sentiment: {sentiment}\n")
    
    # Analyze downloaded 10-Q files
    print("Analyzing downloaded files:")
    earnings_dir = "data/raw/earnings_reports"
    if os.path.exists(earnings_dir):
        txt_files = [f for f in os.listdir(earnings_dir) if f.endswith('.txt')]
        if not txt_files:
            print(f"No .txt files found in {earnings_dir}")
            print("Tip: Use scrap_sec.py to download SEC filings first")
        else:
            print(f"Found {len(txt_files)} file(s) to analyze")
            for filename in txt_files:
                filepath = os.path.join(earnings_dir, filename)
                print(f"\nAnalyzing {filename}:")
                try:
                    analyze_text_file(filepath)
                except Exception as e:
                    print(f"Error analyzing {filename}: {e}")
                    import traceback
                    traceback.print_exc()
    else:
        print(f"Directory {earnings_dir} does not exist")
        print("Tip: Use scrap_sec.py to download SEC filings first")

if __name__ == "__main__":
    main()