import sys,re,os
def process(wordTitle,silenced_path, duration):       
    print(f"processing : {wordTitle}")
    wordToSplit = re.split("_",wordTitle)
    space = ""
    wordFile=space.join(wordToSplit)
    wordFile=wordFile.lower()
    match = re.match(r"(\D*)(\d+)([a-zA-Z-0-9]+)", wordTitle)
    word = match.group(1)      
    wordToSplit = re.split("_",word)
    space = " "
    word=space.join(wordToSplit)
    folders = ["segments","text","utt2spk","wav.scp","reco2file_and_channel"]
    print(f"Working on folder: {silenced_path}\n with words: {word}\n")
    # Get all WAV filenames
    with open(f"{silenced_path}corpus","w") as f:
        f.write(f"{word}\n")

    # Write to a text file
    output_text = f"{silenced_path}text"
    with open(output_text,"w") as f:
        file_base = os.path.splitext(wordFile)[0]
        match = re.match(r"(\D*)(\d+)([a-zA-Z-0-9]+)", file_base)
        if match:
            utt_id = match.group(1)
            letter = match.group(2)
            number = match.group(3)
        else:
            print(f"{file_base}")
        f.write(f"{number}{letter}-{utt_id} {word}\n")
    print(f"Text Saved to {output_text}")

    output_file = f"{silenced_path}segments"
    with open(output_file, "w") as f:
        file_base = os.path.splitext(wordFile)[0]
        match = re.match(r"(\D*)(\d+)([a-zA-Z-0-9]+)", file_base)
        utt_id = match.group(1)
        letter = match.group(2)
        number = match.group(3)
        f.write(f"{number}{letter}-{utt_id} {file_base} 0.0 {duration:.4f}\n")
    print(f"Segments saved to {output_file}")

    output_wavs = f"{silenced_path}wav.scp"
    with open(output_wavs,"w") as f:
        file_base = os.path.splitext(wordFile)[0]
        f.write(f"{file_base} /mnt/KINGSTON/CSTW/CSTW/{silenced_path}{wordTitle}.wav\n")
    print(f"WAVscps saved to {output_wavs}")

    output_spks = f"{silenced_path}utt2spk"
    with open(output_spks,"w") as f:
        file_base = os.path.splitext(wordFile)[0]
        match = re.match(r"(\D*)(\d+)([a-zA-Z-0-9]+)", file_base)
        utt_id = match.group(1)
        letter = match.group(2)
        number = match.group(3)
        f.write(f"{number}{letter}-{utt_id} {number}{letter}\n")
    print(f"UTT2SPKs saved to {output_spks}")
    
    output_reco= f"{silenced_path}reco2file_and_channel"
    with open(output_reco,"w") as f:
        file_base = os.path.splitext(wordFile)[0]
        f.write(f"{file_base} {silenced_path} A\n")
            

if __name__ == "__main__":
    print("I AM ON")
    if len(sys.argv) != 4:
        print("Usage: python script.py word path")
        sys.exit(1)
    
    word = sys.argv[1]
    path = sys.argv[2]
    dura = float(sys.argv[3])
    process(word, path, dura)
