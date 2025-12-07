// Tab switching
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
    
    // Load data for specific tabs
    if (tabName === 'performance') {
        loadPerformance();
    } else if (tabName === 'results') {
        loadResults();
    }
}

// Test single sentiment
async function testSentiment() {
    const text = document.getElementById('test-text').value.trim();
    
    if (!text) {
        alert('Please enter some text to analyze');
        return;
    }
    
    const resultDiv = document.getElementById('test-result');
    const displayDiv = document.getElementById('sentiment-display');
    
    resultDiv.style.display = 'block';
    displayDiv.innerHTML = '<div class="loading">Analyzing...</div>';
    
    try {
        const response = await fetch('/api/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const sentimentClass = `sentiment-${data.sentiment}`;
            displayDiv.innerHTML = `
                <div class="sentiment-badge ${sentimentClass}">
                    ${data.sentiment.toUpperCase()}
                </div>
                <p><strong>Text:</strong> ${escapeHtml(data.text)}</p>
            `;
        } else {
            displayDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        }
    } catch (error) {
        displayDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Batch test
async function batchTest() {
    const text = document.getElementById('batch-text').value.trim();
    
    if (!text) {
        alert('Please enter some text to analyze');
        return;
    }
    
    const texts = text.split('\n').filter(t => t.trim());
    
    if (texts.length === 0) {
        alert('Please enter at least one line of text');
        return;
    }
    
    const resultDiv = document.getElementById('batch-result');
    const displayDiv = document.getElementById('batch-display');
    
    resultDiv.style.display = 'block';
    displayDiv.innerHTML = '<div class="loading">Analyzing ' + texts.length + ' texts...</div>';
    
    try {
        const response = await fetch('/api/batch-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ texts: texts })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            let html = '';
            data.results.forEach((result, index) => {
                if (result.error) {
                    html += `
                        <div class="batch-result-item">
                            <div class="text">${escapeHtml(result.text)}</div>
                            <div class="error">Error: ${result.error}</div>
                        </div>
                    `;
                } else {
                    const sentimentClass = `sentiment-${result.sentiment}`;
                    html += `
                        <div class="batch-result-item">
                            <div class="text">${escapeHtml(result.text)}</div>
                            <div class="sentiment-badge ${sentimentClass}">
                                ${result.sentiment.toUpperCase()}
                            </div>
                        </div>
                    `;
                }
            });
            displayDiv.innerHTML = html;
        } else {
            displayDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        }
    } catch (error) {
        displayDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Load performance metrics
async function loadPerformance() {
    const contentDiv = document.getElementById('performance-content');
    contentDiv.innerHTML = '<div class="loading">Loading performance data...</div>';
    
    try {
        const response = await fetch('/api/performance');
        const data = await response.json();
        
            if (response.ok) {
            // Try to load test results
            let html = `
                <div class="performance-stats">
                    <div class="stat-card">
                        <div class="value">${data.accuracy ? data.accuracy.toFixed(2) + '%' : 'N/A'}</div>
                        <div class="label">Overall Accuracy</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">${data.model_type === 'fine-tuned' ? 'Fine-Tuned' : 'Base'}</div>
                        <div class="label">Model Type</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">${data.total_examples || 0}</div>
                        <div class="label">Test Examples</div>
                    </div>
                </div>
            `;
            
            if (data.per_class) {
                html += `
                    <div style="margin-top: 40px;">
                        <h3 style="font-family: var(--font-gramatika); margin-bottom: 20px; color: var(--primary-light); font-size: 1.4em; position: relative; padding-bottom: 15px; font-weight: 600;">
                            Per-Class Performance
                            <span style="position: absolute; bottom: 0; left: 0; width: 60px; height: 2px; background: linear-gradient(90deg, var(--primary-color), transparent);"></span>
                        </h3>
                        <div class="performance-stats">
                            <div class="stat-card">
                                <div class="value">${data.per_class.positive ? data.per_class.positive.accuracy.toFixed(2) + '%' : 'N/A'}</div>
                                <div class="label">Positive Sentiment</div>
                                <div style="margin-top: 10px; font-size: 0.85em; opacity: 0.8;">${data.per_class.positive ? data.per_class.positive.correct + ' correct out of ' + data.per_class.positive.total : 'N/A'}</div>
                            </div>
                            <div class="stat-card">
                                <div class="value">${data.per_class.negative ? data.per_class.negative.accuracy.toFixed(2) + '%' : 'N/A'}</div>
                                <div class="label">Negative Sentiment</div>
                                <div style="margin-top: 10px; font-size: 0.85em; opacity: 0.8;">${data.per_class.negative ? data.per_class.negative.correct + ' correct out of ' + data.per_class.negative.total : 'N/A'}</div>
                            </div>
                            <div class="stat-card">
                                <div class="value">${data.per_class.neutral ? data.per_class.neutral.accuracy.toFixed(2) + '%' : 'N/A'}</div>
                                <div class="label">Neutral Sentiment</div>
                                <div style="margin-top: 10px; font-size: 0.85em; opacity: 0.8;">${data.per_class.neutral ? data.per_class.neutral.correct + ' correct out of ' + data.per_class.neutral.total : 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Training data info
            const trainingResponse = await fetch('/api/training-data');
            if (trainingResponse.ok) {
                const trainingData = await trainingResponse.json();
                html += `
                    <div style="margin-top: 40px; padding: 25px; background: rgba(15, 23, 42, 0.6); border-radius: 12px; border-left: 3px solid var(--primary-color);">
                        <h3 style="font-family: var(--font-gramatika); margin-bottom: 15px; color: var(--primary-light); font-size: 1.3em; position: relative; padding-bottom: 10px; font-weight: 600;">
                            Training Dataset Information
                            <span style="position: absolute; bottom: 0; left: 0; width: 60px; height: 2px; background: linear-gradient(90deg, var(--primary-color), transparent);"></span>
                        </h3>
                        <p style="margin-bottom: 15px; color: #cbd5e1;"><strong>Total Training Examples:</strong> ${trainingData.total_examples || 0}</p>
                        <p style="margin-bottom: 15px; color: #cbd5e1;"><strong>Label Distribution:</strong></p>
                        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                            ${Object.entries(trainingData.label_distribution || {}).map(([label, count]) => 
                                `<div style="padding: 10px 15px; background: rgba(0, 217, 255, 0.1); border-radius: 8px; border: 1px solid rgba(0, 217, 255, 0.2);">
                                    <div style="font-weight: 600; color: var(--primary-color); text-transform: capitalize;">${label}</div>
                                    <div style="font-size: 1.2em; color: var(--primary-light); margin-top: 5px;">${count}</div>
                                </div>`
                            ).join('')}
                        </div>
                    </div>
                `;
            }
            
            contentDiv.innerHTML = html;
        } else {
            contentDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        }
    } catch (error) {
        contentDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Load results
async function loadResults() {
    const contentDiv = document.getElementById('results-content');
    contentDiv.innerHTML = '<div class="loading">Loading results...</div>';
    
    try {
        const response = await fetch('/api/results');
        const data = await response.json();
        
        if (response.ok) {
            if (data.files.length === 0) {
                contentDiv.innerHTML = '<p>No analysis results found. Run analysis first using main.py</p>';
                return;
            }
            
            let html = `<p><strong>Total Files Analyzed:</strong> ${data.total}</p>`;
            html += '<div class="results-list">';
            
            data.files.forEach(file => {
                html += `
                    <div class="result-item" onclick="loadResultDetails('${file.filename}')">
                        <h4>${file.source_file || file.filename}</h4>
                        <div class="meta">
                            Sections: ${file.sections} | 
                            Words: ${file.total_words.toLocaleString()} | 
                            Date: ${file.analysis_date ? new Date(file.analysis_date).toLocaleDateString() : 'N/A'}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            contentDiv.innerHTML = html;
        } else {
            contentDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        }
    } catch (error) {
        contentDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Load result details
async function loadResultDetails(filename) {
    try {
        const response = await fetch(`/api/results/${filename}`);
        const data = await response.json();
        
        if (response.ok) {
            let html = `
                <h3>${data.source_file}</h3>
                <p><strong>Analysis Date:</strong> ${new Date(data.analysis_date).toLocaleString()}</p>
                <p><strong>Total Words Analyzed:</strong> ${data.total_analyzed_words.toLocaleString()}</p>
                <h4 style="margin-top: 20px;">Sections:</h4>
                <div class="results-list">
            `;
            
            data.sections.forEach((section, index) => {
                const sentimentClass = `sentiment-${section.sentiment}`;
                const hasContent = section.content && section.content.length > 0;
                const sectionId = `section-${index}`;
                html += `
                    <div class="result-item section-item" data-section-index="${index}" style="cursor: pointer;">
                        <h4>${section.name} (${section.item_number})</h4>
                        <div class="sentiment-badge ${sentimentClass}">
                            ${section.sentiment.toUpperCase()}
                        </div>
                        <p>Words: ${section.word_count.toLocaleString()}</p>
                        ${hasContent ? `<div id="section-content-${index}" class="section-content" style="display: none;">
                            <h5 style="color: var(--primary-light); margin-bottom: 15px;">Analyzed Text:</h5>
                            <pre style="color: #cbd5e1; white-space: pre-wrap; word-wrap: break-word; font-family: 'Inter', sans-serif; line-height: 1.6; margin: 0;">${escapeHtml(section.content.substring(0, 5000))}${section.content.length > 5000 ? '\n\n... (truncated for display)' : ''}</pre>
                        </div>` : '<p style="color: var(--neutral-color); font-style: italic;">Text content not available</p>'}
                    </div>
                `;
            });
            
            html += '</div>';
            
            // Store sections data globally for toggle function
            window.currentSections = data.sections;
            
            // Show in modal or replace content
            document.getElementById('results-content').innerHTML = `
                <button onclick="loadResults()" class="btn btn-secondary" style="margin-bottom: 20px;">← Back to List</button>
                ${html}
            `;
        }
    } catch (error) {
        alert('Error loading details: ' + error.message);
    }
}

// Toggle section content visibility
function toggleSectionContent(index) {
    const contentDiv = document.getElementById(`section-content-${index}`);
    if (contentDiv) {
        if (contentDiv.style.display === 'none' || !contentDiv.style.display) {
            contentDiv.style.display = 'block';
        } else {
            contentDiv.style.display = 'none';
        }
    }
}

// Add event listeners for section items after they're loaded
document.addEventListener('click', function(e) {
    const sectionItem = e.target.closest('.section-item');
    if (sectionItem) {
        const index = sectionItem.getAttribute('data-section-index');
        if (index !== null) {
            toggleSectionContent(parseInt(index));
        }
    }
});

// Update file input display
function updateFileName(input) {
    const fileText = document.getElementById('file-upload-text');
    if (input.files && input.files[0]) {
        fileText.textContent = input.files[0].name;
    } else {
        fileText.textContent = 'Choose File';
    }
}

// Analyze uploaded file
async function analyzeUploadedFile() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file to analyze');
        return;
    }
    
    // Show loading
    document.getElementById('file-analysis-loading').style.display = 'block';
    document.getElementById('file-analysis-result').style.display = 'none';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/analyze-file', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        document.getElementById('file-analysis-loading').style.display = 'none';
        
        if (response.ok) {
            let html = '';
            
            if (data.sections && data.sections.length > 0) {
                html += `<p style="margin-bottom: 20px; color: #cbd5e1;"><strong>File:</strong> ${data.filename}</p>`;
                html += `<p style="margin-bottom: 20px; color: #cbd5e1;"><strong>Total Words Analyzed:</strong> ${data.total_words.toLocaleString()}</p>`;
                html += '<h4 style="margin-top: 20px; margin-bottom: 15px; color: var(--primary-light);">Sections:</h4>';
                html += '<div class="results-list">';
                
                data.sections.forEach((section, index) => {
                    const sentimentClass = `sentiment-${section.sentiment}`;
                    html += `
                        <div class="result-item">
                            <h4>${section.name || 'Document'}</h4>
                            <div class="sentiment-badge ${sentimentClass}">
                                ${section.sentiment.toUpperCase()}
                            </div>
                            <p>Words: ${section.word_count.toLocaleString()}</p>
                        </div>
                    `;
                });
                
                html += '</div>';
            } else if (data.sentiment) {
                // Single document analysis
                html += `<p style="margin-bottom: 20px; color: #cbd5e1;"><strong>File:</strong> ${data.filename}</p>`;
                html += `<p style="margin-bottom: 20px; color: #cbd5e1;"><strong>Words Analyzed:</strong> ${(data.word_count || data.total_words || 0).toLocaleString()}</p>`;
                const sentimentClass = `sentiment-${data.sentiment}`;
                html += `
                    <div style="text-align: center; margin-top: 20px;">
                        <div class="sentiment-badge ${sentimentClass}" style="display: inline-block;">
                            ${data.sentiment.toUpperCase()}
                        </div>
                    </div>
                `;
            } else {
                html += `<div class="error">No content found in file or analysis failed. Please check the file format.</div>`;
            }
            
            document.getElementById('file-analysis-content').innerHTML = html;
            document.getElementById('file-analysis-result').style.display = 'block';
        } else {
            document.getElementById('file-analysis-content').innerHTML = `<div class="error">Error: ${data.error}</div>`;
            document.getElementById('file-analysis-result').style.display = 'block';
        }
    } catch (error) {
        document.getElementById('file-analysis-loading').style.display = 'none';
        document.getElementById('file-analysis-content').innerHTML = `<div class="error">Error: ${error.message}</div>`;
        document.getElementById('file-analysis-result').style.display = 'block';
    }
}

// Utility function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

