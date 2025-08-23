"""
Text processing utilities for audiobook generation.

Handles text chunking, token counting, and text preprocessing
to ensure optimal TTS generation.
"""

import re
from typing import List, Optional, Tuple

try:
    import tiktoken
except ImportError:
    tiktoken = None


# Initialize tokenizer globally
try:
    if tiktoken:
        tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    else:
        tokenizer = None
except Exception:
    # Fallback to a rough estimate if tiktoken fails
    tokenizer = None


def count_tokens(text: str) -> int:
    """
    Count actual tokens in text using tiktoken.
    
    Args:
        text: Input text
        
    Returns:
        int: Number of tokens
    """
    if tokenizer is None:
        # Fallback to rough estimate
        return max(1, len(text) // 4)
    
    try:
        return len(tokenizer.encode(text))
    except Exception:
        # Fallback to rough estimate if encoding fails
        return max(1, len(text) // 4)


def chunk_text_smartly(text: str, max_tokens: int = 30000) -> List[str]:
    """
    Split text into chunks that stay under the token limit, breaking at natural boundaries.
    
    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List[str]: List of text chunks
    """
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first (double newlines)
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # Check if adding this paragraph would exceed the limit
        test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph
        
        if count_tokens(test_chunk) <= max_tokens:
            # Safe to add this paragraph
            current_chunk = test_chunk
        else:
            # Adding this paragraph would exceed limit
            if current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk.strip())
                # Check if single paragraph exceeds limit
                if count_tokens(paragraph) > max_tokens:
                    # Force split oversized paragraph
                    para_chunks = chunk_text_smartly(paragraph, max_tokens)
                    chunks.extend(para_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                # Single paragraph is too large, split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    test_sentence_chunk = temp_chunk + (' ' if temp_chunk else '') + sentence
                    
                    if count_tokens(test_sentence_chunk) <= max_tokens:
                        temp_chunk = test_sentence_chunk
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            # Check if single sentence exceeds limit
                            if count_tokens(sentence) > max_tokens:
                                # Force split oversized sentence
                                sent_chunks = chunk_text_smartly(sentence, max_tokens)
                                chunks.extend(sent_chunks)
                                temp_chunk = ""
                            else:
                                temp_chunk = sentence
                        else:
                            # Single sentence is too large, force split by words
                            words = sentence.split()
                            word_chunk = ""
                            
                            for word in words:
                                test_word_chunk = word_chunk + (' ' if word_chunk else '') + word
                                
                                if count_tokens(test_word_chunk) <= max_tokens:
                                    word_chunk = test_word_chunk
                                else:
                                    if word_chunk:
                                        chunks.append(word_chunk.strip())
                                        word_chunk = word
                                    else:
                                        # Single word is too large - force split by characters
                                        if count_tokens(word) > max_tokens:
                                            # Split oversized word by characters
                                            char_chunk = ""
                                            for char in word:
                                                test_char_chunk = char_chunk + char
                                                if count_tokens(test_char_chunk) <= max_tokens:
                                                    char_chunk = test_char_chunk
                                                else:
                                                    if char_chunk:
                                                        chunks.append(char_chunk)
                                                        char_chunk = char
                                                    else:
                                                        # Single character over limit (impossible with normal text)
                                                        chunks.append(char)
                                            if char_chunk:
                                                word_chunk = char_chunk
                                        else:
                                            word_chunk = word
                            
                            if word_chunk:
                                temp_chunk = word_chunk
                
                if temp_chunk:
                    current_chunk = temp_chunk
    
    # Add the last chunk if it exists with final safety check
    if current_chunk:
        if count_tokens(current_chunk) > max_tokens:
            # Force split if final chunk is still too large
            final_chunks = chunk_text_smartly(current_chunk, max_tokens)
            chunks.extend(final_chunks)
        else:
            chunks.append(current_chunk.strip())
    
    # Final verification pass - guarantee no chunk exceeds limit
    verified_chunks = []
    for chunk in chunks:
        if chunk.strip():
            if count_tokens(chunk) > max_tokens:
                # Emergency character-level splitting
                words = chunk.split()
                char_chunk = ""
                for word in words:
                    test_chunk = char_chunk + (' ' if char_chunk else '') + word
                    if count_tokens(test_chunk) <= max_tokens:
                        char_chunk = test_chunk
                    else:
                        if char_chunk:
                            verified_chunks.append(char_chunk.strip())
                        char_chunk = word
                if char_chunk:
                    verified_chunks.append(char_chunk.strip())
            else:
                verified_chunks.append(chunk.strip())
    
    return verified_chunks


def preprocess_text(text: str) -> str:
    """
    Preprocess text for optimal TTS generation.
    
    Args:
        text: Raw text input
        
    Returns:
        str: Preprocessed text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize line breaks
    text = re.sub(r'\n+', '\n\n', text)
    
    # Clean up quotation marks
    text = re.sub(r'["““”]', '"', text)
    text = re.sub(r"['‘’]", "'", text)
    
    # Ensure proper sentence endings
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def estimate_reading_time(text: str, words_per_minute: int = 150) -> float:
    """
    Estimate reading time for text.
    
    Args:
        text: Input text
        words_per_minute: Average reading speed
        
    Returns:
        float: Estimated reading time in minutes
    """
    word_count = len(text.split())
    return word_count / words_per_minute


def extract_chapters(text: str) -> List[Tuple[str, str]]:
    """
    Extract chapters from a long text based on common chapter markers.
    
    Args:
        text: Input text
        
    Returns:
        List[tuple[str, str]]: List of (chapter_title, chapter_content) tuples
    """
    # Common chapter patterns
    chapter_patterns = [
        r'^\s*Chapter\s+\d+[:\s]*(.*?)$',
        r'^\s*CHAPTER\s+\d+[:\s]*(.*?)$',
        r'^\s*\d+\.\s*(.*?)$',
        r'^\s*Part\s+\d+[:\s]*(.*?)$',
    ]
    
    chapters = []
    current_chapter = ""
    current_title = "Chapter 1"
    chapter_num = 1
    
    lines = text.split('\n')
    
    for line in lines:
        # Check if line matches any chapter pattern
        is_chapter_start = False
        for pattern in chapter_patterns:
            match = re.match(pattern, line, re.IGNORECASE | re.MULTILINE)
            if match:
                # Save previous chapter if it exists
                if current_chapter.strip():
                    chapters.append((current_title, current_chapter.strip()))
                
                # Start new chapter
                chapter_num += 1
                current_title = match.group(0).strip() if match.group(0) else f"Chapter {chapter_num}"
                current_chapter = ""
                is_chapter_start = True
                break
        
        if not is_chapter_start:
            current_chapter += line + '\n'
    
    # Add the last chapter
    if current_chapter.strip():
        chapters.append((current_title, current_chapter.strip()))
    
    # If no chapters were found, return the entire text as one chapter
    if not chapters:
        chapters.append(("Chapter 1", text.strip()))
    
    return chapters


def count_words(text: str) -> int:
    """
    Count words in text.
    
    Args:
        text: Input text
        
    Returns:
        int: Number of words
    """
    return len(text.split())


def validate_text_for_tts(text: str) -> Tuple[bool, List[str]]:
    """
    Validate text for TTS generation and return potential issues.
    
    Args:
        text: Input text
        
    Returns:
        tuple[bool, List[str]]: (is_valid, list_of_issues)
    """
    issues = []
    
    # Check minimum length
    if len(text.strip()) < 10:
        issues.append("Text is too short (minimum 10 characters)")
    
    # Check maximum length (approximate)
    if count_tokens(text) > 100000:
        issues.append("Text is very long and may need chunking")
    
    # Check for excessive special characters
    special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s.,!?;:\'"()-]', text)) / len(text)
    if special_char_ratio > 0.1:
        issues.append("Text contains many special characters that may affect TTS")
    
    # Check for excessive capitalization
    caps_ratio = len(re.findall(r'[A-Z]', text)) / len(text)
    if caps_ratio > 0.3:
        issues.append("Text has excessive capitalization")
    
    # Check for potential encoding issues
    if '' in text:
        issues.append("Text contains encoding errors (replacement characters)")
    
    return len(issues) == 0, issues


class TextProcessor:
    """
    Advanced text processor for audiobook generation.
    """
    
    def __init__(self):
        self.default_chunk_size = 30000
    
    def process_for_audiobook(self, text: str, chunk_size: Optional[int] = None) -> List[str]:
        """
        Process text for audiobook generation.
        
        Args:
            text: Raw input text
            chunk_size: Optional chunk size override
            
        Returns:
            List[str]: Processed text chunks
        """
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        
        # Preprocess the text
        processed_text = preprocess_text(text)
        
        # Validate the text
        is_valid, issues = validate_text_for_tts(processed_text)
        if not is_valid:
            print(f"⚠️ Text validation issues: {', '.join(issues)}")
        
        # Chunk the text
        chunks = chunk_text_smartly(processed_text, chunk_size)
        
        print(f"📊 Text processing complete:")
        print(f"   - Original length: {len(text):,} characters")
        print(f"   - Processed length: {len(processed_text):,} characters")
        print(f"   - Total tokens: {count_tokens(processed_text):,}")
        print(f"   - Number of chunks: {len(chunks)}")
        print(f"   - Average chunk size: {count_tokens(processed_text) // len(chunks):,} tokens")
        
        return chunks
    
    def extract_and_process_chapters(self, text: str) -> List[tuple[str, List[str]]]:
        """
        Extract chapters and process each one.
        
        Args:
            text: Raw input text
            
        Returns:
            List[tuple[str, List[str]]]: List of (chapter_title, processed_chunks)
        """
        chapters = extract_chapters(text)
        processed_chapters = []
        
        for title, content in chapters:
            chunks = self.process_for_audiobook(content)
            processed_chapters.append((title, chunks))
        
        return processed_chapters