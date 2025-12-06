"""
Extract and parse SEC filing sections (MD&A, Risk Factors, etc.) for separate analysis.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Section:
    """Represents a section of a SEC filing."""
    name: str
    item_number: str
    content: str
    start_pos: int
    end_pos: int


class SectionExtractor:
    """Extracts structured sections from SEC filings."""
    
    def extract_sections(self, text: str) -> Dict[str, Section]:
        """
        Extract sections by finding Item markers and extracting content until next Item.
        """
        sections = {}
        lines = text.split('\n')
        
        # Find all Item markers with their line numbers
        # Skip table of contents (usually first 50 lines)
        item_markers = []
        for i, line in enumerate(lines):
            # Skip table of contents area (first 50 lines usually)
            if i < 50:
                continue
                
            # Look for "Item X." or "Item XA." patterns
            item_match = re.search(r'Item\s+(\d+[A-Z]?)\s*\.', line, re.IGNORECASE)
            if item_match:
                item_num = item_match.group(1)
                # Check if this line or next few lines contain a section name we care about
                context = ' '.join(lines[i:min(i+3, len(lines))]).lower()
                
                if 'management' in context and 'discussion' in context and 'analysis' in context:
                    item_markers.append((i, 'MD&A', f'Item {item_num}', line))
                elif 'risk' in context and 'factors' in context and i > 100:  # Risk Factors usually later
                    item_markers.append((i, 'Risk Factors', f'Item {item_num}', line))
                elif 'results' in context and 'operations' in context:
                    item_markers.append((i, 'Results of Operations', f'Item {item_num}', line))
                elif 'business' in context and item_num == '1' and i > 50:
                    item_markers.append((i, 'Business Overview', f'Item {item_num}', line))
                elif 'quantitative' in context and 'qualitative' in context and 'market risk' in context:
                    item_markers.append((i, 'Market Risk', f'Item {item_num}', line))
                elif 'legal' in context and 'proceedings' in context:
                    item_markers.append((i, 'Legal Proceedings', f'Item {item_num}', line))
                elif 'controls' in context and 'procedures' in context:
                    item_markers.append((i, 'Controls and Procedures', f'Item {item_num}', line))
                elif 'other information' in context and item_num == '5':
                    item_markers.append((i, 'Other Information', f'Item {item_num}', line))
        
        # Extract content for each section
        # Track used line ranges to prevent overlaps
        used_ranges = []
        
        for idx, (start_line, section_name, item_num, header_line) in enumerate(item_markers):
            # Find end - next Item marker that starts a new section (not just a reference)
            end_line = len(lines)
            
            # Look for next Item X. pattern that's actually a section header
            # Skip references within text (like "Refer to Item 1A" or "Item 7 of our Annual Report")
            current_item_num = item_num.split()[-1]  # Get just the number (e.g., "2" from "Item 2")
            
            for j in range(start_line + 20, len(lines)):  # Skip enough lines to avoid false matches
                line = lines[j].strip()
                # Look for Item at start of line followed by a different number
                if re.match(r'^Item\s+(\d+[A-Z]?)\s*\.', line, re.IGNORECASE):
                    next_item_match = re.match(r'^Item\s+(\d+[A-Z]?)\s*\.', line, re.IGNORECASE)
                    if next_item_match:
                        next_item_num = next_item_match.group(1)
                        # If it's a different item number, check if it's a real section
                        if next_item_num != current_item_num:
                            # For MD&A, ignore Item 1A references (they're just references, not new sections)
                            if section_name == 'MD&A' and next_item_num == '1A':
                                continue
                            
                            # Check next line for section name (real sections have names on next line)
                            if j + 1 < len(lines):
                                next_line = lines[j + 1].lower()
                                # Real section headers have section names, not just references
                                if any(word in next_line for word in ['quantitative', 'controls', 'legal', 'proceedings', 'exhibits', 'signature', 'part ii', 'management', 'risk factors', 'business']):
                                    end_line = j
                                    break
                            # Or if current line has section name
                            if any(word in line.lower() for word in ['quantitative', 'controls', 'legal', 'proceedings', 'exhibits']):
                                end_line = j
                                break
            
            # Also check for next section marker (but only if it's actually after current section)
            if idx + 1 < len(item_markers):
                next_marker_line = item_markers[idx + 1][0]
                # Only use next marker if it's significantly after start (at least 50 lines)
                # This avoids table of contents entries
                if next_marker_line < end_line and next_marker_line > start_line + 50:
                    end_line = next_marker_line
            
            # Check for overlaps with previously extracted sections
            # If this section overlaps, adjust boundaries
            for used_start, used_end in used_ranges:
                if start_line < used_end and end_line > used_start:
                    # Overlap detected - adjust this section's end to start of used section
                    if start_line < used_start:
                        end_line = min(end_line, used_start)
                    else:
                        # This section starts inside another - skip it
                        end_line = start_line
                        break
            
            # Only extract if we have valid boundaries
            if end_line > start_line + 5:
                used_ranges.append((start_line, end_line))
            
            # Skip if boundaries are invalid (overlap was detected)
            if end_line <= start_line + 5:
                continue
            
            # Extract content - skip header line
            section_lines = lines[start_line + 1:end_line]
            
            # For MD&A, skip forward-looking statements and risk sections to get to actual results
            if section_name == 'MD&A':
                # Find where actual financial results discussion starts
                # Search in raw lines (before cleaning) to find quarterly summary
                content_start = 0
                
                # Look for the quarterly summary section (where actual results are discussed)
                # Search through lines to find where quarterly results start
                for j, line in enumerate(section_lines):
                    line_lower = line.lower()
                    
                    # Priority 1: Look for quarterly summary headers (most reliable)
                    # Must have "Summary" to distinguish from "Recent Developments" section
                    if any(phrase in line_lower for phrase in [
                        'third quarter of fiscal year.*summary',
                        'first quarter of fiscal year.*summary',
                        'second quarter of fiscal year.*summary',
                        'fourth quarter of fiscal year.*summary',
                        'quarter of fiscal year summary',
                        'quarter.*summary',  # "Third Quarter Summary"
                    ]):
                        content_start = j
                        break
                    
                    # Priority 2: Look for actual revenue statements with numbers and growth percentages
                    # This is the most reliable - actual results statements
                    if re.search(r'revenue was \$[\d.]+ billion.*up \d+%', line_lower):
                        content_start = j
                        break
                    if re.search(r'revenue was.*up \d+%', line_lower) and '$' in line_lower:
                        content_start = j
                        break
                    
                    # Priority 3: Look for "Revenue was $X billion" (actual results, not risks)
                    if re.search(r'revenue was \$[\d.]+ billion', line_lower):
                        # Make sure it's not in a risk context
                        if 'could' not in line_lower and 'may' not in line_lower and 'risk' not in line_lower:
                            content_start = j
                            break
                
                # If we found quarterly summary, start from there
                if content_start > 0:
                    section_lines = section_lines[content_start:]
                # Otherwise, skip first 30 lines (forward-looking/risk content)
                elif len(section_lines) > 30:
                    section_lines = section_lines[30:]
            
            content = '\n'.join(section_lines)
            
            # Clean up
            content = self._clean_section_content(content, section_name)
            
            if len(content.strip()) > 500:  # Only keep substantial sections
                section = Section(
                    name=section_name,
                    item_number=item_num,
                    content=content,
                    start_pos=start_line,
                    end_pos=end_line
                )
                
                # Handle duplicates (take the longer one)
                if section_name not in sections or len(content) > len(sections[section_name].content):
                    sections[section_name] = section
        
        return sections
    
    def _clean_section_content(self, content: str, section_name: str) -> str:
        """Clean section content by removing excessive whitespace and formatting."""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove common boilerplate phrases at start
        content = re.sub(r'^(This|The following|Refer to|See).*?\.\s*', '', content, flags=re.IGNORECASE)
        # Remove page numbers and references
        content = re.sub(r'\b\d+\s*$', '', content, flags=re.MULTILINE)
        return content.strip()
    
    def split_into_subsections(self, section: Section, max_words: int = 2000) -> List[Section]:
        """
        Split a long section into smaller subsections for better analysis.
        
        Args:
            section: Section to split
            max_words: Maximum words per subsection
            
        Returns:
            List of subsections
        """
        content = section.content
        word_count = len(content.split())
        
        # If section is short enough, return as-is
        if word_count <= max_words:
            return [section]
        
        subsections = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n+', content)
        
        current_subsection = []
        current_words = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            para_words = len(para.split())
            
            # If adding this paragraph would exceed max, start new subsection
            if current_words + para_words > max_words and current_subsection:
                subsection_content = '\n\n'.join(current_subsection)
                subsections.append(Section(
                    name=f"{section.name} (Part {len(subsections) + 1})",
                    item_number=section.item_number,
                    content=subsection_content,
                    start_pos=section.start_pos,
                    end_pos=section.end_pos
                ))
                current_subsection = [para]
                current_words = para_words
            else:
                current_subsection.append(para)
                current_words += para_words
        
        # Add remaining content
        if current_subsection:
            subsection_content = '\n\n'.join(current_subsection)
            subsections.append(Section(
                name=f"{section.name} (Part {len(subsections) + 1})" if len(subsections) > 0 else section.name,
                item_number=section.item_number,
                content=subsection_content,
                start_pos=section.start_pos,
                end_pos=section.end_pos
            ))
        
        return subsections if len(subsections) > 1 else [section]
    
    def get_priority_sections(self) -> List[str]:
        """Return list of sections in priority order for sentiment analysis."""
        return [
            "MD&A",                    # Most important - management's view of results
            "Results of Operations",   # Financial performance discussion
            "Business Overview",      # Company strategy and position (10-K)
            "Risk Factors",           # Required risk disclosures
            "Legal Proceedings",      # Lawsuits/legal issues (can be negative)
            "Market Risk",            # Market-related risks
            "Other Information",      # Material events/updates
            "Controls and Procedures", # Internal controls (usually neutral, negative if issues)
        ]
