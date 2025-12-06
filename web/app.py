"""
Flask web application for testing FinBERT sentiment analysis.
Features:
- Test model on custom text
- View model performance metrics
- Download training data and results
- View analysis results
"""
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

# Import main module - this will load the model
# Import as a module so we can access its functions
import importlib
main_module = importlib.import_module('main')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Model is loaded when main.py is imported
# classify_sentiment from main.py uses the global model and tokenizer
model_loaded = True


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/test', methods=['POST'])
def test_sentiment():
    """Test sentiment on provided text."""
    if not model_loaded:
        return jsonify({'error': 'Model not loaded'}), 500
    
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Use classify_sentiment from main.py (uses global model/tokenizer)
        sentiment = main_module.classify_sentiment(text)
        return jsonify({
            'sentiment': sentiment,
            'text': text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/batch-test', methods=['POST'])
def batch_test():
    """Test sentiment on multiple texts."""
    if not model_loaded:
        return jsonify({'error': 'Model not loaded'}), 500
    
    data = request.get_json()
    texts = data.get('texts', [])
    
    if not texts:
        return jsonify({'error': 'No texts provided'}), 400
    
    results = []
    for text in texts:
        try:
            # Use classify_sentiment from main.py (uses global model/tokenizer)
            sentiment = main_module.classify_sentiment(text)
            results.append({
                'text': text,
                'sentiment': sentiment
            })
        except Exception as e:
            results.append({
                'text': text,
                'sentiment': 'error',
                'error': str(e)
            })
    
    return jsonify({'results': results})


@app.route('/api/performance')
def get_performance():
    """Get model performance metrics."""
    try:
        # Load test results if available
        test_results_file = os.path.join(parent_dir, 'test_results.json')
        results = {
            'model_type': 'fine-tuned' if os.path.exists(os.path.join(parent_dir, 'models', 'finbert_finetuned', 'config.json')) else 'base',
            'status': 'loaded' if model_loaded else 'not loaded'
        }
        
        if os.path.exists(test_results_file):
            with open(test_results_file, 'r') as f:
                test_data = json.load(f)
                results.update(test_data)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/training-data')
def get_training_data():
    """Get training data info."""
    try:
        training_data_path = os.path.join(parent_dir, 'data', 'training_data', 'ground_truth', 'finbert_training_data.json')
        if os.path.exists(training_data_path):
            with open(training_data_path, 'r') as f:
                data = json.load(f)
            
            # Count labels
            label_counts = {}
            for item in data:
                label = item.get('label', 'unknown')
                label_counts[label] = label_counts.get(label, 0) + 1
            
            return jsonify({
                'total_examples': len(data),
                'label_distribution': label_counts,
                'sample_size': min(10, len(data))
            })
        else:
            return jsonify({'error': 'Training data not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/training-data')
def download_training_data():
    """Download training data as CSV."""
    try:
        training_data_path = os.path.join(parent_dir, 'data', 'training_data', 'ground_truth', 'all_indicators_ground_truth.csv')
        if os.path.exists(training_data_path):
            return send_file(
                training_data_path,
                mimetype='text/csv',
                as_attachment=True,
                download_name='training_data.csv'
            )
        else:
            return jsonify({'error': 'Training data not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze-file', methods=['POST'])
def analyze_file():
    """Analyze uploaded file and return sentiment results."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            # Try with different encoding
            file.seek(0)
            content = file.read().decode('latin-1')
        
        filename = file.filename
        
        if not content or len(content.strip()) == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        # Import main module functions
        import main
        
        # Try to extract sections first
        try:
            from src.parsing.section_extractor import SectionExtractor
            section_extractor = SectionExtractor()
            sections = section_extractor.extract_sections(content)
        except Exception as e:
            sections = {}
        
        results = {
            'filename': filename,
            'sections': [],
            'total_words': 0
        }
        
        if sections and len(sections) > 0:
            # Analyze each section
            for section_name, section in sections.items():
                try:
                    # Clean the section content
                    from src.parsing.report_cleaner import ReportCleaner
                    cleaner = ReportCleaner(extract_sections_only=True, remove_boilerplate=True)
                    cleaned_content = cleaner.clean_text(section.content)
                    
                    # Truncate if too long
                    if len(cleaned_content) > 3000:
                        cleaned_content = cleaned_content[:3000]
                    
                    if len(cleaned_content.strip()) < 50:
                        continue
                    
                    # Analyze sentiment
                    sentiment = main.classify_sentiment(cleaned_content)
                    word_count = len(cleaned_content.split())
                    
                    results['sections'].append({
                        'name': section_name,
                        'item_number': section.item_number if hasattr(section, 'item_number') else '',
                        'sentiment': sentiment,
                        'word_count': word_count
                    })
                    results['total_words'] += word_count
                except Exception as e:
                    continue
        else:
            # No sections found, analyze as whole document
            try:
                from src.parsing.report_cleaner import ReportCleaner
                cleaner = ReportCleaner(extract_sections_only=True, remove_boilerplate=True)
                cleaned_content = cleaner.clean_text(content)
                
                # Truncate if too long
                if len(cleaned_content) > 3000:
                    cleaned_content = cleaned_content[:3000]
                
                if len(cleaned_content.strip()) < 50:
                    return jsonify({'error': 'File content too short after cleaning'}), 400
                
                sentiment = main.classify_sentiment(cleaned_content)
                word_count = len(cleaned_content.split())
                
                results['sentiment'] = sentiment
                results['word_count'] = word_count
                results['total_words'] = word_count
            except Exception as e:
                # Fallback: analyze raw content
                if len(content.strip()) < 50:
                    return jsonify({'error': 'File content too short'}), 400
                
                # Simple truncation
                analysis_content = content[:3000] if len(content) > 3000 else content
                sentiment = main.classify_sentiment(analysis_content)
                word_count = len(analysis_content.split())
                
                results['sentiment'] = sentiment
                results['word_count'] = word_count
                results['total_words'] = word_count
        
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/results')
def get_results():
    """Get analysis results summary."""
    try:
        results_dir = os.path.join(parent_dir, 'data', 'output')
        if not os.path.exists(results_dir):
            return jsonify({'files': [], 'total': 0})
        
        json_files = [f for f in os.listdir(results_dir) if f.endswith('_sentiment.json')]
        results = []
        
        for filename in sorted(json_files):
            filepath = os.path.join(results_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                results.append({
                    'filename': filename,
                    'source_file': data.get('source_file', ''),
                    'analysis_date': data.get('analysis_date', ''),
                    'sections': len(data.get('sections', [])),
                    'total_words': data.get('total_analyzed_words', 0)
                })
        
        return jsonify({
            'files': results,
            'total': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/results/<filename>')
def get_result_details(filename):
    """Get detailed results for a specific file."""
    try:
        results_dir = os.path.join(parent_dir, 'data', 'output')
        processed_dir = os.path.join(parent_dir, 'data', 'processed', 'sections')
        filepath = os.path.join(results_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Load actual text content from processed sections
        source_file = data.get('source_file', '')
        base_filename = os.path.splitext(source_file)[0] if source_file else os.path.splitext(filename)[0].replace('_sentiment', '')
        
        # For each section, try to load the processed text file
        for section in data.get('sections', []):
            section_name = section.get('name', '')
            # Create filename pattern: base_filename_SectionName.txt
            section_filename = f"{base_filename}_{section_name.replace(' ', '_').replace('&', 'and')}.txt"
            section_filepath = os.path.join(processed_dir, section_filename)
            
            if os.path.exists(section_filepath):
                with open(section_filepath, 'r', encoding='utf-8') as f:
                    section_content = f.read()
                    # Extract just the content part (skip header)
                    if '=' * 80 in section_content:
                        content_parts = section_content.split('=' * 80)
                        if len(content_parts) > 1:
                            section['content'] = content_parts[-1].strip()
                    else:
                        section['content'] = section_content.strip()
            else:
                section['content'] = None
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*80)
    print("Starting FinBERT Web Interface")
    print("="*80)
    print(f"Model loaded: {model_loaded}")
    port = 5001  # Use 5001 to avoid conflict with AirPlay
    print(f"Access the interface at: http://localhost:{port}")
    print("="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)

