"""
Smart resume functionality for adaptive chunking.
This adds the capability to resume processing from the exact point where a server error occurred.
"""

def process_chunks_with_smart_resume(chunks, output_file, generate_chunk_audio_func, combine_audio_chunks_func, reduce_chunk_limit_func, chunk_text_smartly_func, count_tokens_func):
    """Process chunks with ability to smart resume on server errors."""
    from api_retry_handler import MaxRetriesExceededError, HTTPAPIError
    
    chunk_files = []
    base_name = output_file.replace('.wav', '')
    i = 0
    
    while i < len(chunks):
        chunk = chunks[i]
        chunk_tokens = count_tokens_func(chunk)
        print(f"Processing chunk {i+1}/{len(chunks)} ({chunk_tokens:,} tokens)...")
        
        chunk_output = f"{base_name}_chunk_{i+1:03d}.wav"
        
        try:
            chunk_file = generate_chunk_audio_func(chunk, chunk_output)
            chunk_files.append(chunk_file)
            i += 1  # Move to next chunk
            
        except (MaxRetriesExceededError, HTTPAPIError) as e:
            # Server error detected - check if we should reduce chunk size
            if ("500" in str(e) or "502" in str(e) or "timeout" in str(e).lower()) and reduce_chunk_limit_func():
                print(f"🔧 Server error on chunk {i+1}, splitting with new limit")
                
                # Split the current failing chunk
                import app
                sub_chunks = chunk_text_smartly_func(chunk, max_tokens=app.CURRENT_CHUNK_LIMIT)
                print(f"📦 Split chunk {i+1} into {len(sub_chunks)} sub-chunks")
                
                # Replace current chunk with sub-chunks in the list
                chunks = chunks[:i] + sub_chunks + chunks[i+1:]
                print(f"📋 Updated chunk list: now {len(chunks)} total chunks")
                
                # Continue processing from the first sub-chunk (don't increment i)
                # This ensures we process the sub-chunks with the new limit
                continue
            else:
                # Not a server error or can't reduce further - re-raise
                raise
    
    # Combine all chunk files
    return combine_audio_chunks_func(chunk_files, output_file)