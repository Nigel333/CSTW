#!/usr/bin/env python3

def combine_files(file1_path, file2_path, output_path):
    """
    Combines information from two files:
    - File 1: <something2> <word1> <word2>...
    - File 2: <word1> <phoneme1> <phoneme2>...
              <word2> <phoneme1> <phoneme2>...
    
    Args:
        file1_path: Path to first file
        file2_path: Path to second file with word to phoneme mappings
        output_path: Path for output file
    """
    # Read the word-to-phonemes mapping file
    word_to_phonemes = {}
    with open(file2_path, 'r') as f2:
        for line in f2:
            parts = line.strip().split()
            if len(parts) >= 2:
                word = parts[0]
                phonemes = parts[1:]  # All remaining elements are phonemes
                word_to_phonemes[word] = phonemes
    
    # Process the first file and create output
    with open(file1_path, 'r') as f1, open(output_path, 'w') as out:
        for line in f1:
            parts = line.strip().split()
            if len(parts) >= 2:
                something2 = parts[0]
                words = parts[1:]
                
                # Start the output line with something2
                output_line = [something2]
                
                # For each word, add its phonemes if available
                for word in words:
                    if word in word_to_phonemes:
                        output_line.extend(word_to_phonemes[word])
                
                # Write the output line
                out.write(" ".join(output_line) + "\n")
    
    print(f"Output written to {output_path}")

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python script.py file1.txt file2.txt output.txt")
        sys.exit(1)
    
    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    output_path = sys.argv[3]
    
    combine_files(file1_path, file2_path, output_path)
